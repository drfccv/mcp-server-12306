# 基础镜像
FROM python:3.10-slim

# 设置工作目录
WORKDIR /app

# 复制依赖文件
COPY pyproject.toml uv.lock ./
COPY README.md ./

# 安装依赖（推荐使用pip，如果你用poetry可自行调整）
RUN pip install --upgrade pip && \
    pip install uv && \
    uv sync --no-install-project

# 复制项目代码
COPY src ./src
COPY docs ./docs
COPY scripts ./scripts

# 安装项目本身
RUN uv sync

# 设置时区（可选）
ENV TZ=Asia/Shanghai

# 暴露端口
EXPOSE 8000

# 启动命令
CMD ["uv", "run", "python", "-m", "mcp_12306.server"]