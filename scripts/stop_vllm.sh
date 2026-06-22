#!/usr/bin/env bash
set -euo pipefail

REMOTE="keaharv@xlogin.comp.nus.edu.sg"

if [ -f /tmp/vllm_job_id ]; then
    JOB_ID=$(cat /tmp/vllm_job_id)
else
    echo "No job ID file found. Trying to find vLLM job..."
    JOB_ID=$(ssh "$REMOTE" "squeue -u keaharv -h -o '%i'" 2>/dev/null | head -1 || true)
    if [ -z "$JOB_ID" ]; then
        echo "No running Slurm jobs found."
        echo "Check with: ssh $REMOTE squeue -u keaharv"
        exit 1
    fi
fi

echo "=== Cancelling Slurm job $JOB_ID ==="
ssh "$REMOTE" "scancel $JOB_ID" 2>/dev/null || echo "Job may already be done"
echo "Job cancelled"

echo ""
echo "=== Killing SSH tunnel ==="
pkill -f "ssh -fL 8003:" 2>/dev/null || echo "No SSH tunnel found"
echo "SSH tunnel stopped"

echo ""
echo "=== Removing socat bridge ==="
docker rm -f vllm-bridge 2>/dev/null || echo "No socat bridge found"
echo "Socat bridge stopped"

rm -f /tmp/vllm_job_id
echo ""
echo "All cleaned up."
