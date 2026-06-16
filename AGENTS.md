# AGENTS.md

## Entrypoints

- **CLI** (`src/main.py`): `uv run python src/main.py` — interactive question loop, no server needed.
- **API** (`src/api/main.py`): `uv run uvicorn src.api.main:app --reload --port 8000` — FastAPI server for frontend.

The `app` instance in `src/api/main.py:38` is the ASGI target; on startup it imports SQLite tables into DuckDB via `global_database.setup_database()`.

## Commands

```bash
# Python tests (skip integration — requires external services like LLMs)
uv run pytest -m "not integration"

# Single test file
uv run pytest tests/path/to/test_file.py -v

# Frontend
cd frontend && npm install
cd frontend && npm run dev        # dev server on :5173
cd frontend && npm run check      # lint + typecheck (tsc + eslint)
cd frontend && npm test           # vitest

# Full eval (runs in Docker):
./scripts/run_insight_eval.sh
```

Requires **Python >= 3.13** and **Node >= 18**. Uses `uv` for Python package management.

## Architecture

Two separate apps connected by a Vite proxy:

- **Frontend** (React 19 + Vite 8 + TS ~5.9, Tailwind 4, shadcn/ui, Vitest) proxies `/api/*` → `http://127.0.0.1:8000`, stripping `/api` prefix.
- **Backend** (FastAPI + LangChain/LangGraph) exposes routes directly (no `/api` prefix server-side).

The NLP → SQL pipeline has **two code paths**:
1. **Agent path** (primary, used by API): `src/agent.py` — LangGraph agent with `query_tool` → extracts `QuerySchema` → vector search → SQL composition → DuckDB. Multi-turn, self-correcting.
2. **Direct pipeline path** (older, used by CLI): `src/llms/main_pipeline.py` — single-shot extraction without agent loop.

## Database

DuckDB wrapping a SQLite source at `data/minidev_raw/financial/`. `global_database` (`src/utils/database.py:138`) is a singleton; **no persistent connection is held** — `query()` opens a fresh DuckDB connection per call (fix for H1 race condition). Paths in `src/config.py`.

## Vector index

Pre-built FAISS index at `data/app_data/columns.faiss` + `columns.json` (41 columns). Must be rebuilt if schema or embedding model changes. Default embedding model is `qwen3-embedding:0.6b` (`src/utils/models.py:36`), not `nomic-embed-text` as the README states — README is stale on this point.

## Models

LLM providers wrapped in `src/utils/models.py` via LangChain: `ChatOllama` (local), `ChatOpenAI`, `ChatGroq`, `ChatOpenRouter` (remote). Defaults in `src/api/routes/query.py:39` — remote uses `llama-3.1-8b-instant` via Groq, local uses `granite4:3b` via Ollama.

API keys loaded from `.env` via `dotenv` in `src/utils/models.py` (`.env` is gitignored but may exist on disk).

## Eval

Runs promptfoo inside Docker (`docker compose run --rm promptfoo-eval`). Single config: `src/eval/insight_config.yaml`. Provider: `src/eval/provider.py`. Scorer: `src/eval/insight_scorer.py` (RAGAS FactualCorrectness against pre-computed `reference_answer` in `tests.yaml`).

## Tests

- `integration` marker filters out tests needing external services (LLMs). CI and local default commands skip these.
- Test package init files exist but are empty — no shared fixtures/conftest at the root.

## Python gotchas

- Package name in `pyproject.toml` is `spx-automation-technical` (legacy); imports use `src.*`.
- No python linting/typechecking configured — only `pytest`.
- `EXTRACTOR_PROMPT` (`src/utils/prompts.py:1`) is logistics-domain-specific (parcels, buyer countries, providers, waiting times) despite the "TinyBI" name.
- `.env` is in `.gitignore` but check its content before running — keys may be stale.

## Workflow

On every new session, you must read the HANDOFF.md

Planning and implementation should be cleanly split as two stages. During
planning, use the grill me skill if implementing a new feature that is not well
defined in order for you and the user to reach a common understanding. Once
satisfied with the answers, present a plan of how you would implement the feature
to the user. The development of all new features should be as much as possible
done through red/green test driven development (tdd skill). As such, after the
user approves of the plan, present the user with a list of test cases
and their failure/ success modes for the user to inspect and work with you
through. Once the user agrees with the test cases, are you allowed to make 
edits. Only if the user gives the explicit go to for this plan, are you 
allowed to start editing and implementing code.
