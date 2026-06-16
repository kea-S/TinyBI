#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

if ! curl -sf http://localhost:8001/v1/models > /dev/null 2>&1; then
    echo "ERROR: vLLM is not running."
    echo "Start it with: ./scripts/start_vllm.sh"
    exit 1
fi

echo "vLLM is running. Starting insight eval..."

TINYBI_VLLM_URL="http://host.docker.internal:8002/v1" \
  docker compose run --rm promptfoo-eval promptfoo eval \
    -c src/eval/insight_config.yaml \
    --output data/app_data/insight_results.json
