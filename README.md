# Smart Scheduler AI Agent 🤖📅

A conversational AI assistant that helps users schedule meetings through natural language interactions, supporting both text and voice input. The agent integrates with Google Calendar to find available time slots and book meetings automatically.

## 🌟 Features

- **Natural Language Processing**: Understands scheduling requests in plain English
- **Voice & Text Support**: Complete voice-to-voice conversations or traditional text chat
- **Google Calendar Integration**: Real-time availability checking and event creation
- **Multi-turn Conversations**: Maintains context throughout the scheduling process
- **Smart Entity Extraction**: Automatically extracts dates, times, durations, and meeting details
- **Timezone Support**: Configured for IST (Indian Standard Time) with proper timezone handling

## 🏗️ Architecture Overview

### Core Components

1. **Agent (agent.py)**: The brain of the system
   - Uses Google's Gemini AI for natural language understanding
   - Manages conversation state and flow
   - Extracts entities (duration, date, time) from user input
   - Coordinates between different services

2. **Calendar Service (calendar_service.py)**: Google Calendar integration
   - Authenticates with Google Calendar API
   - Finds available time slots based on user preferences
   - Creates calendar events with proper timezone handling

3. **Audio Processing (audio_utils.py)**: Voice interaction capabilities
   - Uses OpenAI Whisper for speech-to-text (local processing)
   - Integrates ElevenLabs API for high-quality text-to-speech
   - Optimized for low latency with async processing

4. **Flask API (main.py)**: Web service layer
   - Provides REST endpoints for text and voice interactions
   - Manages user sessions
   - Handles file uploads and audio processing

### Design Philosophy

**Conversational Flow**: The agent follows a natural conversation pattern:
1. Understand user intent
2. Collect required information (duration, date, time)
3. Search calendar for availability
4. Present options to user
5. Confirm selection and book meeting

**State Management**: Each user session maintains conversation state including:
- Required fields (duration, date, time)
- Available time slots
- Selected slot and confirmation status
- Conversation history for context

**Async Processing**: Voice interactions use async processing to handle transcription and TTS simultaneously for better performance.

## 🚀 Setup Instructions

### Prerequisites

- Python 3.8 or higher
- Google Cloud Console account
- ElevenLabs API account (for voice features)
- Google AI Studio API key (for Gemini)

### 1. Clone and Install Dependencies

```bash
git clone <repository-url>
cd smart-scheduler-ai
pip install -r requirements.txt
```

### 2. Google Calendar API Setup

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing one
3. Enable the Google Calendar API
4. Create credentials (Desktop Application)
5. Download the credentials file and save as `credentials.json` in project root

### 3. API Keys Configuration

Create a `.env` file in the project root:

```env
# Google AI Studio (Gemini)
GEMINI_API_KEY=your_gemini_api_key_here

# ElevenLabs (for voice synthesis)
ELEVENLABS_API_KEY=your_elevenlabs_api_key_here
VOICE_ID=EXAVITQu4vr4xnSDxMaL

# Optional: Customize voice settings
# VOICE_ID=your_preferred_voice_id
```

#### Getting API Keys:

**Gemini API Key:**
1. Visit [Google AI Studio](https://aistudio.google.com/)
2. Create a new API key
3. Copy the key to your `.env` file

**ElevenLabs API Key:**
1. Sign up at [ElevenLabs](https://elevenlabs.io/)
2. Go to your profile settings
3. Generate an API key
4. Copy to your `.env` file

### 4. Audio Dependencies (for voice features)

Install system audio dependencies:

**Ubuntu/Debian:**
```bash
sudo apt-get install ffmpeg portaudio19-dev
```

**macOS:**
```bash
brew install ffmpeg portaudio
```

**Windows:**
- Download FFmpeg from [ffmpeg.org](https://ffmpeg.org/download.html)
- Add to system PATH

### 5. First Run Setup

1. Run the application:
```bash
python main.py
```

2. On first run, you'll be redirected to Google OAuth consent screen
3. Grant calendar access permissions
4. A `token.pickle` file will be created for future authentication

### 6. Access the Application

- **Web Interface**: Open `http://localhost:5000` in your browser
- **API Endpoints**:
  - POST `/chat` - Text-based conversations
  - POST `/voice-chat` - Voice-based conversations
  - POST `/reset` - Reset conversation state

## 📱 Usage Examples

### Text Conversation Flow

```
User: "I need to schedule a meeting"
Agent: "Sure! How long should the meeting be?"

User: "1 hour tomorrow afternoon"
Agent: "Got it - 1 hour meeting tomorrow afternoon. Let me check your calendar..."
Agent: "I found these available 60-minute slots on Tuesday, June 26:
1. 2:00 PM - 3:00 PM IST
2. 3:30 PM - 4:30 PM IST
3. 4:00 PM - 5:00 PM IST
Which slot would you prefer?"

User: "I'll take option 2"
Agent: "Great choice! What would you like to name this meeting?"

User: "Team standup"
Agent: "Perfect! Let me confirm:
Title: Team standup
Date: Tuesday, June 26
Time: 3:30 PM - 4:30 PM IST
Duration: 60 minutes
Should I book this meeting?"

User: "Yes"
Agent: "Meeting booked successfully! Event ID: abc123..."
```

### Voice Interaction

1. Click the microphone button
2. Speak your request: *"Schedule a 30-minute meeting for tomorrow morning"*
3. The agent will transcribe, process, and respond with voice
4. Continue the conversation naturally until booking is complete

## 🔧 Configuration Options

### Voice Settings (voice_config.py)

```python
# Whisper model size (speed vs accuracy trade-off)
WHISPER_MODEL = 'tiny'  # Options: tiny, base, small, medium, large

# TTS Voice settings
TTS_VOICE_SETTINGS = {
    'stability': 0.5,        # Voice consistency
    'similarity_boost': 0.5, # Voice similarity to original
    'style': 0.0,           # Style exaggeration
    'use_speaker_boost': True
}

# Performance settings
TTS_TIMEOUT = 8              # API timeout in seconds
MAX_AUDIO_SIZE_MB = 25       # Maximum audio file size
SAMPLE_RATE = 16000          # Audio sample rate
```

### Calendar Settings (calendar_service.py)

```python
# Business hours for slot generation
time_blocks = {
    'morning': (9, 12),      # 9 AM - 12 PM
    'afternoon': (12, 17),   # 12 PM - 5 PM  
    'evening': (17, 20),     # 5 PM - 8 PM
    'any': (9, 18)          # 9 AM - 6 PM
}

# Timezone
default_timezone = pytz.timezone('Asia/Kolkata')  # IST
```

## 🐛 Troubleshooting

### Common Issues

**1. "Gemini API Key not found"**
- Ensure `GEMINI_API_KEY` is set in your `.env` file
- Verify the API key is valid and has quota remaining

**2. "Google Calendar authentication failed"**
- Delete `token.pickle` and re-authenticate
- Ensure `credentials.json` is in the project root
- Check that Calendar API is enabled in Google Cloud Console

**3. "ElevenLabs API error"**
- Verify `ELEVENLABS_API_KEY` in `.env` file
- Check your ElevenLabs account quota
- Ensure the `VOICE_ID` exists in your account

**4. "Whisper model loading failed"**
- Install missing audio dependencies (ffmpeg, portaudio)
- Try a different model size in `voice_config.py`
- Check available disk space (models are 40MB-3GB)

**5. "No available slots found"**
- Check if the requested date is in the past
- Verify business hours configuration
- Ensure your calendar has free time during requested periods

### Performance Optimization

**For Faster Voice Processing:**
- Use `WHISPER_MODEL = 'tiny'` (fastest, less accurate)
- Reduce `TTS_TIMEOUT` for quicker failures
- Enable `USE_MEMORY_PROCESSING = True`

**For Better Accuracy:**
- Use `WHISPER_MODEL = 'base'` or `'small'`
- Increase `TTS_TIMEOUT` for more reliable API calls
- Enable `ENABLE_AUDIO_PREPROCESSING = True`

## 📝 API Reference

### Text Chat Endpoint

```http
POST /chat
Content-Type: application/json

{
    "message": "I need to schedule a 1-hour meeting tomorrow"
}
```

**Response:**
```json
{
    "response": "Sure! What time tomorrow works best for you?",
    "success": true
}
```

### Voice Chat Endpoint

```http
POST /voice-chat
Content-Type: multipart/form-data

audio: <audio-file>
```

**Response:**
```json
{
    "transcript": "I need to schedule a meeting",
    "response": "How long should the meeting be?",
    "audio_data": "hex-encoded-audio-data",
    "success": true
}
```

### Reset Conversation

```http
POST /reset
```

**Response:**
```json
{
    "success": true
}
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🙏 Acknowledgments

- Google AI Studio for Gemini API
- ElevenLabs for high-quality text-to-speech
- OpenAI for Whisper speech recognition
- Google Calendar API for scheduling integration

---

**Need help?** Open an issue on GitHub or check the troubleshooting section above.