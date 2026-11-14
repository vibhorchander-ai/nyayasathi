# NyayaSathi

**Know your rights. Find your next step.**

An English-first legal information assistant for India, built for [HackIndia PS-02: Access to Justice](https://hackindia.org/2026/ai-for-lawyers-hackathon).

**Status:** the Python RAG backend is connected to the React app. Local semantic retrieval works without an account or API key. Optional Groq generation is implemented and tested with mocked responses; a real Groq key is still needed to verify live generation. There is no public deployment yet.

## What you can demo

- A responsive conversational interface, source library, assistance contacts and downloadable notes.
- Python ingestion of 16 reviewed source notes, stable chunks with provenance, local BGE embeddings and cosine vector retrieval.
- Optional retrieval-augmented LLM explanations with validated chunk references and exact quotes from the retrieved notes.
- A “Read the retrieved evidence” panel showing the notes and their official source links.
- Explicit labels for AI explanations, retrieved notes, the built-in source guide and coverage limits.
- Out-of-scope handling, emergency signposting and fallback when the Python service or LLM is unavailable.

The collection covers introductory consumer complaints, cyber fraud reporting, legal aid, assistance for women and central RTI requests. These are **reviewed paraphrases**, not a collection of full statutes, judgments or verbatim government documents. Source review date: 14 November 2026. General legal information only; no legal expert validation has been completed.

## Step-by-step setup

The full guide, including Windows commands and troubleshooting, is in **[docs/SETUP.md](docs/SETUP.md)**. Run all commands from the repository root.

1. Install free [Python 3.12](https://www.python.org/downloads/), [Node.js 24 LTS](https://nodejs.org/), [Git](https://git-scm.com/downloads) and [VS Code](https://code.visualstudio.com/).
2. Clone the branch (skip if you already have this checkout):

   ```sh
   git clone --branch feature/initial-setup https://github.com/vibhorchander-ai/nyayasathi.git
   cd nyayasathi
   ```

3. Create and activate an isolated Python environment:

   ```sh
   python3.12 -m venv .venv
   source .venv/bin/activate
   python -m pip install -r backend/requirements-semantic.txt
   ```

4. Copy the example configuration **once**. Keep existing configuration if these files already exist:

   ```sh
   cp backend/.env.example backend/.env
   cp .dev.vars.example .dev.vars
   ```

   Leave `GROQ_API_KEY` blank initially. The default web configuration connects to Python at `http://127.0.0.1:8000`.

5. Build the local vector index, then start Python:

   ```sh
   python -m backend.ingest
   python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 --no-access-log
   ```

   The first ingestion downloads a small public embedding model. No Hugging Face account, GPU or paid endpoint is required. Subsequent runs reuse the model cache. Check [backend health](http://127.0.0.1:8000/health) or [API docs](http://127.0.0.1:8000/docs).

6. Open a **second terminal** in the same project folder, then start the web app:

   ```sh
   npm install --global pnpm@11.25.0
   pnpm install --frozen-lockfile
   pnpm dev
   ```

7. Open **[localhost:5173](http://localhost:5173)**. The header should show **Source retrieval**. Ask “How do I track my consumer grievance?” and expand **Read the retrieved evidence**. Keep both terminals running; Ctrl+C stops each server.

VS Code tasks for the frontend, backend, ingestion and tests are included under **Terminal → Run Task**. They use the project’s `.venv`; create it before running the Python tasks.

## Enable optional LLM explanations for free

1. Create an account at the [Groq Console](https://console.groq.com/) and remain on the **Free tier**. Do not add billing or upgrade to a paid tier. Groq applies [free-tier rate limits](https://console.groq.com/docs/rate-limits).
2. Create an API key and put it in `backend/.env` as `GROQ_API_KEY=your-key`.
3. Restart Python. Reload the browser and enable **Use AI to explain the retrieved information**.

The default model is `openai/gpt-oss-20b`. Groq provides [structured outputs](https://console.groq.com/docs/structured-outputs); account/model availability can change. The application does not create or upgrade service accounts. Its daily request cap is a best-effort, per-process demo limit, not a billing guarantee. See [Groq billing information](https://console.groq.com/docs/billing-faqs).

Never commit `.env`/`.dev.vars`, paste keys into chat or put keys in frontend variables. Generation is opt-in. If there is no key, quota is exhausted, the request times out or citation validation fails, the UI displays retrieved notes instead.

## Architecture

```text
Shared reviewed corpus (data/knowledge.json)
    → Python cleaning and chunking with source metadata
    → BGE-small-en-v1.5 embeddings on CPU → local NumPy vector index

React chat → same-origin Worker API → Python FastAPI
    → scope checks → hybrid semantic + lexical retrieval
    → optional Groq generation using retrieved notes only
    → validate citations and evidence quotes → response + visible evidence
```

The default embedding model is [BAAI/bge-small-en-v1.5](https://huggingface.co/BAAI/bge-small-en-v1.5), run through [FastEmbed](https://qdrant.github.io/fastembed/). It produces 384-dimensional vectors. A separate, lighter TF-IDF mode is available; it performs lexical retrieval and must not be presented as neural semantic search. No paid vector database or embedding API is used.

| File or directory | Responsibility |
| --- | --- |
| `backend/main.py` | FastAPI endpoints, input limits, origin/token checks and request throttling |
| `backend/corpus.py`, `backend/ingest.py` | Validate notes, clean text and build the index |
| `backend/retrieval.py` | Embeddings, cached index and cosine ranking |
| `backend/rag.py`, `backend/llm.py` | Coverage rules, prompt construction, generation and citation validation |
| `data/knowledge.json` | Shared source notes, metadata and topic guidance |
| `lib/backend-proxy.mjs` | Server-side proxy and explicit fallback |
| `app/page.tsx` | Chat interface and retrieved evidence display |
| `backend/evaluate.py` | Reproducible retrieval/routing evaluation |

Read [the architecture and API contract](docs/ARCHITECTURE.md), [measured evaluation results](docs/EVALUATION.md) and [the remaining roadmap](docs/ROADMAP.md).

## Verification

With the Python environment activated:

```sh
python -m unittest discover -s backend/tests -v
NYAYA_TEST_SEMANTIC=1 python -m unittest discover -s backend/tests -v
python -m backend.evaluate --engine bge
pnpm test
pnpm build
pnpm typecheck
pnpm lint
```

The first command skips the two real-model tests; the second includes them. Windows equivalents are in the setup guide. CI installs the semantic dependencies and runs all Python and web checks. Generation tests use a mocked provider, so they incur no API charges. The evaluation is a small authored regression set, not an independent legal-accuracy benchmark.

## Privacy and limits

The application has no chat database or browser chat storage. The web and Python servers receive questions. Basic email, phone and ID patterns are removed before LLM processing, but this is not comprehensive anonymisation. AI-enabled requests send the redacted question and retrieved notes to Groq. Browser read-aloud and operational provider processing depend on their respective policies. Downloaded notes include your questions.

Valid chunk IDs and matching quotes do not prove that a generated claim logically follows from its citation. The source collection is small, does not update automatically and excludes most Indian law. Topic filters, similarity thresholds and emergency matching can miss unfamiliar wording. Practical next steps are curated topic guidance. Further evaluation and legal review remain necessary before broader use.

## Deployment and license

This milestone runs locally and adds no paid services. Public deployment is the next milestone. The Python process cannot run inside the Cloudflare Worker; it needs a separate Python host. See deployment considerations in the setup guide before exposing a backend with an API key.

Project code retains the [MIT license](LICENSE). Dependency/model licenses and official source terms remain separate. The web foundation uses the Sites React/Vinext scaffold; its third-party notices remain in `vendor/` and `scripts/vite/`.
