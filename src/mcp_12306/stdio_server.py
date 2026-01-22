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
}



@server.list_tools()
async def list_tools() -> list[Tool]:
    """列出所有可用工具"""
    return [
        Tool(
            name="query-tickets",
            description="官方12306余票/车次/座席/时刻一站式查询。输入出发站、到达站、日期，返回所有可购车次、时刻、历时、各席别余票等详细信息。支持中文名、三字码。\n\n【智能筛选指南】返回结果通常包含出发/到达城市的所有相关车站（如北京/北京西/北京南）。请根据用户输入语境灵活处理：\n1. 用户仅输入城市名（如'九江'）：请展示所有相关站点的车次，不要过滤。\n2. 用户指定具体车站（如'九江站'）：优先展示匹配车站的车次，但若其他同城车站有更优方案（如时间更短、有票），也应作为补充选项提供。\n请避免机械地仅通过字符串匹配过滤车次，以免遗漏用户可能感兴趣的出行方案。", 
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
            name="query-ticket-price",
            description="查询火车票价信息。输入出发站、到达站、日期，返回各车次的票价详情。支持指定车次号过滤。\n\n【智能筛选指南】返回结果通常包含出发/到达城市的所有相关车站（如北京/北京西/北京南）。请根据用户输入语境灵活处理：\n1. 用户仅输入城市名（如'九江'）：请展示所有相关站点的车次，不要过滤。\n2. 用户指定具体车站（如'九江站'）：优先展示匹配车站的车次，但若其他同城车站有更优方案（如时间更短、有票），也应作为补充选项提供。\n请避免机械地仅通过字符串匹配过滤车次，以免遗漏用户可能感兴趣的出行方案。",
            inputSchema={
                "type": "object",
                "properties": {
                    "from_station": {"type": "string", "description": "出发站", "minLength": 1},
                    "to_station": {"type": "string", "description": "到达站", "minLength": 1},
                    "train_date": {"type": "string", "description": "出发日期", "pattern": "^\\d{4}-\\d{2}-\\d{2}$"},
                    "train_code": {"type": "string", "description": "车次号（可选）", "title": "车次号（可选）"},
                    "purpose_codes": {"type": "string", "description": "乘客类型 (ADULT=成人, 0X=学生)", "default": "ADULT", "title": "乘客类型"}
                },
                "required": ["from_station", "to_station", "train_date"],
                "additionalProperties": False
            }
        ),
        Tool(
            name="search-stations",
            description="智能车站搜索。支持中文名、拼音、简拼、三字码（Code）。可用于模糊搜索（如“北京”），也可用于精确获取车站代码（如输入“BJP”返回北京站信息）。",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "车站搜索关键词，支持：车站名称、拼音、简拼等", "minLength": 1, "maxLength": 20},
                    "limit": {"type": "integer", "description": "返回结果的最大数量", "minimum": 1, "maximum": 50, "default": 10}
                },
                "required": ["query"],
                "additionalProperties": False
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
