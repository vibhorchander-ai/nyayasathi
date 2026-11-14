"""Measure retrieval/routing on a small authored regression set; never calls an LLM."""
import argparse
from dataclasses import replace
import json
from pathlib import Path
import time

from .config import ROOT, Settings
from .rag import Pipeline
from .retrieval import Retriever


def evaluate(pipeline):
    cases = json.loads((ROOT / "backend/eval_cases.json").read_text())
    rows = []
    for case in cases:
        start = time.perf_counter()
        answer = pipeline.retrieve(case["question"], case.get("previousTopic"))
        retrieved = {h["factId"] for h in answer.get("retrieval", {}).get("chunks", [])}
        if answer["topic"] == "emergency":
            retrieved.update(p["id"] for p in answer["points"])
        rows.append({"question": case["question"], "expectedTopic": case["topic"],
                     "actualTopic": answer["topic"], "topicCorrect": case["topic"] == answer["topic"],
                     "expectedFact": case.get("fact"), "factFound": case.get("fact") in retrieved if case.get("fact") else None,
                     "latencyMs": round((time.perf_counter() - start) * 1000, 2)})
    supported = [r for r in rows if r["expectedFact"]]
    unsupported = [r for r in rows if r["expectedTopic"] is None]
    return {"evaluation": "Small authored regression set; not an independent legal-accuracy benchmark.",
            "engine": pipeline.settings.engine, "model": pipeline.retriever.signature["model"],
            "corpusHash": pipeline.retriever.corpus_hash, "chunks": len(pipeline.retriever.chunks),
            "generationEvaluated": False, "cases": len(rows),
            "topicAccuracy": round(sum(r["topicCorrect"] for r in rows) / len(rows), 4),
            "expectedFactRecallAt4": round(sum(r["factFound"] for r in supported) / len(supported), 4),
            "outOfScopeAbstentionRate": round(sum(r["actualTopic"] is None for r in unsupported) / len(unsupported), 4),
            "results": rows}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--engine", choices=["bge", "tfidf"], default="bge")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    settings = replace(Settings.from_env(), engine=args.engine, groq_key="")
    result = evaluate(Pipeline(Retriever(settings), settings))
    output = json.dumps(result, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(output)
    print(json.dumps({k: v for k, v in result.items() if k != "results"}, indent=2))


if __name__ == "__main__":
    main()
