import json
from typing import Any, Text, Dict, List
from rasa_sdk import Action, Tracker
from rasa_sdk.executor import CollectingDispatcher
from rasa_sdk.events import SlotSet
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from datetime import datetime

class ActionSuggestRestaurant(Action):
    def name(self) -> Text:
        return "action_suggest_restaurant"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        
        # Extract user preferences
        cuisine_pref = tracker.get_slot("cuisine_preferences") or []  # This is now a list
        dietary_pref = tracker.get_slot("dietary_preferences") or []  # This is now a list
        num_of_guests = tracker.get_slot("num_of_guests") or 1  # Default to 1 guest if not provided
        date_and_time = tracker.get_slot("date_and_time") or ""  # Date and time combined slot
        
        # Extract time and date if available
        booking_time, booking_day = None, None
        if date_and_time:
            try:
                # Assuming Duckling provided a valid ISO datetime string (with both date and time)
                datetime_obj = datetime.fromisoformat(date_and_time)
                booking_time = datetime_obj.time().strftime('%H:%M:%S')
                booking_day = datetime_obj.date().strftime('%Y-%m-%d')
            except ValueError:
                dispatcher.utter_message("Sorry, I couldn't understand the time or date you provided.")
                return []

        # Combine preferences into a single search string for similarity comparison
        user_pref = " ".join(cuisine_pref) + " " + " ".join(dietary_pref)  # Combine multiple cuisines and dietary preferences

        # Load restaurant data from local JSON file
        with open("data/restaurants.json", "r") as file:
            restaurants = json.load(file)

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

        # Check if there's a matching restaurant with similarity score above threshold
        if all_matches and all_matches[0][1] > 0.2:
            best = all_matches[0][0]
            response = (
                f"Based on your preferences, I recommend {best['name']}, which serves {best['cuisine']} cuisine. "
                f"It offers {', '.join(best['dietary_options'])} options and has a rating of {best['rating']}."
            )
        else:
            # If no suitable match, suggest a fallback restaurant based on dietary preference and availability
            fallback_restaurant = self.suggest_fallback(dietary_pref, num_of_guests, restaurants, booking_time, booking_day)
            response = (
                f"Could not find an exact match based on your preferences. "
                f"How about trying **{fallback_restaurant['name']}**? It serves {fallback_restaurant['cuisine']} cuisine and offers {', '.join(fallback_restaurant['dietary_options'])} options."
            )

        dispatcher.utter_message(text=response)
        return []

    def suggest_fallback(self, dietary_pref: List[str], num_of_guests: int, restaurants: List[Dict[Text, Any]], time_of_booking: str, day_of_booking: str) -> Dict[Text, Any]:
        """Suggest a fallback restaurant based on dietary preference, number of guests, time and date."""
        
        # Filter restaurants by dietary preferences first
        filtered_restaurants = [
            r for r in restaurants if all(d.lower() in [option.lower() for option in r.get("dietary_options", [])] for d in dietary_pref)
        ]
        
        # If no match found based on dietary preference, send a fallback message
        if not filtered_restaurants:
            # No restaurant matching all dietary preferences
            return {"name": "No restaurant found", "cuisine": "N/A", "dietary_options": ["N/A"], "rating": "N/A"}

        # Further filter based on time, date, and number of guests (if available)
        if time_of_booking and day_of_booking and num_of_guests:
            filtered_restaurants = self.filter_by_time_date_and_guests(filtered_restaurants, time_of_booking, day_of_booking, num_of_guests)

        # If no filtered restaurants left, return the first available option
        return filtered_restaurants[0] if filtered_restaurants else restaurants[0]

    def filter_by_time_date_and_guests(self, restaurants: List[Dict[Text, Any]], time_of_booking: str, day_of_booking: str, num_of_guests: int) -> List[Dict[Text, Any]]:
        """Filter restaurants by time, date, and number of guests availability."""
        
        available_restaurants = []
        
        # Convert time_of_booking into datetime for easier comparison
        try:
            booking_time = datetime.strptime(time_of_booking, "%I:%M %p") if time_of_booking else None
        except ValueError:
            booking_time = None
        
        # Assuming day_of_booking is in format 'YYYY-MM-DD'
        try:
            booking_day = datetime.strptime(day_of_booking, "%Y-%m-%d") if day_of_booking else None
        except ValueError:
            booking_day = None

        # Check if restaurants are available based on time, date, and number of guests
        for restaurant in restaurants:
            if booking_time and booking_day:
                # Example logic: Assume each restaurant has a "availability" field with a list of datetime tuples and guest capacity
                for availability in restaurant.get("availability", []):
                    if availability['date'] == booking_day.date() and availability['time'] == booking_time.time() and availability['max_guests'] >= num_of_guests:
                        available_restaurants.append(restaurant)
                        break
            else:
                # If no time, date, or guest number is provided, just return the restaurant
                available_restaurants.append(restaurant)

        return available_restaurants
