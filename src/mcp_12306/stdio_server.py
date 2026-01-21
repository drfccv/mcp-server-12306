"""MCP Server 12306 - Stdio Transport Implementation"""

import asyncio
import logging
from typing import Any
from mcp.server import Server
from mcp.types import Tool, TextContent

from .services.station_service import StationService

# 导入现有的工具处理函数
from .server import (
    search_stations_validated,
    query_tickets_validated,
    get_train_no_by_train_code_validated,
    get_train_route_stations_validated,
    query_transfer_validated,
    get_current_time_validated,
    station_service as global_station_service,
    SERVER_NAME
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# 创建 MCP Server 实例
server = Server("mcp-server-12306")

# 工具名称映射到处理函数
TOOL_HANDLERS = {
    "query-tickets": query_tickets_validated,
    "search-stations": search_stations_validated,
    "get-train-no-by-train-code": get_train_no_by_train_code_validated,
    "get-train-route-stations": get_train_route_stations_validated,
    "query-transfer": query_transfer_validated,
    "get-current-time": get_current_time_validated,
    "get-station-info": None,  # 将在下面实现
}


# get_station_info 工具实现
async def get_station_info_validated(args: dict) -> list:
    """获取车站详细信息"""
    import json
    try:
        query = args.get("query", "").strip()
        if not query:
            response_data = {"success": False, "error": "请输入车站名称或代码"}
            return [{"type": "text", "text": json.dumps(response_data, ensure_ascii=False)}]
        
        # 尝试通过代码获取
        station = await global_station_service.get_station_by_code(query)
        if not station:
            # 尝试通过名称获取
            code = await global_station_service.get_station_code(query)
            if code:
                station = await global_station_service.get_station_by_code(code)
        
        if station:
            response_data = {
                "success": True,
                "station": {
                    "name": station.name,
                    "code": station.code,
                    "pinyin": station.pinyin,
                    "py_short": station.py_short if station.py_short else "",
                    "num": station.num if hasattr(station, 'num') else ""
                }
            }
            return [{"type": "text", "text": json.dumps(response_data, ensure_ascii=False)}]
        else:
            response_data = {
                "success": False,
                "query": query,
                "error": "未找到该车站",
                "suggestion": "请使用 search-stations 工具进行模糊搜索"
            }
            return [{"type": "text", "text": json.dumps(response_data, ensure_ascii=False)}]
    except Exception as e:
        logger.error(f"获取车站信息失败: {repr(e)}")
        response_data = {"success": False, "error": "获取车站信息失败", "detail": str(e)}
        return [{"type": "text", "text": json.dumps(response_data, ensure_ascii=False)}]


TOOL_HANDLERS["get-station-info"] = get_station_info_validated


@server.list_tools()
async def list_tools() -> list[Tool]:
    """列出所有可用工具"""
    return [
        Tool(
            name="query-tickets",
            description="官方12306余票/车次/座席/时刻一站式查询。输入出发站、到达站、日期，返回所有可购车次、时刻、历时、各席别余票等详细信息。支持中文名、三字码。",
            inputSchema={
                "type": "object",
                "properties": {
                    "from_station": {"type": "string", "description": "出发车站名称"},
                    "to_station": {"type": "string", "description": "到达车站名称"},
                    "train_date": {"type": "string", "description": "出发日期，格式：YYYY-MM-DD"}
                },
                "required": ["from_station", "to_station", "train_date"]
            }
        ),
        Tool(
            name="search-stations",
            description="智能模糊查站，支持中文名、拼音、简拼、三字码等多种方式，快速获取车站全名与三字码。",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "车站搜索关键词"},
                    "limit": {"type": "integer", "description": "返回结果数量限制", "default": 10}
                },
                "required": ["query"]
            }
        ),
        Tool(
            name="get-station-info",
            description="获取车站详细信息（名称、代码、拼音等）。输入车站名称或三字码，返回完整车站信息。",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "车站名称或三字码"}
                },
                "required": ["query"]
            }
        ),
        Tool(
            name="query-transfer",
            description="官方中转换乘方案查询。输入出发站、到达站、日期，可选中转站/无座/学生票，自动分页抓取全部中转方案。",
            inputSchema={
                "type": "object",
                "properties": {
                    "from_station": {"type": "string", "description": "出发站"},
                    "to_station": {"type": "string", "description": "到达站"},
                    "train_date": {"type": "string", "description": "出发日期，格式：YYYY-MM-DD"},
                    "middle_station": {"type": "string", "description": "指定中转站（可选）"},
                    "isShowWZ": {"type": "string", "description": "是否显示无座车次（Y/N）", "default": "N"},
                    "purpose_codes": {"type": "string", "description": "乘客类型（00=普通，0X=学生）", "default": "00"}
                },
                "required": ["from_station", "to_station", "train_date"]
            }
        ),
        Tool(
            name="get-train-route-stations",
            description="列车经停站全表查询。支持输入车次号或官方编号，返回所有经停站、到发时刻、停留时间。",
            inputSchema={
                "type": "object",
                "properties": {
                    "train_no": {"type": "string", "description": "车次编码或车次号"},
                    "from_station": {"type": "string", "description": "出发站"},
                    "to_station": {"type": "string", "description": "到达站"},
                    "train_date": {"type": "string", "description": "出发日期，格式：YYYY-MM-DD"}
                },
                "required": ["train_no", "from_station", "to_station", "train_date"]
            }
        ),
        Tool(
            name="get-train-no-by-train-code",
            description="车次号转官方唯一编号（train_no），支持三字码/全名。常用于经停站查询前置转换。",
            inputSchema={
                "type": "object",
                "properties": {
                    "train_code": {"type": "string", "description": "车次号"},
                    "from_station": {"type": "string", "description": "出发站"},
                    "to_station": {"type": "string", "description": "到达站"},
                    "train_date": {"type": "string", "description": "出发日期，格式：YYYY-MM-DD"}
                },
                "required": ["train_code", "from_station", "to_station", "train_date"]
            }
        ),
        Tool(
            name="get-current-time",
            description="获取当前日期和时间信息，支持相对日期计算。返回当前日期、时间，以及常用的相对日期。",
            inputSchema={
                "type": "object",
                "properties": {
                    "timezone": {"type": "string", "description": "时区", "default": "Asia/Shanghai"},
                    "format": {"type": "string", "description": "日期格式", "default": "YYYY-MM-DD"}
                }
            }
        ),
    ]


@server.call_tool()
async def call_tool(name: str, arguments: Any) -> list[TextContent]:
    """调用工具"""
    logger.info(f"调用工具: {name}, 参数: {arguments}")
    
    try:
        # 获取工具处理函数
        handler = TOOL_HANDLERS.get(name)
        if not handler:
            error_msg = f"未知工具: {name}"
            logger.error(error_msg)
            return [TextContent(type="text", text=f'{{"success": false, "error": "{error_msg}"}}')]
        
        # 调用工具处理函数
        result = await handler(arguments if arguments else {})
        
        # 转换结果格式
        if result and isinstance(result, list):
            text_contents = []
            for item in result:
                if isinstance(item, dict) and item.get("type") == "text":
                    text_contents.append(TextContent(type="text", text=item["text"]))
            return text_contents if text_contents else [TextContent(type="text", text='{"success": false, "error": "工具返回格式错误"}')]
        else:
            return [TextContent(type="text", text='{"success": false, "error": "工具返回格式错误"}')]
            
    except Exception as e:
        error_msg = f"工具执行失败: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return [TextContent(type="text", text=f'{{"success": false, "error": "{error_msg}"}}')]


async def run_stdio_server():
    """运行 stdio 服务器"""
    import os
    import sys
    import mcp_12306

    logger.info("启动 mcp-server-12306 (stdio 模式)...")
    logger.info(f"版本: {mcp_12306.__version__}")
    
    logger.info("正在加载车站数据...")
    
    # 加载车站数据
    await global_station_service.load_stations()
    logger.info(f"已加载 {len(global_station_service.stations)} 个车站")
    
    # 运行服务器
    from mcp.server.stdio import stdio_server
    
    async with stdio_server() as (read_stream, write_stream):
        logger.info("MCP Server 已启动，等待客户端连接...")
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options()
        )
