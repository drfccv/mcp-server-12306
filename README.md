[![MseeP.ai Security Assessment Badge](https://mseep.net/pr/drfccv-mcp-server-12306-badge.png)](https://mseep.ai/app/drfccv-mcp-server-12306)

# 🚄 MCP Server 12306

![screenshot](https://img.shields.io/badge/12306-MCP-blue?logo=railway)
![Python](https://img.shields.io/badge/Python-3.10%2B-blue?logo=python)
![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)

---

## ✨ 项目简介

MCP Server 12306 是一款基于 Model Context Protocol (MCP) 的高性能火车票查询服务，支持官方 12306 余票、票价、车站、经停、换乘查询以及智能时间工具，适配 AI/自动化/智能助手等场景，开箱即用。


---

## 🚀 功能亮点

- 实时余票/车次/座席/时刻/换乘一站式查询
- 全国车站信息管理与模糊搜索，支持中文、拼音、简拼、三字码
- 官方经停站、中转换乘方案全支持
- 实时查询各车次票价信息
- 智能时间工具，支持时区和时间戳
- 双传输模式：Stdio（Claude Desktop 推荐）| Streamable HTTP（远程部署）
- MCP 2025-03-26 标准，AI/自动化场景即插即用

---

## 🛠️ 快速上手

本项目支持两种运行模式：
1. **Stdio 模式**：适用于 Claude Desktop 等本地 MCP 客户端（推荐）。
2. **Streamable HTTP 模式**：适用于远程部署或通过 SSE/POST 访问。

---

### 模式 1：Stdio 模式（Claude Desktop 推荐）

在此模式下，MCP Server 通过标准输入/输出与客户端通信，无需占用网络端口。

#### 方式 A：使用 uvx（推荐）

`uvx` 是 `uv` 包管理器提供的工具，环境隔离且启动极快。

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

#### 方式 B：使用 pipx

如果您更习惯使用 pipx：

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

#### 方式 C：本地源码运行

适用于开发者调试：

```bash
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


---

### 模式 2：Streamable HTTP 模式

在此模式下，Server 启动一个 Web 服务（默认 8000 端口），支持 MCP 的 SSE 和 POST 交互。

#### 方式 A：pip 安装后运行

```bash
# 安装 HTTP 模式（含 FastAPI / uvicorn）
pip install mcp-server-12306[http]
# 启动
mcp-12306
```

#### 方式 B：本地源码运行

```bash
# 1. 克隆并安装依赖
git clone https://github.com/drfccv/mcp-server-12306.git
cd mcp-server-12306
uv sync --extra http

# 2. 启动服务器
uv run python scripts/start_server.py
```

**MCP 客户端配置：**

```json
{
  "mcpServers": {
    "12306": {
      "url": "http://localhost:8000/mcp"
    }
  }
}
```

#### 方式 C：Docker 部署

```bash
# 拉取镜像并运行
docker run -d -p 8000:8000 --name mcp-server-12306 drfccv/mcp-server-12306:latest
```

---

## 🤖 工具一览

### 支持的主流程工具
| 工具名                       | 功能描述                          |
|-----------------------------|-----------------------------------|
| `query-tickets`             | 余票/车次/座席/时刻一站式查询      |
| `query-ticket-price`        | 实时查询各车次票价信息              |
| `search-stations`           | 车站模糊搜索，支持中文/拼音/简拼    |
| `query-transfer`            | 中转换乘方案，自动拼接最优路径      |
| `get-train-route-stations`  | 查询指定列车经停站及时刻表          |
| `get-train-no-by-train-code`| 车次号转官方唯一编号               |
| `get-current-time`          | 当前时间与相对日期，辅助日期选择    |

---

## 📚 工具文档

本项目所有主流程工具的详细功能、实现与使用方法，均已收录于 [`/docs`](./docs) 目录下：

- [query_tickets.md](./docs/query_tickets.md) — 余票/车次/座席/时刻一站式查询
- [query_ticket_price.md](./docs/query_ticket_price.md) — 实时查询各车次票价信息
- [search_stations.md](./docs/search_stations.md) — 车站智能搜索
- [query_transfer.md](./docs/query_transfer.md) — 中转换乘方案
- [get_train_route_stations.md](./docs/get_train_route_stations.md) — 查询列车经停站
- [get_current_time.md](./docs/get_current_time.md) — 获取当前时间与相对日期

每个文档包含：
- 工具功能说明
- 实现方法
- 请求参数与返回示例
- 典型调用方式

如需二次开发或集成，建议先阅读对应工具的文档。

---

## 🧩 目录结构

```
src/mcp_12306/          # 主源代码
  ├─ http_server.py     # FastAPI HTTP 传输层
  ├─ stdio_server.py    # Stdio 传输层 + CLI 入口
  ├─ services/          # 业务逻辑
  │   ├─ station_service.py  # 车站数据服务
  │   └─ ticket_service.py   # 票务查询核心（stdio/HTTP 共享）
  ├─ utils/             # 配置与日期工具
  │   ├─ config.py
  │   └─ date_utils.py
  └─ resources/         # 静态资源（车站数据）
scripts/                # 启动与数据更新脚本
  ├─ start_server.py    # HTTP 模式一键启动
  └─ update_stations.py # 更新车站数据
```

---

## 📄 License
MIT License

---

## ⚠️ 免责声明

- 本项目仅供学习、研究与技术交流，严禁用于任何商业用途。
- 本项目不存储、不篡改、不传播任何 12306 官方数据，仅作为官方公开接口的智能聚合与转发。
- 使用本项目造成的任何后果（包括但不限于账号封禁、数据异常、法律风险等）均由使用者本人承担，项目作者不承担任何责任。
- 请遵守中国法律法规及 12306 官方相关规定，合理合规使用。

---


