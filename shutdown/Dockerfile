# =========================================================
# Stage 1: Builder
# =========================================================
FROM docker.io/python:3.12-slim AS builder

# Copy uv binary from the official image (minimalist approach)
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

# Enable bytecode compilation for better performance
ENV UV_COMPILE_BYTECODE=1
# Use copy mode instead of symlinks/hardlinks for Docker layers
ENV UV_LINK_MODE=copy

# Copy dependency definitions
# Note: You should run 'uv lock' locally first to generate uv.lock
COPY pyproject.toml uv.lock ./

# Install dependencies (Production mode)
# Using cache mount to speed up repeated builds
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-install-project --no-dev

# =========================================================
# Stage 2: Final Image
# =========================================================
FROM docker.io/python:3.12-slim

WORKDIR /app

# 1. Copy the virtual environment from builder
COPY --from=builder /app/.venv /app/.venv

# 2. Copy the application code
COPY main.py .

# 3. Set environment variables
ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONUNBUFFERED=1

# 4. Expose the application port
EXPOSE 5008

# 5. Start the application
CMD ["python", "main.py"]