from flask import Flask, request, jsonify, send_from_directory, render_template
import requests
import os

app = Flask(__name__)

# Define a route for the home page that renders index.html
@app.route('/')
def home():
    return render_template('index.html')


# Endpoint to process voice assistant requests
@app.route('/process', methods=['POST'])
def process_input():
    data = request.get_json()
    user_text = data.get('text', '')
    
    # Send the user text to the Rasa server
    rasa_url = 'http://localhost:5005/webhooks/rest/webhook'
    rasa_payload = {"sender": "user1", "message": user_text}
    response = requests.post(rasa_url, json=rasa_payload)
    rasa_response = response.json()
    
    # For simplicity, pick the first text response from Rasa
    response_text = rasa_response[0].get('text', 'Sorry, I did not understand that.')
    
    # Generate TTS audio using Kokoro (for now, we simulate this)
    audio_url = generate_tts_audio(response_text)
    
    return jsonify({
        "response": response_text,
        "audioUrl": audio_url
    })

def generate_tts_audio(text):
    """
    Replace this dummy implementation with the actual Kokoro TTS call.
    For now, assume you have a pre-generated audio file in the static folder.
    """
    # For the MVP, use a static audio file (ensure 'static/response.wav' exists)
    return "/static/response.wav"

# Serve static files (like the audio file)
@app.route('/static/<path:filename>')
def static_files(filename):
    return send_from_directory('static', filename)

if __name__ == '__main__':
    app.run(debug=True, port=5000)
