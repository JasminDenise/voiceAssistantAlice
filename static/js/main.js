// Check if the browser supports the Web Speech API
const SpeechRecognition =
    window.SpeechRecognition || window.webkitSpeechRecognition;
if (!SpeechRecognition) {
  alert(
      'Your browser does not support Speech Recognition. Please use Chrome or Edge.');
} else {
  const recognition = new SpeechRecognition();
  recognition.lang = 'en-US';
  recognition.interimResults = false;  // return only final results
  recognition.maxAlternatives =
      1;  // nr of alternative matches that should be returned

  // Triggered when the speech recognition service returns a result.
  // Sends the text to the Rasa server via the /process endpoint.
  // Adds the spoken text to the chat box.
  recognition.onresult = (event) => {
    const transcript = event.results[0][0].transcript;
    addChatMessage('You:', transcript);
    sendTextToBackend(transcript);

    // After processing, continue listening automatically
    recognition.start();  // Restart listening for the next input
  };

  recognition.onerror = (event) => {
    console.error('Speech recognition error:', event.error);
    console.log('Restarting speech recognition...');
    recognition.start();  // Restart on error
  };

  // Triggered when speech recognition ends (e.g., user stops talking)
  recognition.onspeechend = () => {
    recognition.stop();   // Stop the recognition, then restart
    recognition.start();  // Automatically start listening again
  };

  // Start SpeechRecognition if button is clicked
  document.getElementById('record-btn').addEventListener('click', () => {
    recognition.start();
  });
}

document.getElementById('stop-btn').addEventListener('click', () => {
  recognition.stop();  // Stop the recognition
  console.log('Speech recognition stopped.');
});


recognition.onspeechend = () => {
  recognition.stop();
  console.log('Speech recognition has stopped.');
};

// Send recognized text to the Flask backend
function sendTextToBackend(text) {
  fetch(' http://127.0.0.1:5000/process', {
    // http://127.0.0.1:5000/process
    method: 'POST',  // send data to server
    headers: {
      'Content-Type': 'application/json'
    },                                  // request body contains JSOn data
    body: JSON.stringify({text: text})  // convert text to JSON string
  })
      .then(response => response.json())  // handling response from backend;
                                          // parsed into JS object
      .then(data => {  // handles processed data from the server
        addChatMessage('Alice:', data.response);
        if (data.audioUrl) {
          playAudio(data.audioUrl);
        }
      })
      .catch(error => console.error('Error:', error));
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

  //  // Try playing again on user interaction
  //  document.body.addEventListener('click', () => {
  //   audio.play().catch(err => console.error('Audio playback error:', err));
  // }, { once: true });
}
