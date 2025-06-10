"""API endpoints for user authentication and credential management."""

from fastapi import APIRouter, Request, HTTPException
from typing import Dict, Any
from app.core.session_manager import session_manager
from app.core.scrapers.account_manager import AccountManager
from app.core.auth.credential_manager import credential_manager
from app.models.auth import LoginResponse, LoginRequest

router = APIRouter(prefix="/auth", tags=["authentication"])
account_manager = AccountManager()


@router.post("/login", response_model=LoginResponse)
async def login(request: Request, login_data: LoginRequest):
    """Login to weather.com"""
    session_id = getattr(request.state, "session_id", None)

    if not session_id:
        raise HTTPException(status_code=400, detail="No session ID found")

    # Get or create session
    session = await session_manager.get_or_create_session(session_id)

    # Save credentials if requested
    if login_data.save_credentials:
        credential_manager.save_credentials(
            user_id=session_id, email=login_data.email, password=login_data.password
        )

    # Perform login
    result = await account_manager.login(
        session=session, email=login_data.email, password=login_data.password
    )

    return LoginResponse(
        success=result["success"],
        message=result["message"],
        session_id=result["session_id"],
        email=result.get("email"),
    )


@router.get("/status")
async def auth_status(request: Request) -> Dict[str, Any]:
    """Check authentication status from the session state."""
    session_id = getattr(request.state, "session_id", None)

    if not session_id:
        return {"authenticated": False, "message": "No session"}

    session = await session_manager.get_session(session_id)
    if not session:
        return {"authenticated": False, "message": "Session not found"}

    return {
        "authenticated": session.is_authenticated,
        "session_id": session_id,
        "email": session.user_data.get("email"),
        "has_saved_credentials": credential_manager.has_credentials(session_id),
    }


@router.post("/logout")
async def logout(request: Request) -> Dict[str, Any]:
    """
    Logout by destroying the current server-side session and its browser context.
    This provides a clean slate for the next interaction.
    """
    session_id = getattr(request.state, "session_id", None)

    if not session_id:
        raise HTTPException(status_code=400, detail="No session ID found")

    session = await session_manager.get_session(session_id)
    if not session:
        return {
            "success": True,
            "message": "No active session to clear.",
            "session_id": session_id,
        }

    # Destroy the session in the session manager. This closes the
    # browser context and removes all associated cookies and storage.
    await session_manager.destroy_session(session_id)

    return {
        "success": True,
        "message": "Session has been cleared. You are now logged out.",
        "session_id": session_id,
    }


@router.delete("/credentials")
async def delete_saved_credentials(request: Request) -> Dict[str, Any]:
    """Delete saved credentials"""
    session_id = getattr(request.state, "session_id", None)

    if not session_id:
        raise HTTPException(status_code=400, detail="No session ID found")

    deleted = credential_manager.delete_credentials(session_id)

    return {
        "success": deleted,
        "message": "Credentials deleted" if deleted else "No credentials found",
        "session_id": session_id,
    }
