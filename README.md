<div align="center">

# 🚄 MCP Server 12306

**基于 Model Context Protocol (MCP) 的 12306 火车票查询服务**

[![PyPI - Version](https://img.shields.io/pypi/v/mcp-server-12306?style=flat-square&logo=pypi&logoColor=white&label=PyPI&labelColor=57606a&color=2d8cf0)](https://pypi.org/project/mcp-server-12306)
[![PyPI - Downloads](https://img.shields.io/pypi/dm/mcp-server-12306?style=flat-square&logo=pypi&logoColor=white&label=Downloads&labelColor=57606a&color=2d8cf0)](https://pypi.org/project/mcp-server-12306)
[![Python - 3.10+](https://img.shields.io/badge/Python-3.10%20%7C%203.11%20%7C%203.12%20%7C%203.13-3776ab?style=flat-square&logo=python&logoColor=white&labelColor=57606a)](https://pypi.org/project/mcp-server-12306)
[![Docker - Pulls](https://img.shields.io/docker/pulls/drfccv/mcp-server-12306?style=flat-square&logo=docker&logoColor=white&labelColor=57606a&color=2496ed)](https://hub.docker.com/r/drfccv/mcp-server-12306)
[![License - MIT](https://img.shields.io/badge/License-MIT-97ca00?style=flat-square&logo=opensourceinitiative&logoColor=white&labelColor=57606a)](https://github.com/drfccv/mcp-server-12306/blob/main/LICENSE)
[![MCP - SDK v2](https://img.shields.io/badge/MCP%20SDK-v2-6f42c1?style=flat-square&logo=modelcontextprotocol&logoColor=white&labelColor=57606a)](https://github.com/modelcontextprotocol/python-sdk)
[![Transport - Stdio/HTTP](https://img.shields.io/badge/Transport-Stdio%20%7C%20HTTP-409eff?style=flat-square&labelColor=57606a)](docs/)
[![GitHub - Stars](https://img.shields.io/github/stars/drfccv/mcp-server-12306?style=flat-square&logo=github&logoColor=white&labelColor=57606a&color=24292e)](https://github.com/drfccv/mcp-server-12306)

<br/>

支持 **余票 / 票价 / 车站 / 经停 / 换乘 / 时间** 六大查询能力，开箱即用，适配 AI 助手、自动化脚本、智能终端等场景。

</div>

---

## 📑 目录

- [✨ 功能特性](#-功能特性)
- [🚀 快速开始](#-快速开始)
  - [环境要求](#环境要求)
  - [方式一：Stdio 模式（本地客户端推荐）](#方式一stdio-模式本地客户端推荐)
  - [方式二：Streamable HTTP 模式（远程部署）](#方式二streamable-http-模式远程部署)
  - [方式三：Docker 部署](#方式三docker-部署)
- [🛠️ 工具一览](#️-工具一览)
- [⚙️ 配置项](#️-配置项)
- [🏗️ 项目结构](#️-项目结构)
- [🧑‍💻 开发指南](#-开发指南)
- [📚 详细文档](#-详细文档)
- [⚠️ 免责声明](#️-免责声明)
- [📄 License](#-license)

---

## ✨ 功能特性

| 类别 | 能力 |
|------|------|
| 🎫 **余票查询** | 余票 / 车次 / 座席 / 时刻一站式查询，支持按车次过滤 |
| 💰 **票价查询** | 实时查询各车次各席别票价（商务座 → 无座全覆盖） |
| 🏙️ **车站搜索** | 全国 3382+ 车站，支持中文 / 拼音 / 简拼 / 三字码模糊搜索 |
| 🔄 **中转换乘** | 官方换乘方案自动分页抓取，返回完整路径与等待时间 |
| 🛤️ **经停查询** | 查询指定列车全部经停站与到发时刻 |
| 🕐 **时间工具** | 获取任意时区当前时间、相对日期计算，辅助选择出行日期 |
| 🔌 **双传输模式** | Stdio（本地）\| Streamable HTTP（远程），同一核心实例共享 |
| 🔄 **协议自动协商** | 基于 MCP SDK v2，自动兼容握手时代（2025-11-25）与现代协议（2026-07-28） |

---

## 🚀 快速开始

### 环境要求

| 依赖 | 要求 |
|------|------|
| Python | `>= 3.10, < 3.14` |
| 包管理器 | `uv`（推荐）或 `pip` / `pipx` |
| 网络 | 可访问 12306 官方接口 |

> 💡 推荐使用 [`uv`](https://docs.astral.sh/uv/)：环境隔离、安装快、锁文件管理依赖版本。

### 方式一：Stdio 模式（本地客户端推荐）

> MCP Server 通过标准输入/输出与客户端通信，**不占用网络端口**，适合 Claude Desktop、Cursor 等本地 MCP 客户端。

**安装：**

```bash
# uvx（推荐，环境隔离）
uvx mcp-server-12306

# 或 pip / pipx
pip install mcp-server-12306
```

**客户端配置**（如 `claude_desktop_config.json`）：

```json
{
  "mcpServers": {
    "12306": {
      "command": "uvx",
      "args": ["mcp-server-12306"]
    }
  }
}
```

<details>
<summary><b>其他安装方式（点击展开）</b></summary>

**pipx：**

```json
{
  "mcpServers": {
    "12306": {
      "command": "pipx",
      "args": ["run", "--no-cache", "mcp-server-12306"]
    }
  }
}
```

**本地源码（开发者调试）：**

```bash
git clone https://github.com/drfccv/mcp-server-12306.git
cd mcp-server-12306
uv sync
```

```json
{
  "mcpServers": {
    "12306": {
      "command": "uv",
      "args": ["--directory", "/path/to/mcp-server-12306", "run", "mcp-server-12306"]
    }
  }
}
```

</details>

### 方式二：Streamable HTTP 模式（远程部署）

> Server 启动 Web 服务（默认 `8000` 端口），通过 MCP Streamable HTTP 协议通信：`POST` 发送 JSON-RPC、`GET` 订阅流式响应、`DELETE` 结束会话。

**启动：**

```bash
# 安装后直接启动
mcp-12306

# 或本地源码启动
uv run python scripts/start_server.py
```

**客户端配置：**

```json
{
  "mcpServers": {
    "12306": {
      "url": "http://localhost:8000/mcp"
    }
  }
}
```

**内置 HTTP 端点：**

| 端点 | 方法 | 说明 |
|------|------|------|
| `/mcp` | POST / GET / DELETE | MCP Streamable HTTP 协议入口 |
| `/health` | GET | 健康检查（含已加载车站数、活跃会话数） |
| `/schema/tools` | GET | 全部工具 JSON Schema |
| `/` | GET | 服务信息（版本、协议版本、端点） |

### 方式三：Docker 部署

```bash
# 拉取镜像并运行（默认端口 8000）
docker run -d -p 8000:8000 --name mcp-server-12306 drfccv/mcp-server-12306:latest

# 自定义端口
docker run -d -p 8080:8000 \
  -e SERVER_HOST=0.0.0.0 \
  -e SERVER_PORT=8000 \
  --name mcp-server-12306 \
  drfccv/mcp-server-12306:latest
```

---

## 🛠️ 工具一览

| 工具名 | 功能 | 必填参数 |
|--------|------|----------|
| `query-tickets` | 余票 / 车次 / 座席 / 时刻一站式查询 | `from_station`、`to_station`、`train_date` |
| `query-ticket-price` | 实时查询车次票价 | `from_station`、`to_station`、`train_date` |
| `search-stations` | 车站模糊搜索（中文 / 拼音 / 简拼 / 三字码） | `query` |
| `query-transfer` | 中转换乘方案查询 | `from_station`、`to_station`、`train_date` |
| `get-train-route-stations` | 查询列车经停站及时刻表 | `train_no`、`from_station`、`to_station`、`train_date` |
| `get-train-no-by-train-code` | 车次号 → 官方唯一编号 | `train_code`、`from_station`、`to_station`、`train_date` |
| `get-current-time` | 当前时间与相对日期（辅助选日期） | 无 |

> 📖 每个工具的**参数说明、返回示例、调用示例**详见 [📚 详细文档](#-详细文档)。

---

## ⚙️ 配置项

通过环境变量或项目根目录 `.env` 文件配置：

| 环境变量 | 默认值 | 说明 |
|----------|--------|------|
| `SERVER_HOST` | `0.0.0.0` | HTTP 监听地址 |
| `SERVER_PORT` | `8000` | HTTP 监听端口 |
| `DEBUG` | `false` | 调试模式 |
| `LOG_LEVEL` | `INFO` | 日志级别（`DEBUG` / `INFO` / `WARNING` / `ERROR`） |

```bash
# 示例：.env
SERVER_HOST=127.0.0.1
SERVER_PORT=8000
LOG_LEVEL=INFO
```

---

## 🏗️ 项目结构

```
mcp-server-12306/
├── src/mcp_12306/            # 主包
│   ├── server.py             # 核心 Server（工具注册与分发，双传输共享）
│   ├── stdio_server.py       # Stdio 传输层 + CLI 入口
│   ├── http_server.py        # Streamable HTTP 传输层 + HTTP 端点
│   ├── services/             # 业务逻辑
│   │   ├── station_service.py    # 车站数据服务（加载/搜索/编码转换）
│   │   └── ticket_service.py     # 票务查询核心（7 个工具实现）
│   ├── utils/                # 配置与日期工具
│   │   ├── config.py             # pydantic-settings 配置
│   │   └── date_utils.py         # 日期校验工具
│   └── resources/            # 静态资源（车站数据 station_name.js）
├── scripts/                  # 运维脚本
│   ├── start_server.py       # HTTP 模式一键启动（环境自检）
│   └── update_stations.py    # 更新车站数据
├── docs/                     # 工具详细文档
├── pyproject.toml            # 项目元数据 / 依赖 / 构建配置
├── Dockerfile                # 多阶段构建（python:3.12-alpine）
├── server.json               # MCP 注册表元数据
└── uv.lock                   # 依赖锁文件
```

---

## 🧑‍💻 开发指南

```bash
# 1. 克隆并初始化
git clone https://github.com/drfccv/mcp-server-12306.git
cd mcp-server-12306
uv sync

# 2. 类型检查（mypy，严格模式）
uv run mypy src scripts

# 3. 代码格式化
uv run black src scripts
uv run isort src scripts

# 4. 构建与发布
uv run python -m build
uv run twine upload dist/*
```

**架构要点：**

- `server.py` 是**传输无关的核心模块**——工具注册（`TOOL_HANDLERS`）与业务分发（`call_tool`）都在此，stdio 与 HTTP 复用同一实例，保证两种模式行为完全一致。
- 工具 Schema **单一来源**于 `ticket_service.MCP_TOOLS`，HTTP 的 `/schema/tools` 端点与 MCP 工具列表同源。
- 网络请求统一走 `_request_with_retry`（自动重试 + init 会话保持），业务错误与网络错误分离处理。

---

## 📚 详细文档

| 文档 | 内容 |
|------|------|
| [query_tickets.md](./docs/query_tickets.md) | 余票 / 车次 / 座席 / 时刻一站式查询 |
| [query_ticket_price.md](./docs/query_ticket_price.md) | 实时票价查询 |
| [search_stations.md](./docs/search_stations.md) | 车站智能搜索 |
| [query_transfer.md](./docs/query_transfer.md) | 中转换乘方案 |
| [get_train_route_stations.md](./docs/get_train_route_stations.md) | 列车经停站查询 |
| [get_current_time.md](./docs/get_current_time.md) | 当前时间与相对日期 |

每份文档均包含：功能说明、实现方法、请求参数、返回示例与典型调用方式。

---

## ⚠️ 免责声明

- 本项目仅供学习、研究与技术交流，**严禁用于任何商业用途**。
- 本项目仅作为官方公开接口的智能聚合与转发。
- 使用本项目造成的任何后果（包括但不限于账号封禁、数据异常、法律风险等）均由使用者本人承担，项目作者不承担任何责任。
- 请遵守中国法律法规及 12306 官方相关规定，合理合规使用。

---

## 📄 License

[MIT](./LICENSE) © [Drfccv](https://github.com/drfccv)

---

<div align="center">

**⭐ 如果这个项目对你有帮助，欢迎 Star 支持！**

</div>


