# Supermarket Query Dashboard

This project builds a small supermarket pricing dataset with TinyFish, stores it as a CSV, and lets you query it through a local web dashboard backed by deterministic SQL generation.

Current scope:
- supermarket data source coverage: FairPrice, Cold Storage, Sheng Siong
- query interface: natural language
- current product scope: noodles only

The naming is intentionally broader than noodles because the dashboard and query pipeline are meant to be reusable for wider supermarket product coverage later. Right now, the extracted dataset is constrained to noodle listings to keep the project scope controlled.

## Workflow

1. Run the ETL to scrape supermarket listings and write the CSV.
2. Launch the dashboard.
3. Ask natural-language questions such as:
   - `Give me the cheapest instant noodles globally`
   - `Give me the cheapest instant noodles in Sheng Siong`
   - `Give me the cheapest instant noodles that are not on sale in Sheng Siong with a weight above 1 kilogram`

## Setup

Python `3.13+` is recommended.

### Option 1: Using `uv`

```bash
uv venv
uv pip install -r requirements.txt
```

### Option 2: Standard Python

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Configuration

Create a `.env` file in the project root.

Use this template:

```env
GROQ_API_KEY=
OPENAI_API_KEY=
LANGSMITH_TRACING=true
LANGSMITH_ENDPOINT=https://api.smith.langchain.com
LANGSMITH_API_KEY=
LANGSMITH_PROJECT=
TINYFISH_API_KEY=
```

What is required vs optional:

- `TINYFISH_API_KEY`: required for the ETL
- `OPENAI_API_KEY`: required if you want to use OpenAI-backed query/explainer models
- `GROQ_API_KEY`: optional, only needed if you want to use the Groq-backed model option
- `LANGSMITH_API_KEY`, `LANGSMITH_TRACING`, `LANGSMITH_ENDPOINT`, `LANGSMITH_PROJECT`: optional, only needed if you want LangSmith tracing

Minimal examples:

If you only want to run the ETL:

```env
TINYFISH_API_KEY=your_tinyfish_api_key
```

If you want ETL plus the default dashboard model:

```env
OPENAI_API_KEY=your_openai_api_key
TINYFISH_API_KEY=your_tinyfish_api_key
```

If you want tracing enabled as well:

```env
GROQ_API_KEY=
OPENAI_API_KEY=your_openai_api_key
LANGSMITH_TRACING=true
LANGSMITH_ENDPOINT=https://api.smith.langchain.com
LANGSMITH_API_KEY=your_langsmith_api_key
LANGSMITH_PROJECT=spx-automation-technical
TINYFISH_API_KEY=your_tinyfish_api_key
```

## Run The ETL

This scrapes the currently configured supermarket pages and writes:

- [data/raw/noodle_database.csv](/Users/keaharvan/Documents/University/Spx-Automation-Technical/data/raw/noodle_database.csv)

Run:

```bash
python -m src.utils.etl
```

Debug payloads from TinyFish are written to:

- [data/raw/tinyfish_debug](/Users/keaharvan/Documents/University/Spx-Automation-Technical/data/raw/tinyfish_debug)

## Launch The Dashboard

The dashboard does not automatically run ETL. It uses the existing CSV if it is already present.

Run either:

```bash
python run_dashboard.py
```

or:

```bash
python -m src.web_dashboard
```

Useful flags:

```bash
python -m src.web_dashboard --no-browser
python -m src.web_dashboard --port 8001
```

If the CSV does not exist yet, the dashboard still launches, but queries will fail until you run the ETL.

## Quick Start

From a fresh clone, the shortest working path is:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Then create `.env`:

```env
OPENAI_API_KEY=your_openai_api_key
TINYFISH_API_KEY=your_tinyfish_api_key
```

Then run:

```bash
python -m src.utils.etl
python run_dashboard.py
```

## Project Structure

```text
.
├── data/
│   └── raw/
│       ├── noodle_database.csv
│       └── tinyfish_debug/
├── notebooks/
├── src/
│   ├── llms/
│   ├── tools/
│   ├── utils/
│   └── web_dashboard.py
├── run_dashboard.py
└── requirements.txt
```

## Notes

- The dashboard is named `Supermarket Query Dashboard`, but the current ETL and query schema are scoped to noodles.
- SQL generation is deterministic through a structured query schema rather than free-form SQL prompting.
- The notebook submission still exists in `notebooks/`, but the main runnable interface is now the local web dashboard.
