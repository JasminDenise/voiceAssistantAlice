#!/bin/bash
# start it with: ./start_bot.sh

cd "$(dirname "$0")"

echo "Starting virtual environment..."
source va_env/bin/activate  #for macOS/Linux

echo "Starting Duckling..."
cd duckling
stack exec duckling-example-exe > ../logs/duckling.log 2>&1 &
DUCKLING_PID=$!
cd ..

echo "Starting Rasa server (this can take 10–20 seconds)..."
rasa run --enable-api --cors "*" > logs/rasa.log 2>&1 &
RASA_PID=$!

echo "Waiting for Rasa to load its model..."
# Poll Rasa’s endpoint until it responds with {"status":"ok"}
until curl -s http://localhost:5005/health | grep -q '"status":"ok"'; do
  sleep 1
done
echo "Rasa is up and running!"

echo "Starting Rasa action server..."
rasa run actions > logs/actions.log 2>&1 &
ACTIONS_PID=$!

echo "Starting Flask app (app.py)..."
gunicorn -b 127.0.0.1:5000 app:app > logs/app.log 2>&1 &
APP_PID=$!

echo ""
echo "All servers were started. You can access the app now at http://127.0.0.1:5000"
echo "To stop everything, run: kill $DUCKLING_PID $RASA_PID $ACTIONS_PID $APP_PID"
