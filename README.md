# TinyBI

https://github.com/user-attachments/assets/ef863c27-7b77-49b3-8f8c-684482d04a33

Natural-language-to-SQL analytics pipeline: ask a business question in plain English, get back an SQL query, a result table, and an AI-generated explanation.

https://github.com/user-attachments/assets/beb64c96-c296-4536-b1c1-3189945a2dcc

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

## Quick Start

Requires **Python ≥ 3.13** and **Node.js ≥ 18**.

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

Create a `.env` file in the project root if you want to use OpenAI instead of local Ollama:

```env
OPENAI_API_KEY=sk-...
```

### 4. Install and start Ollama

**macOS / Linux:**

```bash
curl -fsSL https://ollama.com/install.sh | sh
ollama serve
```

**Windows:**

Download and run the installer from [ollama.com/download/windows](https://ollama.com/download/windows). Ollama starts automatically as a system tray service — no manual `serve` command needed.

### 5. Pull the required models

```bash
# Embedding model (used for vector search and index building)
ollama pull nomic-embed-text

# At least one chat model for extraction
ollama pull granite4:3b       # 3B — fastest, decent quality
# or
ollama pull llama3.2:3b       # alternative lightweight model
# or
ollama pull qwen2.5:7b        # larger, better quality
```

### 6. Set environment variables (optional)

The web app defaults to `granite4:3b` in local mode. To change the model or switch to remote, edit the `get_extractor` call in `src/api/routes/query.py`.

### Supported local models

| Model | Size | Notes |
|---|---|---|
| `granite4:3b` | 2 GB | Good balance of speed / quality |
| `gemma3:4b` | 2.5 GB | Google's lightweight model |
| `llama3.2:3b` | 2 GB | Meta's compact model |
| `phi4-mini:3.8b` | 2.4 GB | Microsoft's small model |
| `qwen2.5:7b` | 4.7 GB | Highest quality local option |

### Supported embedding models

| Model | Source | Notes |
|---|---|---|
| `nomic-embed-text` | Ollama | Default — 768-dim, fast |
| `qwen3-embedding:0.6b` | Ollama | Lightweight alternative |
| `bge-m3:567m` | Ollama | Multilingual |
| `text-embedding-3-small` | OpenAI | Remote — requires API key |

To change the embedding model, edit `DEFAULT_EMBEDDING_MODEL` in `src/utils/models.py:33`.

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

Use the **frontend's Vector Index Builder** — navigate to `/vector-index`, load the 41 columns from `data/app_data/columns.json`, verify them, and click "Submit Index Batch".

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

## Project structure

```
.
├── data/
│   ├── app_data/                  # FAISS vector index + column metadata
│   │   ├── columns.faiss          # 41 pre-built column embeddings
│   │   └── columns.json           # 41 column entries (descriptions, FK refs, etc.)
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
| `GROQ_API_KEY` | — | Alternative remote provider (Groq) |
| `VITE_BACKEND_URL` | `http://127.0.0.1:8000` | Backend URL for the frontend proxy |

Database paths are configured in `src/config.py`.

## Known limitations

- The explainer agent is currently commented out (returns `null`/empty). To re-enable, uncomment the marked blocks in `src/api/routes/query.py` and `src/llms/main_pipeline.py`.
- The vector index must be rebuilt if you change the database schema or the embedding model.
