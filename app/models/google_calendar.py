"""Pydantic models for Google Calendar API"""

from pydantic import BaseModel
from typing import List, Optional, Dict, Any

class AuthUrlResponse(BaseModel):
    """Response for getting OAuth authorization URL"""
    auth_url: str
    instructions: str

class AuthCallbackRequest(BaseModel):
    """Request for handling OAuth callback"""
    authorization_code: str

class AuthStatusResponse(BaseModel):
    """Response for authentication status"""
    authenticated: bool
    message: str

class Calendar(BaseModel):
    """Google Calendar information"""
    id: str
    name: str
    primary: bool = False
    access_role: str

class CalendarListResponse(BaseModel):
    """Response for calendar list"""
    calendars: List[Calendar]
    count: int

class Event(BaseModel):
    """Google Calendar event"""
    id: str
    summary: str
    start: str
    end: str
    location: Optional[str] = None
    description: Optional[str] = None
    attendees: List[str] = []
    creator: Optional[str] = None
    html_link: Optional[str] = None

class EventsResponse(BaseModel):
    """Response for events list"""
    events: List[Event]
    count: int

class SimpleEvent(BaseModel):
    """Simplified event for today's events"""
    summary: str
    start: str
    location: Optional[str] = None