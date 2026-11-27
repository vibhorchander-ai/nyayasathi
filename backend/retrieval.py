"""CPU embeddings + a local cosine index. No hosted vector database."""
from collections import Counter
import importlib.metadata
import json
import math
import os
import re
from threading import Lock

import numpy as np

from .config import MODEL
from .corpus import load_corpus, make_chunks

STOP = set("a an the is are am was were be been being to for of on in it this that i my me you your can could do does how what which where when why and or with about please have has had get need want help information tell know would should not".split())


def tokens(text):
    return [w for w in re.findall(r"[a-z0-9]+", text.lower()) if len(w) > 1 and w not in STOP]


def unit_rows(matrix):
    lengths = np.linalg.norm(matrix, axis=1, keepdims=True)
    return matrix / np.maximum(lengths, 1e-12)


class LexicalEncoder:
    def __init__(self, documents):
        counts = [Counter(tokens(d)) for d in documents]
        self.vocabulary = {word: i for i, word in enumerate(sorted({w for c in counts for w in c}))}
        self.idf = np.array([math.log((1 + len(counts)) / (1 + sum(w in c for c in counts))) + 1
                             for w in self.vocabulary], dtype=np.float32)

    def encode(self, documents):
        matrix = np.zeros((len(documents), len(self.vocabulary)), dtype=np.float32)
        for row, doc in enumerate(documents):
            for word, count in Counter(tokens(doc)).items():
                if word in self.vocabulary:
                    col = self.vocabulary[word]
                    matrix[row, col] = (1 + math.log(count)) * self.idf[col]
        return unit_rows(matrix)


class Retriever:
    def __init__(self, settings):
        self.settings = settings
        self.catalog, self.corpus_hash = load_corpus(settings.corpus_path)
        self.chunks = make_chunks(self.catalog)
        documents = [c["searchText"] for c in self.chunks]
        self.lexical = LexicalEncoder(documents)
        self.lexical_vectors = self.lexical.encode(documents)
        self.model = None
        self.lock = Lock()
        if settings.engine == "bge":
            # Keep download caches in the ignored project directory.
            os.environ.setdefault("HF_HOME", str(settings.cache_dir / "huggingface"))
            os.environ.setdefault("HF_HUB_DISABLE_TELEMETRY", "1")
            try:
                import onnxruntime
                onnxruntime.disable_telemetry_events()
                from fastembed import TextEmbedding
            except ImportError as exc:
                raise RuntimeError("Install backend/requirements-semantic.txt or set NYAYA_EMBEDDINGS=tfidf") from exc
            self.model = TextEmbedding(model_name=MODEL, cache_dir=str(settings.cache_dir), threads=2)
        self.signature = {
            "schema": 1, "corpusHash": self.corpus_hash, "engine": settings.engine,
            "model": MODEL if self.model else "tfidf-v1",
            "encoderVersion": importlib.metadata.version("fastembed") if self.model else "1",
            "chunkIds": [c["id"] for c in self.chunks],
        }
        settings.index_dir.mkdir(parents=True, exist_ok=True)
        manifest = settings.index_dir / f"{settings.engine}.json"
        vectors_file = settings.index_dir / f"{settings.engine}.npy"
        try:
            if json.loads(manifest.read_text()) != self.signature:
                raise ValueError("Stale index")
            self.vectors = np.load(vectors_file, allow_pickle=False)
            expected_dim = 384 if self.model else len(self.lexical.vocabulary)
            if self.vectors.shape != (len(self.chunks), expected_dim) or not np.isfinite(self.vectors).all():
                raise ValueError("Invalid index shape or values")
        except (OSError, ValueError, EOFError):
            self.vectors = unit_rows(np.array(list(self.model.passage_embed(documents)), dtype=np.float32)) if self.model else self.lexical_vectors
            # Only trusted, locally generated arrays; no pickle deserialization.
            with vectors_file.with_suffix(".tmp").open("wb") as output:
                np.save(output, self.vectors, allow_pickle=False)
            vectors_file.with_suffix(".tmp").replace(vectors_file)
            manifest.write_text(json.dumps(self.signature, indent=2) + "\n")
        (settings.index_dir / "chunks.json").write_text(json.dumps(self.chunks, indent=2) + "\n")

    def search(self, query, limit=4):
        lexical_scores = self.lexical_vectors @ self.lexical.encode([query])[0]
        if self.model:
            with self.lock:
                vector = unit_rows(np.array(list(self.model.query_embed(query)), dtype=np.float32))[0]
            semantic_scores = self.vectors @ vector
            scores = 0.8 * semantic_scores + 0.2 * lexical_scores
        else:
            semantic_scores = np.zeros(len(self.chunks))
            scores = lexical_scores
        order = np.argsort(-scores, kind="stable")[:limit]
        return [{**self.chunks[int(i)], "score": round(float(scores[i]), 4),
                 "semanticScore": round(float(semantic_scores[i]), 4),
                 "lexicalScore": round(float(lexical_scores[i]), 4)} for i in order]
