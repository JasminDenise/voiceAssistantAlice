# VoiceAssistantAlice

**A Rasa‑Based Voice Assistant for Restaurant Reservations**

This repository contains all components for a prototype voice assistant that recommends and books restaurants based on user preferences, leveraging TF–IDF content filtering, Duckling for date/time & number parsing, and a web UI for demonstration.

---

## Overview

VoiceAssistantAlice demonstrates an end-to-end conversational AI system built on Rasa. It includes:

* **Custom Form Validation** (`ValidateRestaurantForm`) to collect and validate user slots (cuisine, dietary restrictions, date/time, number of guests, past bookings)  
* **Recommendation Engine** (`ActionSuggestRestaurant`) that:
  * Precomputes TF–IDF vectors for each restaurant description
  * Uses cosine similarity to match user preferences (cuisine + diet) 
  * Checks availability based on Duckling-parsed date/time and guest count  
* **Duckling Integration** for robust natural language date/time & number of guests understanding  
* **Flask App** (`app.py`) as a minimal web interface to demonstrate interactions  
* **Interactive Rasa Shell** for story creation and testing via `rasa interactive`  
* **Automated Preprocessing Script** (`preprocess.py`) to generate and serialize TF–IDF models for fast startup  

All services can be launched via a single script.

---

## Architecture & Key Components 

### 1. System Architecture & Interaction Flow  
<p >
  <img src="docs/images/UpdatedSystemArchitecture.png" alt="System Architecture & Interaction Flow" width="500"/><br/>
  <em>Figure 1: End-to-end architecture and message flow</em>
</p>

### 2. Form Handling & Validation Logic  
<p >
  <img src="docs/images/FormLogic.png" alt="Form Activation Logic" width="500"/><br/>
  <em>Figure 2: Form handling logic</em>
</p>  
<p >
  <img src="docs/images/FormValidationLogic.png" alt="Form Validation Logic" width="500"/><br/>
  <em>Figure 3: Form validation flow</em>
</p>

### 3. Recommendation Logic  
<p >
  <img src="docs/images/RecommendationLogic.png" alt="Recommendation Logic" width="500"/><br/>
  <em>Figure 4: TF–IDF based recommendation and availability check</em>
</p>

---

## Setup & Usage

### 1. Clone & Navigate

```bash
git clone --depth 1 https://github.com/JasminDenise/voiceAssistantAlice.git # for faster setup
cd voiceAssistantAlice
```

### 2. Create Virtual Environment & Install Dependencies

```bash
python3.10 -m venv "va_env" # version 3.10 is required to work
source va_env/bin/activate   # macOS/Linux
# or .\va_env\Scripts\Activate.ps1  # Windows (PowerShell)

pip install -r requirements.txt
```

### 3. Run Duckling 
Duckling is required for date/time & number parsing. You have two options:

a) Via Docker (recommended)
```bash
docker pull rasa/duckling
docker run -d --name duckling -p 8000:8000 rasa/duckling
```

b) From source
```bash
# 1) Clone the official Duckling repo (includes Stack project files)
git clone https://github.com/facebook/duckling.git
cd duckling

# 2) Ensure you have Haskell Stack installed (e.g. `brew install haskell-stack`)
#    and then bootstrap GHC if needed:
stack setup

# 3) Build Duckling:
stack build

# 4) Start the Duckling HTTP server on port 8000:
stack exec duckling-example-exe -- start --port 8000 > ../logs/duckling.log 2>&1 &

# 5) Return to your project root:
cd ..
```

### 4. Preprocess Restaurant Data

Whenever you update `data/restaurants.json`, regenerate TF–IDF:

```bash
python3 preprocess.py
```

### 5. Launch All Services

#### macOS/Linux

```bash
chmod +x ./start_bot.sh
./start_bot.sh
```
 *If you prefer manual setup:*
> ```bash
> # Rasa server
> rasa run --enable-api --cors "*"    > logs/rasa.log 2>&1 &
> # Rasa action server
> rasa run actions                   > logs/actions.log 2>&1 &
> # Flask web app via Gunicorn
> gunicorn -b 127.0.0.1:5000 app:app > logs/app.log 2>&1 &
> ```
#### Windows (Powershell)

```bash
.\va_env\Scripts\Activate.ps1

# Rasa server
rasa run --enable-api --cors "*"    > logs\rasa.log 2>&1 &

# Rasa action server
rasa run actions                   > logs\actions.log 2>&1 &

# Flask web app via Gunicorn
gunicorn -b 127.0.0.1:5000 app:app > logs\app.log 2>&1 &

```
#### Once all services are running, open your browser to http://127.0.0.1:5000.
---

## Testing & Evaluation

### Core (Conversation) Tests

Define conversation test stories in `tests/test_stories.yml` and run:

```bash
rasa test core --stories tests/test_stories.yml
```

### NLU Tests

Define NLU test cases in `data/test_nlu.yml` and run:

```bash
rasa test nlu --nlu data/test_nlu.yml
```

After running, inspect the reports generated under `results/`:

* `results/intent_report.json`  and `results/intent_confusion_matrix.png` for NLU classification metrics and confusion matrix
* `results/DIETClassifier_report.json` and `results/DIETClassifier_confusion_matrix.png` for entity extraction performance.
* `results/story_report.json` & `results/core/failed_test_stories.yml` for conversation‐level accuracy and failed stories


## Demonstration & Evaluation

1. **Web UI / Flask App**: chat + voice at `127.0.0.1:5000`
2. **Rasa Interactive**: Create and refine stories:

   ```bash
   rasa interactive
   ```
3. **Shell Testing**:

   ```bash
   rasa shell --endpoints endpoints.yml
   ```
4. **Logs**: Check `logs/actions.log` and `logs/rasa.log` for diagnostics.

---

## Live Demo Recording

Watch a live session demonstrating the assistant handling new bookings, rebookings, and cancellations:

<a href="https://www.youtube.com/watch?v=IKRH7u9VYPU" target="_blank">
  <img src="https://img.youtube.com/vi/IKRH7u9VYPU/0.jpg" width="400" alt="Live Demo auf YouTube" />
</a><br/>
Link: https://www.youtube.com/watch?v=IKRH7u9VYPU



---

## Privacy Considerations and Future Enhancements

**Privacy in API Integration**

* Minimal data collection (only what's necessary, e.g., location)
* Encrypt all data in transit (TLS) and at rest
* Explicit user consent and opt‑out commands (e.g., "Stop sharing my data")

**Optional UX Features**

* Exit commands (implemented but under refinement) to cancel at any point
* Personalization (remember favorite cuisines)
* Multilingual support with fallbacks to user’s locale

**Risks & Mitigation**

* Privacy: encryption, strict data lifecycle, transparent notices
* Model bias: continuous monitoring, diverse utterance examples
* Complexity: incremental rollout and user acceptance testing

---

## Possible Future Work

* Dynamic data backend (database instead of JSON)
* Voice activation keywords and enhanced front‑end (loading spinners)
* User profiles for long‑term personalization
* Location-based restaurant suggestions via external APIs
* Automated booking confirmations (email/SMS)
* Sentiment-aware recommendations for context‑aware suggestions
