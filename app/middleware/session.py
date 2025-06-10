"""FastAPI middleware for managing user session IDs via cookies."""

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from typing import Optional
import uuid


class SessionMiddleware(BaseHTTPMiddleware):
    """Middleware to handle session IDs"""

    def __init__(self, app, session_cookie_name: str = "weather_session_id"):
        """Initializes the middleware."""
        super().__init__(app)
        self.session_cookie_name = session_cookie_name

    async def dispatch(self, request: Request, call_next):
        """Processes the request, adds a session ID, and sets the session cookie."""
        session_id = self._get_session_id(request)

        # Generate new session ID if not present
        if not session_id:
            session_id = str(uuid.uuid4())
            new_session = True
        else:
            new_session = False

        # Attach session ID to request state
        request.state.session_id = session_id

        # Process request
        response = await call_next(request)

        # Set session cookie if new session
        if new_session and response.status_code < 400:
            response.set_cookie(
                key=self.session_cookie_name,
                value=session_id,
                max_age=3600 * 24 * 7,  # 7 days
                httponly=True,
                samesite="lax",
            )

        return response

    def _get_session_id(self, request: Request) -> Optional[str]:
        """Extract session ID from request"""
        # Try cookie first
        session_id = request.cookies.get(self.session_cookie_name)
        if session_id:
            return session_id

        # Try header as fallback (for API clients)
        return request.headers.get("X-Session-ID")
