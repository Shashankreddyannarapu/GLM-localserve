# Architecture

```text
Client / OpenAI SDK
        |
        |  Bearer token + OpenAI-compatible JSON/SSE
        v
+------------------------------+
| GLM LocalServe (FastAPI)     |
|                              |
| /v1/chat/completions         |
| /v1/models                   |
| /health                      |
| /metrics                     |
| /stats                       |
+---------------+--------------+
                |
                | HTTP / SSE
                v
+------------------------------+
| vLLM OpenAI-compatible server|
| zai-org/GLM-4-9B-0414        |
+---------------+--------------+
                |
                v
+------------------------------+
| NVIDIA DGX Spark             |
| Grace Blackwell / CUDA       |
+------------------------------+

Telemetry side path:
FastAPI -> Prometheus metrics + SQLite metadata log

Benchmark path:
benchmark.py -> FastAPI -> vLLM -> DGX Spark
             <- TTFT / latency / token usage
```

## Design choices

- **vLLM owns inference.** The project does not pretend to implement a new inference engine.
- **FastAPI owns the service contract.** Authentication, health checks, metrics, request metadata, and a stable API live outside the model runtime.
- **The gateway is OpenAI-compatible.** Existing clients can point their base URL at the local service.
- **No prompt text is persisted by default.** SQLite stores operational metadata rather than user content.
- **Inference and gateway are independently replaceable.** The upstream URL and model are environment variables, making it easy to evaluate another runtime or hardware target later.
