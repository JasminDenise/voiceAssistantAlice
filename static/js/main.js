let recognition;

// Check if the browser supports the Web Speech API
const SpeechRecognition =
    window.SpeechRecognition || window.webkitSpeechRecognition;

if (!SpeechRecognition) {
  // If the browser does not support voice input, show an alert
  alert(
      'Your browser does not support Speech Recognition. Please use Chrome or Edge.');
} else {
  // Create a new instance of the Speech Recognition API
  recognition = new SpeechRecognition();

  // Set recognition settings
  recognition.lang = 'en-US';  // Recognize English (US)
  recognition.interimResults =
      false;  // Only return final results (not halfway guesses)
  recognition.maxAlternatives = 1;  // Return only one best match
  recognition.continuous = false;   // make sure each session only fires once

  // This function runs when speech is successfully recognized
  recognition.onresult = (event) => {
    // Get the text version of the spoken words
    // const transcript = event.results[0][0].transcript;
    // get only the newly finalized result
    const idx = event.resultIndex;
    const transcript = event.results[idx][0].transcript.trim();

    // Show the user's message in the chat
    addChatMessage('You:', transcript);

    // Send the text to the backend for processing by Rasa and Kokoro
    sendTextToBackend(transcript);
  };

  // This function runs when there's an error during speech recognition
  recognition.onerror = (event) => {
    console.error('Speech recognition error:', event.error);

    // Stop listening temporarily and prepare to restart
    console.log('Restarting speech recognition...');
    recognition.stop();
  };

  // This function runs when the user stops speaking
  recognition.onspeechend = () => {
    // Stop recognition to prepare for next message
    recognition.stop();
    console.log('Speech recognition has stopped.');
  };

  // Start listening when the "Start conversation" button is clicked
  document.getElementById('record-btn').addEventListener('click', () => {
    recognition.start();
  });
}


// --------------------------------------------
// Send the user's spoken text to the Flask backend
// --------------------------------------------
async function sendTextToBackend(text) {
  try {
    // Send the user's message to the Flask backend via POST request
    const response = await fetch('http://127.0.0.1:5000/process', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({text: text})  // Send the recognized text
    });

    // Get the reply from the backend (includes both text and audio)
    const data = await response.json();

    // Display the bot's text response in the chat
    addChatMessage('Alice:', data.response);

    // If there's an audio response, play it
    if (data.audioUrl) {
      playAudio(data.audioUrl);
    } else {
      // If there's no audio, start listening again
      if (!isRecognizing) recognition.start();
    }
  } catch (error) {
    console.error('Error sending text to backend:', error);
  }
}


// --------------------------------------------
// Add messages to the chat area on the page
// --------------------------------------------
function addChatMessage(sender, message) {
  const chatBox = document.getElementById('chat-box');

  // Create a container for the message
  const wrapper = document.createElement('div');
  const messageElement = document.createElement('p');
  messageElement.innerText = message;

  // Apply different styles depending on the sender (user or bot)
  if (sender === 'You:') {
    wrapper.className = 'chat-message user-message';
  } else {
    wrapper.className = 'chat-message bot-message';
  }

  // Add the message to the wrapper and chat box
  wrapper.appendChild(messageElement);
  chatBox.appendChild(wrapper);

  // Scroll chat to the latest message
  chatBox.scrollTop = chatBox.scrollHeight;
}


// --------------------------------------------
// Play the bot's response as audio
// --------------------------------------------
function playAudio(url) {
  if (!url) return;  // Don't do anything if there's no audio

  // Create a new audio object, adding a timestamp to prevent caching
  const audio = new Audio(url + '?t=' + new Date().getTime());

  audio.play()
      .then(() => {
        // When the audio finishes playing, restart listening
        audio.onended = () => {
          if (!isRecognizing) recognition.start();
        };
      })
      .catch(error => {
        // If there's an error playing the audio, log it and restart listening
        console.error('Audio playback error:', error);
        if (!isRecognizing) recognition.start();
      });
}
