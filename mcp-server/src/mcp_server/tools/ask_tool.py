"""
MCP Tools - ask_knowledge_base

Implements the ask_knowledge_base tool that queries the knowledge base.
"""
from mcp_server.core.logging import get_logger
from mcp_server.core.errors import BackendError

logger = get_logger(__name__)


async def ask_knowledge_base_impl(
    question: str,
    auth_context,
    backend_client
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
        chat_response = await backend_client.ask_knowledge_base(
            question=question,
            backend_jwt=auth_context.backend_jwt
        )
        
        # Extract data from ChatResponse object
        answer = chat_response.answer
        sources = chat_response.sources
        
        # Format with sources
        formatted = f"{answer}\n"
        
        if sources:
            formatted += "\n**Sources:**\n"
            for idx, source in enumerate(sources, 1):
                formatted += (
                    f"{idx}. **{source.document_name}** "
                    f"[{source.sensitivity}]\n"
                )
        
        formatted += f"\n_Retrieved {len(sources)} document(s)_"
        
        logger.info(f"Tool completed: ask_knowledge_base | sources={len(sources)}")
        return formatted
        
    except BackendError as e:
        logger.error(f"Tool error: {e}")
        return f"Error: Backend error occurred"
    except Exception as e:
        logger.error(f"Unexpected tool error: {e}", exc_info=True)
        return "Error: An unexpected error occurred"
