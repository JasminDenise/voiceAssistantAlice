# Rasa Voice Assistant

This is a conversational voice assistant built using [Rasa](https://rasa.com/), which helps users book restaurant reservations, suggest restaurants based on preferences, and handle other booking-related tasks. The assistant also uses Docker for easy deployment and integration with Duckling for extracting date and time information.

## Table of Contents

- [Features](#features)
- [Project Structure](#project-structure)
- [Prerequisites](#prerequisites)
- [Setup](#setup)
- [Running the Application](#running-the-application)
- [Custom Actions](#custom-actions)
- [Testing the Bot](#testing-the-bot)
- [Contributing](#contributing)
- [License](#license)

## Features

- **Intents**: The bot can understand various intents such as greetings, making bookings, asking for dietary preferences, and much more.
- **Entity Extraction**: The bot uses Rasa's NLU pipeline and Duckling for extracting information like time, dates, and numbers.
- **Dockerized Setup**: The project is fully Dockerized, which simplifies running the bot and related services like Duckling.

## Project Structure

Here is the directory structure of the project:

VOICEASSISTANT/ ├── actions/ # Custom actions for the bot │ └── actions.py # Python file for custom actions ├── data/ # Training data (intents, stories, etc.) │ ├── nlu.yml # NLU training data │ ├── stories.yml # Dialogue stories │ └── rules.yml # Optional rules for stories ├── domain.yml # Rasa domain configuration ├── endpoints.yml # Configuration for external services (like Duckling) ├── config.yml # Rasa pipeline and policies configuration ├── requirements.txt # Python dependencies for the bot ├── Dockerfile # Dockerfile for building the bot image ├── docker-compose.yml # Docker Compose file to run the services └── README.md # Project documentation


## Prerequisites

Before running the project, make sure you have the following installed:

- [Docker](https://www.docker.com/) (for building and running the bot in containers)
- [Docker Compose](https://docs.docker.com/compose/) (for managing multi-container setups)
- [Python 3.8 or higher](https://www.python.org/downloads/), if you plan to run the bot locally without Docker.

## Setup

1. **Clone the repository**:

   ```bash
   git clone https://github.com/your-username/voice-assistant.git
   cd voice-assistant

Install the required dependencies:

If you're not using Docker, you can install the dependencies directly on your system using pip.

pip install -r requirements.txt

Running the Application
To run the bot in Docker, follow these steps:

Build the Docker containers:
docker-compose build
Start the services:
docker-compose up

This will start the Rasa bot container and the Duckling container.

Open a new terminal and test the bot:
docker-compose exec rasa rasa shell

You can now interact with the bot directly in the terminal.

Custom Actions
In this project, we have implemented custom actions to perform actions like restaurant suggestions, sending booking details, and more. These actions are defined in the actions/actions.py file.

Adding New Custom Actions
Create a new Python function inside actions.py.
Ensure that the function inherits from Action (Rasa's base class for custom actions).
Update domain.yml to include any new actions or responses.
Add necessary logic for the action (e.g., API calls, database queries, etc.).
Testing the Bot
To test the bot:

Run the bot interactively using rasa shell: