# This file contains your custom actions which can be used to run Python code.
# These actions are triggered by Rasa based on conversation logic.
# This project includes restaurant recommendation, turn tracking, fallback handling, and form validation.

import json
import random
from typing import Any, Text, Dict, List
from rasa_sdk import Action, Tracker
from rasa_sdk.executor import CollectingDispatcher
from rasa_sdk.events import SlotSet, EventType
from rasa_sdk.forms import FormValidationAction
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

# Suggests a restaurant based on user's cuisine, dietary preferences, time, date, and guest count
class ActionSuggestRestaurant(Action):
    def name(self) -> Text:
        return "action_suggest_restaurant"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:

        # Load restaurant data from JSON file
        with open("data/restaurants.json", "r") as file:
            restaurants = json.load(file)

        # Extract preferences from slots
        cuisine_pref = tracker.get_slot("cuisine_preferences") or ""
        dietary_pref = tracker.get_slot("dietary_preferences") or ""
        num_guests = tracker.get_slot("num_of_guests")
        day_of_booking = tracker.get_slot("day_of_booking")
        time_of_booking = tracker.get_slot("time_of_booking")

        # Handle guest number safely
        try:
            num_guests = int(num_guests) if num_guests else None
        except ValueError:
            num_guests = None

        # Build user preference string to compare with restaurant data
        user_pref = f"{cuisine_pref} {dietary_pref}".strip()

        # Convert text to vectors and calculate similarity
        restaurant_texts = [
            f"{r['name']} {r['cuisine']} {' '.join(r['dietary_options'])}" for r in restaurants
        ]
        vectorizer = TfidfVectorizer()
        vectors = vectorizer.fit_transform([user_pref] + restaurant_texts)
        similarities = cosine_similarity(vectors[0:1], vectors[1:]).flatten()

        available_matches = []
        for i, score in enumerate(similarities):
            r = restaurants[i]
            guests_ok = num_guests is None or r.get("max_guests", 0) >= num_guests
            time_ok = True
            if day_of_booking and time_of_booking:
                available_times = r.get("availability", {}).get(day_of_booking, [])
                time_ok = time_of_booking in available_times

            if guests_ok and time_ok:
                available_matches.append((r, score))

        # Fallback: sort all restaurants by similarity
        all_matches = list(zip(restaurants, similarities))
        all_matches.sort(key=lambda x: x[1], reverse=True)

        # Respond to user with best or fallback suggestion
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

# Tracks the number of question-answer turns in the conversation
class ActionTrackTurnCount(Action):
    def name(self):
        return "action_track_turn_count"

    def run(self, dispatcher, tracker, domain):
        current_turn = tracker.get_slot("conversation_turn") or 0
        updated_turn = current_turn + 1

        if updated_turn >= 10:
            dispatcher.utter_message(text="We've reached our 10-question limit. Here's my final suggestion.")
            return [SlotSet("conversation_turn", updated_turn), SlotSet("requested_slot", None)]
        else:
            return [SlotSet("conversation_turn", updated_turn)]

# Handles cases where the assistant does not understand user input
class ActionDefaultFallback(Action):
    def name(self):
        return "action_default_fallback"

    def run(self, dispatcher, tracker, domain):
        dispatcher.utter_message("Sorry, I did not understand that. Can you rephrase, please?")
        return []

# Asks user if they want to rebook the same restaurant as before
class ActionAskPastBookingFollowUp(Action):
    def name(self) -> Text:
        return "action_ask_if_rebook"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[EventType]:

        past_restaurant = tracker.get_slot("past_restaurant_name")

        if past_restaurant:
            dispatcher.utter_message(
                text=f"I see you've booked at {past_restaurant} before. Would you like to book there again?"
            )
        else:
            dispatcher.utter_message(
                text="No problem, let’s find a restaurant for you!"
            )
        return []

# Validation class for the full booking form (new bookings)
class ValidateRestaurantForm(FormValidationAction):
    def name(self) -> Text:
        return "validate_restaurant_form"

    async def required_slots(
        self,
        domain_slots,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any]
    ) -> List[Text]:
        slots = [
            "past_bookings",
            "cuisine_preferences",
            "dietary_preferences",
            "time_of_booking",
            "day_of_booking",
            "num_of_guests"
        ]

        # If user has past bookings, check if restaurant is known
        if tracker.get_slot("past_bookings"):
            restaurant = tracker.get_slot("past_restaurant_name")

            if not restaurant:
                dispatcher.utter_message(response="utter_ask_past_restaurant_name")
                return ["past_restaurant_name"]

            # Ask if user wants to rebook only if this hasn't been asked yet
            if tracker.get_slot("rebook") is None:
                dispatcher.utter_message(
                    text=f"I see you've booked at {restaurant} before. Would you like to book there again?"
                )
                return ["rebook"]

            # If they want to rebook, switch to minimal rebook slots
            if tracker.get_slot("rebook") is True:
                return ["time_of_booking", "day_of_booking", "num_of_guests"]

        return slots


# Validation class for the rebooking form (existing restaurant)
class ValidateRebookForm(FormValidationAction):
    def name(self) -> Text:
        return "validate_rebook_form"

    # Defines only time, date and guest count for rebooking
    def required_slots(self, domain_slots, dispatcher, tracker, domain) -> List[Text]:
        return [
            "time_of_booking",
            "day_of_booking",
            "num_of_guests"
        ]
