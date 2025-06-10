"""Real Google Calendar integration using Google API"""

import os
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import logging

logger = logging.getLogger(__name__)

class GoogleCalendarClient:
    """Real Google Calendar API client"""
    
    SCOPES = ['https://www.googleapis.com/auth/calendar.readonly']
    
    def __init__(self):
        self.credentials_file = "data/google_credentials.json"  # OAuth client config
        self.token_file = "data/google_token.json"             # User tokens
        self.service = None
        
    def get_auth_url(self, redirect_uri: str) -> str:
        """Get authorization URL for OAuth flow"""
        flow = Flow.from_client_secrets_file(
            self.credentials_file,
            scopes=self.SCOPES,
            redirect_uri=redirect_uri
        )
        
        auth_url, _ = flow.authorization_url(
            access_type='offline',
            include_granted_scopes='true'
        )
        return auth_url
    
    def handle_oauth_callback(self, authorization_code: str, redirect_uri: str) -> bool:
        """Handle OAuth callback and store tokens"""
        try:
            flow = Flow.from_client_secrets_file(
                self.credentials_file,
                scopes=self.SCOPES,
                redirect_uri=redirect_uri
            )
            
            flow.fetch_token(code=authorization_code)
            
            # Save credentials
            with open(self.token_file, 'w') as token:
                token.write(flow.credentials.to_json())
                
            return True
        except Exception as e:
            logger.error(f"OAuth callback error: {e}")
            return False
    
    def _get_credentials(self) -> Optional[Credentials]:
        """Load and refresh credentials"""
        creds = None
        
        # Load existing token
        if os.path.exists(self.token_file):
            creds = Credentials.from_authorized_user_file(self.token_file, self.SCOPES)
        
        # Refresh if expired
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
            # Save refreshed token
            with open(self.token_file, 'w') as token:
                token.write(creds.to_json())
                
        return creds if creds and creds.valid else None
    
    def _get_service(self):
        """Get authenticated Google Calendar service"""
        if not self.service:
            creds = self._get_credentials()
            if not creds:
                raise Exception("Not authenticated. Run OAuth flow first.")
            self.service = build('calendar', 'v3', credentials=creds)
        return self.service
    
    async def get_calendars(self) -> List[Dict[str, Any]]:
        """Get list of user's calendars"""
        try:
            service = self._get_service()
            result = service.calendarList().list().execute()
            
            calendars = []
            for calendar in result.get('items', []):
                calendars.append({
                    'id': calendar['id'],
                    'name': calendar['summary'],
                    'primary': calendar.get('primary', False),
                    'access_role': calendar.get('accessRole', 'reader')
                })
            
            return calendars
        except HttpError as e:
            logger.error(f"Calendar list error: {e}")
            return []
    
    async def get_events(
        self, 
        calendar_id: str = 'primary',
        days_ahead: int = 7,
        max_results: int = 10
    ) -> List[Dict[str, Any]]:
        """Get upcoming events from calendar"""
        try:
            service = self._get_service()
            
            # Time range
            now = datetime.utcnow()
            time_min = now.isoformat() + 'Z'
            time_max = (now + timedelta(days=days_ahead)).isoformat() + 'Z'
            
            result = service.events().list(
                calendarId=calendar_id,
                timeMin=time_min,
                timeMax=time_max,
                maxResults=max_results,
                singleEvents=True,
                orderBy='startTime'
            ).execute()
            
            events = []
            for event in result.get('items', []):
                start = event['start'].get('dateTime', event['start'].get('date'))
                end = event['end'].get('dateTime', event['end'].get('date'))
                
                events.append({
                    'id': event['id'],
                    'summary': event.get('summary', 'No title'),
                    'start': start,
                    'end': end,
                    'location': event.get('location'),
                    'description': event.get('description'),
                    'attendees': [
                        attendee.get('email') 
                        for attendee in event.get('attendees', [])
                    ],
                    'creator': event.get('creator', {}).get('email'),
                    'html_link': event.get('htmlLink')
                })
            
            return events
        except HttpError as e:
            logger.error(f"Events fetch error: {e}")
            return []
    
    async def get_next_meeting(self, calendar_id: str = 'primary') -> Optional[Dict[str, Any]]:
        """Get the next upcoming meeting"""
        events = await self.get_events(calendar_id=calendar_id, max_results=1)
        return events[0] if events else None
    
    async def get_todays_events(self, calendar_id: str = 'primary') -> List[Dict[str, Any]]:
        """Get today's events"""
        try:
            service = self._get_service()
            
            # Today's range
            now = datetime.now()
            start_of_day = now.replace(hour=0, minute=0, second=0, microsecond=0)
            end_of_day = now.replace(hour=23, minute=59, second=59, microsecond=999999)
            
            result = service.events().list(
                calendarId=calendar_id,
                timeMin=start_of_day.isoformat() + 'Z',
                timeMax=end_of_day.isoformat() + 'Z',
                singleEvents=True,
                orderBy='startTime'
            ).execute()
            
            events = []
            for event in result.get('items', []):
                start = event['start'].get('dateTime', event['start'].get('date'))
                events.append({
                    'summary': event.get('summary', 'No title'),
                    'start': start,
                    'location': event.get('location')
                })
            
            return events
        except HttpError as e:
            logger.error(f"Today's events error: {e}")
            return []
    
    def is_authenticated(self) -> bool:
        """Check if user is authenticated"""
        return self._get_credentials() is not None
    
    def logout(self) -> bool:
        """Logout by removing stored tokens"""
        try:
            if os.path.exists(self.token_file):
                os.remove(self.token_file)
                logger.info("User logged out - tokens removed")
                
            # Clear cached service
            self.service = None
            return True
        except Exception as e:
            logger.error(f"Logout error: {e}")
            return False