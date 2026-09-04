from __future__ import annotations

import argparse
import asyncio
import csv
import json
import math
import statistics
import time
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path

DEFAULT_PROMPTS = [
    "Explain continuous batching in LLM inference in two paragraphs.",
    "Write a Python function that validates an IPv4 address and explain its complexity.",
    "Compare REST and gRPC for an internal model-serving platform.",
    "Summarize three practical ways to reduce LLM serving latency.",
    "Explain the difference between throughput and latency in inference systems.",
    "Give an example of a production health check for an AI inference service.",
    "Describe how containerization improves reproducibility for ML deployment.",
    "Explain why p95 latency is useful when benchmarking an API.",
]


@dataclass
class Result:
    request_id: int
    concurrency: int
    ttft_ms: float | None
    latency_ms: float
    completion_tokens: int | None
    tokens_per_second: float | None
    success: bool
    error: str | None = None


def percentile(values: list[float], p: float) -> float:
    if not values:
        return math.nan
    ordered = sorted(values)
    index = (len(ordered) - 1) * p
    lower = math.floor(index)
    upper = math.ceil(index)
    if lower == upper:
        return ordered[lower]
    return ordered[lower] + (ordered[upper] - ordered[lower]) * (index - lower)


async def run_request(
    client,
    request_id: int,
    concurrency: int,
    model: str,
    prompt: str,
    max_tokens: int,
    semaphore: asyncio.Semaphore,
) -> Result:
    async with semaphore:
        started = time.perf_counter()
        ttft_ms: float | None = None
        completion_tokens: int | None = None
        try:
            stream = await client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=max_tokens,
                temperature=0.2,
                stream=True,
                stream_options={"include_usage": True},
            )
            async for chunk in stream:
                if chunk.usage and chunk.usage.completion_tokens is not None:
                    completion_tokens = chunk.usage.completion_tokens
                if chunk.choices:
                    delta = chunk.choices[0].delta
                    text = getattr(delta, "content", None) or getattr(
                        delta, "reasoning_content", None
                    )
                    if text and ttft_ms is None:
                        ttft_ms = (time.perf_counter() - started) * 1000

            latency_ms = (time.perf_counter() - started) * 1000
            tps = None
            if completion_tokens and latency_ms > 0:
                tps = completion_tokens / (latency_ms / 1000.0)
            return Result(
                request_id=request_id,
                concurrency=concurrency,
                ttft_ms=ttft_ms,
                latency_ms=latency_ms,
                completion_tokens=completion_tokens,
                tokens_per_second=tps,
                success=True,
            )
        except Exception as exc:  # benchmark should record failures, not abort the run
            latency_ms = (time.perf_counter() - started) * 1000
            return Result(
                request_id=request_id,
                concurrency=concurrency,
                ttft_ms=ttft_ms,
                latency_ms=latency_ms,
                completion_tokens=completion_tokens,
                tokens_per_second=None,
                success=False,
                error=str(exc),
            )


async def benchmark(args: argparse.Namespace) -> list[Result]:
    from openai import AsyncOpenAI

    client = AsyncOpenAI(base_url=args.base_url, api_key=args.api_key)
    prompts = DEFAULT_PROMPTS * math.ceil(args.requests / len(DEFAULT_PROMPTS))
    prompts = prompts[: args.requests]
    semaphore = asyncio.Semaphore(args.concurrency)
    tasks = [
        run_request(
            client,
            request_id=i + 1,
            concurrency=args.concurrency,
            model=args.model,
            prompt=prompt,
            max_tokens=args.max_tokens,
            semaphore=semaphore,
        )
        for i, prompt in enumerate(prompts)
    ]
    results = await asyncio.gather(*tasks)
    await client.close()
    return results


def summarize(results: list[Result]) -> dict[str, object]:
    successful = [result for result in results if result.success]
    latencies = [result.latency_ms for result in successful]
    ttfts = [result.ttft_ms for result in successful if result.ttft_ms is not None]
    tps = [
        result.tokens_per_second
        for result in successful
        if result.tokens_per_second is not None
    ]
    return {
        "timestamp_utc": datetime.now(UTC).isoformat(),
        "requests": len(results),
        "successful": len(successful),
        "failed": len(results) - len(successful),
        "p50_latency_ms": percentile(latencies, 0.50),
        "p95_latency_ms": percentile(latencies, 0.95),
        "p50_ttft_ms": percentile(ttfts, 0.50),
        "p95_ttft_ms": percentile(ttfts, 0.95),
        "mean_tokens_per_second": statistics.fmean(tps) if tps else None,
    }


def write_results(results: list[Result], output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    csv_path = output_dir / "benchmark_results.csv"
    json_path = output_dir / "benchmark_summary.json"

    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=asdict(results[0]).keys())
        writer.writeheader()
        writer.writerows(asdict(result) for result in results)

    json_path.write_text(json.dumps(summarize(results), indent=2), encoding="utf-8")
    print(json.dumps(summarize(results), indent=2))
    print(f"\nSaved {csv_path} and {json_path}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Benchmark GLM LocalServe")
    parser.add_argument("--base-url", default="http://127.0.0.1:8000/v1")
    parser.add_argument("--api-key", default="local-dev-key")
    parser.add_argument("--model", default="zai-org/GLM-4-9B-0414")
    parser.add_argument("--requests", type=int, default=16)
    parser.add_argument("--concurrency", type=int, default=4)
    parser.add_argument("--max-tokens", type=int, default=128)
    parser.add_argument("--output-dir", default="benchmarks/results")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    results = asyncio.run(benchmark(args))
    if not results:
        raise SystemExit("No benchmark results produced")
    write_results(results, Path(args.output_dir))


if __name__ == "__main__":
    main()
