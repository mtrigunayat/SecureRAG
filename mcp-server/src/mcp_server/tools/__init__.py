"""
MCP Tools

Implements MCP tools that the model can invoke.
"""
from mcp_server.auth import AuthenticatedContext
from mcp_server.client import BackendAPIClient
from mcp_server.core.logging import get_logger
from mcp_server.core.errors import BackendError

logger = get_logger(__name__)


async def ask_knowledge_base_impl(
    question: str,
    auth_context: AuthenticatedContext,
    backend_client: BackendAPIClient
) -> str:
    """
    Implementation of ask_knowledge_base tool.
    
    This tool allows the model to ask questions about the company's
    internal knowledge base (documents, policies, guidelines, etc.).
    
    The tool:
    1. Receives a question from the model
    2. Uses the authenticated context (user identity from MCP token)
    3. Calls the backend /api/chat endpoint
    4. Backend performs RAG retrieval with department-based ACL
    5. Backend generates answer using LLM
    6. Returns formatted response with sources
    
    Args:
        question: User's question
        auth_context: Authenticated user context (from MCP token validation)
        backend_client: Client for backend communication
        
    Returns:
        Formatted response string with answer and sources
        
    Security:
        - Uses authenticated user identity (from MCP token)
        - User's department enforced by backend (ACL)
        - Only authorized sources returned
        - No credentials passed to model
        - Backend remains authoritative
    """
    logger.info(
        f"Tool invoked: ask_knowledge_base | "
        f"user_id={auth_context.user_id} | "
        f"department={auth_context.department_name} | "
        f"question_len={len(question)}"
    )
    
    try:
        # Call backend with authenticated JWT
        response = await backend_client.ask_knowledge_base(
            question=question,
            backend_jwt=auth_context.backend_jwt
        )
        
        # Build formatted response
        answer = response.get("answer", "")
        sources = response.get("sources", [])
        retrieved_count = response.get("retrieved_count", 0)
        user_dept = response.get("user_department_name", "")
        
        # Format with sources
        formatted = f"{answer}\n"
        
        if sources:
            formatted += "\n**Sources:**\n"
            for idx, source in enumerate(sources, 1):
                doc_name = source.get("document_name", "Unknown")
                dept = source.get("department_name", "Unknown")
                score = source.get("score", 0)
                page_start = source.get("page_start", "?")
                page_end = source.get("page_end", "?")
                
                formatted += (
                    f"{idx}. **{doc_name}** ({dept}) "
                    f"[p.{page_start}-{page_end}, score: {score:.2f}]\n"
                )
        
        formatted += f"\n_Retrieved {retrieved_count} document(s) from {user_dept}_"
        
        logger.info(f"Tool completed: ask_knowledge_base | sources={len(sources)}")
        return formatted
        
    except BackendError as e:
        logger.error(f"Tool error: {e.message}")
        return f"Error: {e.safe_message}"
    except Exception as e:
        logger.error(f"Unexpected tool error: {e}")
        return "Error: An unexpected error occurred"
