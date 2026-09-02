"""
MCP Server Main Application

Initializes and runs the MCP (Model Context Protocol) server.

Architecture:
    MCP Client (Claude)
        ↓ MCP over HTTPS
    MCP Server (this app)
        ↓ internal authentication
    Backend FastAPI (existing)
        ↓ existing RAG pipeline
    Returns answer with sources
        ↓
    MCP Client response
"""
import asyncio
from contextlib import asynccontextmanager

from mcp.server.server import Server
from mcp.types import Tool, TextContent, McpError
import mcp.types as types

from mcp_server.core.config import settings
from mcp_server.core.logging import get_logger
from mcp_server.auth import (
    validate_mcp_token,
    AuthenticatedContext,
)
from mcp_server.client import BackendAPIClient
from mcp_server.tools import ask_knowledge_base_impl
from mcp_server.core.errors import AuthenticationError, BackendError

logger = get_logger(__name__)


# Global MCP server instance
_server: Server = None
_backend_client: BackendAPIClient = None


def create_app() -> Server:
    """
    Create and configure the MCP server.
    
    Returns:
        Configured MCP Server instance
    """
    global _server, _backend_client
    
    server = Server("secure-rag-mcp")
    _backend_client = BackendAPIClient()
    
    logger.info(f"MCP Server initialized: {server.name}")
    logger.info(f"Backend URL: {settings.backend_url}")
    
    @server.list_tools()
    async def list_tools() -> list[Tool]:
        """List available tools."""
        return [
            Tool(
                name="ask_knowledge_base",
                description=(
                    "Query the company's internal knowledge base to answer questions "
                    "about policies, procedures, documentation, and organizational knowledge. "
                    "Use this tool when the user asks about company-specific information, "
                    "internal guidelines, security procedures, HR policies, or technical documentation. "
                    "This tool will only return information that you are authorized to access "
                    "based on your department."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "question": {
                            "type": "string",
                            "description": "The question to ask about the knowledge base",
                            "minLength": 1,
                            "maxLength": 1000
                        }
                    },
                    "required": ["question"]
                }
            )
        ]
    
    @server.call_tool()
    async def call_tool(
        name: str,
        arguments: dict
    ) -> list[TextContent]:
        """
        Execute a tool.
        
        The request context contains the authenticated user information,
        which is used to:
        1. Resolve user identity (from MCP token)
        2. Enforce department-based authorization
        3. Authenticate with backend
        
        The MCP SDK provides request context through the server's
        request state. We extract the authenticated context from there.
        """
        if name != "ask_knowledge_base":
            raise McpError(f"Unknown tool: {name}")
        
        # Extract parameters
        question = arguments.get("question", "").strip()
        if not question:
            raise McpError("Question is required")
        
        # Get authenticated context from request
        # The MCP SDK's server.request_context or similar mechanism
        # should provide the authenticated context set during authentication
        # For this implementation, we assume it's available as a property
        auth_context: AuthenticatedContext = getattr(
            server,
            '_current_auth_context',
            None
        )
        
        if not auth_context:
            raise McpError("Authentication context not found (internal error)")
        
        logger.info(f"Tool call: {name} | user_id={auth_context.user_id}")
        
        try:
            # Call tool implementation
            result = await ask_knowledge_base_impl(
                question=question,
                auth_context=auth_context,
                backend_client=_backend_client
            )
            
            return [TextContent(type="text", text=result)]
            
        except Exception as e:
            logger.error(f"Tool error: {e}")
            raise McpError(f"Tool execution failed: {str(e)}")
    
    _server = server
    return server


async def authenticate_request(server: Server, token: str) -> AuthenticatedContext:
    """
    Authenticate incoming MCP request using MCP token.
    
    This function:
    1. Validates the MCP token
    2. Calls backend to get user identity
    3. Gets short-lived backend JWT
    4. Returns authenticated context
    
    The authenticated context is then stored in the request
    for use by tool handlers.
    
    Args:
        server: MCP Server instance
        token: MCP token from client
        
    Returns:
        AuthenticatedContext with user identity and backend JWT
        
    Raises:
        AuthenticationError: If token invalid
    """
    try:
        logger.info("Authenticating MCP request")
        
        # Validate MCP token with backend
        auth_context = await validate_mcp_token(token)
        
        logger.info(f"MCP request authenticated: user_id={auth_context.user_id}")
        
        return auth_context
        
    except AuthenticationError as e:
        logger.warning(f"Authentication failed: {e.message}")
        raise
    except Exception as e:
        logger.error(f"Unexpected authentication error: {e}")
        raise AuthenticationError("Authentication failed")


async def health_check() -> dict:
    """
    Health check endpoint for deployment/readiness.
    
    Returns:
        Health status dictionary
    """
    return {
        "status": "healthy",
        "service": "mcp-server",
        "backend": settings.backend_url
    }


def get_server() -> Server:
    """
    Get the global MCP server instance.
    
    Returns:
        Server instance
    """
    if _server is None:
        return create_app()
    return _server


# Note: The actual HTTP transport and request handling will be configured
# in main.py using the MCP SDK's Streamable HTTP transport
