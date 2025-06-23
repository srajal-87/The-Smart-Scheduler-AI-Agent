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


class ConversationState:
    """Manages the state of a scheduling conversation"""
    
    def __init__(self):
        # Required fields for booking
        self.meeting_duration = None
        self.preferred_date = None
        self.preferred_time = None
        self.parsed_date = None
        
        # Optional fields
        self.meeting_title = None
        
        # System state
        self.available_slots = []
        self.selected_slot = None
        self.conversation_history = []
        self.awaiting_confirmation = False
    
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
    
    def get_missing_required_fields(self) -> List[str]:
        """Return list of required fields that are still missing"""
        missing = []
        if not self.meeting_duration:
            missing.append('duration')
        if not self.parsed_date:
            missing.append('date')
        if not self.preferred_time:
            missing.append('time')
        return missing
    
    def is_ready_for_slots(self) -> bool:
        """Check if we have enough info to search for slots"""
        return len(self.get_missing_required_fields()) == 0
    
    def is_ready_for_booking(self) -> bool:
        """Check if we have selected a slot and ready to book"""
        return self.selected_slot is not None


class SchedulerAgent:
    """
    Intent-based scheduling agent that handles conversation flow and coordinates
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
        """Main entry point for processing user messages"""
        state = self._get_conversation_state(session_id)
        state.add_message('user', user_input, self.timezone)
        
        try:
            if self._is_restart_request(user_input):
                self.reset_conversation(session_id)
                state = self._get_conversation_state(session_id)
                response = "Let's start fresh! I'll help you schedule a new meeting. How long should the meeting be?"
            else:
                response = self._process_intent_and_state(user_input, state)
            
            state.add_message('assistant', response, self.timezone)
            return response
            
        except Exception as e:
            logger.error(f"Error processing message: {e}")
            return f"I encountered an error: {str(e)}. Please try again or say 'start over'."
    
    def _is_restart_request(self, user_input: str) -> bool:
        """Check if user wants to restart the conversation"""
        return any(keyword in user_input.lower() for keyword in self.RESTART_KEYWORDS)
    
    def _process_intent_and_state(self, user_input: str, state: ConversationState) -> str:
        """Process user input based on intent and current state"""
        # Extract all possible entities from user input
        entities = self._extract_all_entities(user_input, state)
        
        # Update state with any new entities
        self._update_state_with_entities(state, entities)
        
        # Determine primary intent and respond accordingly
        intent = entities.get('intent', 'unclear')
        
        # Handle specific intents
        if intent == 'greeting' or (not any([state.meeting_duration, state.parsed_date, state.preferred_time]) 
                                   and any(word in user_input.lower() for word in ['meeting', 'schedule', 'book'])):
            return self._handle_initial_request(state)
        
        elif intent == 'slot_selection' and entities.get('slot_number'):
            return self._handle_slot_selection(entities['slot_number'], state)
        
        elif intent == 'confirmation':
            return self._handle_confirmation(entities.get('confirmation'), state)
        
        # Default: determine next action based on state completion
        return self._determine_next_action(state)
    
    def _extract_all_entities(self, user_input: str, state: ConversationState) -> Dict[str, Any]:
        """Extract all possible entities from user input regardless of current state"""
        
        extraction_prompt = f"""
        Extract all structured information from the user's message for meeting scheduling.
        
        CURRENT STATE:
        - Duration: {state.meeting_duration or 'Not set'} minutes
        - Date: {state.preferred_date or 'Not set'}
        - Time: {state.preferred_time or 'Not set'}
        - Title: {state.meeting_title or 'Not set'}
        - Available slots: {len(state.available_slots)} options
        - Awaiting confirmation: {state.awaiting_confirmation}
        
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
    
    def _update_state_with_entities(self, state: ConversationState, entities: Dict[str, Any]):
        """Update conversation state with all valid entities"""
        
        # Update duration if valid
        if entities.get('duration_minutes') and self._is_valid_duration(entities['duration_minutes']):
            state.meeting_duration = entities['duration_minutes']
        
        # Update date if valid
        if entities.get('date_preference'):
            parsed_date = self._parse_date_with_gemini(entities['date_preference'])
            if parsed_date:
                state.preferred_date = entities['date_preference']
                state.parsed_date = parsed_date
        
        # Update time preference
        if entities.get('time_preference'):
            state.preferred_time = entities['time_preference']
        
        # Update meeting title
        if entities.get('meeting_title'):
            state.meeting_title = entities['meeting_title'].strip()
    
    def _determine_next_action(self, state: ConversationState) -> str:
        """Determine what to do next based on current state"""
        
        # If awaiting confirmation, ask for confirmation
        if state.awaiting_confirmation and state.selected_slot:
            return self._show_final_confirmation(state)
        
        # If ready to book, book the meeting
        if state.is_ready_for_booking():
            return self._book_meeting(state)
        
        # If we have slots available and waiting for selection
        if state.available_slots and not state.selected_slot:
            return self._format_available_slots(state.available_slots, state)
        
        # If ready to search for slots, do it
        if state.is_ready_for_slots():
            return self._search_and_show_slots(state)
        
        # Ask for missing required information
        missing_fields = state.get_missing_required_fields()
        
        if 'duration' in missing_fields:
            return f"How long should the meeting be? (e.g., 30 minutes, 1 hour)"
        elif 'date' in missing_fields:
            return f"What date would you prefer? (e.g., tomorrow, June 30, next Monday)"
        elif 'time' in missing_fields:
            date_str = state.parsed_date.strftime('%A, %B %d') if state.parsed_date else "that day"
            return f"What time do you prefer on {date_str}? (e.g., morning, 2 PM, any time)"
        
        return "I'm not sure what you need. Would you like to schedule a meeting?"
    
    def _handle_initial_request(self, state: ConversationState) -> str:
        """Handle initial meeting request"""
        missing_fields = state.get_missing_required_fields()
        
        if not missing_fields:
            return self._search_and_show_slots(state)
        elif len(missing_fields) == 3:  # All fields missing
            return "Great! I'll help you schedule a meeting. How long should the meeting be? (e.g., 30 minutes, 1 hour)"
        else:
            return self._determine_next_action(state)
    
    def _handle_slot_selection(self, slot_number: int, state: ConversationState) -> str:
        """Handle slot selection from available options"""
        if slot_number and 1 <= slot_number <= len(state.available_slots):
            selected_slot = state.available_slots[slot_number - 1]
            state.selected_slot = selected_slot
            state.awaiting_confirmation = True
            
            # If we don't have a title, ask for it; otherwise go to confirmation
            if not state.meeting_title:
                start_time = selected_slot['start']
                if start_time.tzinfo != self.timezone:
                    start_time = start_time.astimezone(self.timezone)
                
                date_str = start_time.strftime('%A, %B %d')
                time_str = start_time.strftime('%I:%M %p')
                
                return (
                    f"Great choice! I've selected {date_str} at {time_str}.\n\n"
                    f"What would you like to name this meeting? (or say 'skip' for a default name)"
                )
            else:
                return self._show_final_confirmation(state)
        else:
            return f"Please choose a number between 1 and {len(state.available_slots)}."
    
    def _handle_confirmation(self, confirmation: str, state: ConversationState) -> str:
        """Handle booking confirmation"""
        if confirmation == 'yes':
            return self._book_meeting(state)
        elif confirmation == 'no':
            # Reset slot selection and show slots again
            state.selected_slot = None
            state.awaiting_confirmation = False
            return "No problem! Here are the available slots again:\n\n" + self._format_available_slots(state.available_slots, state)
        else:
            return "Please reply 'yes' to confirm the booking or 'no' to see other options."
    
    # Existing helper methods (unchanged)
    
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
    
    def _show_final_confirmation(self, state: ConversationState) -> str:
        """Show final confirmation with all meeting details"""
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
            f"Title: {display_title}\n"
            f" Date: {date_str}\n"
            f"Time: {time_str} - {end_time_str} IST\n"
            f"Duration: {state.meeting_duration} minutes\n\n"
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
                # Reset state for new conversation
                state.reset()
                
                start_time = selected_slot['start']
                if start_time.tzinfo != self.timezone:
                    start_time = start_time.astimezone(self.timezone)
                
                date_str = start_time.strftime('%A, %B %d')
                time_str = start_time.strftime('%I:%M %p')
                
                return (
                    f"Meeting booked successfully!\n\n"
                    f"Title: {meeting_title}\n"
                    f"Date: {date_str}\n"
                    f"Time: {time_str} IST\n"
                    f"Duration: {state.meeting_duration} minutes\n\n"
                    f"Event ID: {event_id}\n"
                    f"The meeting has been added to your calendar. Need to schedule another meeting?"
                )
            else:
                return "I had trouble booking the meeting. Please try again."
                
        except Exception as e:
            logger.error(f"Booking failed: {e}")
            return f"Sorry, I couldn't book the meeting: {str(e)}. Please try again."