"""
MCP Server Entry Point

Starts the MCP server with HTTP transport using Starlette and Uvicorn.

The server exposes:
- Health check: GET /health → {"status":"healthy"}
- MCP endpoint: POST /mcp → Streamable HTTP transport for MCP protocol

Authentication:
  - MCP clients include Authorization: Bearer <mcp_token> header
  - Server validates token with backend
  - Backend returns authenticated user info + short-lived JWT
  - Server uses JWT for backend API calls
"""
import asyncio
import sys
import json
from typing import Optional

import uvicorn
from starlette.applications import Starlette
from starlette.responses import JSONResponse
from starlette.routing import Route
from starlette.requests import Request

from mcp_server.core.config import settings
from mcp_server.core.logging import get_logger
from mcp_server import create_app, health_check
import mcp_server as mcp_server_module

logger = get_logger(__name__)

# Global MCP server instance
_mcp_server = None


async def health_endpoint(request):
    """
    Health check endpoint for deployment and monitoring.
    
    Returns:
        JSON response with status
    """
    try:
        health_info = await health_check()
        return JSONResponse({"status": "healthy", "details": health_info})
    except Exception as e:
        logger.error(f"Health check error: {e}")
        return JSONResponse(
            {"status": "unhealthy", "error": str(e)},
            status_code=503
        )


async def mcp_endpoint(request: Request):
    """
    MCP protocol HTTP endpoint using Streamable HTTP transport.
    
    Receives JSON-RPC style MCP requests and routes them to the server handlers.
    This is a Streamable HTTP transport implementation that integrates with the
    MCP Server's registered request handlers.
    """
    global _mcp_server
    
    try:
        # Initialize MCP server once
        if _mcp_server is None:
            _mcp_server = create_app()
        
        # Parse incoming request
        try:
            body = await request.json()
        except json.JSONDecodeError:
            return JSONResponse(
                {"error": "Invalid JSON in request body"},
                status_code=400
            )
        
        # MCP protocol uses JSON-RPC style messages
        method = body.get("method")
        params = body.get("params", {})
        request_id = body.get("id")
        
        if not method:
            return JSONResponse({
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {"code": -32700, "message": "Parse error - missing method"}
            }, status_code=400)
        
        logger.info(f"MCP request: {method}")
        
        # Get handler functions from module (populated by create_app)
        
        if method == "tools/list":
            try:
                from mcp import types
                list_request = types.ListToolsRequest()
                
                # Call the handler
                handler = mcp_server_module._handle_list_tools_fn
                if handler and callable(handler):
                    result = await handler(list_request)
                    return JSONResponse({
                        "jsonrpc": "2.0",
                        "id": request_id,
                        "result": result.model_dump() if hasattr(result, "model_dump") else result
                    })
                else:
                    return JSONResponse({
                        "jsonrpc": "2.0",
                        "id": request_id,
                        "error": {"code": -32601, "message": "tools/list handler not available"}
                    }, status_code=500)
            except Exception as e:
                logger.error(f"Error in tools/list: {e}", exc_info=True)
                return JSONResponse({
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "error": {"code": -32603, "message": str(e)}
                }, status_code=500)
        
        elif method == "tools/call":
            try:
                from mcp import types
                call_request = types.CallToolRequest(**params)
                
                # Call the handler
                handler = mcp_server_module._handle_call_tool_fn
                if handler and callable(handler):
                    result = await handler(call_request)
                    return JSONResponse({
                        "jsonrpc": "2.0",
                        "id": request_id,
                        "result": result.model_dump() if hasattr(result, "model_dump") else result
                    })
                else:
                    return JSONResponse({
                        "jsonrpc": "2.0",
                        "id": request_id,
                        "error": {"code": -32601, "message": "tools/call handler not available"}
                    }, status_code=500)
            except Exception as e:
                logger.error(f"Error in tools/call: {e}", exc_info=True)
                return JSONResponse({
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "error": {"code": -32603, "message": str(e)}
                }, status_code=500)
        
        else:
            return JSONResponse({
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {"code": -32601, "message": f"Method not found: {method}"}
            }, status_code=400)
    
    except Exception as e:
        logger.error(f"MCP endpoint error: {e}", exc_info=True)
        return JSONResponse(
            {"error": f"Internal server error: {str(e)}"},
            status_code=500
        )


async def run_mcp_server():
    """
    Run MCP server with HTTP transport (Starlette + Uvicorn).
    
    Creates an HTTP server that:
    1. Listens on configured host:port
    2. Exposes /health endpoint
    3. Exposes /mcp endpoint for MCP protocol
    4. Uses Uvicorn ASGI server
    """
    logger.info("=" * 60)
    logger.info("MCP Server Starting with HTTP Transport")
    logger.info("=" * 60)
    logger.info(f"Host: {settings.mcp_host}:{settings.mcp_port}")
    logger.info(f"Backend: {settings.backend_url}")
    logger.info(f"Log Level: {settings.log_level}")
    logger.info("=" * 60)
    
    # Create Starlette application with routes
    app = Starlette(
        routes=[
            Route("/health", health_endpoint, methods=["GET"]),
            Route("/mcp", mcp_endpoint, methods=["POST", "GET"]),
        ],
    )
    
    # Configure Uvicorn server
    config = uvicorn.Config(
        app=app,
        host=settings.mcp_host,
        port=settings.mcp_port,
        log_level=settings.log_level.lower(),
    )
    server = uvicorn.Server(config)
    
    logger.info(f"HTTP server binding to {settings.mcp_host}:{settings.mcp_port}")
    logger.info(f"Health endpoint: http://{settings.mcp_host}:{settings.mcp_port}/health")
    logger.info(f"MCP endpoint: http://{settings.mcp_host}:{settings.mcp_port}/mcp")
    logger.info("")
    
    try:
        # Start Uvicorn server (blocks until interrupted)
        await server.serve()
    except KeyboardInterrupt:
        logger.info("MCP Server stopped by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"MCP Server error: {e}", exc_info=True)
        sys.exit(1)


def main():
    """
    Main entry point for production deployment.
    """
    try:
        asyncio.run(run_mcp_server())
    except KeyboardInterrupt:
        logger.info("Shutdown")
        sys.exit(0)


if __name__ == "__main__":
    main()

