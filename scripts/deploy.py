"""Free-demo deployment helpers. Credentials come from CI env, never CLI args.

Run only in GitHub Actions after tests pass. No function upgrades hosting plans.
"""
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener


class DeploymentError(Exception):
    def __init__(self, message, *, http_status=None):
        super().__init__(message)
        self.http_status = http_status


class NoRedirects(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def origin(value, suffix):
    url = urlsplit(value)
    if (url.scheme != "https" or not url.hostname or not url.hostname.endswith(suffix)
            or url.username or url.password or url.port not in (None, 443)
            or url.path not in ("", "/") or url.query or url.fragment):
        raise DeploymentError(f"Use an HTTPS root URL on {suffix}, without credentials or a path.")
    return f"https://{url.netloc}"


def deploy_hook(value, revision):
    url = urlsplit(value)
    query = dict(parse_qsl(url.query))
    if (url.scheme != "https" or url.netloc != "api.render.com"
            or not re.fullmatch(r"/deploy/srv-[A-Za-z0-9]+", url.path)
            or url.fragment or not query.get("key") or set(query) - {"key", "ref"}
            or not re.fullmatch(r"[a-f0-9]{40}", revision)):
        raise DeploymentError("Invalid Render deploy hook or Git commit. Check the private GitHub secret.")
    query["ref"] = revision
    return urlunsplit((url.scheme, url.netloc, url.path, urlencode(query), ""))


def request_json(url, *, method="GET", body=None, token=None, decode_json=True):
    headers = {"Content-Type": "application/json", "User-Agent": "NyayaSathi-deploy"}
    if token:
        headers["Authorization"] = "Bearer " + token
    data = json.dumps(body).encode() if body is not None else (b"" if method == "POST" else None)
    try:
        with build_opener(NoRedirects()).open(Request(url, data=data, headers=headers, method=method), timeout=25) as response:
            content = response.read(200_000)
            return json.loads(content) if decode_json else content
    except HTTPError as exc:
        # HTTP errors can contain the secret deploy-hook URL. Do not print it.
        raise DeploymentError(f"Hosting request returned HTTP {exc.code}.", http_status=exc.code) from None
    except (URLError, TimeoutError, OSError, ValueError):
        raise DeploymentError("Hosting request failed or did not return JSON.") from None


def preflight(env):
    required = ("CLOUDFLARE_API_TOKEN", "CLOUDFLARE_ACCOUNT_ID", "RENDER_DEPLOY_HOOK_URL",
                "NYAYA_BACKEND_TOKEN", "NYAYA_BACKEND_URL", "NYAYA_PUBLIC_URL", "GITHUB_SHA")
    missing = [name for name in required if not env.get(name)]
    if missing:
        raise DeploymentError("Missing GitHub configuration: " + ", ".join(missing))
    origin(env["NYAYA_BACKEND_URL"], ".onrender.com")
    origin(env["NYAYA_PUBLIC_URL"], ".workers.dev")
    deploy_hook(env["RENDER_DEPLOY_HOOK_URL"], env["GITHUB_SHA"])
    if not re.fullmatch(r"[a-f0-9]{32}", env["CLOUDFLARE_ACCOUNT_ID"]):
        raise DeploymentError("CLOUDFLARE_ACCOUNT_ID must be the 32-character account ID.")
    if len(env["NYAYA_BACKEND_TOKEN"]) < 32:
        raise DeploymentError("Copy the generated NYAYA_API_TOKEN from Render as NYAYA_BACKEND_TOKEN.")


def prepare_worker(env, path=Path("dist/server/wrangler.json")):
    backend = origin(env.get("NYAYA_BACKEND_URL", ""), ".onrender.com")
    config = json.loads(path.read_text())
    config.update(name="nyayasathi", workers_dev=True)
    config["vars"] = {**config.get("vars", {}), "NYAYA_BACKEND_URL": backend}
    # The default public demo does not need request logs, D1, R2 or paid bindings.
    config["observability"] = {"enabled": False}
    path.write_text(json.dumps(config, indent=2) + "\n")


def wait_for_revision(base, revision, *, timeout=900):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            health = request_json(base + "/health")
            if (health.get("status") == "ok" and health.get("service") == "nyayasathi-python-rag"
                    and health.get("revision") == revision):
                return
        except DeploymentError:
            pass
        time.sleep(15)
    raise DeploymentError("The new backend commit did not become healthy within 15 minutes. Check Render logs; the web deployment was not started.")


def deploy_render(env):
    base = origin(env["NYAYA_BACKEND_URL"], ".onrender.com")
    hook = deploy_hook(env["RENDER_DEPLOY_HOOK_URL"], env["GITHUB_SHA"])
    request_json(hook, method="POST")
    print("Render accepted the deployment request. Waiting for this commit...", flush=True)
    wait_for_revision(base, env["GITHUB_SHA"])
    try:
        request_json(base + "/api/status")
    except DeploymentError as exc:
        if exc.http_status != 401:
            raise DeploymentError("Could not verify backend token protection.") from None
    else:
        raise DeploymentError("Backend API is public without its token. Set NYAYA_API_TOKEN on Render before deploying the web app.")
    status = request_json(base + "/api/status", token=env["NYAYA_BACKEND_TOKEN"])
    if status.get("backendAvailable") is not True or status.get("engine") != "bge" or status.get("aiAvailable") is not True:
        raise DeploymentError("The new backend is healthy, but BGE/Groq configuration is incomplete.")
    print("The requested backend commit is ready; BGE and Groq configuration are enabled.")


def deploy_cloudflare(env):
    prepare_worker(env)
    # The initial Worker is created first. Until its secret is installed, the
    # authenticated backend rejects proxy requests and the app uses its guide.
    for args, payload in [
        (["deploy", "--config", "dist/server/wrangler.json", "--keep-vars"], None),
        (["secret", "bulk", "--config", "dist/server/wrangler.json"],
         json.dumps({"NYAYA_BACKEND_TOKEN": env["NYAYA_BACKEND_TOKEN"]})),
    ]:
        result = subprocess.run(["pnpm", "exec", "wrangler", *args], input=payload,
                                text=True, capture_output=True, check=False)
        if result.returncode:
            # Do not echo CLI output or stdin containing a deployment credential.
            raise DeploymentError(f"Cloudflare {args[0]} failed. Check account/token permissions and Workers deployment logs.")
    print("Cloudflare Worker and backend secret deployed.")


def smoke_once(env):
    base = origin(env["NYAYA_PUBLIC_URL"], ".workers.dev")
    page = request_json(base + "/", decode_json=False)
    if b"NyayaSathi" not in page:
        raise DeploymentError("The public homepage did not return the NyayaSathi app.")
    status = request_json(base + "/api/status")
    if status.get("backendAvailable") is not True or status.get("engine") != "bge" or status.get("aiAvailable") is not True:
        raise DeploymentError("The public app cannot reach its configured BGE/Groq backend.")
    answer = request_json(base + "/api/chat", method="POST",
                          body={"question": "How do I track my consumer grievance?", "useAI": False})
    if answer.get("mode") != "retrieval" or answer.get("topic") != "consumer" or not answer.get("points"):
        raise DeploymentError("Public retrieval smoke test failed; a guide fallback is not a successful deployment test.")
    print("Public app → authenticated Python → BGE retrieval passed. No Groq quota used by CI.")


def smoke(env):
    for attempt in range(8):
        try:
            smoke_once(env)
            return
        except DeploymentError:
            if attempt == 7:
                raise
            time.sleep(15)


def main():
    commands = {"preflight": preflight, "prepare-worker": prepare_worker,
                "render": deploy_render, "cloudflare": deploy_cloudflare, "smoke": smoke}
    try:
        if len(sys.argv) != 2 or sys.argv[1] not in commands:
            raise DeploymentError("Expected preflight, prepare-worker, render, cloudflare or smoke.")
        commands[sys.argv[1]](os.environ)
    except (DeploymentError, OSError, ValueError, KeyError) as exc:
        print(str(exc) if isinstance(exc, DeploymentError) else "Deployment configuration is invalid or unavailable.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
