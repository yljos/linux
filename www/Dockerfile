# =========================================================
# 阶段一：构建者 (BUILDER)
# =========================================================
FROM docker.io/python:3.12-slim AS builder

# 安装 PDM
RUN pip install pdm

WORKDIR /app

# 复制依赖定义
COPY pyproject.toml pdm.lock .

# 安装依赖 (生产环境模式)
RUN pdm install --prod --no-self

# =========================================================
# 阶段二：最终镜像 (FINAL)
# =========================================================
FROM docker.io/python:3.12-slim

WORKDIR /app

# 1. 复制虚拟环境
COPY --from=builder /app/.venv /app/.venv

# 2. 复制主程序
COPY app.py .

# 3. 设置环境变量
ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONUNBUFFERED=1

# 4. 暴露端口 (app.py 里写的是 5008)
EXPOSE 5008

# 5. 启动命令
CMD ["python", "app.py"]