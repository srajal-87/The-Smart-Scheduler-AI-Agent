import os
from dotenv import load_dotenv

load_dotenv()

# ElevenLabs API Configuration
ELEVENLABS_API_KEY = os.getenv('ELEVENLABS_API_KEY')
VOICE_ID = os.getenv('VOICE_ID', 'EXAVITQu4vr4xnSDxMaL')  # Default: Bella voice

# Audio Processing Settings
SAMPLE_RATE = 16000 
OUTPUT_AUDIO_FORMAT = 'mp3' 
WHISPER_MODEL = 'base' 

# API Configuration
TTS_TIMEOUT = 30  # seconds
ELEVENLABS_BASE_URL = 'https://api.elevenlabs.io/v1'

# Audio Quality Settings
TTS_VOICE_SETTINGS = {
    'stability': 0.5,
    'similarity_boost': 0.5,
    'style': 0.0,
    'use_speaker_boost': True
}

MAX_AUDIO_SIZE_MB = 25
SUPPORTED_AUDIO_FORMATS = ['.wav', '.mp3', '.m4a', '.flac', '.ogg']