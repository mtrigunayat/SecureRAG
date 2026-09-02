"""
Backend API Client

Communicates with the existing FastAPI backend.
"""
import httpx
from typing import Optional

from mcp_server.core.config import settings
from mcp_server.core.logging import get_logger
from mcp_server.core.errors import (
    BackendError,
    BackendUnavailableError,
    BackendTimeoutError,
    InvalidBackendResponseError,
)

logger = get_logger(__name__)


class BackendAPIClient:
    """
    Client for communicating with backend FastAPI application.
    
    Handles:
    - Calling backend endpoints
    - Managing backend JWT credentials
    - Timeout and error handling
    """
    
    def __init__(self, backend_url: Optional[str] = None, timeout: Optional[int] = None):
        self.backend_url = backend_url or settings.backend_url
        self.timeout = timeout or settings.backend_api_timeout
    
    async def ask_knowledge_base(self, question: str, backend_jwt: str) -> dict:
        """
        Ask a question to the backend knowledge base.
        
        This calls the backend /api/chat endpoint with the authenticated user's JWT.
        The backend handles all authorization, RAG retrieval, and LLM generation.
        
        Args:
            question: User's question
            backend_jwt: Short-lived backend JWT (obtained from /api/internal/mcp/validate)
            
        Returns:
            Backend ChatResponse as dictionary
            
        Raises:
            BackendError: If backend request fails
            BackendUnavailableError: If backend unreachable
            BackendTimeoutError: If backend request times out
            InvalidBackendResponseError: If backend response is invalid
            
        Security:
            - Uses backend JWT for authentication (short-lived)
            - Does NOT pass user_id or department (backend derives from JWT)
            - Backend enforces authorization and ACL
            - Only authorized sources returned
        """
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.backend_url}/api/chat",
                    json={"question": question},
                    headers={
                        "Authorization": f"Bearer {backend_jwt}",
                        "Content-Type": "application/json",
                    }
                )
            
            if response.status_code == 401:
                logger.warning("Backend rejected JWT authentication")
                raise BackendError("Backend authentication failed", "Authentication failed")
            
            if response.status_code == 403:
                logger.warning("Backend rejected request (forbidden)")
                raise BackendError("Authorization failed", "Access denied")
            
            if response.status_code == 400:
                logger.warning(f"Backend request validation failed: {response.text}")
                raise InvalidBackendResponseError("Invalid request")
            
            if response.status_code == 500:
                logger.error(f"Backend error: {response.text}")
                raise BackendError("Backend error", "Backend service error")
            
            if response.status_code != 200:
                logger.error(f"Unexpected backend response: {response.status_code}")
                raise BackendError(f"Unexpected status {response.status_code}", "Backend error")
            
            # Parse response
            data = response.json()
            
            # Validate response structure
            if "answer" not in data:
                logger.error(f"Invalid backend response: missing 'answer' field")
                raise InvalidBackendResponseError("Missing 'answer' in response")
            
            logger.info(f"Backend request succeeded: {len(data.get('sources', []))} sources")
            return data
            
        except httpx.TimeoutException:
            logger.error("Backend request timed out")
            raise BackendTimeoutError()
        except httpx.ConnectError:
            logger.error(f"Cannot connect to backend: {self.backend_url}")
            raise BackendUnavailableError()
        except httpx.HTTPError as e:
            logger.error(f"Backend HTTP error: {e}")
            raise BackendUnavailableError()
        except ValueError as e:
            logger.error(f"Invalid JSON response from backend: {e}")
            raise InvalidBackendResponseError("Invalid response format")
        except Exception as e:
            logger.error(f"Unexpected backend error: {e}")
            raise BackendError(str(e), "Backend error")
