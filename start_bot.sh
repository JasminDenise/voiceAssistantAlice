#!/bin/bash
# start it with: source ./start_bot.sh or ./start_bot.sh

cd "$(dirname "$0")"

if [ -z "$VIRTUAL_ENV" ]; then
  echo "Starting virtual environment..."
  source va_env/bin/activate #for macOS/Linux
else
  echo "Already in venv: $VIRTUAL_ENV"
fi

echo "Starting Duckling..."
cd duckling
stack exec duckling-example-exe > ../logs/duckling.log 2>&1 &
DUCKLING_PID=$!
cd ..

echo "Starting Rasa server ..."
rasa run --enable-api --cors "*" > logs/rasa.log 2>&1 &
RASA_PID=$!

echo "Waiting for Rasa to load its model... this can take a while..."
# Poll the rasa.log until we see the ready message
while ! grep -q "Rasa server is up and running" logs/rasa.log; do
  sleep 1
done

echo "Rasa server is ready!"

echo "Starting Rasa action server..."
rasa run actions > logs/actions.log 2>&1 &
ACTIONS_PID=$!

echo "Starting Flask web app ..."
gunicorn -b 127.0.0.1:5000 app:app > logs/app.log 2>&1 &
APP_PID=$!

echo ""
echo "All servers are running."
echo " - Duckling  -> logs/duckling.log"
echo " - Rasa      -> logs/rasa.log"
echo " - Actions   -> logs/actions.log"
echo " - Front-end -> logs/app.log"
echo ""
echo "You can now access the web app at: http://127.0.0.1:5000"
echo ""
echo "To stop everything, run:"
echo "  kill $DUCKLING_PID $RASA_PID $ACTIONS_PID $APP_PID"