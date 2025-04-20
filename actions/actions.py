import json
from typing import Any, Text, Dict, List
from rasa_sdk import Action, Tracker
from rasa_sdk.events import AllSlotsReset
from rasa_sdk.executor import CollectingDispatcher
from rasa_sdk.forms import FormValidationAction 
from rasa_sdk.types import DomainDict
from rasa_sdk.events import SlotSet
from sklearn.metrics.pairwise import cosine_similarity
from datetime import datetime
from joblib import load
import random

# based on: https://legacy-docs-oss.rasa.com/docs/rasa/forms/#validating-form-input

class ValidateRestaurantForm(FormValidationAction):
    def name(self) -> Text:
        return "validate_restaurant_form"

    # valid cuisines
    @staticmethod
    def cuisine_db() -> List[Text]:
        return ["italian", "mexican", "japanese", "indian", "chinese",
                "french", "fusion", "thai", "korean", "german"]

    # valid dietary options
    @staticmethod
    def dietary_db() -> List[Text]:
        return ["vegan", "vegetarian", "gluten-free", "halal",
                "kosher", "lactose-free", "omnivore", "pescatarian"]

    # overwrite required slots 
    async def required_slots(
        self,
        domain_slots: List[Text],
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: DomainDict,
    ) -> List[Text]:
        # always ask whether they’ve booked before
        slots = ["past_bookings"]
        if tracker.get_slot("past_bookings") is True:
            # rebooking path: only need restaurant name, datetime & guests
            slots += ["past_restaurant_name", "date_and_time", "num_of_guests"]
        elif tracker.get_slot("past_bookings") is False:
            # new booking: all the details are required
            slots += [
                "cuisine_preferences",
                "dietary_preferences",
                "date_and_time",
                "num_of_guests",
            ]
        return slots

    def validate_past_bookings(
        self,
        slot_value: Any,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: DomainDict,
    ) -> Dict[Text, Any]:
        # check if past_restaurant_name was already provided
        # if user said yes but no restaurant yet, ask for it next

         # Get the last intent
        last_intent = tracker.latest_message["intent"].get("name")

        # Set value here based on intent because automatic intent mapping doesn't work 
        if last_intent == "affirm":
            return {"past_bookings": True}
        elif last_intent == "deny":
            return {"past_bookings": False}
        
        # if past_restaurant_name was already provided then past_bookings is True
        if tracker.get_slot("past_restaurant_name") is not None:
            return {"past_bookings": True}
        
        return {"past_bookings": slot_value}

    def validate_past_restaurant_name(
        self,
        slot_value: Any,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: DomainDict,
    ) -> Dict[Text, Any]:
        # set past booking to true if restaurant name was provided TODOO
        if not slot_value == None:
            return {"past_restaurant_name": slot_value, "past_bookings": True} 

    async def validate_cuisine_preferences(
        self,
        slot_value: List[Text],
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: DomainDict,
    ) -> Dict[Text, Any]:
        # check if there are any invalid cuisine preferences
        invalid = [v for v in (v.lower() for v in slot_value) if v not in self.cuisine_db()]
        if invalid:
            dispatcher.utter_message(
                f"Sorry, I don’t offer {', '.join(invalid)}. I only support: {', '.join(self.cuisine_db())}."
            )
            return {"cuisine_preferences": None}
        return {"cuisine_preferences": slot_value}

    async def validate_dietary_preferences(
        self,
        slot_value: List[Text],
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: DomainDict,
    ) -> Dict[Text, Any]:
        last_intent = tracker.get_intent_of_latest_message()
        # Handle case where user says "no", "none", or similar
        if last_intent == "deny":
            dispatcher.utter_message("Got it, I’ll assume you have no special dietary needs.")
            return {"dietary_preferences": ["omnivore"]}

        invalid = [v for v in (v.lower() for v in slot_value) if v not in self.dietary_db()]
        if invalid:
            dispatcher.utter_message(
                f"Sorry, I don’t offer {', '.join(invalid)}. I only support: {', '.join(self.dietary_db())}."
            )
            return {"dietary_preferences": None}
        return {"dietary_preferences": slot_value}

    async def validate_date_and_time(
        self,
        slot_value: Any,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: DomainDict,
    ) -> Dict[Text, Any]:
        # check if there is a valid datetime
        try:
            dt = datetime.fromisoformat(slot_value)
            # print(dt)
            # print(dt.time())
            # print(dt.time().hour)
            # print(dt.time().minute)
        except Exception:
            return {"date_and_time": None}
        
        # check if user only gave date (default time is 00:00:00) + ask again
        if dt.time().hour == 0 and dt.time().minute == 0:
            dispatcher.utter_message(
                "It looks like you only gave me a date."
            )
            return {"date_and_time": None}
        return {"date_and_time": slot_value}

    async def validate_num_of_guests(
        self,
        slot_value: Any,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: DomainDict,
    ) -> Dict[Text, Any]:
        try:
            guests = int(slot_value)
            if guests < 1:
                raise ValueError()
            return {"num_of_guests": guests}
        except Exception:
            dispatcher.utter_message("Please provide a valid number of guests. It needs to be at least one person.")
            return {"num_of_guests": None}


class ActionSuggestRestaurant(Action):
    """
    Suggests a restaurant prioritizing dietary restrictions over cuisine.

    - Uses content-based TF–IDF encoding and cosine similarity for ranking
    - Filters strictly by dietary preference (unless treated as no restriction)
    - If no restaurant meets diet and availability, returns an apology
    """

    def __init__(self):
        # ----------------------------------------------------------------
        # One-time initialization: load restaurant data and TF–IDF resources
        # ----------------------------------------------------------------
        with open("data/restaurants.json") as f:
            self.restaurants = json.load(f)
        self.vectorizer      = load("vectorizer/vectorizer.joblib")
        self.restaurant_vecs = load("vectorizer/restaurant_vectors.joblib")
        # Simple in-memory cache to store TF–IDF vectors for preference strings
        self.tf_cache = {}
        # Synonyms interpreted as no dietary restriction (i.e., omnivore)
        self.omnivore_synonyms = {"omnivore", "none", "no preference", "anything", "no dietary restrictions"}

    def name(self) -> Text:
        # Name of the action as defined in domain.yml
        return "action_suggest_restaurant"

    def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> List[Dict[Text, Any]]:
        # ------------------------------
        # 1) Extract all relevant slots
        # ------------------------------
        past      = tracker.get_slot("past_bookings")
        past_name = tracker.get_slot("past_restaurant_name")
        cuisine   = [c.lower() for c in (tracker.get_slot("cuisine_preferences") or [])]
        raw_diet  = [d.lower() for d in (tracker.get_slot("dietary_preferences") or [])]
        dt_iso    = tracker.get_slot("date_and_time")
        guests    = int(tracker.get_slot("num_of_guests") or 1)

        # Determine whether to apply dietary filter
        diet = []
        for d in raw_diet:
            if d in self.omnivore_synonyms:
                diet = []  # no restriction if synonym detected
                break
            diet.append(d)

        # --------------------------------
        # 2) Parse and validate datetime
        # --------------------------------
        # if not dt_iso:
        #     dispatcher.utter_message("When would you like to dine?")
        #     return []
        dt_obj = datetime.fromisoformat(dt_iso)
        # If only a date is provided without time, prompt user again
        if dt_obj.hour == 0 and dt_obj.minute == 0:
            dispatcher.utter_message(
                "It seems you only provided a date. Please include a time as well."
            )
            return [SlotSet("date_and_time", None)]
        day  = dt_obj.date().isoformat()
        time = dt_obj.time().strftime("%I:%M %p").lstrip("0")

        # ------------------------------
        # 3) Rebooking path
        # ------------------------------
        if past and past_name:
            restaurant = next(
                (r for r in self.restaurants if r["name"].lower() == past_name.lower()),
                None
            )
            if restaurant and self._is_available(restaurant, guests, day, time):
                dispatcher.utter_message(
                    f"{restaurant['name']} is available for {guests} guests on {day} at {time}. Would you like to book it?"
                )
                return []
            # Suggest an alternative from the same cuisine
            alt_cuisine = restaurant.get("cuisine", "").lower() if restaurant else None
            candidates = [
                r for r in self.restaurants
                if r.get("cuisine", "").lower() == alt_cuisine
                   and self._is_available(r, guests, day, time)
            ]
            if candidates:
                alt = random.choice(candidates)
                dispatcher.utter_message(
                    f"{restaurant['name']} is not available at that time. How about {alt['name']} instead?"
                )
            else:
                dispatcher.utter_message(
                    f"No {alt_cuisine.title()} restaurants are available at that time."
                )
            return []

        # --------------------------------------------------
        # 4) New booking: prioritize dietary restrictions
        # --------------------------------------------------
        # Build a preference string for TF–IDF vectorization, e.g. "italian vegetarian"
        pref_text = " ".join(cuisine + diet).strip()
        # Retrieve from cache or compute and store
        if pref_text in self.tf_cache:
            query_vec = self.tf_cache[pref_text]
        else:
            query_vec = self.vectorizer.transform([pref_text])
            self.tf_cache[pref_text] = query_vec

        # Apply dietary filter if applicable
        filtered = self.restaurants
        if diet:
            filtered = [
                r for r in self.restaurants
                if all(d in (r.get("dietary_options") or []) for d in diet)
            ]
            if not filtered:
                dispatcher.utter_message(
                     f"No restaurants match your dietary requirements for {day} at {time}. "
                    "Would you like to try a different date or time?"
                )
                return []

        # Compute cosine similarity scores on the filtered subset
        indices     = [self.restaurants.index(r) for r in filtered]
        sub_vectors = self.restaurant_vecs[indices]
        sims        = cosine_similarity(query_vec, sub_vectors).flatten()

        # Choose best match by highest similarity score
        best_idx  = int(sims.argmax())
        best_rest = filtered[best_idx]

        # Check availability of the best match
        if self._is_available(best_rest, guests, day, time):
            dispatcher.utter_message(
                f"I recommend {best_rest['name']}. It offers {best_rest['cuisine']} cuisine, "
                f"has options {', '.join(best_rest.get('dietary_options', []))}, "
                f"and can seat {guests} on {day} at {time}. Should I book it?"
            )
        else:
            dispatcher.utter_message(
                f"{best_rest['name']} meets your preferences but is not available at that time. Would you like a reservation on another day?"
            )
        return []

    def _is_available(self, restaurant: Dict, guests: int, day: str, time: str) -> bool:
        """
        Determine if a given restaurant has availability for the specified day, time, and guest count.
        """
        try:
            weekday = datetime.fromisoformat(day).strftime("%A")
            slots   = restaurant.get("availability", {}).get(weekday, [])
            return (time in slots) and (restaurant.get("max_guests", 0) >= guests)
        except Exception:
            return False


# class ActionSuggestRestaurant(Action):
#     def __init__(self):
#         # Load restaurant data and pretrained TF–IDF model once at startup
#         with open("data/restaurants.json") as f:
#             self.restaurants = json.load(f)
#         self.vectorizer      = load("vectorizer/vectorizer.joblib")
#         self.restaurant_vecs = load("vectorizer/restaurant_vectors.joblib")
#         self.tf_cache = {}

#     def name(self) -> Text:
#         return "action_suggest_restaurant"

#     def run(
#         self,
#         dispatcher: CollectingDispatcher,
#         tracker: Tracker,
#         domain: Dict[Text, Any],
#     ) -> List[Dict[Text, Any]]:
#         # Pull slots
#         past       = tracker.get_slot("past_bookings")
#         past_name  = tracker.get_slot("past_restaurant_name")
#         cuisine    = [c.lower() for c in (tracker.get_slot("cuisine_preferences") or [])]
#         diet       = [d.lower() for d in (tracker.get_slot("dietary_preferences") or [])]
#         dt     = tracker.get_slot("date_and_time")
#         guests     = int(tracker.get_slot("num_of_guests") or 1)

#         # Parse & validate datetime
#         if not dt:
#             dispatcher.utter_message("When would you like to dine?")
#             return []
#         dt_obj = datetime.fromisoformat(dt)
#         if dt_obj.hour == 0 and dt_obj.minute == 0:
#             dispatcher.utter_message("It looks like you only gave me a date. Could you include a time, please?")
#             return [SlotSet("date_and_time", None)]
#         day   = dt_obj.date().isoformat()
#         time  = dt_obj.time().strftime("%I:%M %p").lstrip("0")

#         # 1) Rebooking path
#         if past and past_name:
#             restaurant = next(
#                 (r for r in self.restaurants if r["name"].lower() == past_name.lower()),
#                 None
#             )
#             if restaurant and self._is_available(restaurant, guests, day, time):
#                 dispatcher.utter_message(
#                     f"Great news! {restaurant['name']} is free for {guests} on {day} at {time}. Shall I book it for you?"
#                 )
#                 return []
#             # Offer same-cuisine alternative
#             alt_cuisine = restaurant["cuisine"].lower() if restaurant else None
#             candidates = [
#                 r for r in self.restaurants
#                 if r["cuisine"].lower() == alt_cuisine
#                    and self._is_available(r, guests, day, time)
#             ]
#             if candidates:
#                 alt = random.choice(candidates)
#                 dispatcher.utter_message(
#                     f"Sorry, {restaurant['name']} isn't available then. How about {alt['name']}? It's also {alt_cuisine.title()} cuisine."
#                 )
#             else:
#                 dispatcher.utter_message(
#                     f"Sorry, no {alt_cuisine.title()} restaurant is available at that time."
#                 )
#             return []

#         # 2) New booking: recommendation
#         pref_text = " ".join(cuisine + diet).strip()
#         if pref_text in self.tf_cache:
#             query_vec = self.tf_cache[pref_text]
#         else:
#             query_vec = self.vectorizer.transform([pref_text])
#             self.tf_cache[pref_text] = query_vec

#         # Filter to user-requested cuisines
#         candidates = [
#             (r, idx) for idx, r in enumerate(self.restaurants)
#             if r["cuisine"].lower() in cuisine
#         ]
#         if not candidates:
#             return self._fallback(dispatcher, day, time, guests)

#         # Compute similarity on that subset
#         indices     = [idx for _, idx in candidates]
#         sub_vectors = self.restaurant_vecs[indices]
#         sims        = cosine_similarity(query_vec, sub_vectors).flatten()

#         # Choose top match
#         best_i       = int(sims.argmax())
#         best_rest, _ = candidates[best_i]

#         if self._is_available(best_rest, guests, day, time):
#             dispatcher.utter_message(
#                 f"Based on your preferences, I recommend {best_rest['name']}. It offers {best_rest['cuisine']} cuisine and has {', '.join(best_rest.get('dietary_options', []))} options. They can seat {guests} on {day} at {time}. Shall I book it?"
#             )
#             return []
#         return self._fallback(dispatcher, day, time, guests)

#     def _is_available(self, restaurant: Dict, guests: int, day: str, time: str) -> bool:
#         """
#         Check if a restaurant has an open slot and enough capacity.
#         """
#         try:
#             weekday = datetime.fromisoformat(day).strftime("%A")
#             slots   = restaurant.get("availability", {}).get(weekday, [])
#             return (time in slots) and (restaurant.get("max_guests", 0) >= guests)
#         except Exception as e:
#             print(f"Availability error: {e}")
#             return False

#     def _fallback(
#         self,
#         dispatcher: CollectingDispatcher,
#         day: str,
#         time: str,
#         guests: int,
#     ) -> List[Dict[Text, Any]]:
#         """Fallback: recommend any available restaurant at random."""
#         available = [
#             r for r in self.restaurants
#             if self._is_available(r, guests, day, time)
#         ]
#         if available:
#             fb = random.choice(available)
#             dispatcher.utter_message(
#                 f"I couldn’t find a match in your cuisines, but {fb['name']} is free then. Shall I book it for you?"
#             )
#         else:
#             dispatcher.utter_message(
#                 f"Sorry, no tables are available for {guests} on {day} at {time}."
#             )
#         return []

# class ActionSuggestRestaurant(Action):
#     def __init__(self):
#          # Runs once at startup: load restaurant data and pretrained TF–IDF model + vectors
#         with open("data/restaurants.json") as f:
#             self.restaurants = json.load(f)
#         # load precomputed vectorizer and vectors -> reduce computation time
#         self.vectorizer      = load("vectorizer/vectorizer.joblib")
#         self.restaurant_vecs = load("vectorizer/restaurant_vectors.joblib")
#         # Simple cache mapping "pref_text" -> precomputed query_vec
#         self.tf_cache = {}
#     def name(self) -> Text:
#         return "action_suggest_restaurant"

#     def run(
#         self,
#         dispatcher: CollectingDispatcher,
#         tracker: Tracker,
#         domain: Dict[Text, Any],
#     ) -> List[Dict[Text, Any]]:

    

#          # --- helper: check availability for given restaurant, date and time ---
#         def is_available(restaurant: Dict, guests: int, day: str, time: str) -> bool:

#             try:
#                 weekday = datetime.fromisoformat(day).strftime("%A") # convert day and time to datetime object and format it to string with weekday
#                 available_times = restaurant.get("availability", {}).get(weekday, []) # get available times of the day

#                 if time in available_times and restaurant.get("max_guests", 0) >= guests:
#                     return True # table is avilable
#                 return False
#             except Exception as e:
#                 print(f"Error checking availability: {e}")
#                 return False # table is not avilable

#         # pull all rleevant slots 
#         past = tracker.get_slot("past_bookings")
#         past_name = tracker.get_slot("past_restaurant_name")
#         cuisine = tracker.get_slot("cuisine_preferences") or []
#         diet = tracker.get_slot("dietary_preferences") or []
#         dt = tracker.get_slot("date_and_time")  
#         guests = int(tracker.get_slot("num_of_guests") or 1)  

#         # parse & validate datetime slot
#         day, time = None, None
#         if dt:
#             obj = datetime.fromisoformat(dt) # convert to python datetime object

#         #  if user only gave date (default: 00:00 time), ask again
#         if obj.time().hour == 0 and obj.time().minute == 0:
#                 dispatcher.utter_message(
#                     "It looks like you only gave me a date."
#                 )
#                 return {"date_and_time": None}
                
#         day = obj.date().isoformat()
#         time = obj.time().strftime("%I:%M %p").lstrip("0") 
#             # print(time)


        
#         # 1) Rebooking path: User wants to rebook a past restaurant
#         if past and past_name:

#             # check if mentioned restaurant exists
#             restaurant = next(
#                 (r for r in self.restaurants if r["name"].lower() == past_name.lower()), None # returns None if no restaurant found -> handle it TODOO
#             )

#             if restaurant and day and time and is_available(restaurant, guests, day, time):
#                 dispatcher.utter_message(
#                     f"Great news! {restaurant['name']} is available for {guests} on "
#                     f"{day} at {time}. Shall I book it for you?"
#                 )
#             else:
#                 #  offer an alternative restaurant with same cuisine if the original is unavailable
#                 alt_cuisines = (
#                     [restaurant["cuisine"].lower()] if restaurant else None
#                 )  # could be expanded later with user preferences

#                 # Get all candidates that match any of the preferred cuisines and are available
#                 candidates = [
#                     r for r in self.restaurants
#                     if r["cuisine"].lower() == alt_cuisines
#                     and is_available(r, guests, day, time)
#                 ]
#                 if candidates:
#                     alt = random.choice(candidates) # pick a random alternative or: alt = sorted(candidates, key=lambda r: r["name"])[0]
#                     dispatcher.utter_message(
#                         f"Sorry, {restaurant['name']} is not available for that time and date. How about "
#                         f"{alt['name']} instead? It’s the same {alt_cuisines} cuisine."
#                     )
#                 else:
#                     # could not find an alternative with same cuisine
#                     dispatcher.utter_message(
#                         f"Sorry, no {alt_cuisines.title()} restaurant is available at that time."
#                     )
       
#             return []

#         # 2) New booking: content‑based recommendation
#         # build preference string e.g. "italian vegetarian"
#         pref_text = " ".join(cuisine + diet).strip()

#         # fetch or compute TF–IDF vector for these preferences
#         if pref_text in self.tf_cache:
#             query_vec = self.tf_cache[pref_text]
#         else:
#             query_vec = self.vectorizer.transform([pref_text])
#             self.tf_cache[pref_text] = query_vec

#         # pre‑filter restaurants to only those cuisines user asked for
#         candidates = [
#             (r, idx) for idx, r in enumerate(self.restaurants)
#             if r["cuisine"].lower() in cuisine
#         ]

#         # if no candidate of requested cuisine, go directly to fallback
#         if not candidates:
#             return self._fallback(dispatcher, day, time, guests)

#         # compute similarities only on the filtered subset
#         indices     = [idx for _, idx in candidates]
#         sub_vectors = self.restaurant_vecs[indices]
#         sims        = cosine_similarity(query_vec, sub_vectors).flatten()

#         # pick the best match among those
#         best_i      = int(sims.argmax())
#         best_rest, _ = candidates[best_i]

#         if is_available(best_rest, guests, day, time):
#             dispatcher.utter_message(
#                 f"Based on your preferences, I recommend {best_rest['name']}. "
#                 f"It offers {best_rest['cuisine']} cuisine and has "
#                 f"{', '.join(best_rest.get('dietary_options', []))} options. "
#                 f"They can seat {guests} on {day} at {time}. Shall I book it?"
#             )
#             return []
#         else:
#             # if top match isn't open, fallback
#             return self._fallback(dispatcher, day, time, guests)

#     def _fallback(
#         self,
#         dispatcher: CollectingDispatcher,
#         day: str,
#         time: str,
#         guests: int,
#     ) -> List[Dict[Text, Any]]:
#         """Fallback: pick any available restaurant at that slot, at random."""
#         available = [
#             r for r in self.restaurants
#             if is_available(r, guests, day, time)
#         ]
#         if available:
#             fb = random.choice(available)
#             dispatcher.utter_message(
#                 f"I couldn’t find an exact cuisine match, but {fb['name']} is free at that time. "
#                 f"Shall I book {fb['name']} on {day} at {time} for you?"
#             )
#         else:
#             dispatcher.utter_message(
#                 f"Sorry, no tables are available for {guests} on {day} at {time}."
#             )
#         return []
    #*************


        # # build preference string e.g. Italian Vegetarian -> query will be compared with each restaurant
        # cuisine_text = " ".join(cuisine) if isinstance(cuisine, list) else cuisine or ""
        # diet_text = " ".join(diet) if isinstance(diet, list) else diet or ""
        # pref_text = f"{cuisine_text} {diet_text}".strip()
        # # print("User Preferences (pref_text):", pref_text)
        # # print(type(pref_text))
        

        # #Transform user input into the same vector space as restaurant vectors
        # query_vec = vectorizer.transform([pref_text.lower()])
        # #Compute cosine similarity between the transformed user input and restaurant vectors
        # scores = cosine_similarity(query_vec, restaurant_vectors).flatten() # convert to 1D array
        # # print("Query Vector (query_vec):", query_vec)
        # # print("Cosine Similarity Scores:", scores)
        # # # TF‑IDF & cosine similarity: vectorize text and compare
        # # vec = TfidfVectorizer().transform([pref_text] + texts)
        # # scores = cosine_similarity(vec[0:1], vec[1:]).flatten() # list of similarity scores, one per restaurant, based on how well it matches the query

        # # rank by similaroity score & pick first available (=most similar)
        # ranked = sorted(zip(restaurants, scores), key=lambda x: -x[1])
        # for r, sc in ranked:
        #     if day and time and is_available(r, guests, day, time):
        #         dispatcher.utter_message(
        #             f"Based on your preferences, I recommend {r['name']}. " 
        #             f"It offers {r['cuisine']} cuisine and has {', '.join(r.get('dietary_options', []))} options "
        #             f"and has a table for {guests} guests on {day} at {time}. Shall I book it?"
        #         )
        #         return []

        # # 3) fallback: random available
        # fallback = [
        #     r for r in restaurants
        #     if day and time and is_available(r, guests, day, time)
        # ]
        # if fallback:
        #     fallback_r = random.choice(fallback) # or: fallback_r = sorted(fallback, key=lambda r: r["name"])[0]
        #     dispatcher.utter_message(
        #         f"I couldn’t find an exact match, but {fallback_r['name']} is available at that time. "
        #         f"Shall I book it for you?"
        #     )
        # else:
        #     dispatcher.utter_message(
        #         f"Sorry, I couldn’t find any table for {guests} guests on {day} at {time}."
        #     )


        # return []




class ActionClearSlots(Action):
    def name(self) -> str:
        return "action_clear_slots"

    async def run(self, dispatcher, tracker, domain):
        dispatcher.utter_message(text="All set! I've cleared our previous conversation. Feel free to start a new booking whenever you're ready!")
        return [AllSlotsReset()]
