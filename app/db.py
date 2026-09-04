from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.config import settings


def _connect() -> sqlite3.Connection:
    path = Path(settings.database_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    return connection


def init_db() -> None:
    with _connect() as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS request_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TEXT NOT NULL,
                endpoint TEXT NOT NULL,
                model TEXT,
                status_code INTEGER NOT NULL,
                latency_ms REAL NOT NULL,
                prompt_tokens INTEGER,
                completion_tokens INTEGER,
                streaming INTEGER NOT NULL
            )
            """
        )


def log_request(
    *,
    endpoint: str,
    model: str | None,
    status_code: int,
    latency_ms: float,
    prompt_tokens: int | None = None,
    completion_tokens: int | None = None,
    streaming: bool = False,
) -> None:
    with _connect() as connection:
        connection.execute(
            """
            INSERT INTO request_log (
                created_at, endpoint, model, status_code, latency_ms,
                prompt_tokens, completion_tokens, streaming
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                datetime.now(timezone.utc).isoformat(),
                endpoint,
                model,
                status_code,
                latency_ms,
                prompt_tokens,
                completion_tokens,
                int(streaming),
            ),
        )


def recent_requests(limit: int = 20) -> list[dict[str, Any]]:
    with _connect() as connection:
        rows = connection.execute(
            """
            SELECT created_at, endpoint, model, status_code, latency_ms,
                   prompt_tokens, completion_tokens, streaming
            FROM request_log
            ORDER BY id DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
    return [dict(row) for row in rows]
