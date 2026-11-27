"""Exercise the real embedding service in CI and leave headroom on Render Free."""
from pathlib import Path
import resource
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from fastapi.testclient import TestClient
from backend.config import Settings
from backend.main import create_app

with tempfile.TemporaryDirectory() as directory:
    settings = Settings(index_dir=Path(directory), engine="bge", groq_key="")
    with TestClient(create_app(settings)) as client:
        for question in ["How do I track my consumer grievance?", "consumer grievance " * 60]:
            response = client.post("/api/chat", json={"question": question, "useAI": False})
            assert response.status_code == 200, f"Memory probe request returned HTTP {response.status_code}"
            assert response.json()["mode"] == "retrieval"
peak = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
peak_mib = peak / (1024 * 1024 if sys.platform == "darwin" else 1024)
print(f"Embedding API smoke-test peak RSS: {peak_mib:.1f} MiB (400 MiB CI guard).")
if peak_mib > 400:
    raise SystemExit("Memory guard exceeded. Reassess the free hosting plan; do not auto-upgrade.")
