# VoiceAssistantAlice

**Master’s Project: A Rasa‑Based Voice Assistant for Restaurant Reservations**

This repository contains all components for a prototype voice assistant—VoiceAssistantAlice—that recommends and books restaurants based on user preferences, leveraging TF–IDF content filtering, Duckling for date/time parsing, and a Flask (or other) frontend for demonstration.

---

##  Overview

VoiceAssistantAlice demonstrates an end-to-end conversational AI system built on Rasa. It includes:

- **Custom Form Validation** (`ValidateRestaurantForm`) to collect and validate user slots (cuisine, dietary restrictions, date/time, number of guests, past bookings).
- **Recommendation Engine** (`ActionSuggestRestaurant`) that:
  - Precomputes TF–IDF vectors for each restaurant description.
  - Uses cosine similarity to match user preferences (dietary > cuisine).
  - Checks real-time availability based on Duckling‑parsed date/time and guest count.
- **Duckling Integration** for robust natural language date/time & number of guests understanding.
- **Flask App** (`app.py`) as a minimal web interface to demonstrate interactions.
- **Interactive Rasa Shell** for story creation and testing via `rasa interactive`.
- **Automated Preprocessing Script** (`actions/preprocess.py`) to generate and serialize TF–IDF models for fast startup.

All services can be launched via a single orchestrator script or manually per platform instructions.

---

## ⚙️ Architecture & Key Components

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
   - **ActionSuggestRestaurant**: Filters and ranks restaurants.  
5. **Data**:  
   - `data/restaurants.json`: Restaurant metadata (cuisine, dietary options, availability).  
   - `vectorizer/`: Serialized TF–IDF vectorizer and restaurant vectors.  

---

## 🚀 Setup & Usage (Master’s Student Guide)

### 1. Clone & Navigate  
```bash
git clone https://github.com/<your-username>/VoiceAssistantAlice.git
cd VoiceAssistantAlice
```

### 2. Create Virtual Environment & Install Dependencies  
```bash
python3.10 -m venv va_env
# macOS/Linux
source va_env/bin/activate
# Windows (PowerShell)
.\va_env\Scripts\Activate.ps1
pip install -r requirements.txt
```

### 3. Build & Run Duckling  
Duckling is required for date/time parsing.  
```bash
cd duckling
stack build
stack exec duckling-example-exe > ../logs/duckling.log 2>&1 &
cd ..
```

### 4. Preprocess Restaurant Data  
Whenever you update `data/restaurants.json`, regenerate TF–IDF artifacts:  
```bash
python preprocess.py
```

### 5. Launch All Services  
#### macOS/Linux  
```bash
chmod +x actions/start_bot.sh
./actions/start_bot.sh
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

## 📝 Demonstration & Evaluation

1. **Web UI / Flask App**: Interact at `app.py`’s address.  
2. **Rasa Interactive**: Create/refine stories:  
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

## 🔄 Extensibility & Future Work

- **Large catalog**: Integrate ANN libraries (Faiss, Annoy).  
- **Dynamic data**: Use a database instead of JSON.  
- **Enhanced UX**: Add automatic voice recognition (Hey Alice) or customize front-end (Loading spinner and so on).


