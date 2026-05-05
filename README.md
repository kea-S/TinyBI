# TinyBI

https://github.com/user-attachments/assets/cb99aeeb-8042-45b4-b035-0dec7fbd5d59

## Project Setup and Execution Guide

This project is optimised for reproducibility using the `uv` package manager, but also supports standard Python virtual environments using `pip`.

For maximum compatibility, use python 3.13.5>=

**The projects main entrypoint is notebooks/submission.ipynb**

---

### Option 1: Using `uv` (Recommended)

If you have `uv` installed, this is the most efficient method to ensure environment parity.

1. Unzip the project folder.
2. Open a terminal in the project root directory.
3. Launch the notebook server using the following commands:
```bash
uv venv
uv pip install -r requirements.txt
uv run jupyter lab
```

---

### Option 2: Standard Python (Alternative)

If you do not have `uv` installed, follow these steps to set up the environment manually:

1. Create and activate a virtual environment:
```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
```

2. Install the necessary dependencies:
```bash
pip install -r requirements.txt
```

3. Launch the Jupyter server:
```bash
jupyter lab
```

---

### Configuration

Before executing the cells in the notebook, ensure you have a `.env` file located in the project root directory containing your API credentials:
e.g.
```env
OPENAI_API_KEY=your_actual_key_here
```
there's a script inside notebooks/submission.ipynb that you can edit to set easily

---

### Project Structure
```
.
├── notebooks/       # Contains the main submission notebook (submission.ipynb)
├── src/             # Core logic, pipeline components, and configuration files
├── data/            # Directory for raw and processed dataset storage
└── requirements.txt # List of project dependencies
```

## TODO

## Phase 1 — Schema profiling
- [ ] Pick one BIRD database to develop against
- [ ] Implement automatic schema profiler (column stats, distinct value counts, top-k samples, FK detection)
- [ ] LLM-summarise each column from profile output (short description for schema linking, long for SQL generation)
- [ ] Build LSH index for literal matching

## Phase 2 — Template / deterministic path
- [ ] Analyse query distribution on chosen database — cluster by structural intent, identify top N query shapes
- [ ] Build SQL template layer for top N intents (parametric, not hardcoded — schema attributes injected at runtime)
- [ ] Build intent classifier to route queries to a template or fallback (fine-tune small open-source model here)
- [ ] Tune classifier confidence threshold

## Phase 3 — Fallback / free-generation path
- [ ] Implement free SQL generation using open-source model with schema-linked columns + long column descriptions
- [ ] Build query bank for RAG few-shot retrieval (seed with BIRD training pairs + SQL-to-text generated questions)
- [ ] Implement semantic retrieval for few-shot examples
- [ ] Add post-generation SQL validation with one retry on failure

## Phase 4 — Eval harness
- [ ] Set up execution accuracy on BIRD mini-dev (500 questions)
- [ ] Instrument latency per query, measured separately for template path vs fallback path
- [ ] Run ablations: template-only vs fallback-only vs hybrid; RAG vs no-RAG; classifier model size comparisons
- [ ] Document failure modes honestly

## Phase 5 — Production layer
- [ ] Wrap pipeline in a FastAPI endpoint (POST /query — input: question + db connection, output: SQL + result + latency)
- [ ] Dockerise — must run fully locally with no external API calls
