FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

# Copy package and install dependencies
COPY pyproject.toml .
COPY sycek_osint_mcp/ sycek_osint_mcp/
RUN pip install --no-cache-dir -e .

# SSE transport — binds on 0.0.0.0:8001
ENV MCP_TRANSPORT=sse
ENV MCP_HOST=0.0.0.0
ENV MCP_PORT=8001

# SYCEK_API_KEY and SYCEK_API_URL are injected at runtime via docker-compose env
EXPOSE 8001

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s \
    CMD curl -f http://localhost:8001/health || exit 1

CMD ["python", "-m", "sycek_osint_mcp"]
