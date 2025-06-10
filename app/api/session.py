"""Session management endpoints"""

from fastapi import APIRouter, Request
from app.core.session_manager import session_manager
from typing import Dict, Any

router = APIRouter(prefix="/session", tags=["session"])


@router.get("/info")
async def get_session_info(request: Request) -> Dict[str, Any]:
    """Get current session information"""
    session_id = getattr(request.state, "session_id", None)

    if not session_id:
        return {"error": "No session ID found", "session_id": None}

    session = await session_manager.get_session(session_id)

    if session:
        return {
            "session_id": session_id,
            "created_at": session.created_at.isoformat(),
            "age_minutes": round(session.age_minutes, 2),
            "idle_minutes": round(session.idle_minutes, 2),
            "is_authenticated": session.is_authenticated,
            "user_data": session.user_data,
        }
    else:
        return {"session_id": session_id, "error": "Session not found in manager"}


@router.post("/test")
async def test_session(request: Request) -> Dict[str, Any]:
    """Test session creation and persistence"""
    session_id = getattr(request.state, "session_id", None)

    # Get or create session
    session = await session_manager.get_or_create_session(session_id)

    # Increment a counter in user data
    if "counter" not in session.user_data:
        session.user_data["counter"] = 0
    session.user_data["counter"] += 1

    return {
        "session_id": session.session_id,
        "counter": session.user_data["counter"],
        "message": f"This is request #{session.user_data['counter']} in this session",
    }


@router.delete("/")
async def destroy_session(request: Request) -> Dict[str, Any]:
    """Destroy current session"""
    session_id = getattr(request.state, "session_id", None)

    if session_id:
        await session_manager.destroy_session(session_id)
        return {"message": "Session destroyed", "session_id": session_id}
    else:
        return {"error": "No session to destroy"}
