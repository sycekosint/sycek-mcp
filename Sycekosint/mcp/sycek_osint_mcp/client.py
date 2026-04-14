"""
Shared async HTTP client for all Sycek OSINT MCP tools.

API key resolution order (first non-empty wins):
  1. Per-request ContextVar  — set by ApiKeyMiddleware from the SSE connection
                               (Authorization: Bearer sk_... or X-API-Key header,
                                or ?api_key=sk_... query param)
  2. SYCEK_API_KEY env var   — stdio mode (Claude Desktop local config) or fallback

Configuration:
  SYCEK_API_URL  — optional — defaults to https://sycek.io/api
                   (Docker: set to http://api:8000 to bypass nginx)
  SYCEK_API_KEY  — optional in SSE mode (key comes from per-connection header/param)
                   required in stdio mode
"""
import contextvars
import os
from typing import Any
from urllib.parse import parse_qs

import httpx

BASE_URL: str = os.environ.get("SYCEK_API_URL", "https://sycek.io/api").rstrip("/")

# Per-connection API key — set by ApiKeyMiddleware in SSE mode.
# Falls back to SYCEK_API_KEY env var when not set (stdio mode).
_api_key_ctx: contextvars.ContextVar[str] = contextvars.ContextVar("mcp_api_key", default="")

# Singleton connection pool — no API key baked in; injected per-request instead
_client: httpx.AsyncClient | None = None


def _get_client() -> httpx.AsyncClient:
    global _client
    if _client is None or _client.is_closed:
        _client = httpx.AsyncClient(
            base_url=BASE_URL,
            headers={"User-Agent": "sycek-osint-mcp/0.1.0"},
            timeout=httpx.Timeout(120.0, connect=10.0),
        )
    return _client


def _effective_key() -> str:
    """Return the API key for the current request context."""
    return _api_key_ctx.get() or os.environ.get("SYCEK_API_KEY", "")


async def api_get(path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
    """HTTP GET against the Sycek API. Returns parsed JSON dict."""
    key = _effective_key()
    if not key:
        raise RuntimeError(
            "No API key available. In stdio mode: set SYCEK_API_KEY in your MCP config. "
            "In SSE mode: pass Authorization: Bearer sk_... header or ?api_key=sk_... param."
        )
    client = _get_client()
    cleaned = {k: v for k, v in (params or {}).items() if v is not None}
    resp = await client.get(path, params=cleaned, headers={"X-API-Key": key})
    _check_response(resp)
    return resp.json()


async def api_post(path: str, body: dict[str, Any]) -> dict[str, Any]:
    """HTTP POST against the Sycek API. Returns parsed JSON dict."""
    key = _effective_key()
    if not key:
        raise RuntimeError(
            "No API key available. In stdio mode: set SYCEK_API_KEY in your MCP config. "
            "In SSE mode: pass Authorization: Bearer sk_... header or ?api_key=sk_... param."
        )
    client = _get_client()
    resp = await client.post(path, json=body, headers={"X-API-Key": key})
    _check_response(resp)
    return resp.json()


def _check_response(resp: httpx.Response) -> None:
    """Translate HTTP error codes into descriptive exceptions for Claude to read."""
    if resp.is_success:
        return

    detail = ""
    try:
        detail = resp.json().get("detail", "")
    except Exception:
        pass

    if resp.status_code == 401:
        raise PermissionError(
            "Invalid API key — check the key in your MCP client config. "
            "Generate a new key at sycek.io/app/developer"
        )
    if resp.status_code == 402:
        raise ValueError(
            f"Insufficient credits — {detail}. "
            "Top up at sycek.io/app/subscription"
        )
    if resp.status_code == 403:
        raise PermissionError(
            f"Access denied — {detail}. "
            "Upgrade your plan at sycek.io/app/subscription"
        )
    if resp.status_code == 404:
        raise LookupError(f"Not found — {detail or resp.url}")
    if resp.status_code == 429:
        raise ConnectionError("Rate limit exceeded — wait 60 seconds before retrying")
    if resp.status_code == 503:
        raise ConnectionError("Sycek API temporarily unavailable — wait 30 seconds and retry")

    resp.raise_for_status()
