# =========================================================
# 阶段一：构建者 (BUILDER) - 专注于安装依赖并生成 .venv
# =========================================================
# 保持你选择的 3.12 slim 镜像
FROM docker.io/python:3.12-slim AS builder

# 1. 安装 PDM 工具本身 (使用 pipx 是最佳实践)
RUN pip install pipx && pipx install pdm

WORKDIR /app

# 2. 复制 PDM 配置文件和锁定文件
# 注意：你需要先在本地运行一次 pdm install 来生成 pdm.lock
COPY pyproject.toml .
COPY pdm.lock . 

# 3. 安装依赖，只安装生产环境依赖 (核心优化!)
# --prod/--no-dev 确保不安装 pytest 等开发工具
# --no-self 适用于库项目
RUN pdm install --prod --no-self

# =========================================================
# 阶段二：最终镜像 (FINAL) - 专注于运行应用
# =========================================================
FROM python:3.12-slim

WORKDIR /app

# 1. 从构建阶段复制 PDM 的虚拟环境 (.venv)
# 这是加速和缩减镜像的关键步骤！
COPY --from=builder /app/.venv /app/.venv

# 2. 复制项目源代码
COPY . /app

# 3. 设置运行路径：将 .venv 的 bin 目录添加到 PATH
# 这样就可以直接使用 venv 里的 python 解释器和脚本
ENV PATH="/app/.venv/bin:$PATH"

# 4. 运行应用
CMD ["python", "app.py"]