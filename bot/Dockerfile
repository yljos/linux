# =========================================================
# Stage 1: Builder
# =========================================================
FROM docker.io/python:3.12-slim AS builder

# Copy uv binary from the official image for a minimalist setup
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

# Enable bytecode compilation for better performance [cite: 2026-02-11]
ENV UV_COMPILE_BYTECODE=1
# Use copy mode instead of symlinks for container portability
ENV UV_LINK_MODE=copy

# Copy dependency definitions (Ensure uv.lock exists locally)
COPY pyproject.toml uv.lock ./

# Install production dependencies only using cache mount to save time/space [cite: 2026-03-24]
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-install-project --no-dev

# =========================================================
# Stage 2: Final Image
# =========================================================
FROM docker.io/python:3.12-slim

WORKDIR /app

# 1. Copy the pre-built virtual environment from builder stage
COPY --from=builder /app/.venv /app/.venv

# 2. Copy core code (app.py and ha.py)
COPY main.py ha.py .

# Note: JSON data files (blocked_users.json, whitelist.json) do not need to be COPY'd
# They require persistence and will be mounted via -v at runtime

# 3. Set environment variables
# Add the virtual env to PATH so 'python' refers to the correct environment
ENV PATH="/app/.venv/bin:$PATH"
# Ensure real-time log output for easier debugging
ENV PYTHONUNBUFFERED=1

# 4. Expose Webhook port
EXPOSE 5005

# 5. Start the application
CMD ["python", "main.py"]