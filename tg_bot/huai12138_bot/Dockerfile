# =========================================================
# Stage 1: Builder
# =========================================================
FROM docker.io/python:3.12-slim AS builder

# Install pdm directly with pip to avoid pipx path issues [cite: 1]
RUN pip install pdm

WORKDIR /app

# Copy PDM config files [cite: 1]
COPY pyproject.toml pdm.lock .

# Install production dependencies only 
RUN pdm install --prod --no-self

# =========================================================
# Stage 2: Final Image
# =========================================================
FROM docker.io/python:3.12-slim

WORKDIR /app

# 1. Copy virtual environment 
COPY --from=builder /app/.venv /app/.venv

# 2. Copy core code (Added ha.py) 
COPY app.py ha.py .

# Note: JSON data files (blocked_users.json, whitelist.json) do not need to be COPY'd [cite: 3]
# They require persistence and will be mounted via -v at runtime [cite: 3]

# 3. Set environment variables [cite: 3]
# Add PDM virtual env to PATH [cite: 3]
ENV PATH="/app/.venv/bin:$PATH"
# Ensure real-time log output [cite: 3]
ENV PYTHONUNBUFFERED=1

# 4. Expose port (Webhook port) [cite: 3]
EXPOSE 5005

# 5. Start [cite: 3]
CMD ["python", "app.py"]