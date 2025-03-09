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
  };

  recognition.onerror = (event) => {
    console.error('Speech recognition error:', event.error);
  };

  // Start SpeechRecognition if button is clicked
  document.getElementById('start-record-btn').addEventListener('click', () => {
    recognition.start();
  });
}

recognition.onspeechend = () => {
  recognition.stop();
  console.log('Speech recognition has stopped.');
};

// Send recognized text to the Flask backend
function sendTextToBackend(text) {
  fetch('/process', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({text: text})
  })
      .then(response => response.json())
      .then(data => {
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
  const audio = new Audio(url);
  audio.play();
}
