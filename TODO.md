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

