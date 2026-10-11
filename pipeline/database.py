"""Database connection helpers for the VistaBalayan ETL pipeline.

The pipeline reads Supabase/PostgREST in batches and writes CSV files locally.
No database credentials should be committed to GitHub. Put local values in `.env`.
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any


DEFAULT_TABLES = ("establishments", "visitor_reports", "accommodation_reports", "room_occupancy_details")


@dataclass(frozen=True)
class DatabaseConfig:
    """Supabase REST connection settings loaded from environment variables."""

    supabase_url: str
    supabase_key: str
    batch_size: int = 1000

    @property
    def rest_url(self) -> str:
        return self.supabase_url.rstrip("/") + "/rest/v1"


def load_dotenv(path: str | Path = ".env") -> None:
    """Load simple KEY=VALUE pairs from a local .env file if it exists.

    This intentionally avoids a runtime dependency on python-dotenv.
    Existing environment variables are not overwritten.
    """

    env_path = Path(path)
    if not env_path.exists():
        return
    for line in env_path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


def load_database_config(env_path: str | Path = ".env") -> DatabaseConfig:
    """Load Supabase settings from .env/environment and validate required values."""

    load_dotenv(env_path)
    supabase_url = os.getenv("SUPABASE_URL", "").strip()
    supabase_key = (
        os.getenv("SUPABASE_SERVICE_ROLE_KEY", "").strip()
        or os.getenv("SUPABASE_ANON_KEY", "").strip()
        or os.getenv("SUPABASE_KEY", "").strip()
    )
    batch_size_text = os.getenv("BATCH_SIZE", "1000").strip() or "1000"
    try:
        batch_size = int(batch_size_text)
    except ValueError as exc:
        raise ValueError("BATCH_SIZE must be an integer") from exc
    if batch_size < 1:
        raise ValueError("BATCH_SIZE must be greater than zero")
    if not supabase_url:
        raise ValueError("Missing SUPABASE_URL. Create a local .env from .env.example.")
    if not supabase_key:
        raise ValueError("Missing SUPABASE key. Set SUPABASE_ANON_KEY or SUPABASE_SERVICE_ROLE_KEY in local .env.")
    return DatabaseConfig(supabase_url=supabase_url, supabase_key=supabase_key, batch_size=batch_size)


class SupabaseRestClient:
    """Small stdlib-only Supabase PostgREST client for batch extraction."""

    def __init__(self, config: DatabaseConfig):
        self.config = config

    def _headers(self) -> dict[str, str]:
        return {
            "apikey": self.config.supabase_key,
            "Authorization": f"Bearer {self.config.supabase_key}",
            "Accept": "application/json",
        }

    def fetch_rows(self, table: str, offset: int = 0, limit: int | None = None) -> list[dict[str, Any]]:
        """Fetch one ordered batch from a Supabase table."""

        batch_size = self.config.batch_size if limit is None else limit
        query = urllib.parse.urlencode({
            "select": "*",
            "order": "id.asc",
            "limit": str(batch_size),
            "offset": str(offset),
        })
        url = f"{self.config.rest_url}/{urllib.parse.quote(table)}?{query}"
        request = urllib.request.Request(url, headers=self._headers(), method="GET")
        try:
            with urllib.request.urlopen(request, timeout=60) as response:
                payload = response.read().decode("utf-8")
        except urllib.error.HTTPError as exc:
            details = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"Supabase request failed for {table}: HTTP {exc.code} {details}") from exc
        data = json.loads(payload)
        if not isinstance(data, list):
            raise RuntimeError(f"Unexpected Supabase response for {table}: expected a JSON list")
        return data

    def test_connection(self, table: str = "establishments") -> dict[str, Any]:
        """Test that Supabase can be reached by reading one row from a table."""

        rows = self.fetch_rows(table, offset=0, limit=1)
        return {"status": "PASS", "table": table, "sample_rows": len(rows)}


def create_client(env_path: str | Path = ".env") -> SupabaseRestClient:
    return SupabaseRestClient(load_database_config(env_path))
