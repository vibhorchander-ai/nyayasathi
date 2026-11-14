# Retrieval evaluation

These results measure the current 23-note corpus on **64 authored regression questions**. The questions cover supported topics, short follow-ups, unrelated questions, foreign jurisdictions and selected unsupported legal requests. This is a development set: thresholds and guards were adjusted during testing. It is not a held-out benchmark, evidence of general legal accuracy or a substitute for legal expert review.

| Measure | BGE + TF-IDF | TF-IDF only |
| --- | --- | --- |
| Expected topic / abstention | 64/64 | 58/64 |
| Expected fact in the four returned notes (supported cases) | 41/41 | 35/41 |
| Abstention on out-of-scope cases | 23/23 | 23/23 |

The default BGE mode handles the paraphrased broken-appliance complaint in this set. The lighter TF-IDF mode misses that paraphrase and misses or misroutes five other questions involving overlapping assistance topics and constitutional paraphrases. It is an explicit low-resource option with lower measured performance, not an equivalent semantic model.

Reproduce from the repository root with the environment activated:

```sh
python -m backend.evaluate --engine bge --output docs/evaluation-bge.json
python -m backend.evaluate --engine tfidf --output docs/evaluation-tfidf.json
```

The [BGE report](evaluation-bge.json) and [TF-IDF report](evaluation-tfidf.json) include each question, expected/actual topic, expected-fact presence, corpus fingerprint and query latency. Timing excludes model download/startup and varies by computer. Emergency cases use direct signposting rather than vector retrieval; the expected-fact metric therefore includes this safety route. Generation is disabled throughout this evaluation.

## Other verification

- 34 Python tests when `NYAYA_TEST_SEMANTIC=1`: ingestion/provenance, real BGE retrieval, index invalidation, abstention, follow-ups, LLM consent/caps, redaction, provider failure, fabricated citations/quotes and API input/origin/token limits.
- 33 JavaScript tests: existing guide behavior plus Python proxy handling, status, token isolation and explicit failure fallback.
- Type checking, lint and production web build.
- Browser check of the real React → Worker → Python → BGE flow and expandable evidence.

A live Groq Free-tier request for “what is a right to speech?” was verified locally on 14 November 2026: it returned `rag`, with separate claims about Article 19(1)(a) and Article 19(2) and validated references to both retrieved notes. Automated tests use a mocked provider and do not consume Groq quota. One live request is a smoke check, not an evaluation of model factual accuracy or latency. Matching citation IDs and quotes cannot establish that a generated claim is legally correct or logically supported. Before public use, add an independent, larger evaluation set, expert review, state/date-specific coverage checks and live-provider evaluation.

## Speech regression and expanded coverage

The 64 cases include the exact reported question, speech/expression paraphrases, citizen and restriction qualifications, Articles 14/21/21A/32, unrelated uses of “right”, unsupported rights, unknown article clauses, foreign jurisdictions and topic changes after RTI. CI asserts all expected BGE routes and supporting facts; an incorrect result fails the job, rather than merely printing a report. A separate test removes all constitutional notes and verifies that the original speech question abstains instead of becoming an RTI answer.

The bundled web guide is tested separately for backend outages. Public deployment smoke checks cover both consumer retrieval and the exact speech question, requiring both speech facts without calling the LLM. The local expanded-corpus memory smoke check peaked at 259.2 MiB RSS under the 400 MiB CI guard; Linux/Render measurements can differ.
