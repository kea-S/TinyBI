# TinyBI

Natural-language-to-SQL analytics pipeline: ask a business question in plain English, get back an SQL query, a result table, and an AI-generated explanation

https://github.com/user-attachments/assets/2e29a39c-f8f4-4e97-b9cb-34f866fa2d62

Model your database relations intuitively, enrich with semantic meaning from documentation

https://github.com/user-attachments/assets/417e2551-b69e-4093-bdce-d34a230b04d4

Monitor performance

<img width="1688" height="1029" alt="Image" src="https://github.com/user-attachments/assets/a8dfa5a7-8124-4644-9278-e57a2342fe5d" />

Change LLM provider configurations

<img width="1687" height="1031" alt="Image" src="https://github.com/user-attachments/assets/2b95f9f1-c621-4133-bad6-e7921eccf7a6" />

## Architecture

```
User question (natural language)
  → LLM Extractor  →  QuerySchema (structured intent)
  → Vector Search  →  Column resolution (FAISS over schema metadata)
  → SQL Generator  →  SQL query (SELECT, JOINs, WHERE, GROUP BY, ORDER BY, LIMIT)
  → DuckDB         →  pandas DataFrame
  → LLM Explainer  →  Business insight (optional, currently disabled)

Interface: a **FastAPI backend** serving a **React/Vite frontend**.
```

## Prerequisites

Before starting, ensure you have the following installed and running based on your preferred deployment method:

- **Docker Desktop**: Required if you plan to use the Docker Quick Start.
- **Python ≥ 3.13** and **Node.js ≥ 18**: Required if you plan to run the services natively for development.
- **Ollama**: Required if you are using local LLMs. It must be installed and running on your host machine.
- **Cloud / Remote API Keys**: Optional. Required if you use cloud services instead of local Ollama (e.g. Groq for chat LLMs or Jina AI for vector embeddings).

---

## Quick Start (Docker)

The easiest way to run TinyBI is using Docker, which packages both the FastAPI backend and React frontend into a single container.

1. **Build and start the application:**
```bash
docker compose up --build -d app
```

2. **Access the web interface:**
Open [http://localhost:4510](http://localhost:4510) in your browser.

> **Note:** If you are using local LLMs, ensure you have pulled the required models via Ollama on your host machine (e.g., `ollama pull nomic-embed-text` and `ollama pull granite4:3b`). See the *Local Development Setup* section for a full list of supported models.

---

## Ollama Integration & Setup (Local LLMs)

TinyBI tightly integrates with [Ollama](https://ollama.com/) to provide a 100% local, privacy-first analytics pipeline. If you aren't using remote APIs (like OpenAI or Groq), Ollama **must** be running on your host machine.

### 1. Install and Start Ollama

**macOS / Linux:**

```bash
curl -fsSL https://ollama.com/install.sh | sh
ollama serve
```

**Windows:**

Download and run the installer from [ollama.com/download/windows](https://ollama.com/download/windows). Ollama starts automatically as a system tray service (no manual `serve` command needed).

### 2. Networking (Docker vs. Local)

- **Running Natively (Local Dev):** TinyBI expects Ollama at `http://127.0.0.1:11434`.
- **Running via Docker:** TinyBI automatically resolves `localhost` to `host.docker.internal` so the Docker container can reach Ollama on your host machine. You do not need to configure this manually.
- **Custom Endpoint:** If you host Ollama on a different machine or port, set the `OLLAMA_BASE_URL` environment variable (e.g., `OLLAMA_BASE_URL="http://192.168.1.100:11434"`).

### 3. Pull Required Models

TinyBI requires two types of models to function: an **embedding model** (for vector search) and a **chat model** (for text-to-SQL extraction).

```bash
# 1. Embedding Model (Required for vector search and indexing)
ollama pull qwen3-embedding:0.6b

# 2. Chat Model (Required for text-to-SQL extraction)
ollama pull granite4:3b
```

### Recommended Chat Models

Because TinyBI delegates directly to Ollama, **you can use any model available in the Ollama library**. The models below are simply the ones we've tested and recommend for SQL generation. 

By default, the backend falls back to `ibm/granite4:3b` if no model is specified. You can use a different model by passing its name in the `model` field of the JSON payload when calling the `/query` API.

| Model | Size | Notes |
|---|---|---|
| `ibm/granite4.1:3b` | 2 GB | **Default.** Good balance of speed and SQL quality |
| `gemma3:4b` | 2.5 GB | Google's lightweight model |
| `llama3.2:3b` | 2 GB | Meta's compact model |
| `phi4-mini:3.8b` | 2.4 GB | Microsoft's small model |
| `qwen2.5:7b` | 4.7 GB | Highest quality local option (slower) |

### Supported Embedding Models

By default, TinyBI uses `qwen3-embedding:0.6b`. If you change the embedding model, you **must rebuild the vector index** using the Vector Index Builder UI (done automatically via the config menu).

| Model | Source | Notes |
|---|---|---|
| `qwen3-embedding:0.6b`| Ollama | **Default.** Fast and lightweight |
| `nomic-embed-text` | Ollama | 768-dim alternative |
| `bge-m3:567m` | Ollama | Multilingual support |
| `jina-embeddings-v5-text-small` | Jina AI | Fast cloud embeddings — requires Jina API key |
| `text-embedding-3-small`| OpenAI | Remote — requires `OPENAI_API_KEY` |

---

## Cloud Setup (Groq & Jina AI)

If you do not want to run local models with Ollama, you can use cloud providers for both LLMs and vector embeddings.

### 1. Get Free API Keys
- **Groq (Chat LLM):** Create an account at [console.groq.com/home](https://console.groq.com/home) and generate an API key.
- **Jina AI (Vector Embeddings):** Create an account at [jina.ai](https://jina.ai/) and generate an API key.

### 2. Configure via the Setup Page (Web UI)
1. Start the application (`docker compose up -d app`) and open [http://localhost:4510](http://localhost:4510) in your browser.
2. Click the **Setup** tab in the top navigation.
3. Select **Remote LLM** and paste your Groq API key (`gsk_...`).
4. Select a model, `llama-3.1-8b-instant` is recommended
5. Select **Jina AI** under Embeddings, set `base_url` to `https://api.jina.ai/v1`, and paste your Jina API key.
6. Select an embedding model, `jina-embeddings-v3` is recommended
7. Click **Save & Connect**. The backend tests the connection and automatically re-embeds the vector index.

---

## Local Development Setup

If you prefer to run the services natively for development (Requires **Python ≥ 3.13** and **Node.js ≥ 18**):

### 1. Install Python dependencies

```bash
uv venv
uv pip install -r requirements.txt
```

### 2. Install frontend dependencies

```bash
cd frontend && npm install && cd ..
```

### 3. Set up API keys (remote models only)

Create a `.env` file in the project root. e.g.
```env
OPENAI_API_KEY=sk-...
```

## Start the servers

**Terminal 1 — Backend (FastAPI):**

```bash
uv run uvicorn src.api.main:app --reload --port 8000
```

**Terminal 2 — Frontend (Vite dev server):**

```bash
cd frontend && npm run dev
```

The frontend opens at `http://localhost:5173`. It proxies `/api/*` to the backend at `http://127.0.0.1:8000`.

## Vector index

The vector index maps natural language concepts to database columns. **It is pre-built and included in the repo** (`data/app_data/columns.faiss` + `columns.json`) — no action needed.

To rebuild it (e.g. after changing the database schema or the embedding model):

### Rebuild via the frontend

Use the **frontend's Vector Index Builder** — navigate to `/vector-index`, load the columns from `data/app_data/columns.json`, verify them, and click "Submit Index Batch".

### Rebuild via the API

```bash
curl -X POST http://127.0.0.1:8000/vector/index-entries/batch \
  -H "Content-Type: application/json" \
  -d @data/app_data/columns.json
```

> The index is persisted to `data/app_data/columns.faiss` and reused across restarts.

## Testing

### Backend tests

```bash
uv run pytest -m "not integration"
```

### Frontend tests

```bash
cd frontend && npm test
```

## LLM Evaluation (promptfoo)

Promptfoo runs in a Docker container to prevent dependency conflicts on the host machine.

> **Note:** The repository includes a pre-seeded evaluation database (`data/promptfoo_store/promptfoo.db`) with the 2 most recent runs. You do not need to run new evaluations to view the dashboard unless you want to generate fresh benchmark data.

### 1. Build the evaluation image

```bash
docker compose build promptfoo-eval
```

### 2. Prepare the database

```bash
uv run python scripts/prepare_db.py \
  --duckdb data/intermediate/financial.duckdb \
  --sqlite data/minidev_raw/financial/financial.sqlite
```

### 3. Run the insight evaluation

```bash
./scripts/run_insight_eval.sh
```

This script executes the Promptfoo evaluation in Docker. It scores pipeline responses using RAGAS FactualCorrectness against reference answers in `src/eval/tests.yaml`. Execute this evaluation on machines with dedicated GPUs for faster inference.

### 4. Prune the evaluation database

After running evaluations, run the pruning script to keep the database size small (~18 MB) before committing changes:

```bash
uv run python scripts/prune_promptfoo_db.py
```

### 5. Inspect evaluation results

You can inspect the evaluation results in two ways:

**Option A: Via the TinyBI Web UI**
1. Open the **System Health & Evaluation** page at `http://localhost:4510`.
2. Click the **Promptfoo Dashboard** button.
3. Follow the modal instructions to start the viewer container.

**Option B: Via Terminal**
1. Start the viewer container:
```bash
docker compose up promptfoo-view -d
```
2. Open `http://localhost:15500` in your web browser.

To stop the viewer container:

```bash
docker compose stop promptfoo-view
```

## Project structure

```
.
├── data/
│   ├── app_data/                  # FAISS vector index + column metadata
│   │   ├── columns.faiss          # pre-built column embeddings
│   │   └── columns.json           # column entries (descriptions, FK refs, etc.)
│   ├── intermediate/              # Cleaned datasets
│   └── minidev_raw/               # Raw database files
│       ├── financial/             # The financial database (SQLite + DuckDB + CSVs)
│       └── debit_card_specializing/  # Alternative database
│
├── notebooks/                     # Jupyter notebooks (EDA)
├── frontend/                      # React + Vite + TypeScript
│   └── src/
│       ├── pages/
│       │   ├── DashboardHome.tsx
│       │   ├── QueryPage.tsx      # Natural language query UI
│       │   └── VectorIndexBuilderPage.tsx  # Build/rebuild vector index
│       ├── components/ui/         # shadcn/ui components
│       └── lib/api.ts             # API client types + fetch wrappers
│
├── src/                           # Python backend
│   ├── main.py                    # Application entry point
│   ├── agent.py                   # LangGraph agent (multi-turn NLP → SQL orchestrator)
│   ├── config.py                  # Path configuration
│   ├── api/
│   │   ├── main.py                # FastAPI app (lifespan, health, routers)
│   │   └── routes/
│   │       ├── query.py           # POST /query  (NL → SQL → DataFrame → explanation)
│   │       └── vector.py          # GET/POST /vector  (FAISS index management)
│   ├── llms/
│   │   ├── extractor.py           # LLM chain: user question → QuerySchema
│   │   ├── explainer.py           # LLM chain: results → business insight
│   │   └── main_pipeline.py       # Orchestrator (extract → resolve → query → explain)
│   ├── tools/
│   │   └── query_tool.py          # QuerySchema + vector search → SQL generation + execution
│   └── utils/
│       ├── database.py            # DuckDB wrapper (SQLite import, query, singleton)
│       ├── models.py              # LLM model definitions + factory functions
│       ├── prompts.py             # EXTRACTOR_PROMPT and EXPLAINER_PROMPT
│       ├── pydantic_models.py     # Pydantic schemas (QuerySchema, ColumnVectorIndexEntry, etc.)
│       ├── sql_normaliser.py      # Maps structured query → SQL clauses
│       ├── rag/
│       │   ├── vector_controller.py  # High-level vector search logic
│       │   └── vector_index.py       # FAISS index (build, persist, search)
│       └── value_resolution/
│           ├── column_resolver.py    # Pick best column per intent via schema graph
│           ├── db_schema_graph.py    # NetworkX graph of FK relationships
│           ├── join_resolution.py    # BFS join path resolution
│           └── value_resolver.py     # Fuzzy literal matching against column categories
│
├── tests/                         # Python test suite
├── requirements.txt
└── pyproject.toml
```

## API reference

### `GET /health`

```
GET /health  →  {"status": "ok"}
```

### Vector index endpoints

| Method | Path | Description |
|---|---|---|
| `POST` | `/vector/index-entries/batch` | Build/replace the FAISS index with the default embedding model |
| `POST` | `/vector/index-entries/batch/by-model/{key}` | Build/replace the FAISS index with a specific embedding model (`nomic`, `qwen3`, `bge-m3`, `openai-small`) |
| `GET` | `/vector/index-entries/current` | Retrieve the current index metadata |

## Configuration

| Env variable | Default | Description |
|---|---|---|
| `OPENAI_API_KEY` | — | Required for remote extraction with GPT-4o |
| `GROQ_API_KEY` | — | Groq cloud provider API key |
| `JINA_API_KEY` | — | Jina AI embeddings API key |
| `LOCAL_API_BASE` | — | Base URL for custom or cloud embedding API |
| `VITE_BACKEND_URL` | `http://127.0.0.1:8000` | Backend URL for the frontend proxy |

Database paths are configured in `src/config.py`.

## Known limitations

- The explainer agent is currently commented out (returns `null`/empty). To re-enable, uncomment the marked blocks in `src/api/routes/query.py` and `src/llms/main_pipeline.py`.
- The vector index must be rebuilt if you change the database schema or the embedding model.
