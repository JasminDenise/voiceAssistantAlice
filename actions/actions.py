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

class ActionSuggestRestaurant(Action):
    def name(self) -> Text:
        return "action_suggest_restaurant"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        # Load restaurant data from JSON file
        with open("data/restaurants.json", "r") as file:
            restaurants = json.load(file)

        # Get user preferences from slots
        cuisine_pref = tracker.get_slot("cuisine_preferences")
        dietary_pref = tracker.get_slot("dietry_preferences")

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


# import requests
# from rasa_sdk import Action, Tracker
# from rasa_sdk.executor import CollectingDispatcher

# class ActionSuggestRestaurant(Action):
#     def name(self) -> str:
#         return "action_suggest_restaurant"

#     def run(self, dispatcher: CollectingDispatcher,
#             tracker: Tracker, domain: dict) -> list:
#         past_bookings = tracker.get_slot("past_bookings")
#         dietry_preferences = tracker.get_slot("dietry_preferences")
#         cuisine_preferences = tracker.get_slot("cuisine_preferences")
#         time_of_booking = tracker.get_slot("time_of_booking")
#         day_of_booking = tracker.get_slot("day_of_booking")
#         num_of_guests = tracker.get_slot("num_of_guests")

#         # # Here you would typically query your database or API
#         # # For demonstration, we'll use a static suggestion.
#         # restaurant = {
#         #     "name": "Luigi’s Trattoria",
#         #     "cuisine": "Italian",
#         #     "ambiance": "Quiet",
#         #     "rating": 4.5,
#         # }

#         # message = (f"I found a great restaurant: {restaurant['name']}, "
#         #            f"serving {restaurant['cuisine']} cuisine with a {restaurant['ambiance']} ambiance "
#         #            f"and a rating of {restaurant['rating']}.")
#         # dispatcher.utter_message(text=message)
#         # return []

#          # Construct the API URL and parameters
#         url = "https://api.example.com/get_restaurant"  # Replace with the actual open source API URL
#         params = {
#             "cuisine": cuisine,
#             "dietary": dietary,
#             "time": time_booking,
#             "date": day_booking,
#             "guests": num_guests
#         }

#         # Make the API request
#         try:
#             response = requests.get(url, params=params)
#             response.raise_for_status()  # raise an exception for HTTP errors
#             data = response.json()

#             # Extract details from the response
#             restaurant_name = data.get("name", "Unknown Restaurant")
#             restaurant_address = data.get("address", "Address not available")
#             restaurant_rating = data.get("rating", "No rating")
            
#             # Construct a suggestion message
#             message = (f"I suggest {restaurant_name}, located at {restaurant_address}. "
#                        f"It has a rating of {restaurant_rating} and suits your preferences.")
#         except requests.exceptions.RequestException:
#             message = "I'm sorry, I'm having trouble connecting to the restaurant service right now."
        
#         # Dispatch the message to the user
#         dispatcher.utter_message(text=message)
#         return []