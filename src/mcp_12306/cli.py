#!/usr/bin/env python3
"""MCP Server 12306 - CLI Entry Point

This module provides the command-line interface for running the MCP Server 12306
in stdio mode, suitable for use with Claude Desktop and other MCP clients.
"""

import asyncio
import sys
import logging


def main():
    """Main entry point for the CLI command"""
    # 配置日志输出到 stderr，避免干扰 stdio 通信
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        stream=sys.stderr
    )
    
    # 运行 stdio 服务器
    from mcp_12306.stdio_server import run_stdio_server
    
    try:
        asyncio.run(run_stdio_server())
    except KeyboardInterrupt:
        logging.info("收到中断信号，正在关闭服务器...")
    except Exception as e:
        logging.error(f"服务器运行失败: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
