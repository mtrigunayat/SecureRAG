"""
Backend API Client

HTTP client for communicating with the existing FastAPI backend.
"""
import httpx
from typing import Optional

from mcp_server.core.config import settings
from mcp_server.core.logging import get_logger
from mcp_server.core.errors import (
    BackendError,
    BackendUnavailableError,
    BackendTimeoutError,
)

logger = get_logger(__name__)


class ChatSource:
    """Source attribution for chat response."""
    
    def __init__(self, data: dict):
        self.document_id: int = data.get("document_id")
        self.document_name: str = data.get("document_name", "Unknown")
        self.sensitivity: str = data.get("sensitivity", "internal")
    
    def __repr__(self) -> str:
        return f"<ChatSource({self.document_name})>"


class ChatResponse:
    """Response from backend chat endpoint."""
    
    def __init__(self, data: dict):
        self.answer: str = data.get("answer", "")
        sources_data = data.get("sources", [])
        self.sources: list[ChatSource] = [ChatSource(s) for s in sources_data]
    
    def __repr__(self) -> str:
        return f"<ChatResponse(answer_len={len(self.answer)}, sources={len(self.sources)})>"


class BackendAPIClient:
    """
    HTTP client for backend API calls.
    
    Handles:
    - Authenticated requests to /api/chat
    - Error handling and timeouts
    - Response parsing
    """
    
    def __init__(self):
        self.backend_url = settings.backend_url
        self.timeout = settings.backend_api_timeout
    
    async def ask_knowledge_base(
        self,
        question: str,
        backend_jwt: str
    ) -> ChatResponse:
        """
        Query the knowledge base.
        
        Args:
            question: Question to ask
            backend_jwt: Short-lived backend JWT
            
        Returns:
            ChatResponse with answer and sources
            
        Raises:
            BackendError: If backend error
            BackendTimeoutError: If request times out
            BackendUnavailableError: If backend unreachable
        """
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.backend_url}/api/chat",
                    json={"question": question},
                    headers={"Authorization": f"Bearer {backend_jwt}"}
                )
            
            if response.status_code == 401:
                logger.error("Backend JWT rejected (expired or invalid)")
                raise BackendError("Backend authentication failed")
            
            if response.status_code == 403:
                logger.error("Backend authorization denied")
                raise BackendError("Not authorized to access knowledge base")
            
            if response.status_code == 500:
                logger.error(f"Backend error: {response.text}")
                raise BackendError("Backend service error")
            
            if response.status_code != 200:
                logger.error(f"Unexpected backend response: {response.status_code}")
                raise BackendError(f"Backend returned {response.status_code}")
            
            # Parse response
            data = response.json()
            chat_response = ChatResponse(data)
            
            logger.info(
                f"Knowledge base query successful: "
                f"answer_len={len(chat_response.answer)}, "
                f"sources={len(chat_response.sources)}"
            )
            return chat_response
            
        except httpx.TimeoutException:
            logger.error(f"Backend request timed out ({self.timeout}s)")
            raise BackendTimeoutError()
        except httpx.ConnectError:
            logger.error(f"Cannot connect to backend: {self.backend_url}")
            raise BackendUnavailableError()
        except httpx.HTTPError as e:
            logger.error(f"Backend HTTP error: {e}")
            raise BackendUnavailableError()
        except KeyError as e:
            logger.error(f"Invalid backend response format: {e}")
            raise BackendError("Invalid backend response")
        except Exception as e:
            logger.error(f"Unexpected error: {e}", exc_info=True)
            raise BackendError("Unexpected backend error")
