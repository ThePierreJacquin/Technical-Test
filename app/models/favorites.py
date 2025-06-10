"""Pydantic models for favorites-related API requests and responses."""

from pydantic import BaseModel, StringConstraints
from typing import List, Annotated


class FavoriteRequest(BaseModel):
    """Favorite query request"""

    city: Annotated[str, StringConstraints(min_length=1)]


class FavoriteActionResponse(BaseModel):
    """Favorite Response when action taken (add or remove)"""

    success: bool
    message: str
    city: str
    action_taken: bool


class FavoriteCity(BaseModel):
    """Favorited city model"""

    city_name: str


class FavoritesListResponse(BaseModel):
    """ "Favorite Response when listing"""

    favorites: List[FavoriteCity]
    count: int
