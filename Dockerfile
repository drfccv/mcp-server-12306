FROM python:3.12-alpine AS builder
WORKDIR /app
RUN pip install --no-cache-dir uv
COPY pyproject.toml uv.lock README.md ./
RUN uv sync --frozen --no-dev --no-install-project
COPY src ./src
RUN uv sync --frozen --no-dev && \
    find /app/.venv -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null; true

FROM python:3.12-alpine
WORKDIR /app
COPY --from=builder /app/.venv /app/.venv
COPY --from=builder /app/src /app/src
ENV PATH="/app/.venv/bin:$PATH"
ENV TZ=Asia/Shanghai
EXPOSE 8000
CMD ["python", "-m", "mcp_12306.http_server"]