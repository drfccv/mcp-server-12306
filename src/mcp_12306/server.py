import asyncio
import json
import logging
import httpx
from datetime import datetime, date
from typing import Dict, List, Any
import uuid
import pytz
import re

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import StreamingResponse, JSONResponse, Response
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from .services.station_service import StationService
from .utils.config import get_settings
from .utils.date_utils import validate_date
from . import __version__

settings = get_settings()

logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)
station_service = StationService()

# MCP Protocol Version - Support 2025-03-26 Streamable HTTP transport
MCP_PROTOCOL_VERSION = "2025-03-26"  # Updated to latest protocol version
SERVER_NAME = "mcp-server-12306"
SERVER_VERSION = __version__

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/123.0.0.0 Safari/537.36"
)

# Connected clients for session management
connected_clients: Dict[str, Dict] = {}

# MCP Tools Definition according to spec
MCP_TOOLS = [
    {
        "name": "query-tickets",
        "description": "官方12306余票/车次/座席/时刻一站式查询。输入出发站、到达站、日期，返回所有可购车次、时刻、历时、各席别余票等详细信息。支持中文名、三字码。\n\n【重要提示】返回的车次可能包含经停该线路的所有列车，实际起止站点可能与查询站点不同。AI助手应根据用户实际需求筛选合适的车次（例如：用户查询'某地到XX西站'，返回结果可能包含途经'XX站'或'XX东站'的车次，需要注意from_station和to_station字段进行精确匹配）。",
        "inputSchema": {
            "$schema": "http://json-schema.org/draft-07/schema#",
            "type": "object",
            "title": "车票查询参数",
            "description": "查询火车票所需的参数",
            "properties": {
                "from_station": {"type": "string", "title": "出发站", "description": "出发车站名称，例如：北京、上海、广州", "minLength": 1},
                "to_station": {"type": "string", "title": "到达站", "description": "到达车站名称，例如：北京、上海、广州", "minLength": 1},
                "train_date": {"type": "string", "title": "出发日期", "description": "出发日期，格式：YYYY-MM-DD", "pattern": "^\\d{4}-\\d{2}-\\d{2}$"}
            },
            "required": ["from_station", "to_station", "train_date"],
            "additionalProperties": False
        }
    },
    {
        "name": "search-stations",
        "description": "智能模糊查站，支持中文名、拼音、简拼、三字码等多种方式，快速获取车站全名与三字码。",
        "inputSchema": {
            "$schema": "http://json-schema.org/draft-07/schema#",
            "type": "object",
            "title": "车站搜索参数",
            "description": "搜索火车站所需的参数",
            "properties": {
                "query": {"type": "string", "title": "搜索关键词", "description": "车站搜索关键词，支持：车站名称、拼音、简拼等", "minLength": 1, "maxLength": 20},
                "limit": {"type": "integer", "title": "结果数量限制", "description": "返回结果的最大数量", "minimum": 1, "maximum": 50, "default": 10}
            },
            "required": ["query"],
            "additionalProperties": False
        }
    },
    {
        "name": "query-transfer",
        "description": "官方中转换乘方案查询。输入出发站、到达站、日期，可选中转站/无座/学生票，自动分页抓取全部中转方案，输出每段车次、时刻、余票、等候时间、总历时等详细信息。",
        "inputSchema": {
            "$schema": "http://json-schema.org/draft-07/schema#",
            "type": "object",
            "title": "中转查询参数",
            "description": "查询A到B的中转换乘（含一次换乘）",
            "properties": {
                "from_station": {"type": "string", "title": "出发站"},
                "to_station": {"type": "string", "title": "到达站"},
                "train_date": {"type": "string", "title": "出发日期", "pattern": "^\\d{4}-\\d{2}-\\d{2}$"},
                "middle_station": {"type": "string", "title": "中转站（可选）", "description": "指定中转站名称或三字码，可选"},
                "isShowWZ": {"type": "string", "title": "是否显示无座车次（Y/N）", "description": "Y=显示无座车次，N=不显示，默认N", "default": "N"},
                "purpose_codes": {"type": "string", "title": "乘客类型（00=普通，0X=学生）", "description": "00为普通，0X为学生，默认00"}
            },
            "required": ["from_station", "to_station", "train_date"],
            "additionalProperties": False
        }
    },
    {
        "name": "get-train-route-stations",
        "description": "列车经停站全表查询。支持输入车次号或官方编号，自动转换，返回所有经停站、到发时刻、停留时间。支持三字码/全名。",
        "inputSchema": {
            "$schema": "http://json-schema.org/draft-07/schema#",
            "type": "object",
            "title": "列车经停站查询参数",
            "properties": {
                "train_no": {"type": "string", "title": "车次编码", "minLength": 1},
                "from_station": {"type": "string", "title": "出发站id", "minLength": 1},
                "to_station": {"type": "string", "title": "到达站id", "minLength": 1},
                "train_date": {"type": "string", "title": "出发日期", "pattern": "^\\d{4}-\\d{2}-\\d{2}$"}
            },
            "required": ["train_no", "from_station", "to_station", "train_date"],
            "additionalProperties": False
        }
    },
    {
        "name": "get-train-no-by-train-code",
        "description": "车次号转官方唯一编号（train_no），支持三字码/全名。常用于经停站查询前置转换。",
        "inputSchema": {
            "$schema": "http://json-schema.org/draft-07/schema#",
            "type": "object",
            "title": "车次号转编号参数",
            "properties": {
                "train_code": {"type": "string", "title": "车次号", "minLength": 1},
                "from_station": {"type": "string", "title": "出发站id或全名", "minLength": 1},
                "to_station": {"type": "string", "title": "到达站id或全名", "minLength": 1},
                "train_date": {"type": "string", "title": "出发日期", "pattern": "^\\d{4}-\\d{2}-\\d{2}$"}
            },            "required": ["train_code", "from_station", "to_station", "train_date"],
            "additionalProperties": False
        }
    },
    {
        "name": "get-current-time",
        "description": "获取当前日期和时间信息，支持相对日期计算。返回当前日期、时间，以及常用的相对日期（明天、后天等），方便用户在查询火车票时选择正确的日期。",
        "inputSchema": {
            "$schema": "http://json-schema.org/draft-07/schema#",
            "type": "object",
            "title": "获取当前时间参数",
            "description": "获取当前时间和日期信息",
            "properties": {
                "timezone": {"type": "string", "title": "时区", "description": "时区设置，默认为中国时区", "default": "Asia/Shanghai"},
                "format": {"type": "string", "title": "日期格式", "description": "返回的日期格式，默认为YYYY-MM-DD", "default": "YYYY-MM-DD"}
            },
            "additionalProperties": False
        }
    }
]

app = FastAPI(
    title=SERVER_NAME,
    version=SERVER_VERSION,
    description=f"基于MCP协议(2025-03-26 Streamable HTTP)的12306火车票查询服务，支持直达、过站和换乘查询",
    debug=settings.debug
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

@app.get("/")
async def root():
    return {
        "name": SERVER_NAME,
        "version": SERVER_VERSION,
        "status": "running",
        "mcp_endpoint": "/mcp",
        "protocol_version": MCP_PROTOCOL_VERSION,
        "transport": "Streamable HTTP (2025-03-26)",
        "stations_loaded": len(station_service.stations),
        "tools": [tool["name"] for tool in MCP_TOOLS],
        "active_sessions": len(connected_clients)
    }

@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "stations": len(station_service.stations),
        "active_sessions": len(connected_clients)
    }

@app.get("/schema/tools")
async def get_tools_schema():
    return {
        "tools": MCP_TOOLS,
        "schema_version": "http://json-schema.org/draft-07/schema#"
    }

# MCP Streamable HTTP Transport Endpoints (2025-03-26 spec)

@app.options("/mcp")
async def mcp_options():
    """Handle CORS preflight for /mcp endpoint"""
    return JSONResponse(
        {},
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, POST, DELETE, OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type, Authorization, Mcp-Session-Id",
        }
    )

@app.get("/mcp")
async def mcp_endpoint_get(request: Request):
    """MCP Streamable HTTP Endpoint - GET for SSE connection (optional)"""
    # Generate session ID for this connection
    session_id = str(uuid.uuid4())
    logger.info(f"New MCP GET connection established - Session ID: {session_id}")
    
    # Store client connection info
    connected_clients[session_id] = {
        "connected_at": datetime.now().isoformat(),
        "user_agent": request.headers.get("user-agent", ""),
        "client_ip": request.client.host if request.client else "unknown",
        "initialized": False,
        "protocol_version": MCP_PROTOCOL_VERSION
    }
    
    async def generate_events():
        try:
            # Keep connection alive with periodic pings
            while True:
                await asyncio.sleep(30)  # Send ping every 30 seconds
                yield f"event: ping\ndata: {{\"timestamp\": \"{datetime.now().isoformat()}\"}}\n\n"
                
        except asyncio.CancelledError:
            logger.info(f"MCP GET connection closed - Session ID: {session_id}")
            # Clean up client connection
            if session_id in connected_clients:
                del connected_clients[session_id]
        except Exception as e:
            logger.error(f"MCP GET error for session {session_id}: {e}")
            # Clean up client connection
            if session_id in connected_clients:
                del connected_clients[session_id]
    
    return StreamingResponse(
        generate_events(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "*",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
            "Mcp-Session-Id": session_id  # Return session ID in header
        }
    )

@app.post("/mcp")
async def mcp_endpoint_post(request: Request):
    """MCP Streamable HTTP Endpoint - POST for JSON-RPC messages"""
    request_id = None
    try:
        data = await request.json()
        
        # Validate JSON-RPC 2.0 format
        if not isinstance(data, dict) or data.get("jsonrpc") != "2.0":
            raise HTTPException(status_code=400, detail="Invalid JSON-RPC 2.0 message")
        
        method = data.get("method")
        params = data.get("params", {})
        request_id = data.get("id")
        
        if not method:
            raise HTTPException(status_code=400, detail="Method is required")
        
        logger.info(f"Received MCP request: {method} (ID: {request_id})")
        
        # Handle initialization - no session ID required for this
        if method == "initialize":
            client_capabilities = params.get("capabilities", {})
            client_protocol_version = params.get("protocolVersion", MCP_PROTOCOL_VERSION)
            client_info = params.get("clientInfo", {})
            
            logger.info(f"Initialize request - Client Protocol: {client_protocol_version}")
            logger.info(f"Client Info: {client_info}")
            
            # Generate new session ID for this client
            session_id = str(uuid.uuid4())
            
            # Store session info
            connected_clients[session_id] = {
                "connected_at": datetime.now().isoformat(),
                "user_agent": request.headers.get("user-agent", ""),
                "client_ip": request.client.host if request.client else "unknown",
                "initialized": False,
                "protocol_version": client_protocol_version
            }
            
            # Accept the client's protocol version or use our default
            accepted_version = client_protocol_version if client_protocol_version else MCP_PROTOCOL_VERSION
            
            response = {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {
                    "protocolVersion": accepted_version,
                    "serverInfo": {
                        "name": SERVER_NAME,
                        "version": SERVER_VERSION,
                        "description": "12306火车票查询服务，提供车票查询、车站搜索、中转查询等功能"
                    },
                    "capabilities": {
                        "tools": {}
                    }
                }
            }
            
            # Return response with Mcp-Session-Id header
            logger.info(f"Initialize response sent - Protocol: {accepted_version}, Session: {session_id}")
            return JSONResponse(
                response,
                headers={
                    "Mcp-Session-Id": session_id,
                    "Access-Control-Allow-Origin": "*"
                }
            )
        
        # For all other methods, require session ID
        session_id = request.headers.get("mcp-session-id")
        if not session_id:
            logger.error("Missing Mcp-Session-Id header for non-initialize request")
            return JSONResponse(
                {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "error": {
                        "code": -32000,
                        "message": "Bad Request: No valid session ID provided"
                    }
                },
                status_code=400
            )
        
        # Validate session exists
        if session_id not in connected_clients:
            logger.error(f"Invalid session ID: {session_id}")
            return JSONResponse(
                {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "error": {
                        "code": -32000,
                        "message": "Invalid session ID"
                    }
                },
                status_code=404  # Use 404 for invalid session as per spec
            )
        
        logger.info(f"Processing message for session: {session_id}")
        
        # Handle tool listing
        if method == "tools/list":
            logger.info("Tools list requested")
            response = {
                "jsonrpc": "2.0", 
                "id": request_id,
                "result": {
                    "tools": MCP_TOOLS
                }
            }
            return JSONResponse(response)
        
        # Handle tool execution
        elif method == "tools/call":
            tool_name = params.get("name")
            arguments = params.get("arguments", {})
            
            if not tool_name:
                raise HTTPException(status_code=400, detail="Tool name is required")
            
            logger.info(f"Executing tool: {tool_name}")
            logger.info(f"Arguments: {arguments}")
            
            # Execute the appropriate tool
            try:
                # Map tool names with hyphens to underscores for internal functions
                if tool_name == "query-tickets":
                    content = await query_tickets_validated(arguments)
                elif tool_name == "search-stations":
                    content = await search_stations_validated(arguments)
                elif tool_name == "query-transfer":
                    content = await query_transfer_validated(arguments)
                elif tool_name == "get-train-route-stations":
                    content = await get_train_route_stations_validated(arguments)
                elif tool_name == "get-train-no-by-train-code":
                    content = await get_train_no_by_train_code_validated(arguments)
                elif tool_name == "get-current-time":
                    content = await get_current_time_validated(arguments)
                else:
                    content = [{
                        "type": "text", 
                        "text": f"未知工具: {tool_name}"
                    }]
                
                response = {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "result": {
                        "content": content,
                        "isError": False
                    }
                }
                logger.info(f"Tool {tool_name} executed successfully")
                
            except Exception as tool_error:
                logger.error(f"Tool execution error: {tool_error}")
                response = {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "result": {
                        "content": [{
                            "type": "text",
                            "text": f"工具执行失败: {str(tool_error)}"
                        }],
                        "isError": True
                    }
                }
            
            return JSONResponse(response)
        
        # Handle notifications (no response required)
        elif method and method.startswith("notifications/"):
            notification_type = method.replace("notifications/", "")
            logger.info(f"Received notification: {notification_type}")
            
            # Process notification but don't send response
            if notification_type == "initialized":
                logger.info("Client initialized successfully - MCP handshake complete!")
                # Mark session as fully initialized
                if session_id in connected_clients:
                    connected_clients[session_id]["initialized"] = True
            
            # Notifications should return 202 Accepted according to MCP spec
            return Response(status_code=202)  # Accepted
        
        # Handle ping requests
        elif method == "ping":
            response = {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {
                    "timestamp": datetime.now().isoformat(),
                    "status": "alive"
                }
            }
            return JSONResponse(response)
        
        # Unknown method
        else:
            logger.warning(f"Unknown method: {method}")
            error_response = {
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {
                    "code": -32601,
                    "message": "Method not found",
                    "data": {"method": method}
                }
            }
            return JSONResponse(error_response, status_code=404)
            
    except json.JSONDecodeError:
        logger.error("Invalid JSON in request")
        return JSONResponse(
            {
                "jsonrpc": "2.0",
                "id": None,
                "error": {
                    "code": -32700,
                    "message": "Parse error"
                }
            },
            status_code=400
        )
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return JSONResponse(
            {
                "jsonrpc": "2.0", 
                "id": request_id,
                "error": {
                    "code": -32603,
                    "message": "Internal error",
                    "data": {"error": str(e)}
                }
            },
            status_code=500
        )

@app.delete("/mcp")
async def mcp_endpoint_delete(request: Request):
    """MCP Streamable HTTP Endpoint - DELETE for session termination"""
    session_id = request.headers.get("mcp-session-id")
    
    if not session_id:
        return JSONResponse(
            {"error": "Missing Mcp-Session-Id header"},
            status_code=400
        )
    
    if session_id in connected_clients:
        del connected_clients[session_id]
        logger.info(f"Session terminated: {session_id}")
        return Response(status_code=200)
    else:
        return JSONResponse(
            {"error": "Invalid session ID"},
            status_code=404
        )

# 车站名/三字码自动转换
async def ensure_telecode(val):
    if val.isalpha() and val.isupper() and len(val) == 3:
        return val
    code = await station_service.get_station_code(val)
    return code

# 解析票务字符串

def parse_ticket_string(ticket_str, query):
    parts = ticket_str.split('|')
    if len(parts) < 35:
        return None
    return {
        "train_no": parts[3],
        "start_time": parts[8],
        "arrive_time": parts[9],
        "duration": parts[10],
        "business_seat_num": parts[32] or "",
        "first_class_num": parts[31] or "",
        "second_class_num": parts[30] or "",
        "advanced_soft_sleeper_num": parts[21] or "",
        "soft_sleeper_num": parts[23] or "",
        "dongwo_num": parts[33] or "",
        "hard_sleeper_num": parts[28] or "",
        "soft_seat_num": parts[24] or "",
        "hard_seat_num": parts[29] or "",
        "no_seat_num": parts[26] or "",
        "from_station": query["from_station"],
        "to_station": query["to_station"],
        "train_date": query["train_date"]
    }

# 车站模糊搜索工具
async def search_stations_validated(args: dict) -> list:
    query = args.get("query", "").strip()
    limit = args.get("limit", 10)
    if not query:
        return [{"type": "text", "text": json.dumps({"success": False, "error": "请输入搜索关键词"}, ensure_ascii=False)}]
    if not isinstance(limit, int) or limit < 1 or limit > 50:
        limit = 10
    result = await station_service.search_stations(query, limit)
    if result.stations:
        stations_data = []
        for station in result.stations:
            station_dict = {
                "name": station.name,
                "code": station.code,
                "pinyin": station.pinyin,
                "py_short": station.py_short if station.py_short else "",
            }
            if hasattr(station, 'num') and station.num:
                station_dict["num"] = station.num
            stations_data.append(station_dict)
        
        response_data = {
            "success": True,
            "query": query,
            "count": len(stations_data),
            "stations": stations_data
        }
        return [{"type": "text", "text": json.dumps(response_data, ensure_ascii=False)}]
    else:
        response_data = {
            "success": False,
            "query": query,
            "count": 0,
            "stations": [],
            "message": "未找到匹配的车站",
            "suggestions": [
                "尝试完整城市名称 (如: 北京)",
                "尝试拼音 (如: beijing)",
                "尝试简拼 (如: bj)",
                "检查拼写是否正确"
            ]
        }
        return [{"type": "text", "text": json.dumps(response_data, ensure_ascii=False)}]

# ========== query_tickets_validated 重构 ========== 
async def query_tickets_validated(args: dict) -> list:
    try:
        from_station = args.get("from_station", "").strip()
        to_station = args.get("to_station", "").strip()
        train_date = args.get("train_date", "").strip()
        logger.info(f"查询参数: {from_station} -> {to_station} ({train_date})")
        errors = []
        if not from_station:
            errors.append("出发站不能为空")
        if not to_station:
            errors.append("到达站不能为空")
        if not train_date:
            errors.append("出发日期不能为空")
        elif not validate_date(train_date):
            errors.append("日期格式错误，请使用 YYYY-MM-DD 格式")
        if errors:
            response_data = {"success": False, "errors": errors}
            return [{"type": "text", "text": json.dumps(response_data, ensure_ascii=False)}]
        from_code = await ensure_telecode(from_station)
        to_code = await ensure_telecode(to_station)
        if not from_code or not to_code:
            suggestions = []
            if not from_code:
                result = await station_service.search_stations(from_station, 3)
                if result.stations:
                    suggestions.append({"station_type": "from", "input": from_station, "matches": [{"name": s.name, "code": s.code, "pinyin": s.pinyin, "py_short": s.py_short} for s in result.stations]})
            if not to_code:
                result = await station_service.search_stations(to_station, 3)
                if result.stations:
                    suggestions.append({"station_type": "to", "input": to_station, "matches": [{"name": s.name, "code": s.code, "pinyin": s.pinyin, "py_short": s.py_short} for s in result.stations]})
            response_data = {"success": False, "error": "车站名称无效", "suggestions": suggestions, "hint": "可尝试拼音、简拼、三字码或用 search_stations 工具辅助查询"}
            return [{"type": "text", "text": json.dumps(response_data, ensure_ascii=False)}]
        import httpx
        url_init = "https://kyfw.12306.cn/otn/leftTicket/init"
        url_u = "https://kyfw.12306.cn/otn/leftTicket/queryG"
        headers = {
            "User-Agent": USER_AGENT,
            "Referer": "https://kyfw.12306.cn/otn/leftTicket/init",
            "Host": "kyfw.12306.cn",
            "Accept": "application/json, text/javascript, */*; q=0.01"
        }
        max_retries = 3
        last_exception = None
        tickets_data = []

        for attempt in range(max_retries):
            try:
                async with httpx.AsyncClient(follow_redirects=False, timeout=8, verify=False) as client:
                    await client.get(url_init, headers=headers)
                    params = {
                        "leftTicketDTO.train_date": train_date,
                        "leftTicketDTO.from_station": from_code,
                        "leftTicketDTO.to_station": to_code,
                        "purpose_codes": "ADULT"
                    }
                    resp = await client.get(url_u, headers=headers, params=params)
                    logger.info(f"12306 queryG status: {resp.status_code}, url: {resp.url}")
                    if resp.status_code != 200:
                        logger.error(f"12306接口返回异常: {resp.status_code}, body: {resp.text}")
                        response_data = {"success": False, "error": "12306接口返回异常", "status_code": resp.status_code, "detail": resp.text[:200]}
                        return [{"type": "text", "text": json.dumps(response_data, ensure_ascii=False)}]
                    try:
                        data = resp.json().get("data", {})
                        tickets_data = data.get("result", [])
                        break  # Success
                    except Exception as e:
                        logger.error(f"12306响应解析失败: {repr(e)}，原始内容: {resp.text}")
                        response_data = {"success": False, "error": "12306响应解析失败", "detail": f"{type(e).__name__}: {str(e)}"}
                        return [{"type": "text", "text": json.dumps(response_data, ensure_ascii=False)}]
            except (httpx.TimeoutException, httpx.NetworkError, httpx.ConnectError) as e:
                last_exception = e
                if attempt < max_retries - 1:
                    logger.warning(f"查询车票网络请求失败，正在重试 ({attempt + 1}/{max_retries}): {str(e)}")
                    await asyncio.sleep(1)
                else:
                    logger.error(f"查询车票网络请求重试次数已耗尽: {str(e)}")
        else:
            response_data = {"success": False, "error": f"网络请求失败 (已重试{max_retries}次): {str(last_exception)}"}
            return [{"type": "text", "text": json.dumps(response_data, ensure_ascii=False)}]
        tickets = []
        for ticket_str in tickets_data:
            ticket = parse_ticket_string(ticket_str, {
                "from_station": from_station,
                "to_station": to_station,
                "train_date": train_date
            })
            if ticket:
                tickets.append(ticket)
        if tickets:
            trains_list = []
            for i, ticket in enumerate(tickets, 1):
                ticket_str = tickets_data[i-1] if i-1 < len(tickets_data) else None
                from_station_name = to_station_name = from_code_actual = to_code_actual = None
                if ticket_str:
                    parts = ticket_str.split('|')
                    from_code_actual = parts[6] if len(parts) > 6 else None
                    to_code_actual = parts[7] if len(parts) > 7 else None
                    from_station_obj = await station_service.get_station_by_code(from_code_actual) if from_code_actual else None
                    to_station_obj = await station_service.get_station_by_code(to_code_actual) if to_code_actual else None
                    from_station_name = from_station_obj.name if from_station_obj else (from_code_actual or "未知")
                    to_station_name = to_station_obj.name if to_station_obj else (to_code_actual or "未知")
                
                seats = {}
                if ticket['business_seat_num']: seats["business"] = ticket['business_seat_num']
                if ticket['first_class_num']: seats["first_class"] = ticket['first_class_num']
                if ticket['second_class_num']: seats["second_class"] = ticket['second_class_num']
                if ticket['advanced_soft_sleeper_num']: seats["advanced_soft_sleeper"] = ticket['advanced_soft_sleeper_num']
                if ticket['soft_sleeper_num']: seats["soft_sleeper"] = ticket['soft_sleeper_num']
                if ticket['hard_sleeper_num']: seats["hard_sleeper"] = ticket['hard_sleeper_num']
                if ticket['soft_seat_num']: seats["soft_seat"] = ticket['soft_seat_num']
                if ticket['hard_seat_num']: seats["hard_seat"] = ticket['hard_seat_num']
                if ticket['no_seat_num']: seats["no_seat"] = ticket['no_seat_num']
                if ticket['dongwo_num']: seats["dongwo"] = ticket['dongwo_num']
                
                train_data = {
                    "train_no": ticket['train_no'],
                    "from_station": from_station_name,
                    "from_station_code": from_code_actual,
                    "to_station": to_station_name,
                    "to_station_code": to_code_actual,
                    "start_time": ticket['start_time'],
                    "arrive_time": ticket['arrive_time'],
                    "duration": ticket['duration'],
                    "seats": seats
                }
                trains_list.append(train_data)
            
            response_data = {
                "success": True,
                "from_station": from_station,
                "to_station": to_station,
                "train_date": train_date,
                "count": len(trains_list),
                "trains": trains_list
            }
            return [{"type": "text", "text": json.dumps(response_data, ensure_ascii=False)}]
        else:
            response_data = {
                "success": False,
                "from_station": from_station,
                "to_station": to_station,
                "train_date": train_date,
                "count": 0,
                "trains": [],
                "message": "未找到该线路的余票"
            }
            return [{"type": "text", "text": json.dumps(response_data, ensure_ascii=False)}]
    except Exception as e:
        import traceback
        error_detail = f"{type(e).__name__}: {str(e)}"
        logger.error(f"查询车票失败: {error_detail}\n{traceback.format_exc()}")
        response_data = {"success": False, "error": "查询失败", "detail": error_detail}
        return [{"type": "text", "text": json.dumps(response_data, ensure_ascii=False)}]

# ========== get_train_no_by_train_code_validated 重构 ========== 
async def get_train_no_by_train_code_validated(args: dict) -> list:
    """
    根据车次号、出发站、到达站、日期，查询唯一列车编号train_no。
    只允许精确匹配，所有参数必须为全名或三字码。
    直接请求 /otn/leftTicket/queryG。
    """
    train_code = args.get("train_code", "").strip().upper()
    from_station = args.get("from_station", "").strip().upper()
    to_station = args.get("to_station", "").strip().upper()
    train_date = args.get("train_date", "").strip()
    try:
        dt = datetime.strptime(train_date, "%Y-%m-%d")
        if dt.date() < date.today():
            response_data = {"success": False, "error": "出发日期不能早于今天"}
            return [{"type": "text", "text": json.dumps(response_data, ensure_ascii=False)}]
    except Exception:
        response_data = {"success": False, "error": "出发日期格式错误，应为YYYY-MM-DD"}
        return [{"type": "text", "text": json.dumps(response_data, ensure_ascii=False)}]
    def is_telecode(val):
        return val.isalpha() and val.isupper() and len(val) == 3
    if not is_telecode(from_station):
        code = await station_service.get_station_code(from_station)
        if not code:
            response_data = {"success": False, "error": f"出发站无效或无法识别：{from_station}"}
            return [{"type": "text", "text": json.dumps(response_data, ensure_ascii=False)}]
        from_station = code
    if not is_telecode(to_station):
        code = await station_service.get_station_code(to_station)
        if not code:
            response_data = {"success": False, "error": f"到达站无效或无法识别：{to_station}"}
            return [{"type": "text", "text": json.dumps(response_data, ensure_ascii=False)}]
        to_station = code
    import httpx
    url_init = "https://kyfw.12306.cn/otn/leftTicket/init"
    url_u = "https://kyfw.12306.cn/otn/leftTicket/queryG"
    headers = {
        "User-Agent": USER_AGENT,
        "Referer": "https://kyfw.12306.cn/otn/leftTicket/init",
        "Host": "kyfw.12306.cn",
        "Accept": "application/json, text/javascript, */*; q=0.01"
    }
    async with httpx.AsyncClient(follow_redirects=False, timeout=8, verify=False) as client:
        await client.get(url_init, headers=headers)
        params = {
            "leftTicketDTO.train_date": train_date,
            "leftTicketDTO.from_station": from_station,
            "leftTicketDTO.to_station": to_station,
            "purpose_codes": "ADULT"
        }
        resp = await client.get(url_u, headers=headers, params=params)
        try:
            data = resp.json().get("data", {})
            tickets_data = data.get("result", [])
        except Exception:
            response_data = {"success": False, "error": "12306反爬拦截或数据异常，请稍后重试"}
            return [{"type": "text", "text": json.dumps(response_data, ensure_ascii=False)}]
    if not tickets_data:
        response_data = {"success": False, "error": f"未找到该线路的余票数据（{from_station}->{to_station} {train_date}）"}
        return [{"type": "text", "text": json.dumps(response_data, ensure_ascii=False)}]
    found = None
    for ticket_str in tickets_data:
        parts = ticket_str.split('|')
        try:
            idx = parts.index('预订')
            train_no = parts[idx+1].strip()
            train_code_str = parts[idx+2].strip().upper()
            if train_code_str == train_code:
                found = train_no
                break
        except Exception:
            continue
    if not found:
        debug_codes = []
        for p in tickets_data:
            try:
                parts = p.split('|')
                idx = parts.index('预订')
                debug_codes.append(parts[idx+2])
            except Exception:
                continue
        response_data = {"success": False, "train_code": train_code, "from_station": from_station, "to_station": to_station, "train_date": train_date, "error": "未找到该车次号的列车编号", "available_trains": debug_codes}
        return [{"type": "text", "text": json.dumps(response_data, ensure_ascii=False)}]
    response_data = {"success": True, "train_code": train_code, "train_no": found, "from_station": from_station, "to_station": to_station, "train_date": train_date}
    return [{"type": "text", "text": json.dumps(response_data, ensure_ascii=False)}]

# ========== get_train_route_stations_validated 函数实现 ==========
async def get_train_route_stations_validated(args: dict) -> list:
    """
    查询指定车次的所有经停站及时刻信息。
    参数: train_no(列车编号或车次号), from_station(出发站), to_station(到达站), train_date(日期)
    自动检测输入是车次号还是列车编号，如果是车次号则先转换为列车编号。
    """
    try:
        train_no = args.get("train_no", "").strip()
        from_station = args.get("from_station", "").strip().upper()
        to_station = args.get("to_station", "").strip().upper()
        train_date = args.get("train_date", "").strip()
        
        # 参数校验
        if not train_no:
            response_data = {"success": False, "error": "车次编号(train_no)不能为空"}
            return [{"type": "text", "text": json.dumps(response_data, ensure_ascii=False)}]
        if not from_station:
            response_data = {"success": False, "error": "出发站不能为空"}
            return [{"type": "text", "text": json.dumps(response_data, ensure_ascii=False)}]
        if not to_station:
            response_data = {"success": False, "error": "到达站不能为空"}
            return [{"type": "text", "text": json.dumps(response_data, ensure_ascii=False)}]
        if not train_date:
            response_data = {"success": False, "error": "出发日期不能为空"}
            return [{"type": "text", "text": json.dumps(response_data, ensure_ascii=False)}]
        
        # 日期格式校验
        try:
            dt = datetime.strptime(train_date, "%Y-%m-%d")
            if dt.date() < date.today():
                response_data = {"success": False, "error": "出发日期不能早于今天"}
                return [{"type": "text", "text": json.dumps(response_data, ensure_ascii=False)}]
        except Exception:
            response_data = {"success": False, "error": "出发日期格式错误，应为YYYY-MM-DD"}
            return [{"type": "text", "text": json.dumps(response_data, ensure_ascii=False)}]
        
        # 三字码转换
        def is_telecode(val):
            return val.isalpha() and val.isupper() and len(val) == 3
        
        if not is_telecode(from_station):
            code = await station_service.get_station_code(from_station)
            if not code:
                response_data = {"success": False, "error": f"出发站无效或无法识别：{from_station}"}
                return [{"type": "text", "text": json.dumps(response_data, ensure_ascii=False)}]
            from_station = code
        
        if not is_telecode(to_station):
            code = await station_service.get_station_code(to_station)
            if not code:
                response_data = {"success": False, "error": f"到达站无效或无法识别：{to_station}"}
                return [{"type": "text", "text": json.dumps(response_data, ensure_ascii=False)}]
            to_station = code
        
        # 检测输入是车次号还是列车编号
        # 列车编号格式通常为: 5700xxx或类似的长数字+字母格式（如：57000C95690L）
        # 车次号格式通常为: 字母+数字（如：C9569、G1234、T456）
        import re
        is_train_code = bool(re.match(r'^[A-Z]+\d+$', train_no))
        
        if is_train_code:
            # 输入的是车次号，需要先转换为列车编号
            logger.info(f"检测到车次号 {train_no}，正在转换为列车编号...")
            convert_args = {
                "train_code": train_no,
                "from_station": from_station,
                "to_station": to_station,
                "train_date": train_date
            }
            convert_result = await get_train_no_by_train_code_validated(convert_args)
            
            if not convert_result or not convert_result[0].get("text"):
                response_data = {"success": False, "error": f"无法获取车次 {train_no} 的列车编号"}
                return [{"type": "text", "text": json.dumps(response_data, ensure_ascii=False)}]
            
            result_json_str = convert_result[0].get("text", "{}")
            result_data = json.loads(result_json_str)
            if not result_data.get("success"):
                return convert_result  # 返回错误信息
            
            actual_train_no = result_data.get("train_no")
            if not actual_train_no:
                response_data = {"success": False, "error": f"无法解析车次 {train_no} 的列车编号"}
                return [{"type": "text", "text": json.dumps(response_data, ensure_ascii=False)}]
            logger.info(f"车次 {train_no} 转换为列车编号: {actual_train_no}")
        else:
            # 输入的是列车编号，直接使用
            actual_train_no = train_no
            logger.info(f"使用列车编号: {actual_train_no}")
        
        # 调用12306经停站接口 - 使用正确的API端点
        url = "https://kyfw.12306.cn/otn/czxx/queryByTrainNo"
        params = {
            "train_no": actual_train_no,  # 使用转换后的列车编号
            "from_station_telecode": from_station,
            "to_station_telecode": to_station,
            "depart_date": train_date
        }
        
        # 使用与参考实现相同的请求方式
        headers = {
            "User-Agent": USER_AGENT,
            "Referer": "https://kyfw.12306.cn/otn/leftTicket/init",
            "Accept": "application/json, text/javascript, */*; q=0.01",
            "Accept-Language": "zh-CN,zh;q=0.9",
            "Connection": "keep-alive",
            "Host": "kyfw.12306.cn",            "X-Requested-With": "XMLHttpRequest",
            "Origin": "https://kyfw.12306.cn"
        }
        
        max_retries = 3
        last_exception = None
        json_data = None

        for attempt in range(max_retries):
            try:
                async with httpx.AsyncClient(follow_redirects=False, timeout=8, verify=False) as client:
                    # 先访问init获取cookie
                    init_resp = await client.get("https://kyfw.12306.cn/otn/leftTicket/init", headers=headers)
                    logger.info(f"12306 init status: {init_resp.status_code}")
                    
                    resp = await client.get(url, headers=headers, params=params)
                    logger.info(f"12306 route query status: {resp.status_code}, url: {resp.url}")
                    
                    # 检查HTTP状态码
                    if resp.status_code != 200:
                        logger.error(f"12306接口返回异常状态码: {resp.status_code}, body: {resp.text}")
                        response_data = {"success": False, "error": f"12306接口返回异常: {resp.status_code}"}
                        return [{"type": "text", "text": json.dumps(response_data, ensure_ascii=False)}]
                    
                    # 检查是否被重定向到错误页面
                    if "error.html" in str(resp.url) or "ntce" in str(resp.url):
                        response_data = {"success": False, "error": "12306反爬虫拦截，请稍后重试或更换网络环境"}
                        return [{"type": "text", "text": json.dumps(response_data, ensure_ascii=False)}]
                    
                    try:
                        json_data = resp.json()
                        logger.info(f"12306 response keys: {list(json_data.keys()) if json_data else 'None'}")
                        break # Success
                    except Exception as e:
                        logger.error(f"12306响应解析失败: {str(e)}, body: {resp.text}")
                        response_data = {"success": False, "error": f"12306响应解析失败: {str(e)}"}
                        return [{"type": "text", "text": json.dumps(response_data, ensure_ascii=False)}]
            except (httpx.TimeoutException, httpx.NetworkError, httpx.ConnectError) as e:
                last_exception = e
                if attempt < max_retries - 1:
                    logger.warning(f"查询经停站网络请求失败，正在重试 ({attempt + 1}/{max_retries}): {str(e)}")
                    await asyncio.sleep(1)
                else:
                    logger.error(f"查询经停站网络请求重试次数已耗尽: {str(e)}")
        else:
            response_data = {"success": False, "error": f"网络请求失败 (已重试{max_retries}次): {str(last_exception)}"}
            return [{"type": "text", "text": json.dumps(response_data, ensure_ascii=False)}]
        
        if not json_data:
            response_data = {"success": False, "error": "12306接口返回空数据"}
            return [{"type": "text", "text": json.dumps(response_data, ensure_ascii=False)}]
        
        # 解析经停站数据 - 使用与参考实现相同的数据结构解析
        data = json_data.get("data", {})
        stations = data.get("data", [])
        
        # 兼容官方经停站接口返回的多种数据结构
        if not stations and "middleList" in data:
            stations = []
            for m in data["middleList"]:
                if "fullList" in m:
                    stations.extend(m["fullList"])
        if not stations and "fullList" in data:
            stations = data["fullList"]
        if not stations and "route" in data:
            stations = data["route"]
        
        if not stations:
            response_data = {"success": False, "train_no": train_no, "error": "未找到经停站信息"}
            return [{"type": "text", "text": json.dumps(response_data, ensure_ascii=False)}]
        
        # 格式化输出JSON
        stations_list = []
        for station in stations:
            station_data = {
                "station_no": station.get("station_no", station.get("from_station_no", "")),
                "station_name": station.get("station_name", station.get("from_station_name", "")),
                "arrive_time": station.get("arrive_time", "----"),
                "start_time": station.get("start_time", "----"),
                "stopover_time": station.get("stopover_time", "----")
            }
            stations_list.append(station_data)
        
        response_data = {
            "success": True,
            "train_no": train_no,
            "train_date": train_date,
            "count": len(stations_list),
            "stations": stations_list
        }
        return [{"type": "text", "text": json.dumps(response_data, ensure_ascii=False)}]
        
    except Exception as e:
        logger.error(f"查询经停站失败: {repr(e)}")
        response_data = {"success": False, "error": "查询经停站失败", "detail": str(e)}
        return [{"type": "text", "text": json.dumps(response_data, ensure_ascii=False)}]

# ========== query_transfer_validated 函数实现 ==========
async def query_transfer_validated(args: dict) -> list:
    """
    查询中转换乘方案。使用参考代码的正确实现方式。
    支持指定中转站、学生票、无座车次等选项，自动分页获取所有中转方案。
    """
    try:
        from_station = args.get("from_station", "").strip()
        to_station = args.get("to_station", "").strip()
        train_date = args.get("train_date", "").strip()
        middle_station = args.get("middle_station", "").strip() if "middle_station" in args else ""
        isShowWZ = args.get("isShowWZ", "N").strip().upper() or "N"
        purpose_codes = args.get("purpose_codes", "00").strip().upper() or "00"
        
        # 参数校验
        if not from_station or not to_station or not train_date:
            response_data = {"success": False, "error": "请输入出发站、到达站和出发日期"}
            return [{"type": "text", "text": json.dumps(response_data, ensure_ascii=False)}]
        
        # 日期格式校验
        try:
            dt = datetime.strptime(train_date, "%Y-%m-%d")
            if dt.date() < date.today():
                response_data = {"success": False, "error": "出发日期不能早于今天"}
                return [{"type": "text", "text": json.dumps(response_data, ensure_ascii=False)}]
        except Exception:
            response_data = {"success": False, "error": "出发日期格式错误，应为YYYY-MM-DD"}
            return [{"type": "text", "text": json.dumps(response_data, ensure_ascii=False)}]
        
        # 自动转三字码 - 使用参考代码的实现
        async def ensure_telecode(val):
            if val.isalpha() and val.isupper() and len(val) == 3:
                return val
            code = await station_service.get_station_code(val)
            return code
        
        from_code = await ensure_telecode(from_station)
        to_code = await ensure_telecode(to_station)
        if not from_code:
            response_data = {"success": False, "error": f"出发站无效或无法识别：{from_station}"}
            return [{"type": "text", "text": json.dumps(response_data, ensure_ascii=False)}]
        if not to_code:
            response_data = {"success": False, "error": f"到达站无效或无法识别：{to_station}"}
            return [{"type": "text", "text": json.dumps(response_data, ensure_ascii=False)}]

        # 处理中转站：如果是中文名称，尝试转换为三字码
        middle_station_code = ""
        if middle_station:
            middle_station_code = await ensure_telecode(middle_station)
            if not middle_station_code:
                # 如果转换失败，记录日志但继续尝试使用原值（虽然很可能失败）
                logger.warning(f"无法识别中转站: {middle_station}")
                middle_station_code = middle_station 
        
        # 使用中转查询专用接口
        url_init = "https://kyfw.12306.cn/otn/leftTicket/init"
        url = "https://kyfw.12306.cn/lcquery/queryG"  # 中转查询专用接口
        headers = {
            "User-Agent": USER_AGENT,
            "Referer": "https://kyfw.12306.cn/otn/leftTicket/init",
            "Accept": "application/json, text/javascript, */*; q=0.01",
            "Accept-Language": "zh-CN,zh;q=0.9",
            "Connection": "keep-alive",
            "Host": "kyfw.12306.cn",
            "X-Requested-With": "XMLHttpRequest",
            "Origin": "https://kyfw.12306.cn"
        }
        
        all_transfer_list = []
        max_retries = 3
        last_exception = None

        for attempt in range(max_retries):
            try:
                async with httpx.AsyncClient(follow_redirects=False, timeout=8, verify=False) as client:
                    # 先访问init获取cookie
                    await client.get(url_init, headers=headers)
                    
                    # 分页查询所有中转方案
                    page_size = 10
                    result_index = 0
                    page_num = 1
                    
                    while True:
                        params = {
                            "train_date": train_date,
                            "from_station_telecode": from_code,
                            "to_station_telecode": to_code,
                            "middle_station": middle_station_code,
                            "result_index": str(result_index),
                            "can_query": "Y",
                            "isShowWZ": isShowWZ,
                            "purpose_codes": purpose_codes,
                            "channel": "E"
                        }
                        
                        resp = await client.get(url, headers=headers, params=params)
                        
                        # 检查反爬虫
                        if resp.status_code == 302 or "error.html" in str(resp.headers.get("location", "")):
                            if page_num == 1:
                                response_data = {"success": False, "error": "12306反爬虫拦截（302跳转），请稍后重试或更换网络环境"}
                                return [{"type": "text", "text": json.dumps(response_data, ensure_ascii=False)}]
                            else:
                                break
                        
                        try:
                            data = resp.json().get("data", {})
                            transfer_list = data.get("middleList", [])
                        except Exception:
                            if page_num == 1:
                                response_data = {"success": False, "error": "12306反爬拦截或数据异常，请稍后重试"}
                                return [{"type": "text", "text": json.dumps(response_data, ensure_ascii=False)}]
                            else:
                                break
                        
                        if not transfer_list:
                            break
                        
                        all_transfer_list.extend(transfer_list)
                        
                        # 如果返回的数据少于页面大小，说明已经是最后一页
                        if len(transfer_list) < page_size:
                            break
                        
                        result_index += page_size
                        page_num += 1
                    
                    # Success
                    break
            except (httpx.TimeoutException, httpx.NetworkError, httpx.ConnectError) as e:
                last_exception = e
                # 清空可能已获取的部分数据，准备重试
                all_transfer_list = []
                if attempt < max_retries - 1:
                    logger.warning(f"中转查询网络请求失败，正在重试 ({attempt + 1}/{max_retries}): {str(e)}")
                    await asyncio.sleep(1)
                else:
                    logger.error(f"中转查询网络请求重试次数已耗尽: {str(e)}")
        else:
            response_data = {"success": False, "error": f"网络请求失败 (已重试{max_retries}次): {str(last_exception)}"}
            return [{"type": "text", "text": json.dumps(response_data, ensure_ascii=False)}]
        
        if not all_transfer_list:
            response_data = {
                "success": False,
                "from_station": from_station,
                "to_station": to_station,
                "train_date": train_date,
                "count": 0,
                "transfers": [],
                "message": "未查到中转方案"
            }
            return [{"type": "text", "text": json.dumps(response_data, ensure_ascii=False)}]
        
        # 构建JSON格式的中转方案数据
        transfers_list = []
        for item in all_transfer_list:
            try:
                # 优先用 fullList，降级用 trainList
                full_list = item.get("fullList") or item.get("trainList") or []
                if len(full_list) < 2:
                    continue
                
                # 解析每段车次
                segments = []
                for seg in full_list:
                    # 座位余票信息 - 只包含有票的座位类型
                    seats = {}
                    seat_num = seg.get("swz_num", "")
                    if seat_num and seat_num != "--" and seat_num != "":
                        seats["商务座"] = seat_num
                    seat_num = seg.get("tz_num", "")
                    if seat_num and seat_num != "--" and seat_num != "":
                        seats["特等座"] = seat_num
                    seat_num = seg.get("zy_num", "")
                    if seat_num and seat_num != "--" and seat_num != "":
                        seats["一等座"] = seat_num
                    seat_num = seg.get("ze_num", "")
                    if seat_num and seat_num != "--" and seat_num != "":
                        seats["二等座"] = seat_num
                    seat_num = seg.get("gr_num", "")
                    if seat_num and seat_num != "--" and seat_num != "":
                        seats["高级软卧"] = seat_num
                    seat_num = seg.get("rw_num", "")
                    if seat_num and seat_num != "--" and seat_num != "":
                        seats["软卧"] = seat_num
                    seat_num = seg.get("rz_num", "")
                    if seat_num and seat_num != "--" and seat_num != "":
                        seats["一等卧"] = seat_num
                    seat_num = seg.get("yw_num", "")
                    if seat_num and seat_num != "--" and seat_num != "":
                        seats["硬卧"] = seat_num
                    seat_num = seg.get("yz_num", "")
                    if seat_num and seat_num != "--" and seat_num != "":
                        seats["硬座"] = seat_num
                    seat_num = seg.get("wz_num", "")
                    if seat_num and seat_num != "--" and seat_num != "":
                        seats["无座"] = seat_num
                    
                    segment_data = {
                        "train_code": seg.get("station_train_code", ""),
                        "from_station": seg.get("from_station_name", ""),
                        "to_station": seg.get("to_station_name", ""),
                        "start_time": seg.get("start_time", ""),
                        "arrive_time": seg.get("arrive_time", ""),
                        "duration": seg.get("lishi", ""),
                        "seats": seats
                    }
                    segments.append(segment_data)
                
                transfer_data = {
                    "middle_station": item.get("middle_station_name") or (full_list[0].get("to_station_name", "") if full_list else ""),
                    "wait_time": item.get("wait_time", ""),
                    "total_duration": item.get("all_lishi", ""),
                    "segments": segments
                }
                transfers_list.append(transfer_data)
                
            except Exception as e:
                logger.warning(f"解析中转方案失败: {e}")
                continue
        
        response_data = {
            "success": True,
            "from_station": from_station,
            "to_station": to_station,
            "train_date": train_date,
            "count": len(transfers_list),
            "transfers": transfers_list
        }
        return [{"type": "text", "text": json.dumps(response_data, ensure_ascii=False)}]
        
    except Exception as e:
        logger.error(f"查询中转失败: {repr(e)}")
        response_data = {"success": False, "error": "查询中转失败", "detail": str(e)}
        return [{"type": "text", "text": json.dumps(response_data, ensure_ascii=False)}]

# ========== get_current_time_validated 新增时间工具 ==========
async def get_current_time_validated(args: dict) -> list:
    """
    返回当前时间信息JSON格式
    """
    try:
        from datetime import datetime
        import pytz
        timezone_str = args.get("timezone", "Asia/Shanghai")
        date_format = args.get("format", "YYYY-MM-DD")
        try:
            tz = pytz.timezone(timezone_str)
            now = datetime.now(tz)
        except pytz.exceptions.UnknownTimeZoneError:
            tz = pytz.timezone("Asia/Shanghai")
            now = datetime.now(tz)
        
        response_data = {
            "success": True,
            "timezone": tz.zone,
            "datetime": now.strftime("%Y-%m-%d %H:%M:%S"),
            "date": now.strftime("%Y-%m-%d"),
            "time": now.strftime("%H:%M:%S"),
            "timestamp": int(now.timestamp())
        }
        return [{"type": "text", "text": json.dumps(response_data, ensure_ascii=False)}]
    except Exception as e:
        logger.error(f"获取时间信息失败: {repr(e)}")
        response_data = {"success": False, "error": "获取时间信息失败", "detail": str(e)}
        return [{"type": "text", "text": json.dumps(response_data, ensure_ascii=False)}]

@app.on_event("startup")
async def startup_event():
    """应用启动时的初始化工作"""
    logger.info("启动12306 MCP服务器...")
    logger.info(f"协议版本: {MCP_PROTOCOL_VERSION}")
    logger.info(f"传输类型: Streamable HTTP")
    
    # Load station data
    logger.info("正在加载车站数据...")
    await station_service.load_stations()
    logger.info(f"已加载 {len(station_service.stations)} 个车站")

async def main_server():
    """启动MCP服务器"""
    logger.info("启动12306 MCP服务器...")
    logger.info(f"协议版本: {MCP_PROTOCOL_VERSION}")
    logger.info(f"传输类型: Streamable HTTP")
    logger.info(f"MCP端点: http://{settings.server_host}:{settings.server_port}/mcp")
    logger.info(f"健康检查: http://{settings.server_host}:{settings.server_port}/health")
    
    config = uvicorn.Config(
        app,
        host=settings.server_host,
        port=settings.server_port,
        log_level=settings.log_level.lower()
    )
    uvicorn_server = uvicorn.Server(config)
    await uvicorn_server.serve()

def main():
    asyncio.run(main_server())

if __name__ == "__main__":
    main()
