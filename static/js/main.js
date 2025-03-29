
// Check if the browser supports the Web Speech API
const SpeechRecognition =
    window.SpeechRecognition || window.webkitSpeechRecognition;
if (!SpeechRecognition) {
  alert(
      'Your browser does not support Speech Recognition. Please use Chrome or Edge.');
} else {
  const recognition = new SpeechRecognition();
  // let isRecognizing = false;  // State of recognition

  // Initialize SpeechRecognition only when needed
  recognition.lang = 'en-US';
  recognition.interimResults = false;  // Return only final results
  recognition.maxAlternatives = 1;  // Number of alternative matches to return


  // Triggered when the speech recognition service returns a result.
  // Sends the text to the Rasa server via the /process endpoint.
  // Adds the spoken text to the chat box.
  recognition.onresult = (event) => {
    const transcript = event.results[0][0].transcript;
    addChatMessage('You:', transcript);
    sendTextToBackend(transcript);

    // // Restart listening only if it's not already recognizing
    // if (!isRecognizing) {
    //   isRecognizing = true;
    // recognition.start();  // Restart listening for the next input
  };


  recognition.onerror = (event) => {
    console.error('Speech recognition error:', event.error);
    console.log('Restarting speech recognition...');
    // isRecognizing = false;
    recognition.stop();  // Restart on error
  };

  // Triggered when speech recognition ends (e.g., user stops talking)
  recognition.onspeechend = () => {
    recognition.stop();  // Stop the recognition, then restart
    console.log('Speech recognition has stopped.');
    // isRecognizing = false;
    // recognition.start();  // Automatically start listening again
  };

  // Start SpeechRecognition if button is clicked
  document.getElementById('record-btn').addEventListener('click', () => {
    // if (!isRecognizing) {
    //   if (!recognition) {
    //     initRecognition();  // Initialize recognition if not already done
    //   }
    recognition.start();  // Start recognizing only if not already started
    // isRecognizing = true;  // Update recognition state to 'recognizing'
    //}
  });
}

// Send recognized text to the Flask backend
// Function to send recognized text to the backend
async function sendTextToBackend(text) {
  try {
    const response = await fetch('http://127.0.0.1:5000/process', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({text: text})
    });

    const data = await response.json();
    addChatMessage('Alice:', data.response);

    if (data.audioUrl) {
      playAudio(data.audioUrl);
    }
  } catch (error) {
    console.error('Error:', error);
  }
}


// Add messages to the chat box
// TODO Left & right aligned Bot/user
function addChatMessage(sender, message) {
  const chatBox = document.getElementById('chat-box');
  const newMessage = document.createElement('p');
  newMessage.innerHTML = `<strong>${sender}</strong> ${message}`;
  chatBox.appendChild(newMessage);
  chatBox.scrollTop = chatBox.scrollHeight;
}

// Play audio from the TTS engine
function playAudio(url) {
  if (!url) return;  // Prevent trying to play a missing file
  const audio = new Audio(
      url + '?t=' +
      new Date().getTime());  // force fresh request (avoid caching issues)
  audio.play().catch(
      error => console.error(
          'Audio playback error:', error));  // handle autoplay restrictions
}
