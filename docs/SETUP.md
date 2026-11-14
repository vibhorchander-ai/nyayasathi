# Beginner setup guide

The repository root is the folder containing `package.json`, `backend/` and `data/`. Open that folder in VS Code. Use **Terminal → New Terminal** for commands. You need two running terminals: Python on port 8000 and the web app on port 5173.

## 1. Check the tools

Use Python 3.12 and Node 24 LTS. Check with `python3.12 --version` (macOS/Linux) or `py -3.12 --version` (Windows), and `node --version`. Install missing tools from the official links in the README, then restart VS Code. If your `python3` already reports 3.12, it can replace `python3.12` below.

On the prepared local checkout, `.venv`, dependencies, configuration and the model/index already exist. You can start from step 4. A fresh GitHub clone needs every step.

## 2. Prepare Python

macOS/Linux:

```sh
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -r backend/requirements-semantic.txt
```

Windows PowerShell:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r backend/requirements-semantic.txt
```

In the remaining Windows commands, replace `python` with `.\.venv\Scripts\python.exe`. This works without changing PowerShell execution policies or activating the environment.

The virtual environment isolates this project’s packages from other projects. The normal setup includes FastEmbed and ONNX Runtime for local CPU inference. No paid model API is used for embeddings. The index and model cache are ignored by Git and are rebuilt/downloaded on a fresh machine.

If your device cannot install or run the semantic model, install only `backend/requirements.txt`, then set `NYAYA_EMBEDDINGS=tfidf` in step 3. This is a lighter lexical mode; its retrieval quality differs from BGE and it is not neural semantic search.

## 3. Create the two configuration files

In VS Code Explorer, duplicate `.dev.vars.example` as `.dev.vars`, and `backend/.env.example` as `backend/.env`. Do this only when the destination does not already exist.

- `.dev.vars` belongs to the web server. `NYAYA_BACKEND_URL=http://127.0.0.1:8000` connects it to Python.
- `backend/.env` belongs to Python. Keep `NYAYA_EMBEDDINGS=bge` for semantic search.
- Leave `GROQ_API_KEY` blank until you create your own free Groq account.
- Leave the backend tokens blank for this local-only setup.

Do not put secrets in `data/knowledge.json`, source files, `NEXT_PUBLIC_*` or `VITE_*` variables. Restart the affected server after editing its environment file.

## 4. Index and start Python

In terminal 1, from the repository root:

```sh
source .venv/bin/activate
python -m backend.ingest
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 --no-access-log
```

On Windows, omit `source` and use `.\.venv\Scripts\python.exe` for the two commands.

The first ingestion downloads public model files. Wait for the JSON report showing `engine: bge`, `chunks: 16` and `dimensions: 384`. The server also checks the corpus fingerprint at startup and rebuilds stale indexes. Start only one ingestion/server process at a time while rebuilding an index.

Visit [health](http://127.0.0.1:8000/health): expect `status: ok`. [Interactive API docs](http://127.0.0.1:8000/docs) let you inspect `/api/chat`. Keep this terminal open.

## 5. Start the web app

In terminal 2, in the same repository root:

```sh
npm install --global pnpm@11.25.0
pnpm install --frozen-lockfile
pnpm dev
```

The first two commands are setup steps; on later starts just run `pnpm dev`. Open [the app](http://localhost:5173). **Source retrieval** means the Python backend is connected. **Source guide** means you are using the built-in fallback.

## 6. Try the demo

1. Ask: “The shop delivered a broken appliance and refuses to return my payment. Where can I complain?”
2. Expand **Read the retrieved evidence** and inspect the official source links.
3. Ask: “How do I track it?” to test a short follow-up.
4. Ask an unsupported question, such as “What are my tenant rights in California?”
5. Stop Python with Ctrl+C and ask a consumer question again. The answer should explicitly say that the Python backend is unavailable and show the source guide.
6. Restart Python, reload the app, and repeat the first question.

## 7. Optional Groq LLM

Create an account at [Groq Console](https://console.groq.com/) and keep the Free tier. Create an API key there, save it privately in `backend/.env`, then restart Python and reload the app. Do not share the key in a conversation or commit it to GitHub.

Enable **Use AI to explain the retrieved information**. A successful generated response shows **AI explanation + evidence**. Without consent, all retrieval still runs locally and no LLM call is made. The default model is `openai/gpt-oss-20b`; invalid or unavailable model responses fall back visibly to retrieved notes.

No live Groq key was available during development. Code and failure handling were tested using mocked responses; you still need to verify a real free-tier call from your account. Free quotas can change. Do not upgrade or add billing to follow this zero-budget setup.

## 8. Run the checks

```sh
python -m unittest discover -s backend/tests -v
python -m backend.evaluate --engine bge
pnpm test
pnpm build
pnpm typecheck
pnpm lint
```

To include the two tests using real embedding weights, macOS/Linux:

```sh
NYAYA_TEST_SEMANTIC=1 python -m unittest discover -s backend/tests -v
```

Windows PowerShell:

```powershell
$env:NYAYA_TEST_SEMANTIC = "1"
.\.venv\Scripts\python.exe -m unittest discover -s backend/tests -v
Remove-Item Env:NYAYA_TEST_SEMANTIC
```

## Troubleshooting

| What you see | What to do |
| --- | --- |
| `No module named fastembed` | Activate `.venv` and install `backend/requirements-semantic.txt`, or deliberately choose TF-IDF mode. |
| Model download fails | Check connectivity and retry ingestion. An HF account/token is not required for this public model; anonymous download limits may require waiting. |
| `Source guide` instead of retrieval | Check Python health, the URL in `.dev.vars`, and that both servers were restarted after configuration changes. |
| No AI checkbox | Add a valid Groq key in `backend/.env`, keep `NYAYA_DAILY_AI_LIMIT` above zero, restart Python and reload the browser. |
| AI falls back to notes | Check your model access/quota in Groq and your private configuration. Do not paste credentials or private questions into bug reports. |
| Port already in use | Stop the older server in its terminal. If choosing another Python port, update `.dev.vars` to match. |
| `pnpm` or `node` not found | Install the required tool and restart VS Code. The README does not depend on Codex-specific runtime paths. |
| Origin rejected | Add your exact development origin to `NYAYA_ALLOWED_ORIGINS`; do not use a wildcard for a public service. |

## Adding reviewed content

Edit `data/knowledge.json`. Keep stable fact/source IDs, official HTTPS source URLs, the jurisdiction, review dates and `contentKind: reviewed_paraphrases`. Add facts only after checking their support and any state/time limitations. Update the evaluation cases for the changed scope, run ingestion, restart Python and rerun tests. The web source library and Python pipeline share this file.

The pipeline does not scrape arbitrary websites or accept private document uploads. Chunking applies to reviewed notes in this file, and longer notes are split into overlapping word windows. A cache fingerprint detects changed corpus bytes.

## Before later public deployment

The frontend Worker must use the Python service’s HTTPS root URL in `NYAYA_BACKEND_URL`. Set a random `NYAYA_API_TOKEN` in the backend and the same value as `NYAYA_BACKEND_TOKEN` in the Worker’s server-side secrets. Keep `GROQ_API_KEY` only in Python. Restrict origins to the deployed frontend and use one backend worker for the documented demo limits.

The local NumPy index can be rebuilt from the checked-in corpus; no paid database is required. Model downloads, memory, cold starts, persistent cache availability and free hosting quotas still need to be tested on the chosen host. Do not assume a local semantic model fits every free hosting instance. The lighter TF-IDF configuration is an explicit alternative, with its own evaluation results. Deployment and live-provider verification remain separate milestones.
