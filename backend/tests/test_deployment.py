import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from urllib.error import HTTPError
from urllib.parse import parse_qs, urlsplit

from scripts import deploy


class DeploymentTests(unittest.TestCase):
    def test_root_urls_reject_credentials_lookalikes_and_http(self):
        self.assertEqual(deploy.origin("https://demo.onrender.com/", ".onrender.com"), "https://demo.onrender.com")
        for url in ["http://demo.onrender.com", "https://demo.onrender.com.evil.test",
                    "https://user:secret@demo.onrender.com", "https://demo.onrender.com?key=x",
                    "https://demo.onrender.com/path"]:
            with self.assertRaises(deploy.DeploymentError):
                deploy.origin(url, ".onrender.com")

    def test_hook_targets_exact_tested_commit(self):
        result = deploy.deploy_hook("https://api.render.com/deploy/srv-demo?key=test-secret", "a" * 40)
        self.assertEqual(parse_qs(urlsplit(result).query), {"key": ["test-secret"], "ref": ["a" * 40]})
        for url in ["https://other.test/deploy/srv-demo?key=test-secret",
                    "https://api.render.com/deploy/srv-demo?key=test-secret&imgURL=wrong"]:
            with self.assertRaises(deploy.DeploymentError):
                deploy.deploy_hook(url, "a" * 40)

    def test_request_failure_does_not_disclose_hook_secret(self):
        private_url = "https://api.render.com/deploy/srv-demo?key=test-secret"
        with patch.object(deploy, "build_opener") as opener:
            opener.return_value.open.side_effect = HTTPError(private_url, 401, "test-secret", {}, None)
            with self.assertRaises(deploy.DeploymentError) as error:
                deploy.request_json(private_url, method="POST")
        self.assertEqual(str(error.exception), "Hosting request returned HTTP 401.")

    def test_old_healthy_revision_is_not_ready(self):
        responses = [
            {"status": "ok", "service": "nyayasathi-python-rag", "revision": "old"},
            {"status": "ok", "service": "nyayasathi-python-rag", "revision": "a" * 40},
        ]
        with patch.object(deploy, "request_json", side_effect=responses) as request, patch.object(deploy.time, "sleep"):
            deploy.wait_for_revision("https://demo.onrender.com", "a" * 40)
        self.assertEqual(request.call_count, 2)

    def test_missing_configuration_stops_before_network(self):
        with patch.object(deploy, "request_json") as request:
            with self.assertRaises(deploy.DeploymentError):
                deploy.preflight({})
            request.assert_not_called()

    def test_deployment_stops_if_backend_authentication_is_disabled(self):
        env = {"NYAYA_BACKEND_URL": "https://demo.onrender.com", "GITHUB_SHA": "a" * 40,
               "RENDER_DEPLOY_HOOK_URL": "https://api.render.com/deploy/srv-demo?key=test-secret",
               "NYAYA_BACKEND_TOKEN": "test-token"}
        with patch.object(deploy, "wait_for_revision"), patch.object(deploy, "request_json", return_value={}):
            with self.assertRaisesRegex(deploy.DeploymentError, "Backend API is public"):
                deploy.deploy_render(env)

    def test_worker_configuration_never_contains_backend_token(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "wrangler.json"
            path.write_text(json.dumps({"main": "index.js", "assets": {"directory": "../client"}}))
            deploy.prepare_worker({"NYAYA_BACKEND_URL": "https://demo.onrender.com",
                                   "NYAYA_BACKEND_TOKEN": "test-secret"}, path)
            config = json.loads(path.read_text())
            self.assertTrue(config["workers_dev"])
            self.assertEqual(config["assets"], {"directory": "../client"})
            self.assertNotIn("test-secret", path.read_text())

    def test_public_fallback_is_not_success(self):
        with patch.object(deploy, "request_json", side_effect=[b"NyayaSathi", {
            "backendAvailable": True, "engine": "bge", "aiAvailable": True}, {
                "mode": "guide", "topic": "consumer", "points": [{"text": "fallback"}]}]):
            with self.assertRaises(deploy.DeploymentError):
                deploy.smoke_once({"NYAYA_PUBLIC_URL": "https://demo.account.workers.dev"})

    def test_smoke_does_not_spend_llm_quota(self):
        with patch.object(deploy, "request_json", side_effect=[b"NyayaSathi", {
            "backendAvailable": True, "engine": "bge", "aiAvailable": True}, {
                "mode": "retrieval", "topic": "consumer", "points": [{"text": "retrieved"}]}, {
                "mode": "retrieval", "topic": "speech", "retrieval": {"chunks": [{"factId": "speech-right"}, {"factId": "speech-limits"}]}}]) as request:
            deploy.smoke_once({"NYAYA_PUBLIC_URL": "https://demo.account.workers.dev"})
            posts = [call for call in request.call_args_list if call.kwargs.get('method') == 'POST']
            self.assertEqual(len(posts), 2)
            for call in posts:
                self.assertIs(call.kwargs["body"]["useAI"], False)

    def test_public_speech_regression_blocks_missing_qualifications(self):
        with patch.object(deploy, "request_json", side_effect=[b"NyayaSathi", {
            "backendAvailable": True, "engine": "bge", "aiAvailable": True}, {
                "mode": "retrieval", "topic": "consumer", "points": [{"text": "retrieved"}]}, {
                "mode": "retrieval", "topic": "speech", "retrieval": {"chunks": [{"factId": "speech-right"}]}}]):
            with self.assertRaisesRegex(deploy.DeploymentError, "speech regression"):
                deploy.smoke_once({"NYAYA_PUBLIC_URL": "https://demo.account.workers.dev"})


if __name__ == "__main__":
    unittest.main()
