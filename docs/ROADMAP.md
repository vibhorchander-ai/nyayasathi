# Delivery roadmap

This file separates the current foundation from the complete hackathon project. An unchecked item is not delivered.

## Milestone 1 — Web foundation

- [x] English chat UI, source library and assistance links.
- [x] Reviewed source catalog with explicit coverage limits.
- [x] Source-guide mode that runs without paid services.
- [x] Optional Groq selection code, with mocked integration tests.
- [x] Beginner setup instructions and VS Code tasks.
- [ ] Verify Groq using the owner’s free account.
- [ ] Complete mobile, keyboard and screen-reader review.

## Milestone 2 — Python RAG

- [ ] Python FastAPI service with documented API contracts and dependencies.
- [ ] Reproducible ingestion of approved official sources with provenance, review date and jurisdiction metadata.
- [ ] Document cleaning and chunking, preserving section/page references.
- [ ] Embeddings and a vector index with reproducible build instructions.
- [ ] Retrieval filters for jurisdiction and source validity, with an explicit insufficient-evidence path.
- [ ] LLM answers grounded in retrieved passages, checked citations and supported next steps.
- [ ] Emergency handling and useful fallback when providers are unavailable.
- [ ] Connect the React app to the Python API; keep a clearly labelled no-key guide mode.

Planned flow: approved sources → ingestion → chunks + metadata → embeddings/index → query retrieval → supported LLM response → citations in the web app.

The final vector store and embedding provider must fit the verified free-tier limits. Do not describe the present keyword/source-selection implementation as vector RAG.

## Milestone 3 — Evaluation and deployment

- [ ] Versioned evaluation questions covering supported topics, ambiguity, out-of-scope questions and adversarial prompts.
- [ ] Report retrieval recall, citation support, answer correctness, latency and fallback behavior; distinguish measured results from targets.
- [ ] Independent review of legal content where available, and documented limits where unavailable.
- [ ] Deploy the frontend and Python backend with secrets held server-side.
- [ ] Configure allowed frontend origins, request limits, health checks and provider budgets.
- [ ] Verify a fresh GitHub clone can install, test and run using documented commands.
- [ ] Test the public demo from a separate browser session, including a backend cold start and provider failure.
- [ ] Add the verified demo URL, demo video, architecture explanation and presentation.

## Judging alignment

The [event page](https://hackindia.org/2026/ai-for-lawyers-hackathon) listed the following weights when checked on 14 November 2026. Recheck the final rubric before submission.

| Criterion | Weight | Evidence to prepare |
| --- | --- | --- |
| Technical execution | 40% | Real Python RAG, reproducible pipeline, evaluation results, working deployment |
| Innovation | 30% | Evidence-backed next steps, transparent source limits and a focused access-to-justice workflow |
| User experience | 20% | Plain language, responsive design, accessible interactions and useful follow-ups |
| Impact | 10% | Clear target users, no-cost access within quotas, links to appropriate assistance and feedback from users |

A generic chat interface alone does not satisfy these goals. The finished demo should show a useful answer, its supporting passages, an honest refusal when evidence is insufficient and recovery from an unavailable provider.
