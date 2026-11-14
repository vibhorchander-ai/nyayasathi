"""Ingest reviewed notes, never unreviewed arbitrary URLs or user uploads."""
from datetime import date
from hashlib import sha256
import json
import re
from urllib.parse import urlparse


def load_corpus(path):
    raw = path.read_bytes()
    catalog = json.loads(raw)
    if catalog.get("schemaVersion") != 1 or catalog.get("jurisdiction") != "India":
        raise ValueError("Unsupported corpus schema or jurisdiction")
    if catalog.get("contentKind") != "reviewed_paraphrases":
        raise ValueError("Corpus must identify its reviewed paraphrases")
    date.fromisoformat(catalog["reviewedOn"])
    sources = catalog["sources"]
    for source_id, source in sources.items():
        url = urlparse(source["url"])
        if source["id"] != source_id or url.scheme != "https" or not (url.hostname or "").endswith(".gov.in"):
            raise ValueError("Sources must use their stable ID and an official HTTPS URL")
        date.fromisoformat(source["reviewedOn"])
    ids = set()
    topic_ids = set()
    for topic in catalog["topics"]:
        if topic["id"] in topic_ids:
            raise ValueError("Duplicate topic ID")
        topic_ids.add(topic["id"])
        for fact in topic["facts"]:
            if fact["id"] in ids or fact["source"] not in sources or not fact["text"].strip():
                raise ValueError("Duplicate fact ID, missing source or empty text")
            ids.add(fact["id"])
    return catalog, sha256(raw).hexdigest()


def split_text(text, size=90, overlap=15):
    """Bound word windows within one note; never mix sources across chunks."""
    if size <= overlap or overlap < 0:
        raise ValueError("Chunk size must exceed overlap")
    words = re.sub(r"\s+", " ", text).strip().split()
    for start in range(0, len(words), size - overlap):
        yield " ".join(words[start:start + size])
        if start + size >= len(words):
            break


def make_chunks(catalog):
    chunks = []
    for topic in catalog["topics"]:
        for fact in topic["facts"]:
            for position, text in enumerate(split_text(fact["text"])):
                chunks.append({
                    "id": f'{fact["id"]}-{position}-{sha256(text.encode()).hexdigest()[:8]}',
                    "factId": fact["id"], "topic": topic["id"], "source": fact["source"],
                    "text": text, "jurisdiction": "India", "kind": "reviewed_paraphrase",
                    "reviewedOn": catalog["sources"][fact["source"]]["reviewedOn"],
                    "searchText": f'{topic["name"]}. {topic["short"]}. {text}',
                })
    return chunks
