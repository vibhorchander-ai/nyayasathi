"""Run from the repository root: python -m backend.ingest [--engine bge|tfidf]."""
import argparse
from dataclasses import replace
import json

from .config import Settings
from .retrieval import Retriever


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--engine", choices=["bge", "tfidf"])
    args = parser.parse_args()
    settings = Settings.from_env()
    if args.engine:
        settings = replace(settings, engine=args.engine)
    index = Retriever(settings)
    print(json.dumps({"engine": settings.engine, "model": index.signature["model"],
                      "chunks": len(index.chunks), "dimensions": index.vectors.shape[1],
                      "corpusHash": index.corpus_hash, "indexDirectory": str(settings.index_dir)}, indent=2))


if __name__ == "__main__":
    main()
