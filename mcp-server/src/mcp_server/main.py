"""
MCP Server Entry Point - Streamable HTTP Transport

Starts the MCP server with proper Streamable HTTP transport using the official MCP SDK.

The server exposes:
- Health check: GET /health → {"status":"healthy"}
- MCP endpoint: POST /mcp → Streamable HTTP MCP transport
- OAuth discovery: GET /.well-known/oauth-authorization-server
- OAuth token endpoint: POST /oauth/token
- OAuth authorization: GET /oauth/authorize

Authentication:
  - MCP clients include Authorization: Bearer <mcp_token> header
  - Server validates token with backend
  - Backend returns authenticated user info + short-lived JWT
  - Server uses JWT for backend API calls
  
Lifecycle:
  1. Client connects
  2. Client sends initialize request (no auth required)
  3. Server returns capabilities + protocol version
  4. Client sends tools/list (requires auth)
  5. Server validates token, loads user, returns tools
  6. Client sends tools/call (requires auth)
  7. Server validates token, executes tool, returns result
"""
import asyncio
import sys
from typing import Optional

import uvicorn
from starlette.applications import Starlette
from starlette.responses import JSONResponse
from starlette.routing import Route
from starlette.requests import Request

from mcp.server import Server

from mcp_server.core.config import settings
from mcp_server.core.logging import get_logger
from mcp_server import create_app
from mcp_server.transport import mcp_endpoint, _auth_context
from mcp_server.oauth import (
    oauth_authorization_server_metadata,
    oauth_authorize,
    oauth_token
)

logger = get_logger(__name__)

# Global MCP server instance
_mcp_server: Optional[Server] = None


async def health_endpoint(request):
    """
    Health check endpoint for deployment and monitoring.
    
    Returns:
        JSON response with status
    """
    try:
        return JSONResponse({
            "status": "healthy",
            "service": "MCP Server",
            "version": "0.2.0"
        })
    except Exception as e:
        logger.error(f"Health check error: {e}")
        return JSONResponse(
            {"status": "unhealthy", "error": str(e)},
            status_code=503
        )


async def mcp_endpoint_handler(request: Request):
    """
    MCP Streamable HTTP endpoint handler.
    
    Routes through the official transport layer.
    """
    global _mcp_server
    
    # Initialize MCP server once
    if _mcp_server is None:
        _mcp_server = create_app()
    
    # Clear auth context for this request
    _auth_context.set(None)
    
    try:
        return await mcp_endpoint(_mcp_server, request)
    finally:
        # Clean up context after request
        _auth_context.set(None)


async def oauth_metadata_handler(request: Request):
    """OAuth authorization server metadata endpoint."""
    return await oauth_authorization_server_metadata(request)


async def oauth_authorize_handler(request: Request):
    """OAuth authorization endpoint."""
    return await oauth_authorize(request)


async def oauth_token_handler(request: Request):
    """OAuth token endpoint."""
    return await oauth_token(request)


async def run_mcp_server():
    """
    Run MCP server with Streamable HTTP transport (Starlette + Uvicorn).
    
    Creates an HTTP server that:
    1. Listens on configured host:port
    2. Exposes health endpoint
    3. Exposes MCP protocol endpoint
    4. Exposes OAuth discovery and token endpoints
    5. Uses Uvicorn ASGI server
    
    The server implements the official MCP Streamable HTTP transport
    and OAuth 2.1 authorization for Claude Custom Remote Connector support.
    """
    logger.info("=" * 70)
    logger.info("MCP Server Starting with Streamable HTTP Transport")
    logger.info("=" * 70)
    logger.info(f"Host: {settings.mcp_host}:{settings.mcp_port}")
    logger.info(f"Public URL: {settings.mcp_public_url}")
    logger.info(f"Backend: {settings.backend_url}")
    logger.info(f"Log Level: {settings.log_level}")
    logger.info("=" * 70)
    logger.info("Endpoints:")
    logger.info(f"  Health:        GET /health")
    logger.info(f"  MCP:           POST /mcp")
    logger.info(f"  OAuth Metadata GET /.well-known/oauth-authorization-server")
    logger.info(f"  OAuth Authorize GET /oauth/authorize")
    logger.info(f"  OAuth Token:   POST /oauth/token")
    logger.info("=" * 70)
    
    # Create Starlette application with routes
    app = Starlette(
        routes=[
            # Health check
            Route("/health", health_endpoint, methods=["GET"]),
            
            # MCP Streamable HTTP endpoint
            Route("/mcp", mcp_endpoint_handler, methods=["POST"]),
            
            # OAuth endpoints
            Route(
                "/.well-known/oauth-authorization-server",
                oauth_metadata_handler,
                methods=["GET"]
            ),
            Route("/oauth/authorize", oauth_authorize_handler, methods=["GET"]),
            Route("/oauth/token", oauth_token_handler, methods=["POST"]),
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
    
    # Start server
    await server.serve()


def main():
    """Entry point for MCP server."""
    logger.info("MCP Server starting")
    
    try:
        # Run async event loop
        asyncio.run(run_mcp_server())
    except KeyboardInterrupt:
        logger.info("MCP Server shut down by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"MCP Server error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()

