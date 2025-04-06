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
from rasa_sdk.events import SlotSet, EventType
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


# Action to suggest a restaurant based on user preferences
class ActionSuggestRestaurant(Action):
    def name(self) -> Text:
        return "action_suggest_restaurant"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:

        # Load restaurant data
        with open("data/restaurants.json", "r") as file:
            restaurants = json.load(file)

        # Extract slot values
        cuisine_pref = tracker.get_slot("cuisine_preferences") or ""
        dietary_pref = tracker.get_slot("dietary_preferences") or ""
        num_guests = tracker.get_slot("num_of_guests")
        day_of_booking = tracker.get_slot("day_of_booking")
        time_of_booking = tracker.get_slot("time_of_booking")

        try:
            num_guests = int(num_guests) if num_guests else None
        except ValueError:
            num_guests = None

        # Build user preference string for vectorizer
        user_pref = f"{cuisine_pref} {dietary_pref}".strip()

        # Prepare TF-IDF matching
        restaurant_texts = [
            f"{r['name']} {r['cuisine']} {' '.join(r['dietary_options'])}" for r in restaurants
        ]
        vectorizer = TfidfVectorizer()
        vectors = vectorizer.fit_transform([user_pref] + restaurant_texts)
        similarities = cosine_similarity(vectors[0:1], vectors[1:]).flatten()

        # Attach similarity score and filter by availability
        available_matches = []
        for i, score in enumerate(similarities):
            r = restaurants[i]

            # Check max guests
            guests_ok = num_guests is None or r.get("max_guests", 0) >= num_guests

            # Check availability
            time_ok = True
            if day_of_booking and time_of_booking:
                available_times = r.get("availability", {}).get(day_of_booking, [])
                time_ok = time_of_booking in available_times

            if guests_ok and time_ok:
                available_matches.append((r, score))

        # Sort by similarity regardless of availability
        all_matches = list(zip(restaurants, similarities))
        all_matches.sort(key=lambda x: x[1], reverse=True)

        # Respond with best match or fallback
        if available_matches and available_matches[0][1] > 0.2:
            best = available_matches[0][0]
            response = (
                f"I recommend **{best['name']}**, which serves {best['cuisine']} cuisine. "
                f"It offers {', '.join(best['dietary_options'])} options, has a rating of {best['rating']}, "
                f"and is located in {best['location']}. It's available on {day_of_booking} at {time_of_booking}."
            )
        elif all_matches and all_matches[0][1] > 0.2:
            fallback = all_matches[0][0]
            available_days = ', '.join(fallback["availability"].keys())
            response = (
                f"I couldn't find a perfect match for your requested time and number of guests, "
                f"but you might like **{fallback['name']}**, which serves {fallback['cuisine']} cuisine "
                f"with {', '.join(fallback['dietary_options'])} options. It's located in {fallback['location']} "
                f"and has a rating of {fallback['rating']}. Available days include: {available_days}. "
                f"Would you like to check for another time?"
            )
        else:
            response = (
                "I couldn't find any restaurant that fits your preferences right now. "
                "Want to try adjusting your request or tell me what you're in the mood for?"
            )

        dispatcher.utter_message(text=response)
        return []

# Action to track the number of turns in the conversation
class ActionTrackTurns(Action):
    def name(self) -> Text:
        return "action_track_turns"

    # def run(self, dispatcher: CollectingDispatcher,
    #         tracker: Tracker,
    #         domain: dict):
        
    def run(self, dispatcher, tracker, domain):
        # Track turns using the number of events in the tracker
        current_turns = len(tracker.events)
        
        # Optionally, store it as a slot (if you want to persist it)
        dispatcher.utter_message(text=f"This is turn number {current_turns}")
        
        return []
        # # Get the current turn count from the tracker directly (use metadata storage)
        # current_turns = tracker.get_latest_event_for("user")["timestamp"]  # use timestamp as a proxy for turns
        
        # # Increment turn count
        # updated_turns = current_turns + 1

        # # After 10 turns, trigger restaurant suggestion action
        # if updated_turns >= 10:
        #     dispatcher.utter_message(text="You've asked a lot of questions! Let me suggest a restaurant for you.")
        #     return [EventType("action_suggest_restaurant")]  # Call restaurant suggestion action
        
        # return []  # No action if turn count is less than 10

# Fallback action for handling misunderstandings
class ActionDefaultFallback(Action):
    def name(self):
        return "action_default_fallback"

    def run(self, dispatcher, tracker, domain):
        # Custom behavior for fallback action
        dispatcher.utter_message("Sorry, I did not understand that. Can you rephrase, please?")
        return []

# import json
# import random
# from typing import Any, Text, Dict, List
# from rasa_sdk import Action, Tracker
# from rasa_sdk.executor import CollectingDispatcher
# # from rasa_sdk.events import SlotSet
# # from datetime import datetime

# class ActionSuggestRestaurant(Action):
#     def name(self) -> Text:
#         return "action_suggest_restaurant"

#     def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
#         # Load restaurant data from JSON file
#         with open("data/restaurants.json", "r") as file:
#             restaurants = json.load(file)

#         # Get user preferences from slots
#         cuisine_pref = tracker.get_slot("cuisine_preferences")
#         dietary_pref = tracker.get_slot("dietary_preferences")

#         # Filter restaurants based on user preferences
#         filtered_restaurants = [
#             r for r in restaurants 
#             if (not cuisine_pref or cuisine_pref.lower() in r["cuisine"].lower()) and
#                (not dietary_pref or dietary_pref in r["dietary_options"])
#         ]

#         # Pick a random restaurant from the filtered list
#         if filtered_restaurants:
#             restaurant = random.choice(filtered_restaurants)
#             response = f"I recommend **{restaurant['name']}**, which serves {restaurant['cuisine']} food. It has a rating of {restaurant['rating']} and is located in {restaurant['location']}."
#         else:
#             response = "I couldn't find a perfect match, but how about trying something new? Let me know if you have other preferences!"

#         dispatcher.utter_message(text=response)
#         return []

