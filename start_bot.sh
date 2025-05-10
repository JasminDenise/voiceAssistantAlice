#!/usr/bin/env bash
# start it with: source ./start_bot.sh or ./start_bot.sh

cd "$(dirname "$0")"

if [ -z "$VIRTUAL_ENV" ]; then
  echo "Starting virtual environment..."
  source va_env/bin/activate  # for macOS/Linux
else
  echo "Already in venv: $VIRTUAL_ENV"
fi

# --------------------
# Duckling startup
# --------------------
# Check for existing container named “duckling”
EXISTING="$(docker ps -q -f name=duckling)"
if [ -n "$EXISTING" ]; then
  echo "Found existing Duckling container (ID: $EXISTING). Using that."
  DUCKLING_PID="$EXISTING"
else
  # Check if port 8000 is in use
  if lsof -iTCP:8000 -sTCP:LISTEN >/dev/null; then
    echo "Port 8000 already in use—assuming Duckling is running there."
    DUCKLING_PID="(external)"
  else
    echo "Starting Duckling (via Docker)..."
    docker run -d --name duckling \
      -p 8000:8000 \
      rasa/duckling:latest \
      > logs/duckling.log 2>&1
    DUCKLING_PID=$(docker ps -q -f name=duckling)
  fi
fi

# If you ever need to run Duckling from source, uncomment below:
# echo "Starting Duckling (from source)..."
# cd duckling
# stack exec duckling-example-exe -- start --port 8000 > ../logs/duckling.log 2>&1 &
# DUCKLING_PID=$!
# cd ..

# --------------------
# Rasa server
# --------------------
echo "Starting Rasa server..."
rasa run --enable-api --cors "*" > logs/rasa.log 2>&1 &
RASA_PID=$!

echo "Waiting for Rasa to load its model... this can take a while..."
while ! grep -q "Rasa server is up and running" logs/rasa.log; do
  sleep 1
done
echo "Rasa server is ready!"

# --------------------
# Rasa action server
# --------------------
echo "Starting Rasa action server..."
rasa run actions > logs/actions.log 2>&1 &
ACTIONS_PID=$!

# --------------------
# Flask web app
# --------------------
echo "Starting Flask web app..."
gunicorn -b 127.0.0.1:5000 app:app > logs/app.log 2>&1 &
APP_PID=$!

# --------------------
# Summary
# --------------------
echo ""
echo "All services are now running:"
echo " - Duckling  -> logs/duckling.log (container: $DUCKLING_PID)"
echo " - Rasa      -> logs/rasa.log (pid: $RASA_PID)"
echo " - Actions   -> logs/actions.log (pid: $ACTIONS_PID)"
echo " - Front-end -> logs/app.log (pid: $APP_PID)"
echo " - Fallbacks -> logs/fallbacks.log"
echo ""
echo "Access the web UI at: http://127.0.0.1:5000"
echo ""
echo "To stop everything, run:"
echo "  kill $RASA_PID $ACTIONS_PID $APP_PID"
echo "  docker stop duckling && docker rm duckling"
