FROM python:3.12-slim AS base

WORKDIR /app/jobs/image-download

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Copy shared-py to match local layout
COPY shared-py/ /app/shared-py/

# Copy job files
COPY jobs/image-download/ .

# Install production dependencies
RUN uv sync --frozen --no-dev

# Test stage — runs pytest, fails build if tests fail
FROM base AS test
RUN uv sync --frozen
RUN uv run pytest

# Production stage — clean image without test deps
FROM base AS production

# Run as non-root user
RUN useradd -r -u 1000 -m appuser
USER appuser

# Health check port
ENV PORT=8080
EXPOSE 8080

CMD ["/app/jobs/image-download/.venv/bin/python", "main.py"]
