from __future__ import annotations

import asyncio
import time
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

import httpx
from fastapi import Depends, FastAPI, Header, HTTPException, Query, Request, status
from fastapi.responses import JSONResponse, Response, StreamingResponse
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest

from app.config import settings
from app.db import init_db, log_request, recent_requests

REQUESTS = Counter(
    "glm_localserve_requests_total",
    "Requests handled by the GLM LocalServe gateway",
    ["endpoint", "status_code", "streaming"],
)
LATENCY = Histogram(
    "glm_localserve_request_latency_seconds",
    "End-to-end gateway request latency",
    ["endpoint", "streaming"],
)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    init_db()
    app.state.upstream = httpx.AsyncClient(
        base_url=settings.upstream_base_url,
        timeout=httpx.Timeout(settings.request_timeout_seconds),
    )
    yield
    await app.state.upstream.aclose()


app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    description=(
        "Production-style gateway for a locally hosted GLM model served by vLLM "
        "on NVIDIA DGX Spark."
    ),
    lifespan=lifespan,
)


def require_api_key(authorization: str | None = Header(default=None)) -> None:
    expected = f"Bearer {settings.local_api_key}"
    if authorization != expected:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid API key",
        )


def _usage_from_payload(payload: dict[str, Any]) -> tuple[int | None, int | None]:
    usage = payload.get("usage") or {}
    return usage.get("prompt_tokens"), usage.get("completion_tokens")


async def _record(
    *,
    endpoint: str,
    model: str | None,
    status_code: int,
    latency_ms: float,
    streaming: bool,
    prompt_tokens: int | None = None,
    completion_tokens: int | None = None,
) -> None:
    REQUESTS.labels(endpoint, str(status_code), str(streaming).lower()).inc()
    LATENCY.labels(endpoint, str(streaming).lower()).observe(latency_ms / 1000.0)
    await asyncio.to_thread(
        log_request,
        endpoint=endpoint,
        model=model,
        status_code=status_code,
        latency_ms=latency_ms,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        streaming=streaming,
    )


@app.get("/")
async def root() -> dict[str, str]:
    return {
        "service": settings.app_name,
        "model": settings.model_id,
        "docs": "/docs",
        "health": "/health",
        "metrics": "/metrics",
    }


@app.get("/health")
async def health(request: Request) -> JSONResponse:
    try:
        upstream = await request.app.state.upstream.get("/health", timeout=5.0)
        upstream_ok = upstream.is_success
        upstream_status = upstream.status_code
    except httpx.HTTPError:
        upstream_ok = False
        upstream_status = 0

    payload = {
        "gateway": "ok",
        "upstream": "ok" if upstream_ok else "unavailable",
        "upstream_status_code": upstream_status,
        "model": settings.model_id,
    }
    return JSONResponse(payload, status_code=200 if upstream_ok else 503)


@app.get("/metrics")
async def metrics() -> Response:
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.get("/stats", dependencies=[Depends(require_api_key)])
async def stats(limit: int = Query(default=20, ge=1, le=200)) -> dict[str, Any]:
    return {"requests": await asyncio.to_thread(recent_requests, limit)}


@app.get("/v1/models", dependencies=[Depends(require_api_key)])
async def models(request: Request) -> Response:
    started = time.perf_counter()
    endpoint = "/v1/models"
    try:
        response = await request.app.state.upstream.get(endpoint)
        latency_ms = (time.perf_counter() - started) * 1000
        await _record(
            endpoint=endpoint,
            model=settings.model_id,
            status_code=response.status_code,
            latency_ms=latency_ms,
            streaming=False,
        )
        return Response(
            content=response.content,
            status_code=response.status_code,
            media_type=response.headers.get("content-type", "application/json"),
        )
    except httpx.HTTPError as exc:
        latency_ms = (time.perf_counter() - started) * 1000
        await _record(
            endpoint=endpoint,
            model=settings.model_id,
            status_code=502,
            latency_ms=latency_ms,
            streaming=False,
        )
        raise HTTPException(status_code=502, detail=f"Upstream error: {exc}") from exc


@app.post("/v1/chat/completions", dependencies=[Depends(require_api_key)])
async def chat_completions(request: Request) -> Response:
    endpoint = "/v1/chat/completions"
    payload = await request.json()
    payload.setdefault("model", settings.model_id)
    streaming = bool(payload.get("stream", False))
    started = time.perf_counter()

    if not streaming:
        try:
            response = await request.app.state.upstream.post(endpoint, json=payload)
        except httpx.HTTPError as exc:
            latency_ms = (time.perf_counter() - started) * 1000
            await _record(
                endpoint=endpoint,
                model=payload.get("model"),
                status_code=502,
                latency_ms=latency_ms,
                streaming=False,
            )
            raise HTTPException(status_code=502, detail=f"Upstream error: {exc}") from exc

        latency_ms = (time.perf_counter() - started) * 1000
        prompt_tokens = completion_tokens = None
        if response.headers.get("content-type", "").startswith("application/json"):
            try:
                prompt_tokens, completion_tokens = _usage_from_payload(response.json())
            except ValueError:
                pass

        await _record(
            endpoint=endpoint,
            model=payload.get("model"),
            status_code=response.status_code,
            latency_ms=latency_ms,
            streaming=False,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
        )
        return Response(
            content=response.content,
            status_code=response.status_code,
            media_type=response.headers.get("content-type", "application/json"),
        )

    upstream_request = request.app.state.upstream.build_request(
        "POST", endpoint, json=payload
    )
    try:
        upstream_response = await request.app.state.upstream.send(
            upstream_request, stream=True
        )
    except httpx.HTTPError as exc:
        latency_ms = (time.perf_counter() - started) * 1000
        await _record(
            endpoint=endpoint,
            model=payload.get("model"),
            status_code=502,
            latency_ms=latency_ms,
            streaming=True,
        )
        raise HTTPException(status_code=502, detail=f"Upstream error: {exc}") from exc

    async def relay() -> AsyncIterator[bytes]:
        try:
            async for chunk in upstream_response.aiter_raw():
                yield chunk
        finally:
            await upstream_response.aclose()
            latency_ms = (time.perf_counter() - started) * 1000
            await _record(
                endpoint=endpoint,
                model=payload.get("model"),
                status_code=upstream_response.status_code,
                latency_ms=latency_ms,
                streaming=True,
            )

    return StreamingResponse(
        relay(),
        status_code=upstream_response.status_code,
        media_type=upstream_response.headers.get("content-type", "text/event-stream"),
    )
