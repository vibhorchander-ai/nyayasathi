from dataclasses import dataclass
from pathlib import Path
import os

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
MODEL = "BAAI/bge-small-en-v1.5"


@dataclass(frozen=True)
class Settings:
    corpus_path: Path = ROOT / "data/knowledge.json"
    index_dir: Path = ROOT / "backend/.index"
    cache_dir: Path = ROOT / "backend/.cache"
    engine: str = "bge"
    groq_key: str = ""
    groq_model: str = "openai/gpt-oss-20b"
    api_token: str = ""
    allowed_origins: tuple[str, ...] = ("http://localhost:5173", "http://127.0.0.1:5173")
    daily_ai_limit: int = 100

    @classmethod
    def from_env(cls):
        load_dotenv(ROOT / "backend/.env", override=False)
        engine = os.getenv("NYAYA_EMBEDDINGS", "bge")
        if engine not in {"bge", "tfidf"}:
            raise ValueError("NYAYA_EMBEDDINGS must be bge or tfidf")
        return cls(
            engine=engine,
            groq_key=os.getenv("GROQ_API_KEY", ""),
            groq_model=os.getenv("GROQ_MODEL", "openai/gpt-oss-20b"),
            api_token=os.getenv("NYAYA_API_TOKEN", ""),
            allowed_origins=tuple(x.strip() for x in os.getenv(
                "NYAYA_ALLOWED_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173"
            ).split(",") if x.strip()),
            daily_ai_limit=max(0, int(os.getenv("NYAYA_DAILY_AI_LIMIT", "100"))),
        )
