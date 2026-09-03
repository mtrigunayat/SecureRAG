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

from mcp.server import Server
import mcp.types as types
from mcp import MCPError

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

# Handler function references (populated by create_app)
_handle_list_tools_fn = None
_handle_call_tool_fn = None

# Request-scoped context for authenticated user (async-safe)
_auth_context: ContextVar[AuthenticatedContext] = ContextVar('auth_context', default=None)


def create_app() -> Server:
    """
    Create and configure the MCP server.
    
    Returns:
        Configured MCP Server instance
    """
    global _server, _backend_client, _handle_list_tools_fn, _handle_call_tool_fn
    
    server = Server("secure-rag-mcp")
    _backend_client = BackendAPIClient()
    
    logger.info(f"MCP Server initialized: {server.name}")
    logger.info(f"Backend URL: {settings.backend_url}")
    
    # Define request handlers
    async def handle_list_tools(request: types.ListToolsRequest) -> types.ListToolsResult:
        """List available tools."""
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
    
    async def handle_call_tool(
        request: types.CallToolRequest
    ) -> types.CallToolResult:
        """
        Execute a tool.
        
        The authenticated user context is stored in _auth_context
        and is available for tool execution.
        """
        if request.name != "ask_knowledge_base":
            raise MCPError(f"Unknown tool: {request.name}")
        
        # Extract parameters
        question = request.arguments.get("question", "").strip()
        if not question:
            raise MCPError("Question is required")
        
        # Get authenticated context from context variable
        auth_context: AuthenticatedContext = _auth_context.get()
        
        if not auth_context:
            raise MCPError("Authentication context not found (internal error)")
        
        logger.info(f"Tool call: {request.name} | user_id={auth_context.user_id}")
        
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
    
    # Register handlers with the server using MCP 2.1.1 API
    server.add_request_handler("tools/list", types.RequestParams, handle_list_tools)
    server.add_request_handler("tools/call", types.CallToolRequestParams, handle_call_tool)
    
    # Store handler references for direct access in HTTP transport
    _handle_list_tools_fn = handle_list_tools
    _handle_call_tool_fn = handle_call_tool
    
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
