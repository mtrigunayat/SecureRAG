"""
MCP Server User Authentication & Token Management

Provides login endpoint for users to authenticate and receive MCP tokens.
This solves the Claude UI limitation where Bearer tokens can't be entered.

Flow:
1. User visits /auth/login page
2. Enters username/password
3. Backend validates credentials
4. MCP token is generated and returned
5. User copies token and pastes into Claude MCP connector settings
"""

import logging
from typing import Optional
from pydantic import BaseModel
import httpx

from mcp_server.core.config import settings
from mcp_server.core.errors import AuthenticationError, BackendError

logger = logging.getLogger(__name__)


class LoginRequest(BaseModel):
    """User login credentials"""
    email: str
    password: str


class LoginResponse(BaseModel):
    """Login response with MCP token"""
    success: bool
    message: str
    mcp_token: Optional[str] = None
    user_id: Optional[int] = None
    username: Optional[str] = None
    department: Optional[str] = None


async def authenticate_user(email: str, password: str) -> LoginResponse:
    """
    Authenticate user against backend and return MCP token.
    
    This calls the backend /api/auth/login endpoint to validate credentials,
    then generates an MCP token for the authenticated user.
    
    Args:
        email: User's email
        password: User's password
        
    Returns:
        LoginResponse with MCP token if successful
    """
    try:
        # Call backend login endpoint with email and password
        async with httpx.AsyncClient(timeout=settings.backend_timeout) as client:
            login_response = await client.post(
                f"{settings.backend_url}/api/auth/login",
                json={
                    "email": email,
                    "password": password
                }
            )
            
            if login_response.status_code != 200:
                return LoginResponse(
                    success=False,
                    message="Invalid username or password"
                )
            
            # Get the JWT token from login response
            login_data = login_response.json()
            access_token = login_data.get("access_token")
            
            # Call /api/auth/me to get user info using the JWT
            me_response = await client.get(
                f"{settings.backend_url}/api/auth/me",
                headers={"Authorization": f"Bearer {access_token}"}
            )
            
            if me_response.status_code != 200:
                return LoginResponse(
                    success=False,
                    message="Failed to retrieve user information"
                )
            
            user_data = me_response.json()
            user_id = user_data.get("id")
            username_returned = user_data.get("username")
            department = user_data.get("department")
            
            # Now generate MCP token for this user
            token = await generate_mcp_token(user_id, username_returned)
            
            return LoginResponse(
                success=True,
                message="Login successful. Copy the token below and paste it in Claude MCP connector settings.",
                mcp_token=token,
                user_id=user_id,
                username=username_returned,
                department=department
            )
    
    except httpx.TimeoutException:
        logger.error("Backend timeout during login")
        return LoginResponse(
            success=False,
            message="Backend service unavailable. Try again later."
        )
    except httpx.RequestError as e:
        logger.error(f"Backend connection error: {e}")
        return LoginResponse(
            success=False,
            message="Cannot connect to authentication service. Check if backend is running."
        )
    except Exception as e:
        logger.error(f"Login error: {e}", exc_info=True)
        return LoginResponse(
            success=False,
            message="Authentication failed. Please try again."
        )


async def generate_mcp_token(user_id: int, username: str) -> str:
    """
    Generate an MCP token for an authenticated user.
    
    Calls backend to create a new MCP token in the database.
    
    Args:
        user_id: User ID from authentication
        username: Username
        
    Returns:
        MCP token string (format: mcp_<base64-encoded-bytes>)
    """
    try:
        async with httpx.AsyncClient(timeout=settings.backend_timeout) as client:
            response = await client.post(
                f"{settings.backend_url}/api/internal/mcp/create-token",
                json={
                    "user_id": user_id,
                    "description": f"Claude MCP: {username}"
                },
                headers={
                    # Use internal service auth if available
                    "X-Internal-Service": settings.internal_service_key or "mcp-server"
                }
            )
            
            if response.status_code == 201:
                data = response.json()
                return data.get("token")
            else:
                raise BackendError(f"Failed to generate token: {response.text}")
    
    except httpx.TimeoutException:
        raise BackendError("Backend timeout generating token")
    except httpx.RequestError as e:
        raise BackendError(f"Backend error: {e}")


def get_login_html() -> str:
    """
    Generate HTML for login form.
    
    This is served at /auth/login and allows users to authenticate
    and receive their MCP token.
    
    Can also be called during OAuth flow with parameters:
    - oauth_client_id: OAuth client ID
    - oauth_redirect_uri: OAuth redirect URI
    - oauth_state: OAuth state (for CSRF protection)
    
    After login, either:
    - Shows token for manual copy (direct login)
    - Redirects back with authorization code (OAuth login)
    """
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Secure RAG - MCP Authentication</title>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            * {
                margin: 0;
                padding: 0;
                box-sizing: border-box;
            }
            
            body {
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh;
                display: flex;
                align-items: center;
                justify-content: center;
                padding: 20px;
            }
            
            .container {
                background: white;
                border-radius: 12px;
                box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
                width: 100%;
                max-width: 400px;
                padding: 40px;
            }
            
            h1 {
                font-size: 24px;
                margin-bottom: 10px;
                color: #333;
            }
            
            .subtitle {
                color: #666;
                font-size: 14px;
                margin-bottom: 30px;
            }
            
            .form-group {
                margin-bottom: 20px;
            }
            
            label {
                display: block;
                font-size: 14px;
                font-weight: 500;
                margin-bottom: 8px;
                color: #333;
            }
            
            input[type="text"],
            input[type="password"] {
                width: 100%;
                padding: 12px;
                border: 1px solid #ddd;
                border-radius: 6px;
                font-size: 14px;
                transition: border-color 0.3s;
            }
            
            input[type="text"]:focus,
            input[type="password"]:focus {
                outline: none;
                border-color: #667eea;
                box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
            }
            
            button {
                width: 100%;
                padding: 12px;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                border: none;
                border-radius: 6px;
                font-size: 16px;
                font-weight: 600;
                cursor: pointer;
                transition: transform 0.2s, box-shadow 0.2s;
            }
            
            button:hover {
                transform: translateY(-2px);
                box-shadow: 0 10px 20px rgba(102, 126, 234, 0.3);
            }
            
            button:active {
                transform: translateY(0);
            }
            
            .message {
                margin-top: 20px;
                padding: 12px;
                border-radius: 6px;
                font-size: 14px;
                display: none;
            }
            
            .message.error {
                background: #fee;
                color: #c33;
                border: 1px solid #fcc;
            }
            
            .message.success {
                background: #efe;
                color: #3c3;
                border: 1px solid #cfc;
            }
            
            .token-box {
                background: #f5f5f5;
                border: 2px dashed #667eea;
                border-radius: 6px;
                padding: 15px;
                margin-top: 15px;
                display: none;
            }
            
            .token-box.show {
                display: block;
            }
            
            .token-label {
                font-size: 12px;
                color: #666;
                margin-bottom: 8px;
                font-weight: 600;
                text-transform: uppercase;
            }
            
            .token-value {
                font-family: 'Monaco', 'Courier New', monospace;
                font-size: 12px;
                word-break: break-all;
                background: white;
                padding: 10px;
                border-radius: 4px;
                border: 1px solid #ddd;
                margin-bottom: 10px;
                user-select: all;
            }
            
            .copy-btn {
                width: 100%;
                padding: 8px;
                background: #667eea;
                color: white;
                border: none;
                border-radius: 4px;
                font-size: 12px;
                font-weight: 600;
                cursor: pointer;
                transition: background 0.2s;
            }
            
            .copy-btn:hover {
                background: #764ba2;
            }
            
            .user-info {
                background: #f0f4ff;
                padding: 10px;
                border-radius: 4px;
                font-size: 13px;
                margin-bottom: 10px;
            }
            
            .instructions {
                background: #fff9e6;
                border-left: 4px solid #ffc107;
                padding: 15px;
                border-radius: 4px;
                font-size: 13px;
                line-height: 1.6;
                margin-top: 20px;
                display: none;
            }
            
            .instructions.show {
                display: block;
            }
            
            .loading {
                display: none;
                text-align: center;
                color: #667eea;
            }
            
            .spinner {
                border: 3px solid #f0f0f0;
                border-top: 3px solid #667eea;
                border-radius: 50%;
                width: 30px;
                height: 30px;
                animation: spin 1s linear infinite;
                margin: 0 auto 10px;
            }
            
            @keyframes spin {
                0% { transform: rotate(0deg); }
                100% { transform: rotate(360deg); }
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>Secure RAG</h1>
            <p class="subtitle">Claude MCP Authentication</p>
            
            <form id="loginForm">
                <div class="form-group">
                    <label for="username">Username</label>
                    <input type="text" id="username" name="username" required placeholder="your-username">
                </div>
                
                <div class="form-group">
                    <label for="password">Password</label>
                    <input type="password" id="password" name="password" required placeholder="your-password">
                </div>
                
                <button type="submit">Login</button>
            </form>
            
            <div class="loading" id="loading">
                <div class="spinner"></div>
                <p>Authenticating...</p>
            </div>
            
            <div class="message" id="message"></div>
            
            <div class="token-box" id="tokenBox">
                <div class="user-info" id="userInfo"></div>
                
                <div class="token-label">Your MCP Token:</div>
                <div class="token-value" id="tokenValue"></div>
                <button class="copy-btn" onclick="copyToken()">Copy Token</button>
                
                <div class="instructions show">
                    <strong>Next Steps:</strong><br>
                    1. Copy your MCP token (click "Copy Token" above)<br>
                    2. Open Claude or your AI client<br>
                    3. Go to Model Settings → Connected Applications<br>
                    4. Find "Secure RAG" MCP connection<br>
                    5. Click Edit → Paste token into "Authentication" field<br>
                    6. Save and refresh<br>
                    7. You should now see your department's knowledge base!
                </div>
            </div>
        </div>
        
        <script>
            // Parse URL parameters
            const urlParams = new URLSearchParams(window.location.search);
            const oauthClientId = urlParams.get('oauth_client_id');
            const oauthRedirectUri = urlParams.get('oauth_redirect_uri');
            const oauthState = urlParams.get('oauth_state');
            const isOAuthFlow = !!oauthClientId;
            
            // Update subtitle based on flow type
            if (isOAuthFlow) {
                document.querySelector('.subtitle').textContent = 'Sign in to authorize Claude access';
            }
            
            document.getElementById('loginForm').addEventListener('submit', async (e) => {
                e.preventDefault();
                
                const username = document.getElementById('username').value;
                const password = document.getElementById('password').value;
                
                document.getElementById('loginForm').style.display = 'none';
                document.getElementById('loading').style.display = 'block';
                document.getElementById('message').style.display = 'none';
                
                try {
                    const response = await fetch('/auth/login-api', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                        },
                        body: JSON.stringify({ username, password })
                    });
                    
                    const data = await response.json();
                    
                    document.getElementById('loading').style.display = 'none';
                    
                    if (data.success && data.mcp_token) {
                        if (isOAuthFlow) {
                            // OAuth flow: redirect back with authorization code
                            // In production, exchange token for authorization code
                            const authCode = btoa(data.mcp_token); // Encode token as code for now
                            const redirectParams = new URLSearchParams({
                                code: authCode
                            });
                            if (oauthState) {
                                redirectParams.append('state', oauthState);
                            }
                            
                            // Redirect back to Claude
                            const separator = oauthRedirectUri.includes('?') ? '&' : '?';
                            window.location.href = `${oauthRedirectUri}${separator}${redirectParams.toString()}`;
                        } else {
                            // Direct login flow: show token for manual copy
                            document.getElementById('userInfo').innerHTML = 
                                `<strong>${data.username}</strong> | Department: <strong>${data.department}</strong>`;
                            document.getElementById('tokenValue').textContent = data.mcp_token;
                            document.getElementById('tokenBox').classList.add('show');
                            
                            // Show success message
                            const msg = document.getElementById('message');
                            msg.className = 'message success';
                            msg.textContent = data.message;
                            msg.style.display = 'block';
                        }
                    } else {
                        // Show error
                        const msg = document.getElementById('message');
                        msg.className = 'message error';
                        msg.textContent = data.message || 'Login failed. Please try again.';
                        msg.style.display = 'block';
                        
                        document.getElementById('loginForm').style.display = 'block';
                    }
                } catch (error) {
                    document.getElementById('loading').style.display = 'none';
                    const msg = document.getElementById('message');
                    msg.className = 'message error';
                    msg.textContent = 'Error: ' + error.message;
                    msg.style.display = 'block';
                    document.getElementById('loginForm').style.display = 'block';
                }
            });
            
            function copyToken() {
                const token = document.getElementById('tokenValue').textContent;
                navigator.clipboard.writeText(token).then(() => {
                    const btn = event.target;
                    const original = btn.textContent;
                    btn.textContent = 'Copied!';
                    setTimeout(() => {
                        btn.textContent = original;
                    }, 2000);
                });
            }
        </script>
    </body>
    </html>
    """
