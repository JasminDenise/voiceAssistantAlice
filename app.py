from flask import Flask, request, jsonify, render_template
import requests
from kokoro import KPipeline
import soundfile as sf
import numpy as np
from flask_cors import CORS

# Initialize Flask app
app = Flask(__name__)
CORS(app) # Allow all origins

# Initialize Kokoro Text-to-Speech pipeline (American English)
pipeline = KPipeline(lang_code='a')  # 'a' = American English voice model

# ---------------------------------------------
# Route: Homepage - renders the frontend HTML
# ---------------------------------------------
@app.route('/')
def home():
    return render_template('index.html')


# --------------------------------------------------------
# Route: /process (POST) - handles voice assistant logic
# --------------------------------------------------------
@app.route('/process', methods=['POST'])
def process_request():
    try:
        response_data = process_input()
        return response_data  # Returns JSON response with text and audio
    except Exception as e:
        # Handles unexpected server-side errors
        return jsonify({"status": "error", "message": str(e)}), 500


# ----------------------------------------------------------------------
# Logic: process_input() handles interaction with Rasa & Kokoro
# ----------------------------------------------------------------------
def process_input():
    # Extract user input from incoming request
    data = request.get_json()
    user_text = data.get('text', '').strip()

    if not user_text:
        return jsonify({"response": "Sorry, I didn't catch anything.", "audioUrl": None})

    # Send input to Rasa server for NLU and dialog management
    rasa_url = 'http://localhost:5005/webhooks/rest/webhook'
    rasa_payload = {
        "sender": "user1",  # Unique user session ID
        "message": user_text
    }

    try:
        rasa_response = requests.post(rasa_url, json=rasa_payload).json()
    except Exception as e:
        print("Error contacting Rasa:", e)
        return jsonify({
            "response": "There was a problem processing your request. Please try again.",
            "audioUrl": None
        })

    # Fallback if Rasa does not return a valid text response
    if not rasa_response or not rasa_response[0].get('text'):
        response_text = 'Sorry, I did not understand that. What did you say?'
    else:
        # Take the first valid text response from Rasa
        response_text = rasa_response[0].get('text')

    print(f"Rasa response: {response_text}")  # For debugging 

    # Convert response text to speech (TTS) using Kokoro
    audio_url = generate_tts_audio(response_text)

    # Return JSON with both text and audio file path
    return jsonify({
        "response": response_text,
        "audioUrl": audio_url if audio_url else None
    })


# ----------------------------------------------------------------------
# TTS: generate_tts_audio() uses Kokoro to generate a WAV audio file
# ----------------------------------------------------------------------
def generate_tts_audio(text):
    try:
        # Voice parameters: slower speed for clearer pronunciation
        generator = pipeline(text, voice='af_heart', speed=0.9)

        audio_filename = 'static/response.wav'
        all_audio_chunks = []

        # Collect all audio chunks generated
        for _, _, audio in generator:
            all_audio_chunks.append(audio)

        # Combine all chunks into one wav file
        if all_audio_chunks:
            full_audio = np.concatenate(all_audio_chunks)
            sf.write(audio_filename, full_audio, 24000)  # Save with 24kHz sample rate
            return '/static/response.wav'
        else:
            print("TTS returned no audio.")
            return None

    except Exception as e:
        print(f"Error generating TTS audio: {e}")
        return None


# -------------------------
# Main entry point
# -------------------------
if __name__ == '__main__':
    # Runs the Flask app in debug mode (localhost:5000)
    app.run(debug=True, port=5000)
