import os
import logging
import requests
import whisper
from pydub import AudioSegment
from voice_config import (
    ELEVENLABS_API_KEY, 
    VOICE_ID, 
    SAMPLE_RATE, 
    TTS_TIMEOUT,
    ELEVENLABS_BASE_URL,
    TTS_VOICE_SETTINGS,
    WHISPER_MODEL,
    MAX_AUDIO_SIZE_MB,
    SUPPORTED_AUDIO_FORMATS
)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load Whisper model once at module level for efficiency
try:
    whisper_model = whisper.load_model(WHISPER_MODEL)
    logger.info(f"Whisper {WHISPER_MODEL} model loaded successfully")
except Exception as e:
    logger.error(f"Failed to load Whisper model: {e}")
    whisper_model = None


def transcribe_audio(filepath):
    if not whisper_model:
        logger.error("Whisper model not available")
        return ""
    try:
        if not os.path.exists(filepath):
            logger.error(f"Audio file not found: {filepath}")
            return ""
        file_size_mb = os.path.getsize(filepath) / (1024 * 1024)
        if file_size_mb > MAX_AUDIO_SIZE_MB:
            logger.error(f"Audio file too large: {file_size_mb:.1f}MB (max: {MAX_AUDIO_SIZE_MB}MB)")
            return ""
        
        # Validate file format
        file_ext = os.path.splitext(filepath)[1].lower()
        if file_ext not in SUPPORTED_AUDIO_FORMATS:
            logger.warning(f"Unsupported audio format: {file_ext}")
        
        normalized_path = _normalize_audio(filepath)  # Normalize audio before transcription
        logger.info(f"Transcribing audio: {os.path.basename(filepath)}")
        result = whisper_model.transcribe(normalized_path)
        
        # Clean up normalized file if it's different from original
        if normalized_path != filepath and os.path.exists(normalized_path):
            try:
                os.unlink(normalized_path)
            except OSError:
                pass

        transcript = result.get('text', '').strip()
        if transcript:
            logger.info(f"Transcription successful: '{transcript[:50]}...'")
            return transcript
        else:
            logger.warning("Transcription returned empty text")
            return ""
            
    except Exception as e:
        logger.error(f"Transcription failed: {e}")
        return ""


def synthesize_speech(text, output_path):
    if not ELEVENLABS_API_KEY:
        logger.error("ElevenLabs API key not configured")
        return None
    if not text or not text.strip():
        logger.error("No text provided for synthesis")
        return None
    
    try:
        # Prepare API request
        url = f"{ELEVENLABS_BASE_URL}/text-to-speech/{VOICE_ID}"
        headers = {
            "Accept": "audio/mpeg",
            "Content-Type": "application/json",
            "xi-api-key": ELEVENLABS_API_KEY
        }
        payload = {
            "text": text.strip(),
            "model_id": "eleven_monolingual_v1",
            "voice_settings": TTS_VOICE_SETTINGS
        }
        
        logger.info(f"Synthesizing speech: '{text[:50]}...'")
        
        # Make API request
        response = requests.post(
            url, 
            json=payload, 
            headers=headers, 
            timeout=TTS_TIMEOUT
        )
        
        if response.status_code == 200:
            with open(output_path, 'wb') as f:
                f.write(response.content)
            logger.info(f"Speech synthesis successful: {os.path.basename(output_path)}")
            return output_path
        else:
            logger.error(f"ElevenLabs API error: {response.status_code} - {response.text}")
            return None
            
    except requests.exceptions.Timeout:
        logger.error("TTS request timed out")
        return None
    except requests.exceptions.RequestException as e:
        logger.error(f"TTS request failed: {e}")
        return None
    except Exception as e:
        logger.error(f"Speech synthesis failed: {e}")
        return None

def _normalize_audio(filepath):
    try:
        audio = AudioSegment.from_file(filepath)
        
        # Normalize audio settings for Whisper
        audio = audio.set_frame_rate(SAMPLE_RATE) 
        audio = audio.set_channels(1)  # Mono audio
        audio = audio.set_sample_width(2)  # 16-bit depth
        
        audio = audio.normalize()  
        audio = audio.strip_silence(silence_thresh=-40)
        
        # If original file is already WAV with correct settings, return as-is
        file_ext = os.path.splitext(filepath)[1].lower()
        if (file_ext == '.wav' and 
            audio.frame_rate == SAMPLE_RATE and 
            audio.channels == 1):
            return filepath
        
        # Create normalized temporary file
        normalized_path = filepath.rsplit('.', 1)[0] + '_normalized.wav'
        audio.export(normalized_path, format="wav")
        
        logger.info(f"Audio normalized: {os.path.basename(normalized_path)}")
        return normalized_path
        
    except Exception as e:
        logger.warning(f"Audio normalization failed, using original: {e}")
        return filepath