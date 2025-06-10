"""Session management for user-specific browser contexts"""

import asyncio
import uuid
from typing import Dict, Optional, Any, List
from app.models.chat import Message
from datetime import datetime
from playwright.async_api import BrowserContext
from app.core.scrapers.playwright_manager import playwright_manager
import logging

logger = logging.getLogger(__name__)


class UserSession:
    """Represents a user's browser session"""

    def __init__(self, session_id: str, context: BrowserContext):
        self.session_id = session_id
        self.context = context
        self.created_at = datetime.now()
        self.last_accessed = datetime.now()
        self.user_data: Dict[str, Any] = {}
        self.is_authenticated = False
        self.pending_action: Optional[Dict[str, Any]] = None
        self.chat_history: List[Message] = []

    def touch(self):
        """Update last accessed time"""
        self.last_accessed = datetime.now()

    @property
    def age_minutes(self) -> float:
        """Get session age in minutes"""
        return (datetime.now() - self.created_at).total_seconds() / 60

    @property
    def idle_minutes(self) -> float:
        """Get idle time in minutes"""
        return (datetime.now() - self.last_accessed).total_seconds() / 60


class SessionManager:
    """Manages browser sessions for users"""

    _instance: Optional["SessionManager"] = None

    def __new__(cls):
        """Implements the singleton pattern for the SessionManager."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        """Initializes the session manager's state."""
        if not hasattr(self, "_initialized"):
            self._initialized = True
            self._sessions: Dict[str, UserSession] = {}
            self._lock = asyncio.Lock()
            self._cleanup_task: Optional[asyncio.Task] = None
            self.session_timeout_minutes = 30
            self.idle_timeout_minutes = 15

    async def start(self):
        """Start session manager and cleanup task"""
        if not self._cleanup_task:
            self._cleanup_task = asyncio.create_task(self._cleanup_loop())
            logger.info("Session manager started")

    async def stop(self):
        """Stop session manager and close all sessions"""
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass

        # Close all sessions
        async with self._lock:
            for session in self._sessions.values():
                try:
                    await session.context.close()
                except Exception as e:
                    logger.error(f"Error closing session {session.session_id}: {e}")
            self._sessions.clear()

        logger.info("Session manager stopped")

    async def get_or_create_session(
        self, session_id: Optional[str] = None
    ) -> UserSession:
        """Get existing session or create new one"""
        async with self._lock:
            # Generate session ID if not provided
            if not session_id:
                session_id = str(uuid.uuid4())

            # Return existing session if found
            if session_id in self._sessions:
                session = self._sessions[session_id]
                session.touch()
                logger.info(f"Reusing session {session_id}")
                return session

            # Create new session
            logger.info(f"Creating new session {session_id}")

            # Ensure playwright is running
            if not playwright_manager.is_running:
                await playwright_manager.start()

            # Create new browser context
            context = await playwright_manager._browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                viewport={"width": 1920, "height": 1080},
                locale="en-US",
                # This will store cookies, localStorage, etc.
                storage_state=None,
            )

            session = UserSession(session_id, context)
            self._sessions[session_id] = session

            return session

    async def get_session(self, session_id: str) -> Optional[UserSession]:
        """Get existing session by ID"""
        async with self._lock:
            session = self._sessions.get(session_id)
            if session:
                session.touch()
            return session

    async def destroy_session(self, session_id: str):
        """Destroy a specific session"""
        async with self._lock:
            if session_id in self._sessions:
                session = self._sessions[session_id]
                try:
                    await session.context.close()
                except Exception as e:
                    logger.error(f"Error closing session context: {e}")

                del self._sessions[session_id]
                logger.info(f"Destroyed session {session_id}")

    async def save_session_state(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Save session state (cookies, localStorage, etc.)"""
        session = await self.get_session(session_id)
        if session:
            try:
                state = await session.context.storage_state()
                return state
            except Exception as e:
                logger.error(f"Error saving session state: {e}")
        return None

    async def restore_session_state(
        self, session_id: str, state: Dict[str, Any]
    ) -> bool:
        """Restore session state from saved data"""
        try:
            async with self._lock:
                # Close existing session if any
                if session_id in self._sessions:
                    await self._sessions[session_id].context.close()

                # Create new context with saved state
                context = await playwright_manager._browser.new_context(
                    storage_state=state,
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                    viewport={"width": 1920, "height": 1080},
                    locale="en-US",
                )

                session = UserSession(session_id, context)
                # Check if authenticated based on saved state
                session.is_authenticated = self._check_auth_in_state(state)
                self._sessions[session_id] = session

                logger.info(f"Restored session {session_id}")
                return True

        except Exception as e:
            logger.error(f"Error restoring session state: {e}")
            return False

    def _check_auth_in_state(self, state: Dict[str, Any]) -> bool:
        """Check if session state indicates authenticated user"""
        # Look for weather.com auth cookies
        cookies = state.get("cookies", [])
        for cookie in cookies:
            if cookie.get("domain", "").endswith("weather.com"):
                # Look for typical auth cookie names
                if cookie.get("name", "").lower() in [
                    "auth",
                    "session",
                    "token",
                    "user",
                ]:
                    return True
        return False

    async def _cleanup_loop(self):
        """Background task to clean up expired sessions"""
        while True:
            try:
                await asyncio.sleep(60)  # Check every minute
                await self._cleanup_expired_sessions()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in cleanup loop: {e}")

    async def _cleanup_expired_sessions(self):
        """Remove expired or idle sessions"""
        async with self._lock:
            expired_sessions = []

            for session_id, session in self._sessions.items():
                if (
                    session.age_minutes > self.session_timeout_minutes
                    or session.idle_minutes > self.idle_timeout_minutes
                ):
                    expired_sessions.append(session_id)

            for session_id in expired_sessions:
                logger.info(f"Cleaning up expired session {session_id}")
                try:
                    await self._sessions[session_id].context.close()
                except Exception as e:
                    logger.error(f"Error closing expired session: {e}")
                del self._sessions[session_id]

    @property
    def active_sessions(self) -> int:
        """Get count of active sessions"""
        return len(self._sessions)

    def get_session_info(self) -> Dict[str, Any]:
        """Get information about all sessions"""
        return {
            "active_sessions": self.active_sessions,
            "sessions": [
                {
                    "session_id": session.session_id,
                    "age_minutes": round(session.age_minutes, 2),
                    "idle_minutes": round(session.idle_minutes, 2),
                    "is_authenticated": session.is_authenticated,
                    "created_at": session.created_at.isoformat(),
                }
                for session in self._sessions.values()
            ],
        }


# Global instance
session_manager = SessionManager()
