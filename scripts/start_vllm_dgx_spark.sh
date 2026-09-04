#!/usr/bin/env bash
set -euo pipefail

MODEL_ID="${MODEL_ID:-zai-org/GLM-4-9B-0414}"
VLLM_IMAGE="${VLLM_IMAGE:-vllm/vllm-openai:latest}"
MAX_MODEL_LEN="${MAX_MODEL_LEN:-8192}"
GPU_MEMORY_UTILIZATION="${GPU_MEMORY_UTILIZATION:-0.80}"
HF_TOKEN="${HF_TOKEN:-}"
CONTAINER_NAME="${CONTAINER_NAME:-glm-vllm}"

mkdir -p "$HOME/.cache/huggingface/hub"

echo "Starting $MODEL_ID with vLLM on port 8001..."
docker pull "$VLLM_IMAGE"
docker rm -f "$CONTAINER_NAME" >/dev/null 2>&1 || true

docker run -d \
  --name "$CONTAINER_NAME" \
  --gpus all \
  --ipc host \
  --ulimit memlock=-1 \
  --ulimit stack=67108864 \
  --entrypoint "" \
  -p 8001:8000 \
  -e HF_TOKEN="$HF_TOKEN" \
  -v "$HOME/.cache/huggingface/hub:/root/.cache/huggingface/hub" \
  "$VLLM_IMAGE" \
  vllm serve "$MODEL_ID" \
    --max-model-len "$MAX_MODEL_LEN" \
    --gpu-memory-utilization "$GPU_MEMORY_UTILIZATION"

echo "Container: $CONTAINER_NAME"
echo "Watch startup: docker logs -f $CONTAINER_NAME"
echo "Health check: curl http://127.0.0.1:8001/health"
