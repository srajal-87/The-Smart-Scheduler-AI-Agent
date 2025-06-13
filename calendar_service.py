import os
import pickle
from datetime import datetime, timedelta
from dateutil import parser
import pytz
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from typing import List, Dict, Optional

class CalendarService:
    def __init__(self):
        """Initialize the simplified calendar service"""
        self.SCOPES = ['https://www.googleapis.com/auth/calendar']
        self.service = None
        self.default_timezone = pytz.timezone('Asia/Kolkata')  # IST (GMT+5:30)
        self.authenticate()
    
    def authenticate(self):
        """Authenticate and build the Google Calendar service"""
        creds = None
        
        # Load existing token
        if os.path.exists('token.pickle'):
            with open('token.pickle', 'rb') as token:
                creds = pickle.load(token)
        
        # Refresh or get  new credentials
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    'credentials.json', self.SCOPES)
                creds = flow.run_local_server(port=0)
            
            with open('token.pickle', 'wb') as token:
                pickle.dump(creds, token)
        
        self.service = build('calendar', 'v3', credentials=creds)
    
    def find_available_slots(self, duration_minutes: int, target_date: datetime, 
                           preferred_time: str = 'any', calendar_id: str = 'primary') -> List[Dict]:
        """
        Find available time slots for the given duration and date
        """
        try:
            # Ensure target_date is  timezone-aware
            if target_date.tzinfo is None:
                target_date = self.default_timezone.localize(target_date)
            elif target_date.tzinfo != self.default_timezone:
                target_date = target_date.astimezone(self.default_timezone)
            
            time_blocks = {
                'morning': (9, 12),
                'afternoon': (12, 17),
                'evening': (17, 20),
                'any': (9, 18)
            }
            
            # Determine start and   end hours based on preferred_time
            if preferred_time.lower() in time_blocks:
                start_hour, end_hour = time_blocks[preferred_time.lower()]
            else:
                # Check if it's a specific time like "2 PM" or "6 PM"
                try:
                    from dateutil import parser as date_parser
                    parsed_time = date_parser.parse(preferred_time)
                    start_hour = parsed_time.hour
                    end_hour = min(start_hour + 2, 20)  # Max 8 PM
                except:
                    # Default to 'any' if parsing fails
                    start_hour, end_hour = time_blocks['any']
            
            # Define search window based on preferred time
            start_of_day = target_date.replace(hour=start_hour, minute=0, second=0, microsecond=0)
            end_of_day = target_date.replace(hour=end_hour, minute=0, second=0, microsecond=0)
            
            events = self.get_events_for_date_range(start_of_day, end_of_day, calendar_id)   # Get existing events for the day
            
            time_slots = self.generate_basic_time_slots(start_of_day, end_of_day, duration_minutes)  # Generate basic time slots
            
            available_slots = self.filter_available_slots(time_slots, events) # Filter out conflicting slots
            
            return available_slots[:10]  # Return top 10 options
            
        except Exception as e:
            print(f"Error finding available slots: {e}")
            return []
    
    def generate_basic_time_slots(self, start_time: datetime, end_time: datetime, 
                                duration_minutes: int) -> List[Dict]:
        """
        Generate basic time slots every 30 minutes during business hours (9 AM - 6 PM)
        """
        slots = []
        current_time = start_time
        
        while current_time + timedelta(minutes=duration_minutes) <= end_time:
            slot_end = current_time + timedelta(minutes=duration_minutes)
            
            slots.append({
                'start': current_time,
                'end': slot_end,
                'duration': duration_minutes
            })
            
            # Move to next 30-minute interval
            current_time += timedelta(minutes=30)
        
        return slots
    
    def filter_available_slots(self, time_slots: List[Dict], events: List[Dict]) -> List[Dict]:
        """
        Filter out time slots that conflict with existing events
        """
        available_slots = []
        
        for slot in time_slots:
            is_available = True
            slot_start = slot['start']
            slot_end = slot['end']
            
            for event in events:
                event_start = event['start']
                event_end = event['end']
                
                # Check for overlap
                if (slot_start < event_end and slot_end > event_start):
                    is_available = False
                    break
            
            if is_available:
                available_slots.append(slot)
        
        return available_slots
    
    def get_events_for_date_range(self, start_time: datetime, end_time: datetime, 
                                 calendar_id: str = 'primary') -> List[Dict]:
        """
        Get all events within a date range
        """
        try:
            # Convert to UTC for API call
            start_utc = start_time.astimezone(pytz.UTC).isoformat()
            end_utc = end_time.astimezone(pytz.UTC).isoformat()
            
            events_result = self.service.events().list(
                calendarId=calendar_id,
                timeMin=start_utc,
                timeMax=end_utc,
                singleEvents=True,
                orderBy='startTime'
            ).execute()
            
            events = events_result.get('items', [])
            parsed_events = []
            
            for event in events:
                # Skip all-day events
                if 'dateTime' not in event['start']:
                    continue
                
                start_dt = parser.parse(event['start']['dateTime'])
                end_dt = parser.parse(event['end']['dateTime'])
                
                parsed_events.append({
                    'start': start_dt,
                    'end': end_dt,
                    'summary': event.get('summary', 'Busy'),
                    'id': event.get('id')
                })
            
            return parsed_events
            
        except Exception as e:
            print(f"Error fetching events: {e}")
            return []
    
    def create_event(self, event_details: Dict, title: str = None) -> Optional[str]:
        """
        Create a new calendar event
        Expected event_details format:
        {
            'summary': 'Meeting Title',  # Will be overridden by title parameter if provided
            'start': datetime_object,
            'end': datetime_object,
            'description': 'Optional description'
        }
        
        Args:
            event_details: Dictionary containing event information
            title: Optional meeting title that will override the summary in event_details
        """
        try:
            start_time = event_details['start']
            end_time = event_details['end']
            
            # Ensure times are timezone-aware
            if start_time.tzinfo is None:
                start_time = self.default_timezone.localize(start_time)
            if end_time.tzinfo is None:
                end_time = self.default_timezone.localize(end_time)
            
            # Use provided title or fall  back to summary in event_details or default
            event_title = title or event_details.get('summary', 'Meeting')
            
            event = {
                'summary': event_title,
                'description': event_details.get('description', ''),
                'start': {
                    'dateTime': start_time.isoformat(),
                    'timeZone': str(self.default_timezone),
                },
                'end': {
                    'dateTime': end_time.isoformat(),
                    'timeZone': str(self.default_timezone),
                },
                'reminders': {
                    'useDefault': False,
                    'overrides': [
                        {'method': 'email', 'minutes': 60},  # 1 hour before
                        {'method': 'popup', 'minutes': 15},  # 15 minutes before
                    ],
                },
            }
            
            created_event = self.service.events().insert(
                calendarId='primary', 
                body=event
            ).execute()
            
            return created_event.get('id')
            
        except Exception as e:
            raise Exception(f"Failed to create event: {str(e)}")
    
    def is_time_available(self, start_time: datetime, duration_minutes: int, 
                         calendar_id: str = 'primary') -> bool:
        """
        Check if a specific time slot is available
        """
        try:
            end_time = start_time + timedelta(minutes=duration_minutes)
            
            # Get events in the time range
            events = self.get_events_for_date_range(start_time, end_time, calendar_id)
            
            # Check for conflicts
            for event in events:
                if (start_time < event['end'] and end_time > event['start']):
                    return False
            
            return True
            
        except Exception as e:
            print(f"Error checking availability: {e}")
            return False
    
    def format_slot_for_display(self, slot: Dict) -> str:
        """
        Format a slot dictionary for user-friendly display
        """
        start_time = slot['start']
        end_time = slot['end']
        
        # Ensure timezone is IST
        if start_time.tzinfo != self.default_timezone:
            start_time = start_time.astimezone(self.default_timezone)
            end_time = end_time.astimezone(self.default_timezone)
        
        start_str = start_time.strftime('%I:%M %p')
        end_str = end_time.strftime('%I:%M %p')
        
        return f"{start_str} - {end_str} IST"