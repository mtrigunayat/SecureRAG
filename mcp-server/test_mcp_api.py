#!/usr/bin/env python3
"""
Quick test of MCP Server API
"""
import asyncio
from mcp.server import Server
import mcp.types as types

async def main():
    server = Server("test-server")
    
    # Register handler using decorator syntax
    @server.add_request_handler(types.ListToolsRequest)
    async def handle_list_tools(request: types.ListToolsRequest) -> types.ListToolsResult:
        return types.ListToolsResult(tools=[])
    
    print("✅ Server creation and handler registration successful")

if __name__ == "__main__":
    asyncio.run(main())
