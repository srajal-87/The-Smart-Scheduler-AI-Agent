from flask import Flask, render_template, request, jsonify, session
import os
from dotenv import load_dotenv
from agent import SchedulerAgent
import secrets

load_dotenv()

# Initialize Flask app
app = Flask(__name__)
app.secret_key = secrets.token_hex(16)

# Initialize the scheduler agent
scheduler_agent = SchedulerAgent()

@app.route('/')
def index():
    """Main chat interface"""
    return render_template('index.html')

@app.route('/chat', methods=['POST'])
def chat():
    """Handle chat messages"""
    try:
        data = request.get_json()
        user_message = data.get('message', '')
        
        # Get or create session ID for state management
        if 'session_id' not in session:
            session['session_id'] = secrets.token_hex(8)
        
        session_id = session['session_id']
        
        # Process message with the agent
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

@app.route('/reset', methods=['POST'])
def reset_conversation():
    """Reset the conversation state"""
    if 'session_id' in session:
        scheduler_agent.reset_conversation(session['session_id'])
    return jsonify({'success': True})

if __name__ == '__main__':
    print("🤖 Smart Scheduler AI Agent Starting...")
    print("📅 Make sure you have:")
    print("   - Gemini API key in .env file")
    print("   - credentials.json for Google Calendar")
    print("🌐 Access the chatbot at: http://localhost:5000")
    print("=" * 50)
    
    app.run(debug=True, host='0.0.0.0', port=5000)