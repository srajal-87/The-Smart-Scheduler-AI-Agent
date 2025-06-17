# Smart Scheduler AI Agent 🤖📅🎙️

An intelligent voice-enabled meeting scheduling assistant that combines the power of Google's Gemini AI with Google Calendar integration to provide seamless, conversational meeting booking through natural language processing and voice interaction.

## 📌 Project Overview

The **Smart Scheduler AI Agent** is an AI-powered meeting scheduler that understands natural language and voice commands, automating the entire meeting booking process through conversational dialogue. Unlike traditional calendar tools that require manual input, this agent engages users in both text and voice conversations to gather meeting requirements, checks real-time calendar availability, and books meetings automatically.

### What Makes It Intelligent

- **Large Language Model Integration**: Powered by Google's Gemini AI for natural language understanding
- **Voice-First Interface**: Complete speech-to-text and text-to-speech capabilities for hands-free scheduling
- **Context Awareness**: Maintains conversation state across multiple interactions
- **Multi-turn Dialogue**: Guides users through a structured conversation flow
- **Real-time Calendar Integration**: Accesses live Google Calendar data for accurate availability
- **Smart Entity Extraction**: Parses complex scheduling requests from casual language
- **Natural Voice Synthesis**: Human-like speech responses using ElevenLabs AI
- **Timezone Intelligence**: Handles timezone conversions and displays times in IST

## ⚙️ How It Works

The Smart Scheduler follows an intelligent conversation flow with full voice support:

### 1. **Voice & Natural Language Processing**
- User inputs scheduling requests in plain English (text or voice)
- Whisper AI transcribes speech to text with high accuracy
- Gemini AI extracts entities (duration, date preferences, time slots)
- Agent maintains conversation context and state

### 2. **Information Gathering**
```
User: "I need a 90-minute meeting next Tuesday afternoon"
Agent: 🔊 "Perfect! A 90-minute meeting on Tuesday afternoon. I found these available slots..."
```

### 3. **Calendar Integration**
- Connects to user's Google Calendar via Google Calendar API
- Searches for available time slots based on preferences
- Filters out existing appointments and conflicts

### 4. **Voice-Enabled Slot Presentation**
- Presents numbered options of available time slots
- Responds with synthesized speech for natural conversation
- Shows date, time range, and timezone (IST)
- Allows easy selection through voice commands

### 5. **Booking Confirmation**
- Collects meeting title/subject via voice or text
- Provides audio confirmation with all details
- Creates calendar event with reminders

### Voice Conversation Flow Example:
```
User: "Book a meeting for tomorrow"
Agent: 🔊 "How long should the meeting be?"
User:  "One hour"
Agent: 🔊 "What time do you prefer?"
User: "Morning"
Agent: 🔊 "I found these slots: Option 1, 9 to 10 AM, Option 2, 10:30 to 11:30 AM..."
User: "Option one"
Agent: 🔊 "What would you like to call this meeting?"
User:  "Team standup"
Agent: 🔊 "Perfect! Let me confirm: Team Standup, tomorrow 9 to 10 AM IST. Should I book this?"
User:  "Yes"
Agent: 🔊 "Meeting booked successfully! The meeting has been added to your calendar."
```

## 🚀 Setup Instructions

### Prerequisites
- Python 3.8+
- Google Cloud Console account
- Gemini API access
- Google Calendar API credentials
- ElevenLabs API account (for voice synthesis)

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
ELEVENLABS_API_KEY=your_elevenlabs_api_key_here
VOICE_ID=EXAVITQu4vr4xnSDxMaL  # Optional: Custom voice ID
```

#### 5. Google Calendar Setup
1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing
3. Enable Google Calendar API
4. Create credentials (OAuth 2.0 Client ID)
5. Download credentials as `credentials.json`
6. Place `credentials.json` in the project root

#### 6. ElevenLabs Voice Setup
1. Sign up at [ElevenLabs](https://elevenlabs.io/)
2. Get your API key from the dashboard
3. Optional: Clone or select a custom voice ID
4. Add credentials to your `.env` file

#### 7. Run the Application
```bash
python main.py
```

#### 8. Access the Agent
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
├── main.py                 # Main Flask application with voice endpoints
├── agent.py                # Core AI agent logic and conversation flow
├── audio_utils.py          # Voice processing: STT, TTS, audio normalization
├── voice_config.py         # Voice system configuration and settings
├── calendar_service.py     # Google Calendar API integration
├── prompts.py              # AI system prompts and templates
├── requirements.txt        # Python dependencies
├── .env                    # Environment variables (API keys)
├── credentials.json        # Google Calendar OAuth credentials
├── token.pickle            # Google auth token (generated after first login)
├── templates/
│   └── index.html          # Voice-enabled web chat interface
```

## 📄 Backend Components

### `agent.py` - Core Intelligence
- **SchedulerAgent Class**: Main orchestrator handling conversation states
- **Multi-stage Conversation Flow**: Greeting → Duration → Date → Time → Slots → Title → Confirmation
- **Gemini Integration**: Natural language processing and entity extraction
- **Session Management**: Maintains user context across voice/text interactions
- **Error Handling**: Graceful fallbacks for parsing failures

### `audio_utils.py` - Voice Processing Engine
- **Speech-to-Text**: Whisper AI integration for accurate transcription
- **Text-to-Speech**: ElevenLabs integration for natural voice synthesis
- **Audio Normalization**: Automatic audio preprocessing for optimal quality
- **Format Support**: Multiple audio formats (WAV, MP3, M4A, FLAC, OGG)
- **Error Recovery**: Robust handling of audio processing failures

### `voice_config.py` - Voice System Configuration
- **API Configuration**: ElevenLabs settings and voice parameters
- **Audio Quality Settings**: Sample rates, formats, and optimization
- **Voice Customization**: Stability, similarity, and style parameters
- **Performance Tuning**: Timeout settings and file size limits

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
- **Voice-Optimized Responses**: Instructions for natural speech patterns

### `main.py` - Voice-Enabled Web Interface
- **Flask Application**: RESTful API endpoints for chat and voice functionality
- **Voice Chat Endpoint**: `/voice-chat` for audio processing
- **Session Management**: User state persistence across voice/text sessions
- **Audio Processing**: Real-time transcription and synthesis
- **Error Handling**: Comprehensive audio and API error responses

## 🔧 Key Features

### Voice Interface
- 🎤 **Speech Recognition**: Advanced Whisper AI transcription
- 🔊 **Natural Speech Synthesis**: ElevenLabs AI voice generation
- 🎙️ **Real-time Processing**: Low-latency voice interaction
- 📱 **Cross-platform Audio**: Web-based voice recording and playback
- 🔄 **Seamless Mode Switching**: Switch between voice and text mid-conversation

### Core Scheduling
- ✅ **Conversational Interface**: Natural language scheduling requests
- ✅ **Real-time Calendar Access**: Live availability checking
- ✅ **Smart Time Parsing**: "Tomorrow afternoon", "next Monday morning", etc.
- ✅ **Conflict Prevention**: Automatic busy time detection
- ✅ **Meeting Titles**: Customizable event names and descriptions
- ✅ **Timezone Support**: IST timezone handling with proper conversions
- ✅ **Multi-user Support**: Session-based conversation state management
- ✅ **Error Recovery**: Graceful handling of API failures and user mistakes

---

**Built with**: Python, Flask, Google Gemini AI, Google Calendar API, Whisper AI, ElevenLabs AI, Natural Language Processing