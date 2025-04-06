import json
from typing import Any, Text, Dict, List
from rasa_sdk import Action, Tracker
from rasa_sdk.executor import CollectingDispatcher
from rasa_sdk.events import SlotSet, EventType
from rasa_sdk.forms import FormValidationAction
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

# -------------------------------------------------------------------
# Suggest a restaurant based on user preferences using content-based filtering
# -------------------------------------------------------------------
class ActionSuggestRestaurant(Action):
    def name(self) -> Text:
        return "action_suggest_restaurant"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:

        # Load restaurant data from local JSON file
        with open("data/restaurants.json", "r") as file:
            restaurants = json.load(file)

        # Get user preferences from slots
        cuisine_pref = tracker.get_slot("cuisine_preferences") or ""
        dietary_pref = tracker.get_slot("dietary_preferences") or ""

        # Combine preferences into a single search string
        user_pref = f"{cuisine_pref} {dietary_pref}".strip()

        # Prepare restaurant texts for similarity comparison
        restaurant_texts = [
            f"{r['name']} {r['cuisine']} {' '.join(r['dietary_options'])}" for r in restaurants
        ]

        # TF-IDF encoding + cosine similarity (content-based filtering)
        vectorizer = TfidfVectorizer()
        vectors = vectorizer.fit_transform([user_pref] + restaurant_texts)
        similarities = cosine_similarity(vectors[0:1], vectors[1:]).flatten()

        # Sort restaurants by similarity score
        all_matches = list(zip(restaurants, similarities))
        all_matches.sort(key=lambda x: x[1], reverse=True)

        # Recommend the best match or fallback message
        if all_matches and all_matches[0][1] > 0.2:
            best = all_matches[0][0]
            response = (
                f"I recommend **{best['name']}**, which serves {best['cuisine']} cuisine. "
                f"It offers {', '.join(best['dietary_options'])} options and has a rating of {best['rating']}."
            )
        else:
            response = (
                "I couldn't find any restaurant that fits your preferences right now. "
                "Want to try adjusting your request or tell me what you're in the mood for?"
            )

        dispatcher.utter_message(text=response)
        return []

# -------------------------------------------------------------------
# Track number of turns in the conversation to avoid infinite loops
# -------------------------------------------------------------------
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

# -------------------------------------------------------------------
# Fallback handler when bot doesn't understand user input
# -------------------------------------------------------------------
class ActionDefaultFallback(Action):
    def name(self):
        return "action_default_fallback"

    def run(self, dispatcher, tracker, domain):
        dispatcher.utter_message("Sorry, I did not understand that. Can you rephrase, please?")
        return []

# -------------------------------------------------------------------
# Ask user if they want to rebook their previously visited restaurant
# -------------------------------------------------------------------
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

# -------------------------------------------------------------------
# Validate and dynamically control the required slots in restaurant_form
# -------------------------------------------------------------------
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

        # Default required slots for all bookings
        slots = [
            "past_bookings",
            "cuisine_preferences",
            "dietary_preferences",
            "time_of_booking",
            "day_of_booking",
            "num_of_guests"
        ]

        # If user had past bookings, prompt for rebooking
        if tracker.get_slot("past_bookings"):
            restaurant = tracker.get_slot("past_restaurant_name")

            # Ask for restaurant name if missing
            if not restaurant:
                dispatcher.utter_message(response="utter_ask_past_restaurant_name")
                return ["past_restaurant_name"]

            # Ask if they want to rebook the same place
            if tracker.get_slot("rebook") is None:
                dispatcher.utter_message(
                    text=f"I see you've booked at {restaurant} before. Would you like to book there again?"
                )
                return ["rebook"]

        return slots
