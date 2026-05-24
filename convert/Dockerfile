# =========================================================
# Stage 1: Builder
# =========================================================
FROM docker.io/python:3.12-slim AS builder

# Copy uv binary from the official image for a minimalist setup
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

# Optimization: precompile bytecode for better runtime performance [cite: 2026-02-11]
ENV UV_COMPILE_BYTECODE=1
# Use copy mode instead of symlinks for container portability
ENV UV_LINK_MODE=copy

# Copy dependency files (Ensure uv.lock exists locally)
COPY pyproject.toml uv.lock ./

# Install production dependencies only using cache mount
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-install-project --no-dev

# =========================================================
# Stage 2: Final Image
# =========================================================
FROM docker.io/python:3.12-slim

WORKDIR /app

# Copy the pre-built virtual environment from builder [cite: 1]
COPY --from=builder /app/.venv /app/.venv

# Copy application source code
COPY . .

# Set environment variables for the virtual environment
ENV PATH="/app/.venv/bin:$PATH"
# Disable python buffering for cleaner logging
ENV PYTHONUNBUFFERED=1

# Start the application
CMD ["python", "app.py"]