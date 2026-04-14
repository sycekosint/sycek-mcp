"""
Sycek OSINT MCP Server

Exposes 20 OSINT tools to any MCP-compatible AI assistant (Claude Desktop,
Cursor, Continue, etc.) covering three intelligence modules:

  BreachINT  — breach records, WHOIS, reverse WHOIS, caller ID, Gmail OSINT
  X/Twitter  — user profiles, tweets, search, reply trees, event investigation
  Social     — multi-platform search, narrative analysis, CIB detection, STIX 2.1

Configuration (environment variables):
  SYCEK_API_KEY  — required — your API key starting with sk_
                   Generate at: sycek.io/app/developer
  SYCEK_API_URL  — optional — API base URL (default: https://sycek.io/api)

Claude Desktop config snippet (stdio mode):
  {
    "mcpServers": {
      "sycek-osint": {
        "command": "python",
        "args": ["-m", "sycek_osint_mcp"],
        "env": {
          "SYCEK_API_KEY": "sk_...",
          "SYCEK_API_URL": "https://sycek.io/api"
        }
      }
    }
  }

Claude Desktop config snippet (hosted SSE mode):
  {
    "mcpServers": {
      "sycek-osint": {
        "url": "https://sycek.io/mcp/sse"
      }
    }
  }
"""
from mcp.server.fastmcp import FastMCP

from sycek_osint_mcp.tools import breach, twitter, social

mcp = FastMCP(
    name="sycek-osint",
    instructions=(
        "You have access to the Sycek OSINT Intelligence Platform — a professional-grade "
        "open-source intelligence toolkit covering breach intelligence, X/Twitter "
        "investigation, and social media intelligence.\n\n"
        "TOOL SELECTION GUIDANCE:\n"
        "- For a full dossier on a person/entity: start with breach_full_profile, "
        "then twitter_full_profile if they have a known X handle.\n"
        "- For social narrative analysis: start with social_search to get posts, "
        "then pass posts to social_analyze or social_intelligence.\n"
        "- For disinformation events: use twitter_event (tweet URL) + social_investigate.\n"
        "- For infrastructure pivoting: breach_whois → breach_reverse_whois.\n"
        "- To generate SIEM-ready threat intel: social_investigate → social_stix_export.\n\n"
        "CREDIT AWARENESS:\n"
        "Always tell the user the credit cost after each tool call (visible in the "
        "'Credits used' line of every response). Warn before using meta-tools "
        "(twitter_full_profile costs 9 credits, social_investigate costs ~10 credits).\n\n"
        "SEQUENCING RULES:\n"
        "social_analyze, social_intelligence, social_actor_profile, and social_stix_export "
        "require a posts array — always call social_search first. "
        "The social_investigate tool handles this sequencing automatically."
    ),
)

# Register all tool modules
breach.register(mcp)
twitter.register(mcp)
social.register(mcp)


def main() -> None:
    """
    Entry point for `sycek-osint-mcp` CLI and `python -m sycek_osint_mcp`.

    Transport is selected via MCP_TRANSPORT environment variable:
      stdio (default) — Claude Desktop spawns the process locally.
                        API key comes from SYCEK_API_KEY env var.
      sse             — Runs an HTTP SSE server (Docker/hosted).
                        API key is read per-connection from the request:
                          Authorization: Bearer sk_...   (preferred)
                          X-API-Key: sk_...
                          ?api_key=sk_...                (query param)
                        Each user's key is isolated — no shared credit pool.

    SSE env vars:
      MCP_HOST      — bind address (default: 0.0.0.0)
      MCP_PORT      — bind port    (default: 8001)
      SYCEK_API_KEY — optional fallback when no per-request key is provided
    """
    import os
    transport = os.environ.get("MCP_TRANSPORT", "stdio").lower()

    if transport == "sse":
        import uvicorn
        from sycek_osint_mcp.client import _api_key_ctx

        host = os.environ.get("MCP_HOST", "0.0.0.0")
        port = int(os.environ.get("MCP_PORT", "8001"))

        # Pure ASGI middleware — extracts the user's API key from each incoming
        # request (GET /sse and POST /messages/ both carry the key) and stores
        # it in a ContextVar so tool handlers can read it without any globals.
        # BaseHTTPMiddleware is avoided here because it buffers responses and
        # would break SSE streaming.
        class ApiKeyMiddleware:
            def __init__(self, app):
                self._app = app

            async def __call__(self, scope, receive, send):
                if scope["type"] in ("http", "websocket"):
                    key = _extract_key(scope)
                    token = _api_key_ctx.set(key)
                    try:
                        await self._app(scope, receive, send)
                    finally:
                        _api_key_ctx.reset(token)
                else:
                    await self._app(scope, receive, send)

        sse_app = mcp.sse_app()
        wrapped = ApiKeyMiddleware(sse_app)
        uvicorn.run(wrapped, host=host, port=port, log_level="info")
    else:
        mcp.run()  # stdio


def _extract_key(scope: dict) -> str:
    """
    Pull the user's API key from an ASGI scope.
    Checks (in order): Authorization header, X-API-Key header, api_key query param.
    """
    from urllib.parse import parse_qs

    headers = {k.lower(): v for k, v in scope.get("headers", [])}

    auth = headers.get(b"authorization", b"").decode()
    if auth.lower().startswith("bearer "):
        return auth[7:].strip()

    x_key = headers.get(b"x-api-key", b"").decode()
    if x_key:
        return x_key

    qs = parse_qs(scope.get("query_string", b"").decode())
    return qs.get("api_key", [""])[0]


if __name__ == "__main__":
    main()
