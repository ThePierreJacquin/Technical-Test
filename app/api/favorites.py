"""API endpoints for managing user favorites"""

import logging
from fastapi import APIRouter, Depends, HTTPException, Request

from app.core.scrapers.account_manager import AccountManager
from app.core.session_manager import UserSession, session_manager
from app.models.favorites import (
    FavoriteActionResponse,
    FavoriteCity,
    FavoriteRequest,
    FavoritesListResponse,
)

logger = logging.getLogger(__name__)

# --- API Router Setup ---

router = APIRouter(prefix="/favorites", tags=["favorites"])
account_manager = AccountManager()

# --- Dependency for Authenticated Sessions ---


async def get_authenticated_session(request: Request) -> UserSession:
    """
    FastAPI dependency to get a user's session and ensure it's authenticated.
    Raises 401 Unauthorized if the session is not valid or not authenticated.
    """
    session_id = getattr(request.state, "session_id", None)
    if not session_id:
        raise HTTPException(status_code=401, detail="Session ID missing.")

    session = await session_manager.get_session(session_id)
    if not session or not session.is_authenticated:
        raise HTTPException(status_code=401, detail="Authentication required.")

    return session


# --- API Endpoints ---


@router.get("/", response_model=FavoritesListResponse)
async def list_user_favorites(
    session: UserSession = Depends(get_authenticated_session),
):
    """
    List all cities currently in the user's favorites.
    Requires authentication.
    """
    favorites_list = await account_manager.list_favorites(session)
    return FavoritesListResponse(
        favorites=[FavoriteCity(city_name=city) for city in favorites_list],
        count=len(favorites_list),
    )


@router.post("/add", response_model=FavoriteActionResponse)
async def add_favorite(
    request_data: FavoriteRequest,
    session: UserSession = Depends(get_authenticated_session),
):
    """
    Add a city to the user's favorites.
    Requires authentication.
    """
    city = request_data.city
    logger.info(
        f"API request to ADD favorite: '{city}' for session {session.session_id}"
    )
    result = await account_manager.toggle_favorite(session, city=city, add=True)

    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["message"])

    return FavoriteActionResponse(
        success=True,
        message=result["message"],
        city=city,
        action_taken=result["action_taken"],
    )


@router.post("/remove", response_model=FavoriteActionResponse)
async def remove_favorite(
    request_data: FavoriteRequest,
    session: UserSession = Depends(get_authenticated_session),
):
    """
    Remove a city from the user's favorites.
    Requires authentication.
    """
    city = request_data.city
    logger.info(
        f"API request to REMOVE favorite: '{city}' for session {session.session_id}"
    )
    result = await account_manager.toggle_favorite(session, city=city, add=False)

    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["message"])

    return FavoriteActionResponse(
        success=True,
        message=result["message"],
        city=city,
        action_taken=result["action_taken"],
    )
