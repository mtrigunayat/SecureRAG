"""
Backend API Client

Communicates with the existing FastAPI backend.
"""
from mcp_server.client.backend_api_client import (
    BackendAPIClient,
    ChatResponse,
    ChatSource,
)

__all__ = ["BackendAPIClient", "ChatResponse", "ChatSource"]
