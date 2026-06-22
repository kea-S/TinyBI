#!/usr/bin/env bash
# scripts/check_vllm_health.sh
set -eo pipefail

REMOTE="keaharv@xlogin.comp.nus.edu.sg"

echo "=== 1. Checking Slurm Job Queue on NUS Cluster ==="
ssh "$REMOTE" "squeue -u keaharv" || echo "Failed to fetch squeue info."

echo ""
if [ -f /tmp/vllm_job_id ]; then
    SAVED_JOB_ID=$(cat /tmp/vllm_job_id)
    echo "Saved local job ID is: $SAVED_JOB_ID"
else
    echo "No saved local job ID found in /tmp/vllm_job_id"
fi

echo ""
echo "=== 2. Checking Remote vLLM Logs (/tmp/vllm.log) ==="
ssh "$REMOTE" "tail -n 25 /tmp/vllm.log" || echo "Failed to fetch remote log tail."

echo ""
echo "=== 3. Checking Local SSH Tunnel Process ==="
ps aux | grep "ssh -fL" | grep -v grep || echo "No local SSH tunnel process found."

echo ""
echo "=== 4. Checking Local socat Bridge Docker Container ==="
docker ps -a --filter name=vllm-bridge || echo "vllm-bridge container not found."

echo ""
echo "=== 5. Testing Local Endpoints ==="
echo -n "Pinging localhost:8003 (direct SSH tunnel): "
if curl -sf http://localhost:8003/v1/models > /dev/null 2>&1; then
    echo "SUCCESS (Ready)"
else
    echo "FAILED"
fi

echo -n "Pinging localhost:8002 (docker bridge): "
if curl -sf http://localhost:8002/v1/models > /dev/null 2>&1; then
    echo "SUCCESS (Ready)"
else
    echo "FAILED"
fi
