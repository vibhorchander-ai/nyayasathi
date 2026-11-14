"""FastAPI application. Run: python -m uvicorn backend.main:app --port 8000"""
from collections import OrderedDict
from contextlib import asynccontextmanager
import hmac
import time

import httpx
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field, field_validator
from starlette.concurrency import run_in_threadpool

from .config import Settings
from .rag import Pipeline, redact
from .retrieval import Retriever


class ChatRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    question: str = Field(min_length=1, max_length=1200)
    previousTopic: str | None = None
    useAI: bool = False

    @field_validator("question")
    @classmethod
    def trim_question(cls, value):
        if not value.strip():
            raise ValueError("A question is required")
        return value.strip()


class BodyLimit:
    def __init__(self, app, limit=6000):
        self.app, self.limit = app, limit

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http" or scope["method"] != "POST":
            return await self.app(scope, receive, send)
        parts, size = [], 0
        while True:
            message = await receive()
            if message["type"] == "http.disconnect":
                return
            size += len(message.get("body", b""))
            if size > self.limit:
                return await JSONResponse({"error": "Request is too large"}, status_code=413)(scope, receive, send)
            parts.append(message)
            if not message.get("more_body", False):
                break
        async def replay():
            return parts.pop(0) if parts else await receive()
        await self.app(scope, replay, send)


class Limiter:
    def __init__(self):
        self.windows = OrderedDict()

    def permit(self, key, now=None):
        now = time.monotonic() if now is None else now
        while self.windows and next(iter(self.windows.values()))[0] <= now:
            self.windows.popitem(last=False)
        until, count = self.windows.get(key, (now + 60, 0))
        if count >= 12 or (key not in self.windows and len(self.windows) >= 5000):
            return False
        self.windows[key] = (until, count + 1)
        return True


def create_app(settings=None, retriever=None, client=None):
    settings = settings or Settings.from_env()

    @asynccontextmanager
    async def lifespan(app):
        index = retriever or await run_in_threadpool(Retriever, settings)
        app.state.pipeline = Pipeline(index, settings)
        app.state.client = client or httpx.AsyncClient(timeout=httpx.Timeout(12.0, connect=4.0), follow_redirects=False)
        yield
        if client is None:
            await app.state.client.aclose()

    app = FastAPI(title="NyayaSathi RAG API", version="0.2.0", lifespan=lifespan)
    app.add_middleware(BodyLimit)
    app.add_middleware(CORSMiddleware, allow_origins=list(settings.allowed_origins),
                       allow_methods=["GET", "POST"], allow_headers=["Content-Type", "Authorization"])
    limiter = Limiter()

    @app.exception_handler(RequestValidationError)
    async def invalid_request(request, exc):
        return JSONResponse({"error": "Use a question of 1–1,200 characters, an optional topic and a boolean useAI."}, status_code=422)

    @app.middleware("http")
    async def protect(request, call_next):
        if request.url.path.startswith("/api/") and request.method != "OPTIONS":
            if settings.api_token and not hmac.compare_digest(request.headers.get("authorization", ""), "Bearer " + settings.api_token):
                return JSONResponse({"error": "Unauthorized"}, status_code=401)
            origin = request.headers.get("origin")
            if origin and origin not in settings.allowed_origins:
                return JSONResponse({"error": "Origin is not allowed"}, status_code=403)
            if request.method == "POST":
                if not request.headers.get("content-type", "").lower().startswith("application/json"):
                    return JSONResponse({"error": "Send JSON"}, status_code=415)
                # Forwarded identity is trusted only behind our authenticated Worker proxy.
                key = request.headers.get("x-nyaya-client", "proxy") if settings.api_token else (request.client.host if request.client else "local")
                if not limiter.permit(key[:100]):
                    return JSONResponse({"error": "Please wait a minute before asking again."}, status_code=429)
        response = await call_next(request)
        response.headers["Cache-Control"] = "no-store"
        response.headers["X-Content-Type-Options"] = "nosniff"
        return response

    @app.get("/health")
    async def health():
        return {"status": "ok", "service": "nyayasathi-python-rag"}

    @app.get("/api/status")
    async def status():
        p = app.state.pipeline
        return {"aiAvailable": bool(settings.groq_key) and settings.daily_ai_limit > 0,
                "backendAvailable": True, "engine": settings.engine, "model": p.retriever.signature["model"],
                "chunks": len(p.retriever.chunks), "coverage": 5, "reviewedOn": p.catalog["reviewedOn"]}

    @app.post("/api/chat")
    async def chat(body: ChatRequest):
        p = app.state.pipeline
        # ONNX/NumPy work runs outside the event loop; provider I/O stays asynchronous.
        safe_question = redact(body.question)
        result = await run_in_threadpool(p.retrieve, safe_question, body.previousTopic)
        # Reuse the retrieval result instead of embedding twice.
        return await p.finish(body, safe_question, result, app.state.client)

    return app


app = create_app()
