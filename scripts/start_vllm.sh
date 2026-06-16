#!/usr/bin/env bash
set -euo pipefail

REMOTE="keaharv@xlogin.comp.nus.edu.sg"

echo "=== Launching vLLM on cluster ==="
ssh "$REMOTE" \
  "nohup srun --gpus=a100-40 --time=02:00:00 \
   bash -c 'source ~/vllm_env/bin/activate && cd ~/vllm && VLLM_USE_FLASHINFER_SAMPLER=0 vllm serve ibm-granite/granite-4.1-3b --port 8001 --enable-auto-tool-choice --tool-call-parser granite4 --gpu-memory-utilization 0.85' \
   > /tmp/vllm.log 2>&1 &"

echo ""
echo "=== Waiting for job to start ==="
sleep 5
while true; do
    JOB_INFO=$(ssh "$REMOTE" "squeue -u keaharv -h -o '%i %T %N'" 2>/dev/null || true)
    if [ -n "$JOB_INFO" ]; then
        JOB_ID=$(echo "$JOB_INFO" | awk '{print $1}')
        STATE=$(echo "$JOB_INFO" | awk '{print $2}')
        HOSTNAME=$(echo "$JOB_INFO" | awk '{print $3}')
        if [ "$STATE" = "RUNNING" ]; then
            echo "Job $JOB_ID running on $HOSTNAME"
            break
        fi
        echo "  State: $STATE"
    fi
    sleep 10
done

echo ""
echo "=== Starting SSH tunnel (localhost:8001 -> $HOSTNAME:8001) ==="
ssh -fL 8001:"$HOSTNAME":8001 "$REMOTE" "sleep infinity"
echo "SSH tunnel started"

echo ""
echo "=== Starting socat bridge (Docker 8002 -> localhost:8001) ==="
docker rm -f vllm-bridge 2>/dev/null || true
docker run -d --name vllm-bridge -p 8002:8002 \
  alpine/socat tcp-listen:8002,fork,reuseaddr tcp:host.docker.internal:8001
echo "Socat bridge started"

echo ""
echo "=== Waiting for vLLM to be ready ==="
for i in $(seq 1 60); do
    if curl -sf http://localhost:8001/v1/models > /dev/null 2>&1; then
        echo "vLLM is ready!"
        break
    fi
    sleep 5
done

echo "$JOB_ID" > /tmp/vllm_job_id
echo ""
echo "vLLM is running (job $JOB_ID on $HOSTNAME)."
echo "Run: ./scripts/run_insight_eval.sh"
echo "Stop: ./scripts/stop_vllm.sh"
