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
from contextvars import ContextVar
from typing import Optional

from mcp.server import Server
import mcp.types as types
from mcp import McpError

from mcp_server.core.config import settings
from mcp_server.core.logging import get_logger
from mcp_server.auth import (
    validate_mcp_token,
    AuthenticatedContext,
)
from mcp_server.client import BackendAPIClient
from mcp_server.tools.ask_tool import ask_knowledge_base_impl
from mcp_server.core.errors import AuthenticationError, BackendError

logger = get_logger(__name__)


# Global MCP server instance
_server: Server = None
_backend_client: BackendAPIClient = None

# Request-scoped context for authenticated user (async-safe)
_auth_context: ContextVar[Optional[AuthenticatedContext]] = ContextVar('auth_context', default=None)


def create_app() -> Server:
    """
    Create and configure the MCP server.
    
    This creates the official MCP Server using the SDK, and registers
    handlers for MCP requests (initialize, tools/list, tools/call).
    
    Returns:
        Configured MCP Server instance
    """
    global _server, _backend_client
    
    server = Server("secure-rag-mcp")
    _backend_client = BackendAPIClient()
    
    logger.info(f"MCP Server initialized: {server.name}")
    logger.info(f"Backend URL: {settings.backend_url}")
    
    # Initialize handler - called by MCP clients to discover server capabilities
    async def handle_initialize(request: types.InitializeRequest) -> types.InitializeResult:
        """
        Handle MCP initialize request.
        
        This is the first request from any MCP client and doesn't require authentication.
        Returns server capabilities and protocol version.
        """
        logger.info(f"MCP initialize request from client: {request.params.clientInfo.name}")
        
        return types.InitializeResult(
            protocolVersion="2024-11-05",  # MCP protocol version
            capabilities=types.ServerCapabilities(
                tools=types.ToolsCapability(
                    listChanged=False
                ),
                resources=None,
                prompts=None,
            ),
            serverInfo=types.Implementation(
                name="secure-rag-mcp",
                version="0.2.0"
            ),
        )
    
    # Tools list handler
    async def handle_list_tools(request: types.ListToolsRequest) -> types.ListToolsResult:
        """
        List available tools.
        
        This handler returns the list of tools available to the client.
        Requires authentication via Authorization header.
        """
        return types.ListToolsResult(
            tools=[
                types.Tool(
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
        )
    
    # Tool call handler
    async def handle_call_tool(
        request: types.CallToolRequest
    ) -> types.CallToolResult:
        """
        Execute a tool.
        
        The authenticated user context is stored in the transport layer
        and available through the ContextVar.
        
        Requires authentication via Authorization header.
        """
        if request.params.name != "ask_knowledge_base":
            raise McpError(f"Unknown tool: {request.params.name}")
        
        # Extract parameters
        question = request.params.arguments.get("question", "").strip()
        if not question:
            raise McpError("Question is required")
        
        # Get authenticated context from context variable
        # (set by transport layer during authentication)
        from mcp_server.transport import get_auth_context
        auth_context: Optional[AuthenticatedContext] = get_auth_context()
        
        if not auth_context:
            raise McpError("Authentication context not found (internal error)")
        
        logger.info(f"Tool call: {request.params.name} | user_id={auth_context.user_id}")
        
        try:
            # Call tool implementation
            result = await ask_knowledge_base_impl(
                question=question,
                auth_context=auth_context,
                backend_client=_backend_client
            )
            
            return types.CallToolResult(
                content=[types.TextContent(type="text", text=result)],
                isError=False
            )
            
        except BackendError as e:
            logger.error(f"Backend error in tool: {e}")
            return types.CallToolResult(
                content=[types.TextContent(type="text", text=f"Backend error: {e}")],
                isError=True
            )
        except Exception as e:
            logger.error(f"Tool error: {e}", exc_info=True)
            return types.CallToolResult(
                content=[types.TextContent(type="text", text=f"Tool execution failed: {str(e)}")],
                isError=True
            )
    
    # Register handlers using the request_handlers dict
    server.request_handlers["initialize"] = (handle_initialize, types.InitializeRequest)
    server.request_handlers["tools/list"] = (handle_list_tools, types.ListToolsRequest)
    server.request_handlers["tools/call"] = (handle_call_tool, types.CallToolRequest)
    
    _server = server
    return server


async def authenticate_request(server: Server, token: str) -> AuthenticatedContext:
    """
    Authenticate incoming MCP request using MCP token.
    
    This function:
    1. Validates the MCP token
    2. Calls backend to get user identity
    3. Gets short-lived backend JWT
    4. Stores context for tool handlers
    5. Returns authenticated context
    
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
        
        # Store in context variable for tool handlers
        _auth_context.set(auth_context)
        
        logger.info(f"MCP request authenticated: user_id={auth_context.user_id}, dept={auth_context.department_name}")
        
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


# Exports
__all__ = [
    "create_app",
    "authenticate_request",
    "health_check",
    "get_server",
    "settings",
]

# Note: The actual HTTP transport and request handling will be configured
# in main.py using the MCP SDK's Streamable HTTP transport
