"""MCP Server 12306 — 核心 Server 实例与工具注册（stdio / HTTP 共用）

此处定义唯一的 ``Server`` 实例及工具注册逻辑（list_tools / call_tool），
不包含任何传输实现。stdio 与 Streamable HTTP 两种传输均复用本模块：
- ``stdio_server``  通过 stdin/stdout 运行 ``server``
- ``http_server``   通过 ``server.streamable_http_app()`` 暴露为 /mcp 端点
"""

import logging
from typing import Any

from mcp.server import Server, ServerRequestContext
from mcp.types import (
    CallToolRequestParams,
    CallToolResult,
    ContentBlock,
    ListToolsResult,
    PaginatedRequestParams,
    TextContent,
    Tool,
)

from .services.ticket_service import (
    MCP_TOOLS,
    search_stations_validated,
    query_tickets_validated,
    query_ticket_price_validated,
    get_train_no_by_train_code_validated,
    get_train_route_stations_validated,
    query_transfer_validated,
    get_current_time_validated,
    SERVER_NAME,
)

logger = logging.getLogger(__name__)

# 工具名称映射到处理函数
TOOL_HANDLERS = {
    "query-tickets": query_tickets_validated,
    "query-ticket-price": query_ticket_price_validated,
    "search-stations": search_stations_validated,
    "get-train-no-by-train-code": get_train_no_by_train_code_validated,
    "get-train-route-stations": get_train_route_stations_validated,
    "query-transfer": query_transfer_validated,
    "get-current-time": get_current_time_validated,
}


def _tool_from_definition(defn: dict[str, Any]) -> Tool:
    """从 MCP_TOOLS 定义构建 Tool 对象（工具 schema 单一数据源）。"""
    return Tool(
        name=defn["name"],
        description=defn["description"],
        input_schema=defn["inputSchema"],
    )


async def list_tools(
    ctx: ServerRequestContext, params: PaginatedRequestParams | None
) -> ListToolsResult:
    """列出所有可用工具"""
    return ListToolsResult(tools=[_tool_from_definition(t) for t in MCP_TOOLS])


async def call_tool(
    ctx: ServerRequestContext, params: CallToolRequestParams
) -> CallToolResult:
    """调用工具"""
    name = params.name
    arguments = params.arguments or {}
    logger.info(f"调用工具: {name}, 参数: {arguments}")

    try:
        # 获取工具处理函数
        handler = TOOL_HANDLERS.get(name)
        if not handler:
            error_msg = f"未知工具: {name}"
            logger.error(error_msg)
            return CallToolResult(
                content=[TextContent(type="text", text=f'{{"success": false, "error": "{error_msg}"}}')],
                is_error=True,
            )

        # 调用工具处理函数
        result = await handler(arguments)

        # 转换结果格式
        if result and isinstance(result, list):
            text_contents: list[ContentBlock] = []
            for item in result:
                if isinstance(item, dict) and item.get("type") == "text":
                    text_contents.append(TextContent(type="text", text=item["text"]))
            if text_contents:
                return CallToolResult(content=text_contents, is_error=False)
            return CallToolResult(
                content=[TextContent(type="text", text='{"success": false, "error": "工具返回格式错误"}')],
                is_error=True,
            )
        else:
            return CallToolResult(
                content=[TextContent(type="text", text='{"success": false, "error": "工具返回格式错误"}')],
                is_error=True,
            )

    except Exception as e:
        error_msg = f"工具执行失败: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return CallToolResult(
            content=[TextContent(type="text", text=f'{{"success": false, "error": "{error_msg}"}}')],
            is_error=True,
        )


# 创建 MCP Server 实例（mcp v2：handler 通过构造参数注册）
server = Server(
    SERVER_NAME,
    on_list_tools=list_tools,
    on_call_tool=call_tool,
)
