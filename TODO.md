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

### H4: Empty SELECT clause (needs design discussion)
- [ ] When LLM fails to resolve any column, SQL becomes `SELECT FROM ...` -- DuckDB Parser Error.
- [ ] Option A: `COALESCE(1)` fallback (hides errors).
- [ ] Option B: Raise clear error, feed back to agent for self-correction.

### H5: Date operations in FilterIntent (deferred)
- [ ] Pipeline targets "simpler" SQL. Complex queries (CTEs, STRFTIME, subqueries) intended for LLM-generated SQL path, not the structured pipeline.
- [ ] Only add if a common high-value pattern emerges.

### Other cleanup
- [ ] `src/utils/queries.py` has unused hardcoded SQL templates -- candidate for removal.
- [ ] `src/llms/explainer.py` is loaded but disabled in `main_pipeline.py` -- wasteful model load.
