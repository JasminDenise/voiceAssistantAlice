# VoiceAssistantAlice

**A Rasa‑Based Voice Assistant for Restaurant Reservations**

This repository contains all components for a prototype voice assistant that recommends and books restaurants based on user preferences, leveraging TF–IDF content filtering, Duckling for date/time & number parsing, and a web UI for demonstration.

---

##  Overview

VoiceAssistantAlice demonstrates an end-to-end conversational AI system built on Rasa. It includes:

- **Custom Form Validation** (`ValidateRestaurantForm`) to collect and validate user slots (cuisine, dietary restrictions, date/time, number of guests, past bookings).
- **Recommendation Engine** (`ActionSuggestRestaurant`) that:
  - Precomputes TF–IDF vectors for each restaurant description.
  - Uses cosine similarity to match user preferences (dietary > cuisine).
  - Checks availability based on Duckling‑parsed date/time and guest count.
- **Duckling Integration** for robust natural language date/time & number of guests understanding.
- **Flask App** (`app.py`) as a minimal web interface to demonstrate interactions.
- **Interactive Rasa Shell** for story creation and testing via `rasa interactive`.
- **Automated Preprocessing Script** (`preprocess.py`) to generate and serialize TF–IDF models for fast startup.

All services can be launched via a single script.

---

## Architecture & Key Components TODO; Picture Flowchart

```plaintext
┌─────────┐    ┌────────────┐    ┌────────┐    ┌───────────┐
│   User  │ ↔︎ │  Frontend  │ ↔︎ │ Rasa   │ ↔︎ │ Duckling  │
└─────────┘    └────────────┘    └────────┘    └───────────┘
                       │
                       ▼
                ┌──────────────────┐
                │ Action Server    │
                │ - TF–IDF models  │
                │ - Recommendation │
                └──────────────────┘
```

1. **Frontend** (Flask or custom `app.py`): Captures voice/text input and displays bot replies.  
2. **Rasa Core & NLU**: Manages dialog and extracts intents/entities.  
3. **Duckling**: Parses date/time expressions into structured slots.  
4. **Action Server**:  
   - **FormValidationAction**: Validates collected slots.  
   - **ActionSuggestRestaurant**: Filters and ranks restaurants & suggest best matching one.  
5. **Data**:  
   - `data/restaurants.json`: Restaurant metadata (cuisine, dietary options, availability).  
   - `vectorizer/`: Serialized TF–IDF vectorizer and restaurant vectors.  

---

## Setup & Usage 

### 1. Clone & Navigate  
```bash
git clone https://github.com/<your-username>/VoiceAssistantAlice.git
cd VoiceAssistantAlice
```

### 2. Create Virtual Environment & Install Dependencies  
```bash
python3.10 -m venv va_env

source va_env/bin/activate # macOS/Linux
.\va_env\Scripts\Activate.ps1 # Windows (PowerShell)

pip install -r requirements.txt
```

### 3. Build & Run Duckling  
Duckling is required for date/time & number parsing.  
```bash
cd duckling
stack build
stack exec duckling-example-exe > ../logs/duckling.log 2>&1 &
cd ..
```

### 4. Preprocess Restaurant Data  
Whenever you update `data/restaurants.json`, regenerate TF–IDF:  
```bash
python preprocess.py
```

### 5. Launch All Services  
#### macOS/Linux  
```bash
chmod +x ./start_bot.sh
./start_bot.sh
```

#### Windows (PowerShell)  
```powershell
# Activate venv
.\va_env\Scripts\Activate.ps1
# Start Duckling
cd duckling; stack exec duckling-example-exe > ..\logs\duckling.log 2>&1 ; cd ..
# Start Rasa server
rasa run --enable-api --cors "*" > logs\rasa.log 2>&1 &
# Start action server
rasa run actions > logs\actions.log 2>&1 &
# Run Flask app
gunicorn -b 127.0.0.1:5000 app:app > logs\app.log 2>&1 &
```

Open your browser at `http://localhost:5000`.

---

## Demonstration & Evaluation

1. **Web UI / Flask App**: Interact at `app.py`’s address.  
2. **Rasa Interactive**: Create new stories:  
```bash
# Unix
rasa interactive
# Windows
rasa interactive --endpoints endpoints.yml
```
3. **Shell Testing**:  
```bash
rasa shell --endpoints endpoints.yml
```
4. **Logs**: Check `logs/actions.log` for action outputs and slot values.

Evaluate: slot flows, dietary-first recommendations, and error handling when no matches exist.

---

## Extensibility & Future Work

- **Dynamic data**: Use a database instead of JSON.  
- **Enhanced UX**: Add automatic voice recognition (Hey Alice) or customize the front-end (loading spinner, etc.).  
- **User profiles & personalization**: Create user profiles and recommend based on past bookings over time.  
- **Location-based suggestions**: Use a location API to suggest restaurants near the user.  
- **Restaurant data API**: Integrate with third‑party restaurant APIs for live menus and availability.  
- **Automated confirmations**: Automatically send confirmation emails after booking.
- **Sentiment-aware recommendations**: Implement sentiment analysis on user utterances (e.g. detecting if they’re in a hurry) to prioritize quick suggestions and streamline the interaction.


