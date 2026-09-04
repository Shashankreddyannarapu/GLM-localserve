# GLM LocalServe

A self-hosted, production-style LLM inference service for running **GLM locally on NVIDIA DGX Spark** instead of coupling an application directly to a paid hosted LLM endpoint.

The project deliberately separates the inference runtime from the application-facing service:

- **vLLM** serves `zai-org/GLM-4-9B-0414` on the DGX Spark GPU.
- **FastAPI** provides a stable OpenAI-compatible gateway, API-key validation, health checks, Prometheus metrics, and request metadata logging.
- **Benchmark tooling** measures time-to-first-token (TTFT), p50/p95 latency, output tokens/sec, failures, and concurrency behavior.
- **Docker + GitHub Actions** make the gateway reproducible and CI-tested without requiring a GPU runner.

> The model is configurable. If the GLM checkpoint you previously ran is different, change `MODEL_ID`; no gateway code changes are required.

## Why this project

A local model demo proves that a model can run. GLM LocalServe focuses on the software engineering needed to make that model usable by another application: a stable API contract, observability, health checks, deployment configuration, automated tests, and repeatable benchmarks.

## Architecture

```text
OpenAI SDK / application
          |
          v
  FastAPI gateway :8000
  - auth
  - /v1/chat/completions
  - /v1/models
  - /health
  - /metrics
  - SQLite request metadata
          |
          v
     vLLM :8001
          |
          v
  GLM on NVIDIA DGX Spark
```

See [ARCHITECTURE.md](ARCHITECTURE.md) for more detail.

## API surface

| Endpoint | Purpose |
|---|---|
| `POST /v1/chat/completions` | OpenAI-compatible chat completion proxy, including streaming |
| `GET /v1/models` | Proxies the vLLM model list |
| `GET /health` | Gateway + upstream readiness |
| `GET /metrics` | Prometheus-format request and latency metrics |
| `GET /stats` | Recent request metadata from SQLite |
| `GET /docs` | FastAPI Swagger documentation |

## 1. Configure

```bash
cp .env.example .env
set -a
source .env
set +a
```

For a public model, `HF_TOKEN` may not be necessary. Set it if your environment or chosen model requires Hugging Face authentication.

Change this if you used another GLM checkpoint:

```bash
export MODEL_ID="zai-org/GLM-4-9B-0414"
```

## 2. Start GLM with vLLM on DGX Spark

The included script follows the containerized DGX Spark serving pattern and binds vLLM to host port `8001` so the gateway can own `8000`.

```bash
./scripts/start_vllm_dgx_spark.sh
```

Watch model startup:

```bash
docker logs -f glm-vllm
```

Check vLLM directly:

```bash
curl http://127.0.0.1:8001/health
```

If the model does not fit with your chosen context size, reduce `MAX_MODEL_LEN`. Start with the repository default before tuning it upward.

## 3. Start the gateway

### Option A: local Python

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### Option B: Docker Compose

```bash
docker compose up -d --build
```

The compose file connects the gateway container to the vLLM server running on the DGX Spark host.

## 4. Call your local service

```bash
curl http://127.0.0.1:8000/v1/chat/completions \
  -H "Authorization: Bearer local-dev-key" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "zai-org/GLM-4-9B-0414",
    "messages": [{"role": "user", "content": "Explain continuous batching."}],
    "max_tokens": 128
  }'
```

Or use the OpenAI Python SDK while pointing it to the local service:

```python
from openai import OpenAI

client = OpenAI(
    base_url="http://127.0.0.1:8000/v1",
    api_key="local-dev-key",
)

response = client.chat.completions.create(
    model="zai-org/GLM-4-9B-0414",
    messages=[{"role": "user", "content": "What is TTFT?"}],
)
print(response.choices[0].message.content)
```

## 5. Smoke test

```bash
./scripts/smoke_test.sh
```

## 6. Benchmark

```bash
python -m benchmarks.benchmark \
  --requests 40 \
  --concurrency 4 \
  --max-tokens 128
```

The script saves:

```text
benchmarks/results/benchmark_results.csv
benchmarks/results/benchmark_summary.json
```

Run at multiple concurrency levels and copy the actual numbers into [BENCHMARKS.md](BENCHMARKS.md). Do not publish invented performance claims.

A notebook in `notebooks/benchmark_analysis.ipynb` loads the CSV and generates simple latency/TTFT summaries and plots.

## 7. Run tests and linting

No GPU is required for CI because HTTP calls to the inference backend are mocked.

```bash
pip install -r requirements-dev.txt
ruff check app benchmarks tests
pytest -q
```

GitHub Actions runs the same checks on pushes and pull requests.

## Repository layout

```text
app/                     FastAPI gateway, settings, SQLite metadata log
benchmarks/              Repeatable async inference benchmark
notebooks/               Benchmark analysis notebook
scripts/                  DGX Spark vLLM launcher + smoke test
tests/                    GPU-independent API/unit tests
.github/workflows/ci.yml  CI pipeline
ARCHITECTURE.md           System design
BENCHMARKS.md             Reproducible experiment template
Dockerfile                Gateway image
docker-compose.yml        Gateway deployment
```

## Security scope

This is a portfolio/reference implementation, not an internet-exposed SaaS service. It supports a gateway bearer token, but the vLLM backend should remain private (localhost/LAN/firewall) rather than being exposed directly to the public internet. Prompt bodies are not stored in SQLite by default.

## Suggested resume framing after you run it

> Deployed and served an open-source GLM model on NVIDIA DGX Spark using vLLM, built an OpenAI-compatible FastAPI inference gateway with health checks and runtime metrics, and benchmarked TTFT, tokens/sec, p95 latency, and concurrency; containerized and CI-tested the service with Docker and GitHub Actions.

Use real benchmark values in the resume once you have measured them.

## References

- NVIDIA DGX Spark vLLM serving playbook: https://build.nvidia.com/spark/vllm
- vLLM OpenAI-compatible server documentation: https://docs.vllm.ai/en/latest/serving/online_serving/openai_compatible_server/
- GLM-4-9B-0414 model page: https://huggingface.co/zai-org/GLM-4-9B-0414
