# =========================================================
# 阶段一：构建者 (BUILDER) - 专注于安装依赖并生成 .venv
# =========================================================
FROM docker.io/python:3.12-slim AS builder

# 1. 安装 PDM 工具本身
RUN pip install pdm

WORKDIR /app

# 2. 复制 PDM 配置文件和锁定文件
# 注意：你需要先在本地运行一次 pdm install 来生成 pdm.lock
COPY pyproject.toml .
COPY pdm.lock . 

# 3. 安装依赖，只安装生产环境依赖
RUN pdm install --prod --no-self

# =========================================================
# 阶段二：最终镜像 (FINAL) - 专注于运行应用
# =========================================================
FROM python:3.12-slim

WORKDIR /app

# 1. 从构建阶段复制 PDM 的虚拟环境 (.venv)
COPY --from=builder /app/.venv /app/.venv

# 2. 复制项目源代码和配置文件
# [重要修改] COPY . . 会把当前目录下所有文件（包括 b_shouji.yam）都复制进去
COPY . .

# 3. 设置运行路径：将 .venv 的 bin 目录添加到 PATH
ENV PATH="/app/.venv/bin:$PATH"

# 4. 运行应用
CMD ["python", "app.py"]