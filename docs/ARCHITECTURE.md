# Python RAG architecture and API

## Data flow

1. `corpus.py` loads the shared reviewed notes and validates source IDs, official HTTPS URLs, dates and jurisdiction.
2. Notes are cleaned and split into windows of at most 90 words, with 15-word overlap for long notes. The current 23 short facts each fit in one chunk. Stable IDs include the fact ID, position and text hash.
3. FastEmbed runs BGE-small-en-v1.5 on CPU. Passage embeddings are normalised and stored as a NumPy array. The local manifest records model, engine, encoder version, chunk IDs and corpus fingerprint. Changed inputs or invalid array shapes trigger a rebuild.
4. The query is embedded with the matching query encoder. Ranking combines semantic cosine similarity (80%) and TF-IDF cosine similarity (20%). TF-IDF-only mode is available separately. Supported follow-ups add the previous topic name; unrelated questions do not inherit it.
5. Scope/emergency checks run first. Exact constitutional article references resolve only to catalogued articles; unknown clauses or articles spanning multiple topics abstain. Generic words such as “right” cannot alone pass lexical acceptance: a score of at least 0.16 also needs overlap with a non-generic query term. BGE acceptance requires similarity of at least 0.64 and either meaningful overlap, at least three distinct non-generic query terms, or a stronger similarity of 0.78. These are development heuristics, not confidence probabilities. All 23 chunks are ranked; up to four notes from the best topic are returned. Catalogued `requiredFacts` retain material qualifications: both the speech right and its restrictions reach the response and LLM context.
6. With explicit consent and a configured key, Groq receives the redacted question and retrieved notes. Structured output contains claims and evidence references. No retrieved document can supply instructions or credentials to the provider.
7. The server checks output structure, reference membership and exact quoted substrings. Unknown references, invented quotes, provider failures or daily limits use the retrieval response. An explicit insufficient-evidence response shows a coverage limit.
8. The Worker proxies browser requests and keeps the backend token server-side. It checks official source links and falls back to the existing source guide when Python cannot respond. The browser displays the actual response mode and retrieved evidence.

## Endpoints

| Method/path | Contract |
| --- | --- |
| `GET /health` | Public readiness after model/index startup; no credentials or question data. |
| `GET /api/status` | Backend/LLM availability, retrieval engine/model and corpus count/date. Requires backend token if configured. |
| `POST /api/chat` | JSON request below; returns the existing web answer fields plus `retrieval`. Requires backend token if configured. |
| `GET /docs` | FastAPI interactive API schema. |

Request:

```json
{"question":"How do I track my consumer complaint?","previousTopic":null,"useAI":false}
```

Response modes:

- `rag`: generated explanation with locally validated evidence references.
- `retrieval`: retrieved note text; no generated explanation.
- `guide`: curated emergency guidance or the web fallback.
- `limited`: insufficient coverage/evidence.

`retrieval.chunks` includes stable chunk/fact IDs, text, source ID, jurisdiction, review date and retrieval scores. These scores must not be presented as legal-accuracy percentages. `points[].evidence` records the validated supporting quotes for generated claims. URLs come from the source catalog, never the LLM.

Input is limited to 1,200 characters and 6,000 body bytes. Invalid schema returns 422; wrong content type 415; disallowed origin 403; token failure 401; request throttling 429. The Worker converts backend availability/limit failures into an explicitly labelled source-guide response. The backend token does not go to Groq. Neither request headers nor provider errors are echoed to the browser.

## Limits and costs

Embeddings/indexing execute locally and use no billed API. Groq is optional, and this setup assumes a Free-tier account. Request throttling is per process: 12 POST requests per client per minute and, by default, at most 100 attempted LLM calls per UTC day per process. Limits reset on restart and are not distributed accounting or a monetary spending cap. Do not use paid account credentials if you require zero spending.

There is no persistent chat store. Source notes, indexes and model caches contain the reviewed public information, not user questions. The server receives raw questions; pattern redaction happens before retrieval/LLM processing. Names, addresses and unusual identifiers can remain. Provider and browser voice processing policies still apply.

Grounding validation detects malformed/fabricated references and quotes. It does not prove semantic entailment, legal correctness or current law. Regex scope/emergency rules are deliberately small and may miss paraphrases. The corpus consists of introductory summaries and curated next steps, not a comprehensive legal database. It has not been reviewed by a lawyer. Prompt-injection and out-of-scope tests reduce known failure modes without guaranteeing all adversarial inputs are handled.

Coverage counts and UI scope text derive from the shared catalog. Changes to the corpus hash rebuild the index during Render’s existing build command. The UI and bundled outage fallback use the same source notes. See [source review](SOURCE_REVIEW.md) for the constitutional text edition, article/page mapping and update procedure.
