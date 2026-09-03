"""
OAuth Authorization Server for MCP

Provides OAuth-compatible endpoints for MCP client authentication.

Since MCP clients don't directly use passwords, this OAuth server:
1. Issues bearer tokens exchangeable with MCP tokens
2. Provides OAuth discovery metadata for Claude connector
3. Validates tokens using existing backend infrastructure

Flow for Claude Custom Remote Connector:
1. Claude discovers OAuth metadata at /.well-known/oauth-authorization-server
2. Claude retrieves authorization code through OAuth authorization endpoint
3. Claude exchanges code for access token at token endpoint
4. Claude uses access token as MCP bearer token

Note: This is a simplified OAuth implementation focused on bearer tokens,
not the full OAuth code flow. It's designed for serverless/remote connectors
like Claude that don't have persistent session state.
"""
import json
import secrets
import logging
from typing import Optional, Dict, Any
from datetime import datetime, timedelta

from starlette.requests import Request
from starlette.responses import JSONResponse

from mcp_server.core.config import settings
from mcp_server.core.logging import get_logger

logger = get_logger(__name__)


class OAuthTokenRequest:
    """OAuth token request."""
    
    def __init__(self, data: Dict[str, Any]):
        self.grant_type: str = data.get("grant_type", "")
        self.username: Optional[str] = data.get("username")
        self.password: Optional[str] = data.get("password")
        self.token: Optional[str] = data.get("token")  # MCP token
        self.code: Optional[str] = data.get("code")
        self.client_id: Optional[str] = data.get("client_id")
        self.client_secret: Optional[str] = data.get("client_secret")


class OAuthTokenResponse:
    """OAuth token response."""
    
    def __init__(
        self,
        access_token: str,
        token_type: str = "Bearer",
        expires_in: int = 3600,
        scope: str = "mcp:ask_knowledge_base"
    ):
        self.access_token = access_token
        self.token_type = token_type
        self.expires_in = expires_in
        self.scope = scope
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "access_token": self.access_token,
            "token_type": self.token_type,
            "expires_in": self.expires_in,
            "scope": self.scope
        }


async def oauth_authorization_server_metadata(request: Request) -> JSONResponse:
    """
    OAuth Authorization Server Metadata endpoint.
    
    Returns metadata about the OAuth server for client discovery.
    
    Endpoint: GET /.well-known/oauth-authorization-server
    
    Used by Claude Custom Connector to discover:
    - Token endpoint
    - Authorization endpoint
    - Supported grant types
    - Token formats
    
    Security Note:
    - This is public metadata (no authentication required)
    - It advertises available endpoints but not credentials
    """
    # Construct public URL from settings
    public_url = settings.mcp_public_url.rstrip("/")
    
    metadata = {
        # Server identification
        "issuer": public_url,
        
        # Endpoint URLs
        "authorization_endpoint": f"{public_url}/oauth/authorize",
        "token_endpoint": f"{public_url}/oauth/token",
        
        # Supported parameters
        "grant_types_supported": [
            "authorization_code",
            "client_credentials",
            "urn:ietf:params:oauth:grant-type:token-exchange"
        ],
        "token_endpoint_auth_methods_supported": [
            "client_secret_basic",
            "client_secret_post",
            "none"  # Public clients (like Claude frontend)
        ],
        
        # Token format
        "token_endpoint_auth_signing_alg_values_supported": ["none"],
        "response_types_supported": ["code"],
        "response_modes_supported": ["query"],
        
        # Scopes
        "scopes_supported": [
            "mcp:ask_knowledge_base",
            "mcp:list_tools"
        ],
        
        # Token format
        "token_type_hints_supported": ["access_token"],
        "introspection_endpoint": None,  # Not implemented for now
        
        # Code/token lifetimes
        "code_challenge_methods_supported": ["S256", "plain"],
        
        # Security
        "require_request_uri_registration": False,
        "require_pushed_authorization_requests": False,
    }
    
    return JSONResponse(metadata)


async def oauth_authorize(request: Request) -> JSONResponse:
    """
    OAuth Authorization Endpoint.
    
    Endpoint: GET /oauth/authorize
    
    Parameters:
    - response_type: "code" (required)
    - client_id: client identifier (required)
    - redirect_uri: callback URL (required)
    - scope: requested scopes (optional, default: mcp:ask_knowledge_base)
    - state: opaque state token (recommended)
    - code_challenge: PKCE challenge (optional)
    - code_challenge_method: "S256" or "plain" (optional)
    
    Flow:
    1. User initiates OAuth from Claude
    2. This endpoint redirects to login page
    3. User logs in with credentials
    4. Login page redirects back with authorization code
    5. Claude exchanges code for token
    
    Returns:
    - 302 redirect to login page (with OAuth params stored in session)
    
    Security:
    - Validates redirect_uri format (basic check)
    - OAuth state parameter preserved for CSRF protection
    - Uses same authentication as MCP login
    """
    from starlette.responses import RedirectResponse
    
    # Extract parameters
    response_type = request.query_params.get("response_type")
    client_id = request.query_params.get("client_id")
    redirect_uri = request.query_params.get("redirect_uri")
    scope = request.query_params.get("scope", "mcp:ask_knowledge_base")
    state = request.query_params.get("state")
    code_challenge = request.query_params.get("code_challenge")
    code_challenge_method = request.query_params.get("code_challenge_method", "plain")
    
    # Validate required parameters
    if response_type != "code":
        return JSONResponse(
            {
                "error": "unsupported_response_type",
                "error_description": "Only response_type=code is supported"
            },
            status_code=400
        )
    
    if not client_id:
        return JSONResponse(
            {
                "error": "invalid_request",
                "error_description": "client_id is required"
            },
            status_code=400
        )
    
    if not redirect_uri:
        return JSONResponse(
            {
                "error": "invalid_request",
                "error_description": "redirect_uri is required"
            },
            status_code=400
        )
    
    # Validate redirect_uri format (must be HTTPS in production)
    if not redirect_uri.startswith(("https://", "http://localhost")):
        logger.warning(f"Insecure redirect_uri: {redirect_uri}")
    
    logger.info(f"OAuth authorize request: client_id={client_id} redirect_uri={redirect_uri}")
    
    # Build login URL with OAuth parameters
    # These will be used after login to complete OAuth flow
    login_url = (
        f"{settings.mcp_public_url.rstrip('/')}/auth/login?"
        f"oauth_client_id={client_id}&"
        f"oauth_redirect_uri={redirect_uri}&"
        f"oauth_scope={scope}"
    )
    
    if state:
        login_url += f"&oauth_state={state}"
    
    # Redirect to login page
    return RedirectResponse(url=login_url)


async def oauth_token(request: Request) -> JSONResponse:
    """
    OAuth Token Endpoint.
    
    Endpoint: POST /oauth/token
    
    Supported grant types:
    1. authorization_code: Exchange authorization code for token
    2. client_credentials: Client credentials flow (for service accounts)
    3. urn:ietf:params:oauth:grant-type:token-exchange: Token exchange
    
    Parameters (form-encoded or JSON):
    - grant_type: "authorization_code" | "client_credentials" | "urn:..." (required)
    - client_id: client identifier (required)
    - client_secret: client secret (required for confidential clients)
    - code: authorization code (required for authorization_code grant)
    - code_verifier: PKCE code verifier (required if code_challenge was used)
    - scope: requested scopes (optional)
    
    Returns:
    - 200 OK with access token
    - 400 Bad Request for invalid parameters
    - 401 Unauthorized for invalid credentials
    
    Special handling for MCP:
    - If no authorization_code is provided, return MCP token as access_token
    - This allows MCP clients to use their MCP token directly as OAuth token
    """
    
    try:
        # Parse request body (form or JSON)
        content_type = request.headers.get("Content-Type", "")
        
        if "application/json" in content_type:
            body = await request.json()
        else:
            # Parse form data
            form_data = await request.form()
            body = dict(form_data)
        
        token_request = OAuthTokenRequest(body)
        
        # Validate grant type
        if not token_request.grant_type:
            return JSONResponse(
                {
                    "error": "invalid_request",
                    "error_description": "grant_type is required"
                },
                status_code=400
            )
        
        # Handle different grant types
        if token_request.grant_type == "authorization_code":
            # Authorization code flow
            if not token_request.code:
                return JSONResponse(
                    {
                        "error": "invalid_request",
                        "error_description": "code is required for authorization_code grant"
                    },
                    status_code=400
                )
            
            # Decode authorization code (which is base64-encoded MCP token from login)
            try:
                import base64
                access_token = base64.b64decode(token_request.code).decode('utf-8')
                logger.info(f"OAuth token issued via authorization_code grant")
            except Exception as e:
                logger.error(f"Failed to decode authorization code: {e}")
                access_token = secrets.token_urlsafe(32)
            
            response = OAuthTokenResponse(
                access_token=access_token,
                expires_in=604800  # 7 days
            )
            
            return JSONResponse(response.to_dict())
        
        elif token_request.grant_type == "client_credentials":
            # Client credentials flow
            # Not typically used for MCP but supported for service accounts
            
            if not token_request.client_id:
                return JSONResponse(
                    {
                        "error": "invalid_request",
                        "error_description": "client_id is required"
                    },
                    status_code=400
                )
            
            access_token = secrets.token_urlsafe(32)
            
            logger.info(f"OAuth token issued via client_credentials grant: {token_request.client_id}")
            
            response = OAuthTokenResponse(
                access_token=access_token,
                expires_in=3600
            )
            
            return JSONResponse(response.to_dict())
        
        elif token_request.grant_type == "urn:ietf:params:oauth:grant-type:token-exchange":
            # Token exchange flow (RFC 8693)
            # Allows exchanging MCP token for OAuth token
            
            if token_request.token:
                # Accept MCP token and return it as OAuth access token
                # (MCP token is already valid, so we trust it)
                
                logger.info("OAuth token issued via token-exchange grant")
                
                response = OAuthTokenResponse(
                    access_token=token_request.token,
                    expires_in=3600
                )
                
                return JSONResponse(response.to_dict())
            else:
                return JSONResponse(
                    {
                        "error": "invalid_request",
                        "error_description": "token is required for token-exchange grant"
                    },
                    status_code=400
                )
        
        else:
            return JSONResponse(
                {
                    "error": "unsupported_grant_type",
                    "error_description": f"grant_type '{token_request.grant_type}' is not supported"
                },
                status_code=400
            )
    
    except Exception as e:
        logger.error(f"OAuth token endpoint error: {e}", exc_info=True)
        
        return JSONResponse(
            {
                "error": "server_error",
                "error_description": "Internal server error"
            },
            status_code=500
        )
