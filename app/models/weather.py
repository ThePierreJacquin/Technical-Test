"""Pydantic models for weather-related API requests and responses."""

from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class WeatherRequest(BaseModel):
    """Natural language query"""

    query: str


class WeatherCondition(BaseModel):
    """Basic data sent back along the model answer."""

    main: str
    description: str
    icon: str


class WeatherData(BaseModel):
    """Weather data model, now with richer information."""

    city: str
    country: Optional[str] = None
    temperature: float
    feels_like: float
    temp_high: Optional[float] = None
    temp_low: Optional[float] = None
    humidity: int
    pressure: Optional[str] = (
        None  # Keep as string to include trend, e.g., "29.92 in (falling)"
    )
    conditions: WeatherCondition
    wind_speed: float
    wind_direction: Optional[str] = None
    uv_index: Optional[str] = None
    visibility: Optional[str] = None
    timestamp: datetime


class WeatherResponse(BaseModel):
    """API Response including LLM generated response"""

    success: bool
    data: Optional[WeatherData] = None
    message: str
    natural_answer: Optional[str] = None
