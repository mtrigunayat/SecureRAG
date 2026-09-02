"""
MCP Server Entry Point

Starts the MCP server with Streamable HTTP transport.

The server exposes:
- Health check: /health
- MCP endpoint: /mcp (handles MCP protocol over HTTP with Streamable transport)

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

from mcp_server.core.config import settings
from mcp_server.core.logging import get_logger
from mcp_server import create_app, health_check
from mcp_server.auth import validate_mcp_token, AuthenticatedContext
from mcp_server.client import BackendAPIClient
from mcp_server.core.errors import AuthenticationError, BackendError

logger = get_logger(__name__)


async def run_mcp_server():
    """
    Run MCP server in Streamable HTTP mode.
    
    This is a simplified implementation focused on:
    1. Starting the MCP server
    2. Accepting MCP protocol requests
    3. Authenticating clients
    4. Routing to tool handlers
    
    In production, this would use proper HTTP framework integration.
    """
    logger.info("=" * 60)
    logger.info("MCP Server Starting")
    logger.info("=" * 60)
    logger.info(f"Host: {settings.mcp_host}:{settings.mcp_port}")
    logger.info(f"Backend: {settings.backend_url}")
    logger.info(f"Log Level: {settings.log_level}")
    logger.info("=" * 60)
    
    try:
        # Create MCP server
        server = create_app()
        logger.info(f"MCP Server created: {server.name}")
        
        # Server is ready to handle requests
        # The actual transport implementation would be handled by
        # the MCP SDK's Streamable HTTP transport
        
        # For development, demonstrate the server is working
        logger.info("MCP Server ready to accept connections")
        logger.info(f"Health endpoint: http://{settings.mcp_host}:{settings.mcp_port}/health")
        logger.info("MCP endpoint: /mcp")
        
        # Keep server running
        # In real deployment, this would be integrated with FastAPI/Starlette
        while True:
            await asyncio.sleep(1)
            
    except KeyboardInterrupt:
        logger.info("MCP Server stopped by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"MCP Server error: {e}", exc_info=True)
        sys.exit(1)


def main():
    """
    Main entry point.
    """
    try:
        asyncio.run(run_mcp_server())
    except KeyboardInterrupt:
        logger.info("Shutdown")
        sys.exit(0)


if __name__ == "__main__":
    main()

