# Retrieval evaluation

These results measure the current 16-note corpus on **29 authored regression questions**. The questions cover supported topics, short follow-ups, unrelated questions, foreign jurisdictions and selected unsupported legal requests. This is a development set: thresholds and guards were adjusted during testing. It is not a held-out benchmark, evidence of general legal accuracy or a substitute for legal expert review.

| Measure | BGE + TF-IDF | TF-IDF only |
| --- | --- | --- |
| Expected topic / abstention | 29/29 | 25/29 |
| Expected fact in the four returned notes (supported cases) | 18/18 | 14/18 |
| Abstention on out-of-scope cases | 11/11 | 11/11 |

The default BGE mode handles the paraphrased broken-appliance complaint in this set. The lighter TF-IDF mode misses that paraphrase and misroutes three overlapping legal-aid/helpline questions. It is an explicit low-resource option with lower measured performance, not an equivalent semantic model.

Reproduce from the repository root with the environment activated:

```sh
python -m backend.evaluate --engine bge --output docs/evaluation-bge.json
python -m backend.evaluate --engine tfidf --output docs/evaluation-tfidf.json
```

The [BGE report](evaluation-bge.json) and [TF-IDF report](evaluation-tfidf.json) include each question, expected/actual topic, expected-fact presence, corpus fingerprint and query latency. Timing excludes model download/startup and varies by computer. Emergency cases use direct signposting rather than vector retrieval; the expected-fact metric therefore includes this safety route. Generation is disabled throughout this evaluation.

## Other verification

- 16 Python tests when `NYAYA_TEST_SEMANTIC=1`: ingestion/provenance, real BGE retrieval, index invalidation, abstention, follow-ups, LLM consent/caps, redaction, provider failure, fabricated citations/quotes and API input/origin/token limits.
- 23 JavaScript tests: existing guide behavior plus Python proxy handling, status, token isolation and explicit failure fallback.
- Type checking, lint and production web build.
- Browser check of the real React → Worker → Python → BGE flow and expandable evidence.

No live Groq account was available. Tests validate prompt/context construction and successful/error response handling with a mocked provider; they do not measure the real model’s factual accuracy or latency. Matching citation IDs and quotes cannot establish that a generated claim is legally correct or logically supported. Before public use, add an independent, larger evaluation set, expert review, state/date-specific coverage checks and live-provider evaluation.
