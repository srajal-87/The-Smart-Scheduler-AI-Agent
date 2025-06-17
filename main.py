from flask import Flask, render_template, request, jsonify, session, send_file
from flask_cors import CORS
import os
import tempfile
import secrets
from dotenv import load_dotenv
from agent import SchedulerAgent
from audio_utils import transcribe_audio, synthesize_speech

load_dotenv()
app = Flask(__name__)
app.secret_key = secrets.token_hex(16)
CORS(app)  # Enable CORS for frontend access
scheduler_agent = SchedulerAgent()

@app.route('/')
def index():
    """Main chat interface"""
    return render_template('index.html')

@app.route('/chat', methods=['POST'])
def chat():
    """Handle text chat messages"""
    try:
        data = request.get_json()
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
    """Handle voice chat messages"""
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
        
        try:
            # Transcribe audio to text using Whisper
            transcript = transcribe_audio(temp_audio_path)
            
            if not transcript or transcript.strip() == '':
                return jsonify({
                    'response': 'Could not transcribe audio. Please try again.',
                    'success': False
                })
            text_response = scheduler_agent.process_message(transcript, session_id)

            # Create temporary file for TTS output
            with tempfile.NamedTemporaryFile(delete=False, suffix='.mp3') as temp_tts: 
                tts_output_path = temp_tts.name
            
            audio_path = synthesize_speech(text_response, tts_output_path)
            with open(audio_path, 'rb') as audio_file:
                audio_data = audio_file.read()
            
            return jsonify({
                'transcript': transcript,
                'response': text_response,
                'audio_data': audio_data.hex(),  # Convert to hex for JSON serialization
                'success': True
            })
            
        except Exception as stt_tts_error:
            return jsonify({
                'response': f'Speech processing error: {str(stt_tts_error)}',
                'success': False
            }), 500
            
        finally:
            # Clean up temporary files
            try:
                if os.path.exists(temp_audio_path):
                    os.unlink(temp_audio_path)
                if 'tts_output_path' in locals() and os.path.exists(tts_output_path):
                    os.unlink(tts_output_path)
                if 'audio_path' in locals() and os.path.exists(audio_path):
                    os.unlink(audio_path)
            except OSError:
                pass  
                
    except Exception as e:
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