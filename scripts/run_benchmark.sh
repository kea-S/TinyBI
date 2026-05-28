#!/bin/bash

# Default paths (relative to the project's 'data/' directory)
INPUT_JSON="data/app_data/bird_financial_minidev.json"
OUTPUT_YAML="src/eval/tests.yaml"
PROMPTFOO_CONFIG="src/eval/bare_config.yaml"
DUCKDB_PATH="minidev_raw/financial/financial.duckdb"
SQLITE_DIR="minidev_raw/financial"
NUM_SAMPLES=""

# Allow overriding via CLI args
while [[ "$#" -gt 0 ]]; do
    case $1 in
        --input) INPUT_JSON="$2"; shift ;;
        --output) OUTPUT_YAML="$2"; shift ;;
        --config) PROMPTFOO_CONFIG="$2"; shift ;;
        --duckdb) DUCKDB_PATH="$2"; shift ;;
        --sqlite) SQLITE_DIR="$2"; shift ;;
        --samples) NUM_SAMPLES="$2"; shift ;;
        *) echo "Unknown parameter passed: $1"; exit 1 ;;
    esac
    shift
done

echo "Starting BIRD Benchmarking Pipeline..."

# 1. Generate tests
echo "Step 1: Generating tests from $INPUT_JSON..."
GENERATE_CMD="PYTHONPATH=. uv run python src/eval/generate_tests.py --input $INPUT_JSON --output $OUTPUT_YAML"
if [ -n "$NUM_SAMPLES" ]; then
    GENERATE_CMD="$GENERATE_CMD --samples $NUM_SAMPLES"
fi
eval $GENERATE_CMD

if [ $? -ne 0 ]; then
    echo "Error: Test generation failed."
    exit 1
fi

# 1.5 Prepare Database
echo "Step 1.5: Preparing database at $DUCKDB_PATH..."
PYTHONPATH=. uv run python scripts/prepare_db.py --duckdb "$DUCKDB_PATH" --sqlite "$SQLITE_DIR"

if [ $? -ne 0 ]; then
    echo "Error: Database preparation failed."
    exit 1
fi

# 2. Run Promptfoo
echo "Step 2: Running Promptfoo with config $PROMPTFOO_CONFIG..."

# Ensure promptfoo uses the uv virtual environment python
export PROMPTFOO_PYTHON=$(uv run which python)
export PYTHONPATH=.
echo "Using Python from: $PROMPTFOO_PYTHON with PYTHONPATH=$PYTHONPATH"

# Using npx promptfoo@latest is safer to ensure compatibility with the current Node version
npx promptfoo@latest eval -c "$PROMPTFOO_CONFIG" --output "data/app_data/eval_results.json"

echo "Pipeline complete. Results saved to data/app_data/eval_results.json"



