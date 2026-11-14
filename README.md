# NyayaSathi

**Know your rights. Find your next step.**

An English-first legal information guide for people in India, built for [HackIndia’s AI for Lawyers hackathon, PS-02: Access to Justice](https://hackindia.org/2026/ai-for-lawyers-hackathon).

> **Status: initial working foundation.** The web app runs locally without an API key. It currently uses reviewed source notes and keyword matching, with optional Groq-assisted selection of those notes. The Python backend, vector retrieval, full RAG pipeline and public deployment are planned, not implemented. See [the roadmap](docs/ROADMAP.md).

## What works today

- Responsive chat interface with suggested questions and limited follow-up handling.
- Five covered subjects: consumer complaints, cyber fraud reporting, free legal aid, assistance for women and central RTI requests; plus emergency signposting.
- Official source links, dated source notes, coverage limits and practical next steps.
- Searchable source library, assistance contacts and downloadable conversation notes.
- Browser read-aloud where supported. Voice availability depends on the browser and operating system.
- Optional AI source selection with user opt-in, output validation and a source-guide fallback.
- Input validation, request-size limits, basic identifier redaction before AI processing and best-effort request throttling.

This is general information, not legal advice or a substitute for a qualified lawyer. Source notes were checked on 14 November 2026; they are not automatically updated. This prototype has not undergone legal expert validation.

## Run it in VS Code

You need [Git](https://git-scm.com/downloads), [VS Code](https://code.visualstudio.com/) and [Node.js](https://nodejs.org/) version 22.13 or later. Use Node 24 LTS for a consistent setup. Python is not needed for this initial version.

1. In VS Code, choose **Terminal → New Terminal**.
2. Clone the working branch and enter its folder:

   ```sh
   git clone --branch feature/initial-setup https://github.com/vibhorchander-ai/nyayasathi.git
   cd nyayasathi
   ```

3. Install the pinned package manager once, then install project dependencies:

   ```sh
   npm install --global pnpm@11.25.0
   pnpm install --frozen-lockfile
   ```

4. Choose **File → Open Folder** and open `nyayasathi` if it is not already open.
5. Start the app from the project terminal:

   ```sh
   pnpm dev
   ```

6. Open [localhost:5173](http://localhost:5173). Keep the terminal running. Press **Ctrl+C** in that terminal to stop the server.

You can also choose **Terminal → Run Task → NyayaSathi: dev**. Tasks for testing, checking types and building are included. If `node` or `pnpm` is not found after installation, restart VS Code and check `node --version` and `pnpm --version` in a new terminal.

## Optional Groq setup

The source-guide mode works without an account or API key. To try AI-assisted matching:

1. Create your own account at the [Groq Console](https://console.groq.com/). Use its free plan; check the account’s current limits before enabling anything billable.
2. Create an API key in the console. Keep it private.
3. In VS Code, copy `.dev.vars.example` to a new file named `.dev.vars` in the project root.
4. Set `GROQ_API_KEY` to your key in that local file. Leave `GROQ_MODEL` as provided unless you have verified another model supports the requested structured output.
5. Restart `pnpm dev`, then enable AI-assisted matching in the interface.

Never paste keys into GitHub, chat, screenshots or frontend code. `.dev.vars` is ignored by Git. A missing key, exhausted quota, timeout or invalid AI response uses the source guide instead. Real Groq requests have not yet been tested with an account; automated tests use mocked provider responses.

## Check the project

```sh
pnpm test
pnpm build
pnpm typecheck
pnpm lint
```

The tests exercise topic routing, follow-ups, source references, provider fallback, consent, basic redaction, API validation and throttling. They are software checks, not proof of legal accuracy or retrieval quality. GitHub Actions runs these checks on pushes and pull requests.

## How this version works

```text
React chat → Worker API → reviewed source catalog → answer + citations
                           ↑
              optional Groq source selection
```

The default mode matches words and phrases to topics. In AI mode, Groq selects IDs from the reviewed catalog; the server validates them and displays the stored text. It does not generate new legal claims. There are no embeddings, document ingestion or vector searches in this version.

| Location | Purpose |
| --- | --- |
| `app/page.tsx` | Chat, sources and assistance interface |
| `app/globals.css` | Responsive styles |
| `lib/knowledge.mjs` | Source metadata and reviewed guide notes |
| `lib/legal-engine.mjs` | Matching, provider selection, validation and API handlers |
| `worker/index.ts` | Cloudflare Worker entry point |
| `tests/legal-engine.test.mjs` | Automated behavior checks |
| `.vscode/tasks.json` | VS Code run tasks |
| `docs/ROADMAP.md` | Python RAG plan and completion criteria |

The web foundation uses React, TypeScript, Vinext and Cloudflare Workers. Starter components and build utilities are included; database and connector scaffolding are not used by the legal guide. The application currently stores no conversation database. Chats live in page memory, and downloaded notes contain the user’s questions. The server receives the submitted question; when AI is enabled, a version with basic email/phone/ID pattern redaction is also sent to Groq. This does not guarantee anonymisation. Hosting and AI providers may retain operational data under their own policies.

## Deployment status

There is no verified public deployment yet. The proposed full-project setup is a Cloudflare frontend and a Python FastAPI backend on Render, using free-tier services subject to their limits. The RAG storage and embedding choices must be validated against the selected free accounts before deployment. Free services may sleep or impose quotas.

This repository includes a Worker build and `deploy:cloudflare` command, but that command is not an end-to-end deployment of the planned Python system. Do not treat a successful local build as evidence of a live site. Deployment instructions and the public demo URL will be added after verification.

## License and attribution

Project code is under the [MIT license](LICENSE), as selected in the original repository. Third-party packages and vendored files retain their own licenses. The MIT license does not relicense linked government documents, model weights or service APIs. This project started from the Sites React/Vinext scaffold; third-party notices are retained in `vendor/` and `scripts/vite/`.
