"""FastAPI server for secure Formlabs credential input.

Runs on localhost only to receive credentials from the web form.
"""

from __future__ import annotations

import asyncio
import os
import secrets
import threading
import time
from dataclasses import dataclass, field
from typing import Callable

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
import uvicorn

from mcp_formlabs.keychain import store_token
from mcp_formlabs.preform_client import PreFormClient, PreFormError


@dataclass
class PendingLogin:
    """Represents a pending login request."""

    telegram_user_id: int
    token: str
    created_at: float = field(default_factory=time.time)
    expires_in: int = 600  # 10 minutes

    def is_expired(self) -> bool:
        return time.time() - self.created_at > self.expires_in


class LoginRequest(BaseModel):
    """Request body for login endpoint."""

    token: str
    username: str
    password: str


# Store pending login requests (token -> PendingLogin)
_pending_logins: dict[str, PendingLogin] = {}
_login_callbacks: dict[str, Callable[[bool, str], None]] = {}

app = FastAPI(title="Formlabs Auth Server")


def create_login_token(telegram_user_id: int) -> str:
    """Create a secure login token for a Telegram user.

    Args:
        telegram_user_id: The Telegram user's unique ID

    Returns:
        A secure random token string
    """
    token = secrets.token_urlsafe(32)
    _pending_logins[token] = PendingLogin(
        telegram_user_id=telegram_user_id,
        token=token,
    )
    return token


def set_login_callback(
    token: str, callback: Callable[[bool, str], None]
) -> None:
    """Set a callback to be called when login completes.

    Args:
        token: The login token
        callback: Function(success: bool, message: str)
    """
    _login_callbacks[token] = callback


def cleanup_expired_logins() -> None:
    """Remove expired pending logins."""
    expired = [t for t, p in _pending_logins.items() if p.is_expired()]
    for token in expired:
        _pending_logins.pop(token, None)
        _login_callbacks.pop(token, None)


LOGIN_FORM_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Formlabs Login</title>
    <style>
        * {
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }
        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 20px;
        }
        .container {
            background: white;
            border-radius: 16px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            padding: 40px;
            width: 100%;
            max-width: 400px;
        }
        .logo {
            text-align: center;
            margin-bottom: 30px;
        }
        .logo h1 {
            color: #fa6400;
            font-size: 28px;
            font-weight: 700;
        }
        .logo p {
            color: #666;
            margin-top: 8px;
        }
        .form-group {
            margin-bottom: 20px;
        }
        label {
            display: block;
            color: #333;
            font-weight: 500;
            margin-bottom: 8px;
        }
        input[type="text"],
        input[type="password"] {
            width: 100%;
            padding: 14px 16px;
            border: 2px solid #e0e0e0;
            border-radius: 8px;
            font-size: 16px;
            transition: border-color 0.2s;
        }
        input:focus {
            outline: none;
            border-color: #fa6400;
        }
        button {
            width: 100%;
            padding: 14px;
            background: #fa6400;
            color: white;
            border: none;
            border-radius: 8px;
            font-size: 16px;
            font-weight: 600;
            cursor: pointer;
            transition: background 0.2s;
        }
        button:hover {
            background: #e05a00;
        }
        button:disabled {
            background: #ccc;
            cursor: not-allowed;
        }
        .message {
            margin-top: 20px;
            padding: 12px;
            border-radius: 8px;
            text-align: center;
            display: none;
        }
        .message.success {
            background: #d4edda;
            color: #155724;
            display: block;
        }
        .message.error {
            background: #f8d7da;
            color: #721c24;
            display: block;
        }
        .security-note {
            margin-top: 20px;
            padding: 12px;
            background: #f0f4f8;
            border-radius: 8px;
            font-size: 13px;
            color: #666;
            text-align: center;
        }
        .security-note::before {
            content: "🔒 ";
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="logo">
            <h1>Formlabs</h1>
            <p>Sign in to connect your Telegram bot</p>
        </div>
        <form id="loginForm">
            <input type="hidden" id="token" value="{{TOKEN}}">
            <div class="form-group">
                <label for="username">Formlabs Email</label>
                <input type="text" id="username" name="username" required
                       placeholder="your@email.com" autocomplete="email">
            </div>
            <div class="form-group">
                <label for="password">Password</label>
                <input type="password" id="password" name="password" required
                       placeholder="Your password" autocomplete="current-password">
            </div>
            <button type="submit" id="submitBtn">Sign In</button>
        </form>
        <div id="message" class="message"></div>
        <div class="security-note">
            Your credentials are sent securely to your local machine only.
            They are never stored in plaintext.
        </div>
    </div>
    <script>
        const form = document.getElementById('loginForm');
        const message = document.getElementById('message');
        const submitBtn = document.getElementById('submitBtn');

        form.addEventListener('submit', async (e) => {
            e.preventDefault();
            submitBtn.disabled = true;
            submitBtn.textContent = 'Signing in...';
            message.className = 'message';

            try {
                const response = await fetch('/api/login', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({
                        token: document.getElementById('token').value,
                        username: document.getElementById('username').value,
                        password: document.getElementById('password').value
                    })
                });

                const data = await response.json();

                if (response.ok) {
                    message.textContent = '✓ Login successful! You can close this window.';
                    message.className = 'message success';
                    form.style.display = 'none';
                } else {
                    message.textContent = data.detail || 'Login failed';
                    message.className = 'message error';
                    submitBtn.disabled = false;
                    submitBtn.textContent = 'Sign In';
                }
            } catch (err) {
                message.textContent = 'Connection error. Please try again.';
                message.className = 'message error';
                submitBtn.disabled = false;
                submitBtn.textContent = 'Sign In';
            }
        });
    </script>
</body>
</html>
"""


@app.get("/login/{token}", response_class=HTMLResponse)
async def login_form(token: str):
    """Serve the login form for a given token."""
    cleanup_expired_logins()

    if token not in _pending_logins:
        return HTMLResponse(
            content="<h1>Invalid or expired login link</h1>"
            "<p>Please request a new login link from the Telegram bot.</p>",
            status_code=404,
        )

    pending = _pending_logins[token]
    if pending.is_expired():
        _pending_logins.pop(token, None)
        return HTMLResponse(
            content="<h1>Login link expired</h1>"
            "<p>Please request a new login link from the Telegram bot.</p>",
            status_code=410,
        )

    html = LOGIN_FORM_HTML.replace("{{TOKEN}}", token)
    return HTMLResponse(content=html)


@app.post("/api/login")
async def process_login(request: LoginRequest):
    """Process login credentials and store token in Keychain."""
    cleanup_expired_logins()

    if request.token not in _pending_logins:
        raise HTTPException(status_code=404, detail="Invalid or expired login token")

    pending = _pending_logins[request.token]
    if pending.is_expired():
        _pending_logins.pop(request.token, None)
        raise HTTPException(status_code=410, detail="Login token expired")

    # Authenticate with Formlabs
    client = PreFormClient()
    try:
        result = client.login(request.username, request.password)
    except PreFormError as e:
        callback = _login_callbacks.get(request.token)
        if callback:
            callback(False, str(e))
        raise HTTPException(status_code=401, detail=f"Formlabs login failed: {e}")

    # Extract token from result
    formlabs_token = result.get("token") or result.get("access_token") or ""
    expires_at = result.get("expires_at")

    # Store in Keychain
    try:
        store_token(
            telegram_user_id=pending.telegram_user_id,
            formlabs_token=formlabs_token,
            username=request.username,
            expires_at=expires_at,
        )
    except Exception as e:
        callback = _login_callbacks.get(request.token)
        if callback:
            callback(False, f"Failed to store credentials: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to store credentials: {e}"
        )

    # Clean up and notify
    _pending_logins.pop(request.token, None)
    callback = _login_callbacks.pop(request.token, None)
    if callback:
        callback(True, f"Successfully logged in as {request.username}")

    return {"status": "success", "username": request.username}


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "ok"}


class CreateTokenRequest(BaseModel):
    """Request to create a login token."""
    telegram_user_id: int


@app.post("/api/create-token")
async def api_create_token(request: CreateTokenRequest):
    """Create a login token for a Telegram user."""
    token = create_login_token(request.telegram_user_id)
    public_url = os.environ.get("PUBLIC_AUTH_URL", f"http://127.0.0.1:8765")
    login_url = f"{public_url.rstrip('/')}/login/{token}"
    
    return {
        "token": token,
        "login_url": login_url,
        "expires_in": 600
    }


class AuthServer:
    """Manages the auth server lifecycle."""

    def __init__(self, host: str = "127.0.0.1", port: int = 8765):
        self.host = host
        self.port = port
        self._server: uvicorn.Server | None = None
        self._thread: threading.Thread | None = None

    def get_login_url(self, telegram_user_id: int) -> str:
        """Create a login URL for a Telegram user.

        Args:
            telegram_user_id: The Telegram user's unique ID

        Returns:
            The full URL for the login form
        """
        token = create_login_token(telegram_user_id)
        # Check for public URL override (e.g., from Cloudflare Tunnel)
        public_url = os.environ.get("PUBLIC_AUTH_URL")
        if public_url:
            return f"{public_url.rstrip('/')}/login/{token}"
        return f"http://{self.host}:{self.port}/login/{token}"

    def start(self) -> None:
        """Start the auth server in a background thread."""
        if self._thread and self._thread.is_alive():
            return

        config = uvicorn.Config(
            app,
            host=self.host,
            port=self.port,
            log_level="warning",
        )
        self._server = uvicorn.Server(config)

        self._thread = threading.Thread(
            target=self._server.run,
            daemon=True,
        )
        self._thread.start()

    def stop(self) -> None:
        """Stop the auth server."""
        if self._server:
            self._server.should_exit = True
        if self._thread:
            self._thread.join(timeout=5)

    @property
    def is_running(self) -> bool:
        """Check if the server is running."""
        return self._thread is not None and self._thread.is_alive()


# Singleton server instance
_auth_server: AuthServer | None = None


def get_auth_server(host: str = "127.0.0.1", port: int = 8765) -> AuthServer:
    """Get or create the auth server singleton."""
    global _auth_server
    if _auth_server is None:
        _auth_server = AuthServer(host=host, port=port)
    return _auth_server


def main():
    """Run the auth server standalone."""
    import argparse

    parser = argparse.ArgumentParser(description="Formlabs Auth Server")
    parser.add_argument("--host", default="127.0.0.1", help="Host to bind to")
    parser.add_argument("--port", type=int, default=8765, help="Port to listen on")
    args = parser.parse_args()

    print(f"Starting auth server on http://{args.host}:{args.port}")
    uvicorn.run(app, host=args.host, port=args.port)


if __name__ == "__main__":
    main()
