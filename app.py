from flask import Flask, request, jsonify, send_from_directory, render_template
import requests
from kokoro import KPipeline
import soundfile as sf
import numpy as np
import os
os.environ['SQLALCHEMY_SILENCE_UBER_WARNING'] = '1' # ignore sqlalchemy warnings


app = Flask(__name__)

# Initialize TTS pipeline globally
pipeline = KPipeline(lang_code='a')  # 'a' = American English 

# Rendering index.html
@app.route('/')
def home():
    return render_template('index.html')

# Endpoint to process voice assistant requests
@app.route('/process', methods=['POST'])
def process_request():
    try:
        # Call the actual processing logic
        response_data = process_input()
        return response_data  # This will return the response from process_input()
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500 # if not successful


# Receives a JSON file containing user text from the client
# Sends user text to the Rasa  and extracts the response text
# Generates TTS audio using Kokoro and returns the response (text & audio)
def process_input():
  
    data = request.get_json() # reads incoming JSON data
    user_text = data.get('text', '') # extract test of user
    
    # Send the user text to the Rasa server
    rasa_url = 'http://localhost:5005/webhooks/rest/webhook'
    rasa_payload = {"sender": "user1", "message": user_text}
    response = requests.post(rasa_url, json=rasa_payload) # send message & sender id
    rasa_response = response.json() # convert rasa response from JSON to python object

    print(f"Rasa response: {rasa_response}")  # Log the response for debugging

    if not rasa_response or not rasa_response[0].get('text'):
        response_text = 'Sorry, I did not understand that.'  # Fallback for empty or invaöld response from Rasa
    else:
        response_text = rasa_response[0].get('text')
        
    # For simplicity, pick the first text response from Rasa
    #response_text = rasa_response[0].get('text', 'Sorry, I did not understand that.') 
    # Extract all text responses from Rasa; if response is empty, default to "Sorry, I didn't understand that."
   # response_text = " ".join([msg.get('text', '') for msg in rasa_response if 'text' in msg]) or "Sorry, I didn't understand that."


    
    # Generate TTS audio using Kokoro, returns path to generated .wav audio file
    audio_url = generate_tts_audio(response_text)

    return jsonify({
        "response": response_text,
        "audioUrl": audio_url if audio_url else None  # Return None if TTS failed
    })

def generate_tts_audio(text):
    """
    Generate TTS audio using Kokoro and save it to a file.
    """
    try:
        # Generate audio from text using Kokoro TTS
        generator = pipeline(text, voice='af_heart', speed=0.9)

        audio_filename = 'static/response.wav'
        all_audio = []  # Store all chunks

        # Extract and store all audio data
        for gs, ps, audio in generator:
            all_audio.append(audio)

        if all_audio:
            # Concatenate all chunks into a single array
            full_audio = np.concatenate(all_audio)
            sf.write(audio_filename, full_audio, 24000)
            return '/static/response.wav'
        #You might instead write each chunk directly to disk 
        #(if your TTS engine supports streaming or if you can process data in chunks), reducing peak memory usage.
        else:
            print("No audio generated.")
            return None  # Handle case where no audio is generated

    except Exception as e:
        print(f"Error generating audio: {e}")
        return None  # Return None if TTS fails

if __name__ == '__main__':
    app.run(debug=True, port=5000)
