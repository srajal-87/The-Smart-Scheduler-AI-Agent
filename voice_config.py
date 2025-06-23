import os
from dotenv import load_dotenv

load_dotenv()

# ElevenLabs API Configuration
ELEVENLABS_API_KEY = os.getenv('ELEVENLABS_API_KEY')
VOICE_ID = os.getenv('VOICE_ID', 'EXAVITQu4vr4xnSDxMaL') 

# Audio Processing Settings - Optimized for Speed
SAMPLE_RATE = 16000 
OUTPUT_AUDIO_FORMAT = 'mp3' 
WHISPER_MODEL = 'tiny'  # Much faster ~40MB model instead of base ~150MB

# API Configuration - Aggressive timeouts for low latency
TTS_TIMEOUT = 8 
ELEVENLABS_BASE_URL = 'https://api.elevenlabs.io/v1'

# Audio Quality Settings - Optimized for speed
TTS_VOICE_SETTINGS = {
    'stability': 0.5,
    'similarity_boost': 0.5,
    'style': 0.0,
    'use_speaker_boost': True
}

# Performance Optimizations
MAX_AUDIO_SIZE_MB = 25
SUPPORTED_AUDIO_FORMATS = ['.wav', '.mp3', '.m4a', '.flac', '.ogg']
SKIP_NORMALIZATION_FORMATS = ['.wav']  
ENABLE_AUDIO_PREPROCESSING = True  # Flag to enable/disable normalization
WHISPER_WARMUP_TEXT = "Hello, this is a test."  # Text for model warmup

# Memory processing settings
USE_MEMORY_PROCESSING = True  # Process audio in memory when possible
CLEANUP_DELAY = 0.1  # Minimal delay for file cleanup

# Connection optimization
CONNECTION_POOL_SIZE = 5  # For potential connection pooling