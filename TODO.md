# TinyBI: Monitoring & Performance Showcase

## Strategy: Monitoring-First Development
The goal is to frame the Text-to-SQL evaluation as a **"System Health & Monitoring"** feature. This proves the system is production-ready, auditable, and transparent about its performance across different LLM providers.

---

## Phase 1: The "Health Check" Engine (Benchmark Baseline)

- [x] **1. Finalize BIRD Benchmarking Data**
  - Use the 32 extracted queries in `data/app_data/bird_financial_minidev.json`.
  - Goal: Use these as the "Gold Standard" for monitoring system accuracy.
  - *Status: Completed. Extraction script `src/eval/generate_tests.py` implemented.*

- [x] **2. Implement Execution Accuracy (EX) Logic**
  - Use `src/eval/assertions.py` to compare LLM output vs. Gold SQL.
  - Logic: Execute both in DuckDB -> Compare DataFrames -> Return Match/Mismatch.
  - *Status: Completed. Assertions bridge and provider integration verified with TDD.*

- [ ] **3. Create the "Monitoring" API Endpoint**
  - Add a FastAPI route `GET /monitoring/health-check`.
  - This should run the 32 queries and return a JSON summary.

---

## Phase 2: The "Performance & Health" Dashboard (Frontend) - PENDING

- [ ] **1. Build the Monitoring Page (`/monitoring`)**
  - [ ] **Headline Stats:** Big cards for "Execution Accuracy", "Mean Latency", and "System Health".
  - [ ] **Model Switcher:** A UI toggle to switch between `Granite-3b (Local)` and `GPT-4o (Remote)`.
  - [ ] **Live Matrix:** A table showing the 32 "Health Check" queries with Pass/Fail indicators.

- [ ] **2. Data Visualization (The "BI" Factor)**
  - [ ] Integrate **Shadcn Charts** (or Recharts) to show:
    - Accuracy vs. Difficulty.
    - Latency per Query (Waterfall chart).

---

## Phase 3: Advanced "Wow" Features - PENDING

- [ ] **1. Semantic "Soft" Evaluation**
  - Integrate a "Semantic Match" score (using an LLM-as-a-judge) for cases where the data matches but the SQL syntax differs significantly.

- [ ] **2. Auto-Charting for Results**
  - Detect Time-Series vs. Categorical data in the main chat and automatically render Line/Bar charts above the result table.

- [ ] **3. Self-Correction Loop**
  - Add logic to catch SQL errors, feed them back to the LLM, and attempt a second "Self-Correction" run before showing the result to the user.

---

## Phase 4: Evaluation Pipeline Bug Fixes

### H1 -- FIXED: Race condition in DB connections
- [x] Singleton `_CONN` + per-query `close_connection()` caused "Connection already closed!" and "Call setup_database() before query()" errors under concurrent Promptfoo workers.
- [x] Rewrote `Database` to use per-call connections. Stores only the file path, not a persistent connection. `query()` opens a fresh connection each time.

### H7: NaN/Timestamp JSON serialization (quick win)
- [ ] Add NaN handling to `BenchmarkEncoder` in `provider.py` and `extractor_provider.py`. Check `math.isnan()` / `pd.isna()` and output `null`.

### H6: `loan.duration` misclassified as temporal (quick win)
- [ ] Fix vector index metadata: change `statistical_type` from `temporal` to `discrete`. Data comes from `data/app_data/columns.json` -- update there and rebuild FAISS index.

### H3: Missing columns in vector index (quick win)
- [ ] `district.A4`-`A16` columns missing from FAISS index. Gold SQL references `district.A11` (average salary) but it doesn't exist in the index.
- [ ] Search git history for original definitions: `git log -- data/app_data/columns.json`
- [ ] Rebuild vector index to include all columns.

### H2: Type compatibility filter (needs design discussion)
- [ ] Vector search places string categorical values ("North Bohemia") onto numeric columns (`trans.amount`). Need a type compatibility gate in `column_resolver.py:resolve_columns()`.
- [ ] Open question: how conservative should the gate be? Numeric comparisons like "balance > 10000" should still land on numeric columns.

### H4: Empty SELECT clause -- FIXED
- [x] When LLM fails to resolve any column, SQL becomes `SELECT FROM ...` -- DuckDB Parser Error.
- [x] Chose Option B: Raise clear error, feed back to agent for self-correction.
- [x] Guard added in `src/tools/query_tool.py:73-78`.

### H5: Date operations in FilterIntent (deferred)
- [ ] Pipeline targets "simpler" SQL. Complex queries (CTEs, STRFTIME, subqueries) intended for LLM-generated SQL path, not the structured pipeline.
- [ ] Only add if a common high-value pattern emerges.

### Other cleanup
- [ ] `src/utils/queries.py` has unused hardcoded SQL templates -- candidate for removal.
- [ ] `src/llms/explainer.py` is loaded but disabled in `main_pipeline.py` -- wasteful model load.

---

## Phase 5: Insight-Level Evaluation (LLM-as-a-Judge)

**Strategy:** Binary EX is the wrong metric -- the constrained `QuerySchema` can't express CTEs, STRFTIME, or complex subqueries, so EX will be near zero. Instead, evaluate whether the *insight* from the generated answer matches the gold answer.

### 5a. Three-way LLM-as-a-Judge comparison

For each of the 32 BIRD queries, produce three answers:
1. **Gold answer** -- execute gold SQL, get result
2. **TinyBI answer** -- agent pipeline generating SQL via `QuerySchema`, execute, get result
3. **Baseline answer** -- full schema dump, one LLM call -> raw SQL, execute, get result

Ask GPT-4o (LLM-as-a-judge): *"Do these two answers convey the same insight?"* with three pairwise comparisons:
- [ ] TinyBI vs Gold -> TinyBI's insight accuracy
- [ ] Baseline vs Gold -> baseline's insight accuracy (benchmark)
- [ ] TinyBI vs Baseline -> agreement score

### 5b. Efficiency metrics (comparative -- currently zero tracking exists)

Instrument the agent loop to capture:
- [x] **Token counting** — `AIMessage.usage_metadata` captured in `agent.py:93-112`. Passed to promptfoo as top-level `tokenUsage` in `provider.py:74`.
- [ ] **Latency tracking** -- `time.perf_counter()` around LLM calls, tool calls, SQL execution. Compute breakdown: discovery vs generation vs execution.
- [ ] **Cost tracking** -- tokens x model pricing ($/1K tokens).
- [ ] **Schema discovery rate** -- columns agent touches / total schema columns.

### 5c. Full schema dump baseline

New code needed (no shared code with existing pipeline):
- [x] `src/baselines/ddl_generator.py` — convert `columns.json` → DuckDB DDL with full comment annotations (description, aliases, statistical_type, categorical_values, sample_values, FKs). 10 TDD tests.
- [x] `src/baselines/raw_query_tool.py` — LangChain tool wrapping `global_database.query()`, takes raw SQL string, returns (result_summary, (df, sql)). 13 TDD tests.
- [x] `src/baselines/schema_dump_agent.py` — Agent using `raw_query_tool` with DDL in system prompt. Same LangGraph loop as TinyBI. 7 TDD tests (incl. e2e integration against Ollama).
- [x] `src/eval/provider.py` — Unified promptfoo provider with `config.agent_type` routing: `"tinybi"` (default) → `run_agent`, `"schema_dump"` → `run_schema_dump_agent`. Shared BenchmarkEncoder. 4 TDD tests.
- [x] `src/eval/comparison_config.yaml` — TinyBI vs Schema Dump side-by-side, granite4:3b, same test suite.
- Run: `./scripts/eval.sh -c src/eval/comparison_config.yaml --output data/app_data/eval_results.json`

### 5d. Composite narrative metric

- [ ] **Tokens consumed per correct insight.** Headline number that sells the architecture tradeoff.

### 5e. Component-level accuracy (fallback if insight eval noisy)

Grade individual `QuerySchema` fields against what the gold SQL does:
- [ ] Table selection accuracy (right tables identified?)
- [ ] Filter column accuracy (right column for each filter?)
- [ ] Filter value accuracy (right DB value for each concept?)
- [ ] Aggregation accuracy (COUNT vs AVG vs SUM?)
- [ ] Metrics accuracy (right entity being measured?)
