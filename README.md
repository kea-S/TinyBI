# TinyBI

Natural-language-to-SQL analytics pipeline: ask a business question in plain English, get back an SQL query, a result table, and an AI-generated explanation.

https://github.com/user-attachments/assets/cb99aeeb-8042-45b4-b035-0dec7fbd5d59

## Architecture

```
User question (natural language)
  → LLM Extractor  →  QuerySchema (structured intent)
  → Vector Search  →  Column resolution (FAISS over schema metadata)
  → SQL Generator  →  SQL query (SELECT, JOINs, WHERE, GROUP BY, ORDER BY, LIMIT)
  → DuckDB         →  pandas DataFrame
  → LLM Explainer  →  Business insight (optional, currently disabled)

Two interfaces:
  • Web app        —  FastAPI backend + React/Vite frontend
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

### 6. Set environment variables

**CLI chatbot:**

```bash
export TINYBI_MODEL=granite4:3b
export TINYBI_LOCAL=true
```

**Web app** — the API endpoint is hardcoded to use `granite4:3b` in local mode. To change the model, edit the `get_extractor` call in `src/api/routes/query.py`.

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
│   ├── main.py                    # CLI chatbot entry point
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
| `TINYBI_MODEL` | `gpt-4o` | Which model the CLI chatbot uses |
| `TINYBI_LOCAL` | `false` | Set to `true` for Ollama models in the CLI |
| `VITE_BACKEND_URL` | `http://127.0.0.1:8000` | Backend URL for the frontend proxy |

Database paths are configured in `src/config.py`.

## Known limitations

- The explainer agent is currently commented out (returns `null`/empty). To re-enable, uncomment the marked blocks in `src/api/routes/query.py` and `src/llms/main_pipeline.py`.
- The vector index must be rebuilt if you change the database schema or the embedding model.
