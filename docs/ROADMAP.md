# Delivery roadmap

Unchecked items remain outstanding. The repository now includes the connected Python RAG implementation; the free public demo and GitHub Actions deployment pipeline are active.

## Delivered — web app and Python RAG

- [x] English chat UI, source library, assistance links, browser read-aloud and downloadable notes.
- [x] Shared reviewed source notes with official URLs, review dates and coverage limits.
- [x] Python FastAPI service with documented request/response contracts.
- [x] Reproducible note ingestion, cleaning, chunking and provenance.
- [x] Real BGE CPU embeddings and a local cosine vector index, with a separate TF-IDF option.
- [x] Query retrieval, limited follow-up handling and an insufficient-coverage path.
- [x] Optional Groq generation using retrieved context; validated reference IDs and exact evidence quotes.
- [x] Connected React interface with visible retrieval/generation/fallback modes and evidence display.
- [x] Emergency signposting and explicit fallback when Python or the provider is unavailable.
- [x] Python/web tests, real-model tests, GitHub CI, a small authored evaluation set and measured results.
- [x] Beginner setup instructions and VS Code tasks.

## Next — validate and improve

- [x] Verify real Groq generation with the owner’s free-tier account.
- [x] Expand to 23 introductory notes, including five constitutional topics from official sources.
- [ ] Arrange independent legal expert review of the expanded corpus.
- [ ] Add a larger evaluation set that was not used to tune the pipeline.
- [ ] Measure real LLM correctness, citation entailment, latency and provider-limit behavior.
- [ ] Complete keyboard, screen-reader and mobile usability review.
- [x] Deploy on Render Free with a CI memory guard; retain explicit fallback for cold starts.
- [x] Deploy the web app and Python backend with separate server-side secrets and exact allowed origins.
- [ ] Verify a fresh public demo session, cold start, API limits and provider/backend failures.
- [x] Add the verified public URL to the README.
- [ ] Record a demo video, prepare a pitch and collect user feedback.

## Judging alignment

The [event page](https://hackindia.org/2026/ai-for-lawyers-hackathon) listed these weights when checked on 14 November 2026. Recheck the final rubric before submission.

| Criterion | Weight | Evidence |
| --- | --- | --- |
| Technical execution | 40% | Python RAG, reproducible indexing, real embeddings, tests and honest evaluation; free public deployment and CI/CD |
| Innovation | 30% | Visible evidence and useful next steps for a focused access-to-justice workflow |
| User experience | 20% | Plain language, responsive design and clear coverage/fallback labels; broader accessibility testing remains pending |
| Impact | 10% | No-cost local retrieval and optional free-tier generation, appropriate assistance links; user validation remains pending |
