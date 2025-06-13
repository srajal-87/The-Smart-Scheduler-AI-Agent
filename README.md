# Smart Scheduler AI Agent 🤖📅

An intelligent meeting scheduling assistant that combines the power of Google's Gemini AI with Google Calendar integration to provide seamless, conversational meeting booking through natural language processing.

## 📌 Project Overview

The **Smart Scheduler AI Agent** is an AI-powered meeting scheduler that understands natural language and automates the entire meeting booking process. Unlike traditional calendar tools that require manual input, this agent engages users in conversational dialogue to gather meeting requirements, checks real-time calendar availability, and books meetings automatically.

### What Makes It Intelligent

- **Large Language Model Integration**: Powered by Google's Gemini AI for natural language understanding
- **Context Awareness**: Maintains conversation state across multiple interactions
- **Multi-turn Dialogue**: Guides users through a structured conversation flow
- **Real-time Calendar Integration**: Accesses live Google Calendar data for accurate availability
- **Smart Entity Extraction**: Parses complex scheduling requests from casual language
- **Timezone Intelligence**: Handles timezone conversions and displays times in IST

## ⚙️ How It Works

The Smart Scheduler follows an intelligent conversation flow:

### 1. **Natural Language Processing**
- User inputs scheduling requests in plain English
- Gemini AI extracts entities (duration, date preferences, time slots)
- Agent maintains conversation context and state

### 2. **Information Gathering**
```
User: "I need a 90-minute meeting next Tuesday afternoon"
Agent: Extracts → Duration: 90 min, Date: Next Tuesday, Time: Afternoon
```

### 3. **Calendar Integration**
- Connects to user's Google Calendar via Google Calendar API
- Searches for available time slots based on preferences
- Filters out existing appointments and conflicts

### 4. **Slot Presentation**
- Presents numbered options of available time slots
- Shows date, time range, and timezone (IST)
- Allows easy selection through natural language

### 5. **Booking Confirmation**
- Collects meeting title/subject
- Shows final confirmation with all details
- Creates calendar event with reminders

### Conversation Flow Example:
```
User: "Book a meeting for tomorrow"
Agent: "How long should the meeting be?"
User: "1 hour"
Agent: "What time do you prefer?"
User: "Morning"
Agent: "I found these slots: 1. 9:00-10:00 AM, 2. 10:30-11:30 AM..."
User: "Option 1"
Agent: "What would you like to call this meeting?"
User: "Team Standup"
Agent: "Confirm: Team Standup, Tomorrow 9:00-10:00 AM IST?"
User: "Yes"
Agent: "✅ Meeting booked successfully!"
```

## 🚀 Setup Instructions

### Prerequisites
- Python 3.8+
- Google Cloud Console account
- Gemini API access
- Google Calendar API credentials

### Step-by-Step Setup

#### 1. Clone the Repository
```bash
git clone https://github.com/yourusername/Smart-Scheduler-AI-Agent.git
cd Smart-Scheduler-AI-Agent
```

#### 2. Create Virtual Environment
```bash
python -m venv scheduler_env
source scheduler_env/bin/activate  # On Windows: scheduler_env\Scripts\activate
```

#### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

#### 4. Set Up Environment Variables
Create a `.env` file in the project root:
```env
GEMINI_API_KEY=your_gemini_api_key_here
```

#### 5. Google Calendar Setup
1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing
3. Enable Google Calendar API
4. Create credentials (OAuth 2.0 Client ID)
5. Download credentials as `credentials.json`
6. Place `credentials.json` in the project root

#### 6. Run the Application
```bash
python main.py
```

#### 7. Access the Agent
Open your browser and navigate to:
```
http://localhost:5000
```

### First-Time Authentication
- On first run, the app will open a browser window for Google Calendar authentication
- Grant necessary permissions
- A `token.pickle` file will be created for future sessions

## 📂 Project Structure

```
Smart-Scheduler-AI-Agent/
├── main.py                 # Main Flask application
├── agent.py                # Core AI agent logic and conversation flow
├── calendar_service.py     # Google Calendar API integration
├── prompts.py              # AI system prompts and templates
├── requirements.txt        # Python dependencies
├── .env                    # Environment variables (API keys)
├── credentials.json        # Google Calendar OAuth credentials
├── token.pickle            # Google auth token (generated after first login)
├── templates/
│   └── index.html          # Simple web chat interface
└── static/
    ├── style.css           # Frontend styling
    └── script.js           # Chat interface JavaScript
```

## 📄 Backend Components

### `agent.py` - Core Intelligence
- **SchedulerAgent Class**: Main orchestrator handling conversation states
- **Multi-stage Conversation Flow**: Greeting → Duration → Date → Time → Slots → Title → Confirmation
- **Gemini Integration**: Natural language processing and entity extraction
- **Session Management**: Maintains user context across interactions
- **Error Handling**: Graceful fallbacks for parsing failures

### `calendar_service.py` - Calendar Integration
- **CalendarService Class**: Google Calendar API wrapper
- **Authentication Management**: OAuth2 flow and token handling
- **Slot Finding**: Intelligent time slot discovery based on preferences
- **Event Creation**: Meeting booking with customizable details
- **Conflict Detection**: Prevents double-booking by checking existing events

### `prompts.py` - AI Instruction Templates
- **System Prompts**: Detailed instructions for Gemini's behavior
- **Conversation Guidelines**: Response formatting and tone specifications
- **Entity Extraction Templates**: Structured prompts for parsing user input
- **Error Handling Instructions**: Graceful failure and recovery patterns

### `main.py` - Web Interface
- **Flask Application**: RESTful API endpoints for chat functionality
- **Session Management**: User state persistence across web sessions
- **Route Handlers**: Chat processing and conversation reset endpoints
- **Error Handling**: API error responses and user feedback

## 🔧 Key Features

- ✅ **Conversational Interface**: Natural language scheduling requests
- ✅ **Real-time Calendar Access**: Live availability checking
- ✅ **Smart Time Parsing**: "Tomorrow afternoon", "next Monday morning", etc.
- ✅ **Conflict Prevention**: Automatic busy time detection
- ✅ **Meeting Titles**: Customizable event names and descriptions
- ✅ **Timezone Support**: IST timezone handling with proper conversions
- ✅ **Multi-user Support**: Session-based conversation state management
- ✅ **Error Recovery**: Graceful handling of API failures and user mistakes

## 🎯 Use Cases

- **Personal Scheduling**: Quick meeting setup for individuals
- **Team Coordination**: Streamlined internal meeting booking
- **Client Appointments**: Professional appointment scheduling
- **Interview Scheduling**: Automated interview slot management
- **Educational Sessions**: Class and tutoring session booking

## 🔒 Security & Privacy

- OAuth2 authentication for secure Google Calendar access
- API keys stored in environment variables
- Session-based user state (no persistent data storage)
- Minimal permission scope (Calendar read/write only)

## 🚀 Future Enhancements

- **Multi-participant Scheduling**: Find common availability across multiple calendars
- **Smart Rescheduling**: AI-powered conflict resolution
- **Integration Expansion**: Zoom, Teams, Slack integration
- **Voice Interface**: Speech-to-text scheduling requests
- **Mobile App**: Native iOS/Android applications

---

**Built with**: Python, Flask, Google Gemini AI, Google Calendar API, Natural Language Processing