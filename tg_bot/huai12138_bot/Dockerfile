# =========================================================
# 阶段一：构建者 (BUILDER)
# =========================================================
FROM docker.io/python:3.12-slim AS builder

# 直接用 pip 安装 pdm，避免 pipx 的路径问题
RUN pip install pdm

WORKDIR /app

# 复制 PDM 配置文件
COPY pyproject.toml pdm.lock .

# 安装依赖 (仅生产环境依赖，不安装项目本身)
RUN pdm install --prod --no-self

# =========================================================
# 阶段二：最终镜像 (FINAL)
# =========================================================
FROM docker.io/python:3.12-slim

WORKDIR /app

# 1. 复制虚拟环境
COPY --from=builder /app/.venv /app/.venv

# 2. 复制核心代码
COPY app.py .

# 注意：JSON 数据文件 (blocked_users.json, whitelist.json) 不需要 COPY
# 因为它们需要持久化，我们将在运行时通过 -v 挂载

# 3. 设置环境变量
# 将 PDM 的虚拟环境加入 PATH，直接使用 python 即可
ENV PATH="/app/.venv/bin:$PATH"
# 确保日志实时输出
ENV PYTHONUNBUFFERED=1

# 4. 暴露端口 (Webhook 端口)
EXPOSE 5005

# 5. 启动
CMD ["python", "app.py"]