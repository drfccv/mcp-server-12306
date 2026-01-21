# 🚄 12306 MCP Server

![screenshot](https://img.shields.io/badge/12306-MCP-blue?logo=railway) 
![FastAPI](https://img.shields.io/badge/FastAPI-async-green?logo=fastapi) 
![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)

---

## ✨ 项目简介

12306 MCP Server 是一款基于 Model Context Protocol (MCP) 的高性能火车票查询后端，支持官方 12306 余票、车站、经停、换乘查询以及智能时间工具，适配 AI/自动化/智能助手等场景。界面友好，易于集成，开箱即用。


---

## 🚀 功能亮点

- 实时余票/车次/座席/时刻/换乘一站式查询
- 全国车站信息管理与模糊搜索
- 官方经停站、一次中转方案全支持
- 智能时间工具，支持时区和时间戳
- Streamable HTTP传输协议，支持MCP 2025-03-26标准
- FastAPI异步高性能，秒级响应
- MCP标准，AI/自动化场景即插即用

---

## 🛠️ 快速上手

### 环境要求
- Python 3.10+
- [uv](https://astral.sh/uv/)（推荐包管理器）

### 本地一键部署
```bash
# 克隆项目
git clone https://github.com/drfccv/mcp-server-12306.git
cd mcp-server-12306

# 安装依赖
uv sync

# 更新车站信息（必须先执行）
uv run python scripts/update_stations.py

# 启动服务器
uv run python scripts/start_server.py
```

### Docker 部署
```bash
# 直接拉取已构建镜像
 docker pull drfccv/mcp-server-12306:latest

# 运行容器（映射8000端口）
 docker run -d -p 8000:8000 --name mcp-server-12306 drfccv/mcp-server-12306:latest
```


### 配置
复制 `.env.example` 为 `.env` 并按需修改：
```bash
cp .env.example .env
```

---

## 🤖 API & 工具一览

### MCP 客户端配置示例
```json
{
  "mcpServers": {
    "12306": {
      "url": "http://localhost:8000/mcp"
    }
  }
}
```

### 支持的主流程工具
| 工具名                    | 典型场景/功能描述                 |
|--------------------------|----------------------------------|
| query_tickets            | 余票/车次/座席/时刻一站式查询     |
| search_stations          | 车站模糊搜索，支持中文/拼音/简拼   |
| get_station_info         | 获取车站详情（名称、代码、地理等） |
| query_transfer           | 一次中转换乘方案，自动拼接最优中转 |
| get_train_route_stations | 查询指定列车经停站及时刻表         |
| get_current_time         | 获取当前时间与相对日期，帮助用户准确选择出行日期 |

---

## 📚 工具文档

本项目所有主流程工具的详细功能、实现与使用方法，均已收录于 [`/docs`](./docs) 目录下：

- [query_tickets.md](./docs/query_tickets.md) — 余票/车次/座席/时刻一站式查询
- [search_stations.md](./docs/search_stations.md) — 车站模糊搜索
- [get_station_info.md](./docs/get_station_info.md) — 获取车站详情
- [query_transfer.md](./docs/query_transfer.md) — 一次中转换乘方案
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
src/mcp_12306/    # 主源代码
  ├─ server.py    # FastAPI主入口
  ├─ services/    # 业务逻辑（车票/车站/HTTP）
  ├─ utils/       # 工具与配置
scripts/          # 启动与数据脚本
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


