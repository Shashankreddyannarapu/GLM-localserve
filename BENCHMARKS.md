# Benchmarks

GLM LocalServe was previously validated on NVIDIA DGX Spark with GLM served through vLLM and accessed through the FastAPI gateway.

This repository includes a reproducible benchmark harness for evaluating local LLM inference performance. Historical performance measurements from the original DGX Spark deployment were not retained, so this repository does not publish estimated or reconstructed benchmark values.

## Benchmark Metrics

The benchmark suite measures the following serving characteristics:

- **Time to First Token (TTFT):** Time between sending a request and receiving the first generated token.
- **End-to-End Latency:** Total time required to complete an inference request.
- **Output Throughput:** Number of generated tokens per second.
- **p50 Latency:** Median request latency.
- **p95 Latency:** Tail latency experienced by slower requests.
- **Concurrency:** Serving behavior with multiple simultaneous requests.
- **Success Rate:** Percentage of requests completed successfully.

These metrics were selected to evaluate both interactive response performance and inference-server behavior under increasing request concurrency.

## Validation Configuration

| Field | Configuration |
|---|---|
| Hardware | NVIDIA DGX Spark |
| Model family | GLM |
| Repository default model | `zai-org/GLM-4-9B-0414` |
| Inference runtime | vLLM |
| API gateway | FastAPI / GLM LocalServe |
| API format | OpenAI-compatible Chat Completions |
| Maximum output tokens | 128 |
| Concurrency levels | 1, 4, 8 |
| Deployment | Containerized local inference |

> The repository default checkpoint can be changed through `MODEL_ID` to reproduce the deployment with another compatible GLM checkpoint.

## Reproducing the Benchmark

Start the vLLM inference server and GLM LocalServe gateway before running the benchmark suite.

### Concurrency 1

```bash
python -m benchmarks.benchmark \
  --requests 20 \
  --concurrency 1 \
  --output-dir benchmarks/results/c1
```

### Concurrency 4

```bash
python -m benchmarks.benchmark \
  --requests 40 \
  --concurrency 4 \
  --output-dir benchmarks/results/c4
```

### Concurrency 8

```bash
python -m benchmarks.benchmark \
  --requests 80 \
  --concurrency 8 \
  --output-dir benchmarks/results/c8
```

Increasing concurrency allows the benchmark to evaluate how the serving stack behaves as multiple inference requests compete for the available compute and memory resources.

## Results

Historical measurements from the original DGX Spark validation were not retained. The table below is therefore intentionally left unpopulated until the benchmark is rerun on compatible hardware.

| Concurrency | p50 TTFT (ms) | p95 TTFT (ms) | p50 Latency (ms) | p95 Latency (ms) | Mean Output tok/s | Success Rate |
|---:|---:|---:|---:|---:|---:|---:|
| 1 | — | — | — | — | — | — |
| 4 | — | — | — | — | — | — |
| 8 | — | — | — | — | — | — |

No benchmark values are estimated or reconstructed.

## Benchmark Architecture

```text
Benchmark Client
       |
       | Concurrent HTTP requests
       v
+-----------------------------+
| GLM LocalServe              |
| FastAPI Gateway             |
|                             |
| /v1/chat/completions        |
| /health                     |
| /metrics                    |
+-------------+---------------+
              |
              | OpenAI-compatible request
              v
+-----------------------------+
| vLLM Inference Server       |
|                             |
| GLM Model                   |
+-------------+---------------+
              |
              v
       NVIDIA DGX Spark
```

Separating the API gateway from the inference runtime allows application-level functionality such as request validation, observability, health checks, and logging to remain independent of the underlying model-serving engine.

## Reproducibility

Benchmark output should be stored under:

```text
benchmarks/results/
```

Example:

```text
benchmarks/
├── benchmark.py
└── results/
    ├── c1/
    ├── c4/
    └── c8/
```

When new measurements are collected, the results can be committed alongside the model configuration and serving parameters used during the run.

This keeps performance claims traceable to an actual hardware execution rather than estimated values.
