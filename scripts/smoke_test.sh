#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${BASE_URL:-http://127.0.0.1:8000}"
API_KEY="${LOCAL_API_KEY:-local-dev-key}"
MODEL_ID="${MODEL_ID:-zai-org/GLM-4-9B-0414}"

curl -fsS "$BASE_URL/health" | python -m json.tool

curl -fsS "$BASE_URL/v1/chat/completions" \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d "{\"model\":\"$MODEL_ID\",\"messages\":[{\"role\":\"user\",\"content\":\"Explain TTFT in one sentence.\"}],\"max_tokens\":64}" \
  | python -m json.tool
