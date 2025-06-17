import json
import logging
import os
import re
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import google.generativeai as genai
import pytz
from dateutil import parser

from calendar_service import CalendarService
from prompts import SYSTEM_PROMPT

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class SchedulingStage:
    """Enum-like class for conversation stages"""
    GREETING = 'greeting'
    COLLECT_DURATION = 'collect_duration'
    COLLECT_DATE = 'collect_date'
    COLLECT_TIME = 'collect_time'
    SHOW_SLOTS = 'show_slots'
    COLLECT_TITLE = 'collect_title'
    CONFIRM_BOOKING = 'confirm_booking'
    COMPLETED = 'completed'


class ConversationState:
    """Manages the state of a scheduling conversation"""
    
    def __init__(self):
        self.stage = SchedulingStage.GREETING
        self.meeting_duration = None
        self.preferred_date = None
        self.preferred_time = None
        self.parsed_date = None
        self.available_slots = []
        self.selected_slot = None
        self.meeting_title = None
        self.conversation_history = []
    
    def reset(self):
        """Reset conversation to initial state"""
        self.__init__()
    
    def add_message(self, role: str, message: str, timezone: pytz.BaseTzInfo):
        """Add a message to conversation history"""
        self.conversation_history.append({
            'role': role,
            'message': message,
            'timestamp': datetime.now(timezone).isoformat()
        })


class SchedulerAgent:
    """
    Main scheduling agent that handles conversation flow and coordinates
    between Gemini LLM and Google Calendar API
    """
    
    # Constants
    MIN_DURATION_MINUTES = 15
    MAX_DURATION_MINUTES = 480  # 8 hours
    MAX_CONVERSATION_HISTORY = 4
    RESTART_KEYWORDS = ['start over', 'restart', 'reset', 'new meeting', 'begin again']
    
    def __init__(self):
        """Initialize the scheduler agent with Gemini and Calendar services"""
        self._setup_gemini()
        self.calendar_service = CalendarService()
        self.conversations = {}  # session_id -> ConversationState
        self.timezone = pytz.timezone('Asia/Kolkata')
        
        logger.info("SchedulerAgent initialized successfully")
    
    def _setup_gemini(self):
        """Configure Gemini API"""
        api_key = os.getenv('GEMINI_API_KEY')
        if not api_key:
            raise ValueError("GEMINI_API_KEY environment variable is required")
        
        try:
            genai.configure(api_key=api_key)
            self.model = genai.GenerativeModel("models/gemini-1.5-flash-002")
        except Exception as e:
            logger.error(f"Failed to initialize Gemini: {e}")
            raise
    
    def _get_conversation_state(self, session_id: str) -> ConversationState:
        """Get or create conversation state for a session"""
        if session_id not in self.conversations:
            self.conversations[session_id] = ConversationState()
        return self.conversations[session_id]
    
    def reset_conversation(self, session_id: str):
        """Reset conversation state for a session"""
        if session_id in self.conversations:
            del self.conversations[session_id]
            logger.info(f"Reset conversation for session: {session_id}")
    
    def process_message(self, user_input: str, session_id: str) -> str:
        """
        Main entry point for processing user messages
        
        Args:
            user_input: The user's message
            session_id: Unique identifier for the conversation session
            
        Returns:
            Bot response string
        """
        state = self._get_conversation_state(session_id)
        state.add_message('user', user_input, self.timezone)
        
        try:
            if self._is_restart_request(user_input):
                self.reset_conversation(session_id)
                state = self._get_conversation_state(session_id)
                response = "Let's start fresh! I'll help you schedule a new meeting. How long should the meeting be?"
            else:
                response = self._route_conversation(user_input, state)
            
            state.add_message('assistant', response, self.timezone)
            return response
            
        except Exception as e:
            logger.error(f"Error processing message: {e}")
            return f"I encountered an error: {str(e)}. Please try again or say 'start over'."
    
    def _is_restart_request(self, user_input: str) -> bool:
        """Check if user wants to restart the conversation"""
        return any(keyword in user_input.lower() for keyword in self.RESTART_KEYWORDS)
    
    def _route_conversation(self, user_input: str, state: ConversationState) -> str:
        """Route conversation based on current stage"""
        entities = self._extract_entities(user_input, state)
        
        # Map stages to handler methods
        handlers = {
            SchedulingStage.GREETING: self._handle_greeting,
            SchedulingStage.COLLECT_DURATION: self._handle_duration,
            SchedulingStage.COLLECT_DATE: self._handle_date,
            SchedulingStage.COLLECT_TIME: self._handle_time,
            SchedulingStage.SHOW_SLOTS: self._handle_slot_selection,
            SchedulingStage.COLLECT_TITLE: self._handle_title,
            SchedulingStage.CONFIRM_BOOKING: self._handle_confirmation,
        }
        
        handler = handlers.get(state.stage)
        if handler:
            return handler(user_input, state, entities)
        else:
            return "I'm not sure where we are in the conversation. Let's start over - do you need to schedule a meeting?"
    
    def _query_gemini(self, prompt: str, chat_history: List[Dict] = None) -> str:
        """
        Send a query to Gemini and get response
        
        Args:
            prompt: The prompt to send
            chat_history: Recent conversation history for context
            
        Returns:
            Gemini's response text
        """
        try:
            full_prompt = self._build_prompt_with_context(prompt, chat_history)
            
            response = self.model.generate_content(
                full_prompt,
                generation_config=genai.types.GenerationConfig(
                    max_output_tokens=2048,
                    temperature=0.7,
                )
            )
            
            return response.text.strip() if response.text else "I didn't receive a proper response. Could you please try again?"
                        
        except Exception as e:
            logger.error(f"Gemini API error: {e}")
            return "I encountered an issue. Please try rephrasing your request."
    
    def _build_prompt_with_context(self, user_prompt: str, chat_history: List[Dict] = None) -> str:
        """Build a comprehensive prompt with system context and history"""
        prompt_parts = []
        
        # System instructions
        if SYSTEM_PROMPT:
            prompt_parts.append(f"SYSTEM INSTRUCTIONS:\n{SYSTEM_PROMPT}\n")
        
        # Recent conversation history
        if chat_history:
            recent_messages = chat_history[-self.MAX_CONVERSATION_HISTORY:]
            history_text = "\n".join([
                f"{'User' if msg['role'] == 'user' else 'Assistant'}: {msg['message']}"
                for msg in recent_messages
            ])
            prompt_parts.append(f"CONVERSATION HISTORY:\n{history_text}\n")
        
        # Current user input
        prompt_parts.append(f"CURRENT USER INPUT:\n{user_prompt}\n")
        
        # Current time context
        current_time = datetime.now(self.timezone)
        prompt_parts.append(f"CURRENT TIME: {current_time.strftime('%A, %B %d, %Y at %I:%M %p IST')}")
        
        return "\n".join(prompt_parts)
    
    def _extract_entities(self, user_input: str, state: ConversationState) -> Dict[str, Any]:
        """Extract structured information from user input using Gemini"""
        
        extraction_prompt = f"""
        Extract structured information from the user's message for meeting scheduling.
        
        CURRENT STAGE: {state.stage}
        ALREADY COLLECTED:
        - Duration: {state.meeting_duration or 'Not set'} minutes
        - Date: {state.preferred_date or 'Not set'}
        - Time: {state.preferred_time or 'Not set'}
        - Title: {state.meeting_title or 'Not set'}
        
        USER MESSAGE: "{user_input}"
        
        Extract and return ONLY a JSON object with these fields (use null for missing info):
        {{
            "duration_minutes": number or null,
            "date_preference": "string description or null",
            "time_preference": "string description or null", 
            "meeting_title": "string or null",
            "intent": "greeting|duration|date|time|slot_selection|title|confirmation|restart|unclear",
            "slot_number": number or null (if selecting from numbered options),
            "confirmation": "yes|no|null" (for booking confirmations)
        }}
        """
        
        try:
            response = self._query_gemini(extraction_prompt)
            
            # Extract JSON from response
            if '{' in response and '}' in response:
                json_start = response.find('{')
                json_end = response.rfind('}') + 1
                json_str = response[json_start:json_end]
                return json.loads(json_str)
            
            return {}
                
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON from Gemini: {e}")
            return {}
        except Exception as e:
            logger.error(f"Entity extraction failed: {e}")
            return {}
    
    # Stage handlers
    
    def _handle_greeting(self, user_input: str, state: ConversationState, entities: Dict[str, Any]) -> str:
        """Handle initial greeting and meeting request"""
        if entities.get('intent') == 'greeting' or any(word in user_input.lower() 
                                                     for word in ['meeting', 'schedule', 'book']):
            state.stage = SchedulingStage.COLLECT_DURATION
            
            # Check if duration was provided upfront
            if entities.get('duration_minutes'):
                duration = entities['duration_minutes']
                if self._is_valid_duration(duration):
                    state.meeting_duration = duration
                    state.stage = SchedulingStage.COLLECT_DATE

                    # Check if date was also provided
                    if entities.get('date_preference'):
                        parsed_date = self._parse_date_with_gemini(entities['date_preference'])
                        if parsed_date:
                            state.preferred_date = entities['date_preference']
                            state.parsed_date = parsed_date
                            state.stage = SchedulingStage.COLLECT_TIME
                            date_str = parsed_date.strftime('%A, %B %d')

                            # Check if time preference was also provided
                            if entities.get('time_preference'):
                                state.preferred_time = entities['time_preference']
                                return self._search_and_show_slots(state)

                            return f"Perfect! A {duration}-minute meeting on {date_str}. What time do you prefer?"

                    return f"Perfect! A {duration}-minute meeting. What date would you prefer?"
                
                
            
            return "Great! I'll help you schedule a meeting. How long should the meeting be? (e.g., 30 minutes, 1 hour)"
        
        return "Hello! I can help you schedule meetings. Would you like to book a meeting?"
    
    def _handle_duration(self, user_input: str, state: ConversationState, entities: Dict[str, Any]) -> str:
        """Handle duration collection"""
        duration = entities.get('duration_minutes')
        
        if duration and self._is_valid_duration(duration):
            state.meeting_duration = duration
            state.stage = SchedulingStage.COLLECT_DATE
            
            # Check if date was also provided
            if entities.get('date_preference'):
                parsed_date = self._parse_date_with_gemini(entities['date_preference'])
                if parsed_date:
                    state.preferred_date = entities['date_preference']
                    state.parsed_date = parsed_date
                    state.stage = SchedulingStage.COLLECT_TIME
                    date_str = parsed_date.strftime('%A, %B %d')

                    # Check if time preference was also provided
                    if entities.get('time_preference'):
                        state.preferred_time = entities['time_preference']
                        return self._search_and_show_slots(state)

                    return f"Perfect! A {duration}-minute meeting on {date_str}. What time do you prefer?"
            
            return f"Perfect! A {duration}-minute meeting. What date would you prefer?"
        else:
            return f"Please specify a meeting duration between {self.MIN_DURATION_MINUTES} minutes and {self.MAX_DURATION_MINUTES // 60} hours (e.g., '30 minutes', '1 hour', '2 hours')."
    
    def _handle_date(self, user_input: str, state: ConversationState, entities: Dict[str, Any]) -> str:
        """Handle date collection"""
        date_preference = entities.get('date_preference') or user_input
        parsed_date = self._parse_date_with_gemini(date_preference)
        
        if parsed_date:
            state.preferred_date = date_preference
            state.parsed_date = parsed_date
            state.stage = SchedulingStage.COLLECT_TIME
            
            date_str = parsed_date.strftime('%A, %B %d')
            
            # Check if time preference was also provided
            if entities.get('time_preference'):
                state.preferred_time = entities['time_preference']
                return self._search_and_show_slots(state)
                
            return f"Got it! {date_str}. What time do you prefer? (e.g., 'morning', 'afternoon', '2 PM', 'any time')"
        else:
            return "I couldn't understand that date. Please try formats like 'tomorrow', 'June 15', 'next Monday', or 'this Friday'."
    
    def _handle_time(self, user_input: str, state: ConversationState, entities: Dict[str, Any]) -> str:
        """Handle time preference collection"""
        time_preference = entities.get('time_preference') or user_input.lower()
        state.preferred_time = time_preference
        
        return self._search_and_show_slots(state)
    
    def _handle_slot_selection(self, user_input: str, state: ConversationState, entities: Dict[str, Any]) -> str:
        """Handle slot selection from available options"""
        slot_number = entities.get('slot_number')
        
        if slot_number and 1 <= slot_number <= len(state.available_slots):
            return self._select_slot_and_ask_title(slot_number, state)
        else:
            return f"Please choose a number between 1 and {len(state.available_slots)}, or say 'show different times' for other options."
    
    def _handle_title(self, user_input: str, state: ConversationState, entities: Dict[str, Any]) -> str:
        """Handle meeting title collection"""
        # Check if user wants to skip title
        if user_input.lower().strip() in ['skip', 'no title', 'default', 'none']:
            state.meeting_title = None
            return self._show_final_confirmation(state)
        
        # Extract title from entities or clean user input
        meeting_title = entities.get('meeting_title') or self._clean_title_input(user_input)
        
        if meeting_title and len(meeting_title.strip()) > 0:
            state.meeting_title = meeting_title.strip()
            return self._show_final_confirmation(state)
        else:
            return "I didn't catch that. What would you like to name the meeting? Or say 'skip' to use a default name."
    
    def _handle_confirmation(self, user_input: str, state: ConversationState, entities: Dict[str, Any]) -> str:
        """Handle booking confirmation"""
        confirmation = entities.get('confirmation')
        
        if confirmation == 'yes':
            return self._book_meeting(state)
        elif confirmation == 'no':
            state.stage = SchedulingStage.SHOW_SLOTS
            return "No problem! Here are the available slots again:\n\n" + self._format_available_slots(state.available_slots, state)
        else:
            return "Please reply 'yes' to confirm the booking or 'no' to see other options."
    
    # Helper methods
    
    def _is_valid_duration(self, duration: int) -> bool:
        """Check if duration is within acceptable limits"""
        return self.MIN_DURATION_MINUTES <= duration <= self.MAX_DURATION_MINUTES
    
    def _clean_title_input(self, user_input: str) -> str:
        """Clean user input to extract meeting title"""
        title = user_input.strip()
        # Remove common prefixes that aren't part of the title
        prefixes_to_remove = ['call it', 'name it', 'title is', "it's called", 'meeting about']
        
        for prefix in prefixes_to_remove:
            if title.lower().startswith(prefix):
                title = title[len(prefix):].strip()
                break
        
        return title
    
    def _parse_date_with_gemini(self, date_text: str) -> Optional[datetime]:
        """Parse date expressions using Gemini"""
        current_time = datetime.now(self.timezone)
        
        parse_prompt = f"""
        Parse this date expression into a specific date. Current date: {current_time.strftime('%A, %B %d, %Y')}
        
        Date expression: "{date_text}"
        
        Return the date in format: YYYY-MM-DD
        
        Examples:
        "tomorrow" → {(current_time + timedelta(days=1)).strftime('%Y-%m-%d')}
        "next Tuesday" → (calculate next Tuesday from current date)
        "June 15" → 2025-06-15 (use current year if not specified)
        
        If unclear or invalid, return "INVALID".
        """
        
        try:
            response = self._query_gemini(parse_prompt)
            
            if "INVALID" in response.upper():
                return None
                
            # Extract YYYY-MM-DD pattern
            date_match = re.search(r'(\d{4})-(\d{2})-(\d{2})', response)
            if date_match:
                year, month, day = date_match.groups()
                parsed_date = datetime(int(year), int(month), int(day))
                return self.timezone.localize(parsed_date)
            
            return None
            
        except Exception as e:
            logger.error(f"Date parsing failed: {e}")
            return None
    
    def _search_and_show_slots(self, state: ConversationState) -> str:
        """Search for available slots and present them to user"""
        try:
            slots = self.calendar_service.find_available_slots(
                duration_minutes=state.meeting_duration,
                target_date=state.parsed_date,
                preferred_time=state.preferred_time
            )
            
            if slots:
                state.available_slots = slots
                state.stage = SchedulingStage.SHOW_SLOTS
                return self._format_available_slots(slots, state)
            else:
                date_str = state.parsed_date.strftime('%A, %B %d')
                return f"No available {state.meeting_duration}-minute slots found on {date_str}. Would you like to try a different date?"
                
        except Exception as e:
            logger.error(f"Calendar search error: {e}")
            return f"I had trouble checking your calendar: {str(e)}. Please try again."
    
    def _format_available_slots(self, slots: List[Dict], state: ConversationState) -> str:
        """Format available slots for user display"""
        date_str = state.parsed_date.strftime('%A, %B %d')
        response = f"I found these available {state.meeting_duration}-minute slots on {date_str}:\n\n"
        
        for i, slot in enumerate(slots[:5], 1):  # Show max 5 slots
            start_time = slot['start']
            end_time = slot['end']
            
            # Ensure timezone consistency
            if start_time.tzinfo != self.timezone:
                start_time = start_time.astimezone(self.timezone)
                end_time = end_time.astimezone(self.timezone)
            
            time_str = start_time.strftime('%I:%M %p')
            end_time_str = end_time.strftime('%I:%M %p')
            response += f"{i}. {time_str} - {end_time_str} IST\n"
        
        response += "\nWhich slot would you prefer? Just say the number (e.g., '1' or '2')."
        return response
    
    def _select_slot_and_ask_title(self, selection_number: int, state: ConversationState) -> str:
        """Select slot and transition to title collection"""
        selected_slot = state.available_slots[selection_number - 1]
        state.selected_slot = selected_slot
        state.stage = SchedulingStage.COLLECT_TITLE
        
        start_time = selected_slot['start']
        end_time = selected_slot['end']
        
        # Ensure timezone consistency
        if start_time.tzinfo != self.timezone:
            start_time = start_time.astimezone(self.timezone)
            end_time = end_time.astimezone(self.timezone)
        
        date_str = start_time.strftime('%A, %B %d')
        time_str = start_time.strftime('%I:%M %p')
        end_time_str = end_time.strftime('%I:%M %p')
        
        return (
            f"Great choice! I've selected:\n\n"
            f"📅 Date: {date_str}\n"
            f"⏰ Time: {time_str} - {end_time_str} IST\n"
            f"⏱️ Duration: {state.meeting_duration} minutes\n\n"
            f"What would you like to name this meeting? (e.g., 'Team Standup', 'Client Call', or just say 'skip' for a default name)"
        )
    
    def _show_final_confirmation(self, state: ConversationState) -> str:
        """Show final confirmation with all meeting details"""
        state.stage = SchedulingStage.CONFIRM_BOOKING
        
        selected_slot = state.selected_slot
        start_time = selected_slot['start']
        end_time = selected_slot['end']
        
        # Ensure timezone consistency
        if start_time.tzinfo != self.timezone:
            start_time = start_time.astimezone(self.timezone)
            end_time = end_time.astimezone(self.timezone)
        
        date_str = start_time.strftime('%A, %B %d')
        time_str = start_time.strftime('%I:%M %p')
        end_time_str = end_time.strftime('%I:%M %p')
        
        display_title = state.meeting_title or "Scheduled Meeting"
        
        return (
            f"Perfect! Let me confirm all the details:\n\n"
            f"📋 Title: {display_title}\n"
            f"📅 Date: {date_str}\n"
            f"⏰ Time: {time_str} - {end_time_str} IST\n"
            f"⏱️ Duration: {state.meeting_duration} minutes\n\n"
            f"Should I book this meeting? Reply 'yes' to confirm or 'no' to make changes."
        )
    
    def _book_meeting(self, state: ConversationState) -> str:
        """Create the calendar event and finalize booking"""
        try:
            selected_slot = state.selected_slot
            meeting_title = state.meeting_title or "Scheduled Meeting"
            
            event_details = {
                'summary': meeting_title,
                'start': selected_slot['start'],
                'end': selected_slot['end'],
                'description': f"Scheduled via Smart Scheduler AI\nDuration: {state.meeting_duration} minutes"
            }
            
            event_id = self.calendar_service.create_event(event_details)
            
            if event_id:
                state.stage = SchedulingStage.COMPLETED
                
                start_time = selected_slot['start']
                if start_time.tzinfo != self.timezone:
                    start_time = start_time.astimezone(self.timezone)
                
                date_str = start_time.strftime('%A, %B %d')
                time_str = start_time.strftime('%I:%M %p')
                
                return (
                    f"🎉 Meeting booked successfully!\n\n"
                    f"📋 Title: {meeting_title}\n"
                    f"📅 Date: {date_str}\n"
                    f"⏰ Time: {time_str} IST\n"
                    f"⏱️ Duration: {state.meeting_duration} minutes\n\n"
                    f"The meeting has been added to your calendar. Need to schedule another meeting?"
                )
            else:
                return "I had trouble booking the meeting. Please try again."
                
        except Exception as e:
            logger.error(f"Booking failed: {e}")
            return f"Sorry, I couldn't book the meeting: {str(e)}. Please try again."
