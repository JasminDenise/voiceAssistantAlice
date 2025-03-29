# This files contains your custom actions which can be used to run
# custom Python code.
#
# See this guide on how to implement these action:
# https://rasa.com/docs/rasa/custom-actions


# This is a simple example for a custom action which utters "Hello World!"

# from typing import Any, Text, Dict, List
#
# from rasa_sdk import Action, Tracker
# from rasa_sdk.executor import CollectingDispatcher
#
#
# class ActionHelloWorld(Action):
#
#     def name(self) -> Text:
#         return "action_hello_world"
#
#     def run(self, dispatcher: CollectingDispatcher,
#             tracker: Tracker,
#             domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
#
#         dispatcher.utter_message(text="Hello World!")
#
#         return []

import json
import random
from typing import Any, Text, Dict, List
from rasa_sdk import Action, Tracker
from rasa_sdk.executor import CollectingDispatcher
# from rasa_sdk.events import SlotSet
# from datetime import datetime

class ActionSuggestRestaurant(Action):
    def name(self) -> Text:
        return "action_suggest_restaurant"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        # Load restaurant data from JSON file
        with open("data/restaurants.json", "r") as file:
            restaurants = json.load(file)

        # Get user preferences from slots
        cuisine_pref = tracker.get_slot("cuisine_preferences")
        dietary_pref = tracker.get_slot("dietary_preferences")

        # Filter restaurants based on user preferences
        filtered_restaurants = [
            r for r in restaurants 
            if (not cuisine_pref or cuisine_pref.lower() in r["cuisine"].lower()) and
               (not dietary_pref or dietary_pref in r["dietary_options"])
        ]

        # Pick a random restaurant from the filtered list
        if filtered_restaurants:
            restaurant = random.choice(filtered_restaurants)
            response = f"I recommend **{restaurant['name']}**, which serves {restaurant['cuisine']} food. It has a rating of {restaurant['rating']} and is located in {restaurant['location']}."
        else:
            response = "I couldn't find a perfect match, but how about trying something new? Let me know if you have other preferences!"

        dispatcher.utter_message(text=response)
        return []


# from rasa_sdk import Action


# class ActionValidateTimeAndDay(Action):

#     def name(self) -> str:
#         return "action_validate_time_and_day"

#     def run(self, dispatcher, tracker, domain):
#         time_of_booking = tracker.get_slot('time_of_booking')
#         day_of_booking = tracker.get_slot('day_of_booking')

#         # Validate time (e.g., ensure it follows a format like "7:00 PM")
#         try:
#             datetime.strptime(time_of_booking, "%I:%M %p")  # Example validation for time
#         except ValueError:
#             dispatcher.utter_message("Please provide a valid time format (e.g., 7:00 PM).")
#             return [SlotSet("time_of_booking", None)]  # Reset invalid slot

#         # Validate day (e.g., ensure it's a valid day)
#         try:
#             datetime.strptime(day_of_booking, "%A")  # Example validation for day (e.g., "Monday")
#         except ValueError:
#             dispatcher.utter_message("Please provide a valid day of the week.")
#             return [SlotSet("day_of_booking", None)]  # Reset invalid slot

#         return []
