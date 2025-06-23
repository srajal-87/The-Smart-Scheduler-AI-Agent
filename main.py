from flask import Flask, render_template, request, jsonify, session
from flask_cors import CORS
import os
import tempfile
import time
import secrets
import logging
import asyncio
from dotenv import load_dotenv
from agent import SchedulerAgent
from audio_utils import transcribe_audio_async, synthesize_speech_async, cleanup_temp_files

logger = logging.getLogger(__name__)

load_dotenv()
app = Flask(__name__)
app.secret_key = secrets.token_hex(16) # Sets a random 32-character secret key for Flask sessions.


CORS(app) # so frontend (e.g., React, JS) can call Flask API from a different domain/port 
scheduler_agent = SchedulerAgent()

@app.route('/')
def index():
    """Main chat interface"""
    return render_template('index.html')

@app.route('/chat', methods=['POST'])
def chat():
    """Handle text chat messages"""
    try:
        data = request.get_json() # Parses the JSON body from the incoming POST request
        user_message = data.get('message', '')
        if 'session_id' not in session:
            session['session_id'] = secrets.token_hex(8)
        
        session_id = session['session_id']
        response = scheduler_agent.process_message(user_message, session_id)
        return jsonify({
            'response': response,
            'success': True
        })
        
    except Exception as e:
        return jsonify({
            'response': f"Sorry, I encountered an error: {str(e)}",
            'success': False
        })

@app.route('/voice-chat', methods=['POST'])
def voice_chat():
    """Handle voice chat messages with optimized async processing"""
    temp_audio_path = None
    tts_output_path = None
    
    try:
        if 'audio' not in request.files:
            return jsonify({
                'response': 'No audio file provided',
                'success': False
            }), 400
        
        audio_file = request.files['audio']
        if audio_file.filename == '':
            return jsonify({
                'response': 'No audio file selected',
                'success': False
            }), 400
        
        if 'session_id' not in session:
            session['session_id'] = secrets.token_hex(8)
        
        session_id = session['session_id']
        
        # Create temporary file for audio processing
        with tempfile.NamedTemporaryFile(delete=False, suffix='.wav') as temp_audio:
            audio_file.save(temp_audio.name)
            temp_audio_path = temp_audio.name
        
        # Create temporary file for TTS output
        with tempfile.NamedTemporaryFile(delete=False, suffix='.mp3') as temp_tts:
            tts_output_path = temp_tts.name
        
        # Use async processing for better performance
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            # Transcribe audio to text
            transcript = loop.run_until_complete(
                transcribe_audio_async(temp_audio_path)
            )
            
            if not transcript or transcript.strip() == '':
                return jsonify({
                    'response': 'Could not transcribe audio. Please try again.',
                    'success': False
                })
            
            # Process the transcribed message
            text_response = scheduler_agent.process_message(transcript, session_id)
            
            # Generate speech response
            audio_path = loop.run_until_complete(
                synthesize_speech_async(text_response, tts_output_path)
            )
            
            if not audio_path or not os.path.exists(audio_path):
                return jsonify({
                    'transcript': transcript,
                    'response': text_response,
                    'success': False,
                    'error': 'Failed to generate audio response'
                })
            
            # Read audio data for response
            with open(audio_path, 'rb') as af:
                audio_data = af.read()
            
            # Clean up temporary files
            cleanup_temp_files(temp_audio_path, tts_output_path)
            
            return jsonify({
                'transcript': transcript,
                'response': text_response,
                'audio_data': audio_data.hex(),
                'success': True
            })
            
        finally:
            loop.close()
            
    except Exception as e:
        # Clean up files on error
        if temp_audio_path:
            cleanup_temp_files(temp_audio_path)
        if tts_output_path:
            cleanup_temp_files(tts_output_path)
            
        return jsonify({
            'response': f"Sorry, I encountered an error: {str(e)}",
            'success': False
        }), 500

@app.route('/reset', methods=['POST'])
def reset_conversation():
    """Reset the conversation state"""
    if 'session_id' in session:
        scheduler_agent.reset_conversation(session['session_id'])
    return jsonify({'success': True})

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)