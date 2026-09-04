from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    app_name: str = os.getenv("APP_NAME", "GLM LocalServe")
    upstream_base_url: str = os.getenv("UPSTREAM_BASE_URL", "http://127.0.0.1:8001")
    model_id: str = os.getenv("MODEL_ID", "zai-org/GLM-4-9B-0414")
    local_api_key: str = os.getenv("LOCAL_API_KEY", "local-dev-key")
    database_path: str = os.getenv("DATABASE_PATH", "data/requests.db")
    request_timeout_seconds: float = float(os.getenv("REQUEST_TIMEOUT_SECONDS", "300"))


settings = Settings()
