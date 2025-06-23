import os
import tempfile
import threading
import time
import logging
from concurrent.futures import ThreadPoolExecutor
import asyncio
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
    SUPPORTED_AUDIO_FORMATS,
    SKIP_NORMALIZATION_FORMATS,
    ENABLE_AUDIO_PREPROCESSING,
    WHISPER_WARMUP_TEXT,
    USE_MEMORY_PROCESSING,
    CLEANUP_DELAY
)

logger = logging.getLogger(__name__)

# Module-level variables for model management
_whisper_model = None  #Initializes a module-level variable to store the Whisper model instance
_model_loaded = threading.Event() # Creates a thread-safe event flag to signal when the Whisper model has finished loading
_thread_pool = ThreadPoolExecutor(max_workers=2)  #Used to run transcription and TTS functions asynchronously without blocking the main thread


def _load_whisper_model():
    """Load Whisper model in background thread with warmup."""
    global _whisper_model
    
    try:
        logger.info("Loading Whisper %s model...", WHISPER_MODEL)
        _whisper_model = whisper.load_model(WHISPER_MODEL)
        logger.info("Whisper %s model loaded successfully", WHISPER_MODEL)
        
        # Warm up the model for better first-run performance
        if WHISPER_WARMUP_TEXT:
            _perform_model_warmup()  # pre-run a dummy transcription
                
    except Exception as e:
        logger.error("Failed to load Whisper model: %s", e)
        _whisper_model = None
    finally:
        _model_loaded.set()


def _perform_model_warmup():
    """Run a dummy transcription to warm up the model."""
    try:
        # Create minimal audio segment for warmup
        warmup_audio = AudioSegment.silent(duration=1000)
        warmup_audio = warmup_audio.set_frame_rate(SAMPLE_RATE).set_channels(1)
        
        # Use temporary file for warmup transcription
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_file:
            warmup_audio.export(temp_file.name, format="wav")
            warmup_path = temp_file.name
        
        # Perform quick warmup transcription
        _whisper_model.transcribe(warmup_path, fp16=False, verbose=False)
        
        # Clean up warmup file
        _cleanup_single_file(warmup_path)
        logger.info("Whisper model warmed up successfully")
        
    except Exception as e:
        logger.warning("Model warmup failed (non-critical): %s", e)


def wait_for_model(timeout=10):
    """Wait for model to load with specified timeout."""
    if not _model_loaded.wait(timeout):
        logger.error("Whisper model loading timed out")
        return False
    return _whisper_model is not None


def transcribe_audio(filepath):
    """ Transcribe audio file to text using optimized Whisper processing."""
    # Ensure model is ready before processing
    if not wait_for_model():
        logger.error("Whisper model not available")
        return ""
    
    try:
        if not os.path.exists(filepath):
            logger.error("Audio file not found: %s", filepath)
            return ""
            
        # Validate file size constraints
        file_size_mb = os.path.getsize(filepath) / (1024 * 1024)
        if file_size_mb > MAX_AUDIO_SIZE_MB:
            logger.error("Audio file too large: %.1fMB (max: %sMB)", 
                        file_size_mb, MAX_AUDIO_SIZE_MB)
            return ""
        
        # Determine if audio preprocessing is needed
        file_ext = os.path.splitext(filepath)[1].lower()
        needs_processing = (ENABLE_AUDIO_PREPROCESSING and 
                          file_ext not in SKIP_NORMALIZATION_FORMATS)
        
        if needs_processing:
            processed_path = _normalize_audio_file(filepath)
        else:
            processed_path = filepath
        
        # Perform the actual transcription
        result = _whisper_model.transcribe(processed_path, fp16=False, verbose=False)

        # Clean up processed file if it differs from original
        if processed_path != filepath and os.path.exists(processed_path):
            _cleanup_single_file(processed_path)

        transcript = result.get('text', '').strip()
        if transcript:
            return transcript
        else:
            logger.warning("Transcription returned empty text")
            return ""
            
    except Exception as e:
        logger.error("Transcription failed: %s", e)
        return ""


def synthesize_speech(text, output_path):
    """Convert text to speech using ElevenLabs API with optimized error handling."""
    if not ELEVENLABS_API_KEY:
        logger.error("ElevenLabs API key not configured")
        return None
        
    if not text or not text.strip():
        logger.error("No text provided for synthesis")
        return None
    
    try:
        # Prepare API request with optimized settings
        api_url = f"{ELEVENLABS_BASE_URL}/text-to-speech/{VOICE_ID}"
        request_headers = {
            "Accept": "audio/mpeg",
            "Content-Type": "application/json",
            "xi-api-key": ELEVENLABS_API_KEY
        }
        
        # Try turbo model first for faster processing
        request_payload = {
            "text": text.strip(),
            "model_id": "eleven_turbo_v2",
            "voice_settings": TTS_VOICE_SETTINGS
        }
        
        # Make API request with session for potential connection reuse
        with requests.Session() as session:
            response = session.post(
                api_url, 
                json=request_payload, 
                headers=request_headers, 
                timeout=TTS_TIMEOUT
            )
        
        if response.status_code == 200:
            # Save audio data to file
            with open(output_path, 'wb') as audio_file:
                audio_file.write(response.content)
            return output_path
            
        elif response.status_code == 422:
            # Fallback to standard model on validation error
            logger.warning("Turbo model failed, trying standard model")
            request_payload["model_id"] = "eleven_monolingual_v1"
            
            with requests.Session() as session:
                response = session.post(
                    api_url, 
                    json=request_payload, 
                    headers=request_headers, 
                    timeout=TTS_TIMEOUT
                )
                
            if response.status_code == 200:
                with open(output_path, 'wb') as audio_file:
                    audio_file.write(response.content)
                return output_path
        
        logger.error("ElevenLabs API error: %s - %s", response.status_code, response.text)
        return None
            
    except requests.exceptions.Timeout:
        logger.error("TTS request timed out after %s seconds", TTS_TIMEOUT)
        return None
    except requests.exceptions.RequestException as e:
        logger.error("TTS request failed: %s", e)
        return None
    except Exception as e:
        logger.error("Speech synthesis failed: %s", e)
        return None


def _normalize_audio_file(filepath):
    """Perform fast audio normalization with minimal processing overhead."""
    try:
        # Load audio file
        audio = AudioSegment.from_file(filepath)
        
        # Check if audio is already in optimal format
        if _is_audio_format_optimal(audio):
            return filepath
        
        # Apply only necessary format conversions
        normalized_audio = _convert_audio_format(audio)
            
        # Export normalized audio to temporary file
        normalized_path = filepath.rsplit('.', 1)[0] + '_fast_norm.wav'
        normalized_audio.export(normalized_path, format="wav")
        return normalized_path
        
    except Exception as e:
        logger.warning("Fast normalization failed, using original: %s", e)
        return filepath


def _is_audio_format_optimal(audio):
    """Check if audio segment is already in the optimal format."""
    return (audio.frame_rate == SAMPLE_RATE and 
            audio.channels == 1 and 
            audio.sample_width == 2)


def _convert_audio_format(audio):
    """Convert audio to optimal format with minimal processing."""
    if audio.frame_rate != SAMPLE_RATE:
        audio = audio.set_frame_rate(SAMPLE_RATE)
    if audio.channels != 1:
        audio = audio.set_channels(1) 
    if audio.sample_width != 2:
        audio = audio.set_sample_width(2)  # 16-bit depth
    return audio


def transcribe_audio_async(filepath):
    """Async wrapper for audio transcription using thread pool."""
    loop = asyncio.get_event_loop()
    return loop.run_in_executor(_thread_pool, transcribe_audio, filepath)


def synthesize_speech_async(text, output_path):
    """Async wrapper for speech synthesis using thread pool."""
    loop = asyncio.get_event_loop() # Gets the current event loop, which manages async tasks.
    return loop.run_in_executor(_thread_pool, synthesize_speech, text, output_path)


def _cleanup_single_file(filepath):
    """Clean up a single temporary file with error handling."""
    try:
        if filepath and os.path.exists(filepath):
            os.unlink(filepath)
    except OSError:
        pass

def cleanup_temp_files(*filepaths):
    """Clean up temporary files with configurable delay for safe deletion."""
    def perform_delayed_cleanup():
        if CLEANUP_DELAY > 0:
            time.sleep(CLEANUP_DELAY)
        
        for filepath in filepaths:
            _cleanup_single_file(filepath)
    
    # Execute cleanup in background thread to avoid blocking
    cleanup_thread = threading.Thread(
        target=perform_delayed_cleanup, 
        daemon=True # Makes the thread non-blocking and exit-safe
    )
    cleanup_thread.start()

# Initialize model loading when module is imported
_model_loading_thread = threading.Thread(
    target=_load_whisper_model, 
    daemon=True
)
_model_loading_thread.start()