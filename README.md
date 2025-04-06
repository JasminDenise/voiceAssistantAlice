
# Voice Assistant Bot

This project implements a restaurant booking bot built with **Rasa** and **Docker**. The bot interacts with users to make restaurant bookings, suggesting restaurants based on user preferences and booking history.

## Prerequisites

Before you begin, ensure you have the following installed on your machine:

- **Docker** (with Docker Compose)
  - [Install Docker](https://docs.docker.com/get-docker/)
  - [Install Docker Compose](https://docs.docker.com/compose/install/)

- **Python 3.x** (for setting up the virtual environment)
  - [Install Python](https://www.python.org/downloads/)

## Setup

### Clone the Repository
First, clone this repository to your local machine.

```bash
git clone https://github.com/your-repository/voice-assistant.git
cd voice-assistant
```

### Create a Virtual Environment (Optional)

If you want to use a virtual environment for running Rasa locally:

```bash
python3 -m venv va_env
source va_env/bin/activate  # For macOS/Linux
# va_env\Scripts\activate  # For Windows
```

### Install Required Dependencies

Install the necessary Python dependencies.

```bash
pip install -r requirements.txt
```

### Docker Setup

This project uses **Docker** to simplify the setup and execution of the Rasa bot and related services.

1. Ensure **Docker** and **Docker Compose** are properly installed and running.
2. In the root directory of this project, create a `docker-compose.yml` file.

#### docker-compose.yml
```yaml
version: "3.1"

services:
  rasa:
    image: rasa/rasa:latest
    command: run --enable-api --cors "*"
    ports:
      - "5005:5005"  # Rasa API will be on port 5005
    volumes:
      - ./voiceassistant:/app  # Mount the voiceassistant folder to /app in the container
    depends_on:
      - actions

  actions:
    build: .
    volumes:
      - ./actions:/actions  # Mount the actions folder to /actions in the container
    command: rasa run actions --port 5055
    ports:
      - "5055:5055"  # Actions will be on port 5055

  app:
    build:
      context: .  # Build from the current directory (root directory)
    volumes:
      - ./app.py:/app.py  # Mount app.py directly to the container
    ports:
      - "5000:5000"  # App will be on port 5000
    depends_on:
      - rasa
      - actions
```

### Start the Bot Using Docker

1. **Build and start the bot**:

   Run the following command to start the Rasa bot, actions, and app container.

   ```bash
   docker-compose up --build
   ```

2. **Access the services**:
   - Rasa API will be running on **port 5005**.
   - Actions will be running on **port 5055**.
   - The app will be running on **port 5000**.

3. **You can now interact with the app** by sending requests to `http://localhost:5000`.

### Running Locally (Optional)
If you prefer to run Rasa locally without Docker, you can do so by following these steps:

1. **Activate the virtual environment** (if using one):
   ```bash
   source va_env/bin/activate  # For macOS/Linux
   # va_env\Scripts\activate  # For Windows
   ```

2. **Start Rasa server** (for API):
   ```bash
   rasa run --enable-api --cors "*"
   ```

3. **Start the actions server**:
   ```bash
   rasa run actions --port 5055
   ```

4. **Start the app** (replace `app.py` with your actual app entry point):
   ```bash
   python app.py
   ```

## How to Interact with the Bot

1. **Access the Bot via HTTP**:
   Once the services are running, you can interact with the bot by making HTTP requests to `http://localhost:5000`.

2. **App Functionality**:
   - The bot will ask for **past restaurant bookings**, **dietary preferences**, **cuisine preferences**, **time** and **day** of booking, and **number of guests**.
   - The bot will suggest restaurants based on these preferences.
   - If the user has previously made a booking, they can rebook their favorite restaurant or try a new one.

## Common Issues & Troubleshooting

### 1. Docker Errors
If you encounter errors related to Docker, ensure the following:
- Docker is running and properly configured on your machine.
- If you see permission issues, you may need to use `sudo` with Docker commands (on Linux).

### 2. Service Not Starting
If a service doesn’t start, check the logs for errors. You can use `docker-compose logs` to get more information about what's going wrong.

```bash
docker-compose logs
```

### 3. Python Errors
If you're using a virtual environment and run into Python-related issues, make sure that all dependencies are installed via `pip install -r requirements.txt`.

---

Now you have a working environment to run your Rasa-based voice assistant with minimal terminal commands and a single Docker Compose command.

Happy Booking! 🎉
