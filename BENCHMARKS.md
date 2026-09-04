# Benchmarks

This file is intentionally shipped without fabricated numbers. Run the benchmark on the actual DGX Spark and commit the resulting measurements.

## Test configuration

| Field | Value |
|---|---|
| Hardware | NVIDIA DGX Spark |
| Model | `zai-org/GLM-4-9B-0414` (replace if you used a different GLM checkpoint) |
| Runtime | vLLM |
| Gateway | GLM LocalServe / FastAPI |
| Max output tokens | 128 |
| Concurrency levels | 1, 4, 8 |

## Commands

```bash
python -m benchmarks.benchmark --requests 20 --concurrency 1 --output-dir benchmarks/results/c1
python -m benchmarks.benchmark --requests 40 --concurrency 4 --output-dir benchmarks/results/c4
python -m benchmarks.benchmark --requests 80 --concurrency 8 --output-dir benchmarks/results/c8
```

## Results to report

| Concurrency | p50 TTFT (ms) | p95 TTFT (ms) | p50 latency (ms) | p95 latency (ms) | Mean output tok/s | Success rate |
|---:|---:|---:|---:|---:|---:|---:|
| 1 | TODO | TODO | TODO | TODO | TODO | TODO |
| 4 | TODO | TODO | TODO | TODO | TODO | TODO |
| 8 | TODO | TODO | TODO | TODO | TODO | TODO |

## Interview notes

Be prepared to explain:

1. Why TTFT and p95 latency matter in interactive inference.
2. How concurrency changes throughput and tail latency.
3. Why the gateway and vLLM server are separate processes.
4. What DGX Spark resource limit you hit first, if any.
5. Which vLLM settings you changed and what effect they had.

Only replace TODO values with measurements you personally collected.
