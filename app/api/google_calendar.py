"""API endpoints for Google Calendar integration"""

from fastapi import APIRouter, HTTPException, Request, Query
from typing import List, Optional
from app.core.google_calendar_client import GoogleCalendarClient
from app.models.google_calendar import (
    AuthUrlResponse, 
    AuthCallbackRequest,
    CalendarListResponse,
    EventsResponse,
    AuthStatusResponse
)

router = APIRouter(prefix="/google-calendar", tags=["google-calendar"])
calendar_client = GoogleCalendarClient()

@router.get("/auth/url", response_model=AuthUrlResponse)
async def get_auth_url(request: Request):
    """
    Step 1: Get Google OAuth authorization URL
    User should visit this URL in their browser to authorize
    """
    try:
        # Use your domain + callback endpoint as redirect URI
        redirect_uri = f"{request.base_url}google-calendar/auth/callback"
        auth_url = calendar_client.get_auth_url(str(redirect_uri))
        
        return AuthUrlResponse(
            auth_url=auth_url,
            instructions="Visit this URL in your browser, authorize the app, then copy the 'code' parameter from the redirect URL and send it to /auth/callback"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate auth URL: {str(e)}")

@router.get("/auth/callback")
async def handle_auth_callback_get(request: Request, code: str = Query(...)):
    """
    Step 2a: Handle OAuth callback from Google (GET request)
    Google redirects here with the authorization code
    """
    try:
        redirect_uri = f"{request.base_url}google-calendar/auth/callback"
        success = calendar_client.handle_oauth_callback(code, str(redirect_uri))
        
        if success:
            return {
                "success": True, 
                "message": "Successfully authenticated with Google Calendar!",
                "next_steps": "You can now use the calendar endpoints like /google-calendar/events"
            }
        else:
            raise HTTPException(status_code=400, detail="Failed to authenticate")
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Auth callback error: {str(e)}")

@router.post("/auth/callback")
async def handle_auth_callback_post(request: Request, callback_data: AuthCallbackRequest):
    """
    Step 2b: Handle authorization callback (POST request for API clients)
    User manually sends the 'code' parameter they got from the redirect URL
    """
    try:
        redirect_uri = f"{request.base_url}google-calendar/auth/callback"
        success = calendar_client.handle_oauth_callback(
            callback_data.authorization_code, 
            str(redirect_uri)
        )
        
        if success:
            return {"success": True, "message": "Successfully authenticated with Google Calendar"}
        else:
            raise HTTPException(status_code=400, detail="Failed to authenticate")
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Auth callback error: {str(e)}")

@router.get("/auth/status", response_model=AuthStatusResponse)
async def get_auth_status():
    """Check if user is authenticated with Google Calendar"""
    try:
        authenticated = calendar_client.is_authenticated()
        return AuthStatusResponse(
            authenticated=authenticated,
            message="Ready to access Google Calendar" if authenticated else "Not authenticated"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/calendars", response_model=CalendarListResponse)
async def get_calendars():
    """Get list of user's Google Calendars"""
    try:
        if not calendar_client.is_authenticated():
            raise HTTPException(status_code=401, detail="Not authenticated. Call /auth/url first")
            
        calendars = await calendar_client.get_calendars()
        return CalendarListResponse(calendars=calendars, count=len(calendars))
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch calendars: {str(e)}")

@router.get("/events", response_model=EventsResponse)
async def get_events(
    calendar_id: str = "primary",
    days_ahead: int = Query(7, ge=1, le=30),
    max_results: int = Query(10, ge=1, le=100)
):
    """Get upcoming events from Google Calendar"""
    try:
        if not calendar_client.is_authenticated():
            raise HTTPException(status_code=401, detail="Not authenticated")
            
        events = await calendar_client.get_events(
            calendar_id=calendar_id,
            days_ahead=days_ahead,
            max_results=max_results
        )
        
        return EventsResponse(events=events, count=len(events))
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch events: {str(e)}")

@router.get("/events/today", response_model=EventsResponse)
async def get_todays_events(calendar_id: str = "primary"):
    """Get today's events from Google Calendar"""
    try:
        if not calendar_client.is_authenticated():
            raise HTTPException(status_code=401, detail="Not authenticated")
            
        events = await calendar_client.get_todays_events(calendar_id=calendar_id)
        return EventsResponse(events=events, count=len(events))
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch today's events: {str(e)}")

@router.get("/events/next")
async def get_next_meeting(calendar_id: str = "primary"):
    """Get the next upcoming meeting"""
    try:
        if not calendar_client.is_authenticated():
            raise HTTPException(status_code=401, detail="Not authenticated")
            
        next_meeting = await calendar_client.get_next_meeting(calendar_id=calendar_id)
        
        if next_meeting:
            return {"success": True, "event": next_meeting}
        else:
            return {"success": True, "event": None, "message": "No upcoming meetings"}
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch next meeting: {str(e)}")

# Alternative endpoint for service account authentication (no OAuth needed)
@router.post("/auth/service-account")
async def authenticate_service_account():
    """
    Alternative: Authenticate using service account
    Requires GOOGLE_APPLICATION_CREDENTIALS environment variable
    pointing to service account JSON file
    """
    # This would be implemented if you want to use service accounts instead
    return {"message": "Service account auth not implemented yet"}

@router.post("/auth/logout")
async def logout():
    """
    Logout user by removing stored tokens
    User will need to re-authenticate to access calendar
    """
    try:
        success = calendar_client.logout()
        if success:
            return {
                "success": True,
                "message": "Successfully logged out. Tokens have been removed.",
                "note": "You'll need to re-authenticate to access your calendar again."
            }
        else:
            return {
                "success": False,
                "message": "Logout failed or no active session found."
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Logout error: {str(e)}")