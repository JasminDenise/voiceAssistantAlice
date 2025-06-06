import json
import random
import logging
import inspect
from typing import Any, Text, Dict, List
from rasa_sdk import Action, Tracker
from rasa_sdk.executor import CollectingDispatcher
from rasa_sdk.forms import FormValidationAction 
from rasa_sdk.types import DomainDict
from rasa_sdk.events import SlotSet, FollowupAction, EventType, AllSlotsReset
from sklearn.metrics.pairwise import cosine_similarity
from datetime import datetime
from joblib import load


# logging fallbacks
# 1) Create  logger for this module
logger = logging.getLogger(__name__)
logger.setLevel(logging.WARNING)

# 2) Create  file handler which logs WARNING (and above) to 'fallbacks.log'
fh = logging.FileHandler("logs/fallbacks.log")
fh.setLevel(logging.WARNING)

# 3) Add a formatter to get timestamps, levels &d messages
formatter = logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s",
                              datefmt="%Y-%m-%d %H:%M:%S")
fh.setFormatter(formatter)

# 4) Attach handler to your logger
logger.addHandler(fh)


def check_turns(fn):
    async def wrapper(self, slot_value, dispatcher, tracker, domain):
        # 1) compute new turn count
        current = tracker.get_slot("turn_counter") or 0
        new_count = current + 1

        # 2) if we've reached or exceeded the max, go ahead with suggestion
        if new_count >= getattr(self, "MAX_TURNS", float("inf")):
            dispatcher.utter_message(response="utter_max_reached")
            return [
                SlotSet("turn_counter", new_count),
                FollowupAction("action_suggest_restaurant")
            ]

        # 3) otherwise, run the normal validator
        if inspect.iscoroutinefunction(fn):
            result = await fn(self, slot_value, dispatcher, tracker, domain)
        else:
            result = fn(self, slot_value, dispatcher, tracker, domain)

        # 4) inject the updated turn_counter into whatever the validator returned (e.g. a dict)
        if isinstance(result, dict):
            result["turn_counter"] = new_count
            return result
        if isinstance(result, list):
            return [SlotSet("turn_counter", new_count)] + result

        # 5) fallback: just increment the counter
        return {"turn_counter": new_count}

    return wrapper

# based on: https://legacy-docs-oss.rasa.com/docs/rasa/forms/#validating-form-input
class ValidateRestaurantForm(FormValidationAction):
    MAX_TURNS = 10
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
            """Dynamically ask only the needed slots, and don’t re-ask past_bookings once set."""
            # Immediate cancel check 
            if  tracker.latest_message["intent"].get("name") == "cancel":
                # inform user 
                dispatcher.utter_message(response="utter_booking_canceled")
                return []  # returning empty list -> deactivate the form

            
             # 1) If they already gave a past_restaurant_name, skip the booking‐check
            if tracker.get_slot("past_restaurant_name"):
                return ["date_and_time", "num_of_guests"]

            # 2) If we don’t yet know whether they’ve booked before, ask that first
            if tracker.get_slot("past_bookings") is None:
                return ["past_bookings"]

            # 3) They’ve said yes -> rebooking path
            if tracker.get_slot("past_bookings"):
                return ["past_restaurant_name", "date_and_time", "num_of_guests"]

            # 4) They’ve said no -> full new booking path
            return ["cuisine_preferences", "dietary_preferences", "date_and_time", "num_of_guests"]

    @check_turns
    async def validate_past_bookings(
        self,
        slot_value: Any,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: DomainDict,
    ) -> Dict[Text, Any]:
        

        # check if past_restaurant_name was already provided
        # if user said "yes" but no restaurant yet, ask for it next

        # Get the last intent 
        last_intent = tracker.latest_message["intent"].get("name")

        # Set value here based on intent because automatic intent mapping doesn't worked as intented
        if last_intent == "affirm":
            return {"past_bookings": True}
        elif last_intent == "deny":
            return {"past_bookings": False, "dietary_preferences": None}
        
        # if past_restaurant_name was already provided then past_bookings is True
        if tracker.get_slot("past_restaurant_name") is not None:
            return {"past_bookings": True}
        
        return {"past_bookings": slot_value}

    @check_turns
    async def validate_past_restaurant_name(
        self,
        slot_value: Any,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: DomainDict,
    ) -> Dict[Text, Any]:
        
        
        # set past booking to true if restaurant name was provided 
        if  slot_value:
            return {"past_restaurant_name": slot_value, "past_bookings": True} 
        return {}

    @check_turns
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

    @check_turns
    async def validate_dietary_preferences(self, slot_value, dispatcher, tracker, domain):
        # 1) if bot asking for diet and user said “no”, map immediately
        if tracker.get_slot("requested_slot") == "dietary_preferences" \
        and tracker.latest_message["intent"].get("name") == "deny":
            return {"dietary_preferences": ["omnivore"]}

        # 2) normalize whatever actually came in from the extractor
        values: List[str] = []
        if isinstance(slot_value, list):
            for v in slot_value:
                if isinstance(v, list):
                    values.extend(v)
                else:
                    values.append(v)
        elif isinstance(slot_value, str):
            values = [slot_value]
        else:
            # truly nothing at all
            return {"dietary_preferences": None}

        # 3) now your DB‐check on values
        invalid = [v for v in (v.lower() for v in values)
                if v not in self.dietary_db()]
        if invalid:
            dispatcher.utter_message(
                f"Sorry, I don’t offer {', '.join(invalid)}. "
                f"I only support: {', '.join(self.dietary_db())}."
            )
            return {"dietary_preferences": None}

        return {"dietary_preferences": values}

    @check_turns
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

        except Exception:
            return {"date_and_time": None}
        
        # check if user only gave date (default time is 00:00:00) + ask again
        if dt.time().hour == 0 and dt.time().minute == 0:
            dispatcher.utter_message(
                "It looks like you only gave me a date."
            )
            return {"date_and_time": None}
        return {"date_and_time": slot_value}

    @check_turns
    async def validate_num_of_guests(
        self,
        slot_value: Any,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: DomainDict,
    ) -> Dict[Text, Any]:
        

         # 1) Direct cast (most common if slot_value = "3")
        try:
            guests = int(slot_value)
            if guests < 1:
                raise ValueError()
            return {"num_of_guests": guests}
        except Exception:
            pass

        # 2) Fallback: look for a Duckling number entity
        for ent in tracker.latest_message.get("entities", []):
            if ent.get("entity") == "number":
                try:
                    guests = int(float(ent.get("value")))
                    if guests < 1:
                        raise ValueError()
                    return {"num_of_guests": guests}
                except Exception:
                    break

        # 3) Still failing -> Ask again
        return {"num_of_guests": None}


class ActionSuggestRestaurant(Action):
    """
      Suggests a restaurant by TF–IDF similarity on "cuisine + diet".

    - Uses content-based filtering (TF–IDF encoding) and cosine similarity for ranking
    - Filters strictly by dietary preference 
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
        dt    = tracker.get_slot("date_and_time")
        guests    = int(tracker.get_slot("num_of_guests") or 1)
    
        # normalize diet -> empty means “no restriction”
        diet = [d for d in raw_diet if d not in self.omnivore_synonyms]


        # --------------------------------
        # 2) Parse and validate datetime
        # --------------------------------
     
        dt_obj = datetime.fromisoformat(dt)
       
        # If only a date is provided without time, prompt user again
        if dt_obj.hour == 0 and dt_obj.minute == 0:
            dispatcher.utter_message(
                "It seems you only provided a date. Please include a time as well."
            )
            return [
                SlotSet("date_and_time", None), # clear slot value
                FollowupAction("restaurant_form") # re‑activate the form so it asks for date_and_time again
            ]
        
        day  = dt_obj.date().isoformat() # save date
        time = dt_obj.time().strftime("%I:%M %p").lstrip("0") # save time in 12-hour format

        # ------------------------------
        # 3) Rebooking path
        # ------------------------------
        if past and past_name:
            restaurant = next(
                (r for r in self.restaurants if r["name"].lower() == past_name.lower()),
                None
            )
            # Check if named restaurant is available
            if restaurant and self._is_available(restaurant, guests, day, time):
                dispatcher.utter_message(
                    f"Great news! {restaurant['name']} is available for {guests} guests on {day} at {time}. Would you like to book it?"
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
                    f"I'm sorry, {restaurant['name']} is not available at that time. How about {alt['name']} instead?"
                )
                return [SlotSet("past_restaurant_name", alt["name"])] # overwrite with new restaurant
            else:
                dispatcher.utter_message(
                    f"Sorry, no {alt_cuisine.title()} restaurants are available at that time."
                )
            return []

        # --------------------------------------------------
        # 4) New booking: content-based filtering
        # --------------------------------------------------
        # Build a preference string for TF–IDF vectorization, e.g. "italian vegetarian"
        pref_text = " ".join(cuisine + diet).strip()
        query_vec = self.vectorizer.transform([pref_text]) # TF–IDF vector 

        # compute similarity score across all restaurants
        sim_score      = cosine_similarity(query_vec, self.restaurant_vecs).flatten()
        best_id  = int(sim_score.argmax()) # position of the highest score 
        best_r = self.restaurants[best_id] # top scoring restaurant

        # check if the diet is still correct
        if diet:
            r_options = [o.lower() for o in best_r.get("dietary_options", [])]
            if any(d not in r_options for d in diet):
                 # pick the first cuisine the user asked for (or fallback to “selected”)
                user_cuisine = cuisine[0].title() if cuisine else "suitable"
                dispatcher.utter_message(
                    f"Sorry, I couldn’t find any {user_cuisine} restaurant that offers {', '.join(diet)} food."
                )
                return []

        # finally check availability
        if self._is_available(best_r, guests, day, time):
            dispatcher.utter_message(
                f"Based on your preferences, I recommend {best_r['name']}. It offers {best_r['cuisine']} cuisine "
                f"and can seat {guests} on {day} at {time}. Shall I book it?"
            )
            return []
        else:
            dispatcher.utter_message(
                f"I'm sorry, {best_r['name']} meets your preferences but isn’t available then. "
                 "Please provide another date and time slot."
            )
            # clear only the date so form can re‑ask it
            return [
                  SlotSet("date_and_time", None),
                  #FollowupAction("restaurant_form")
            ]
    #helper function
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


class ActionClearSlots(Action):
    def name(self) -> str:
        return "action_clear_slots"

    async def run(self, dispatcher, tracker, domain):
        dispatcher.utter_message(response="utter_clear_slots")
        return [AllSlotsReset()]

# logging fallbacks
class ActionLogAndFallback(Action):
    def name(self) -> str:
        return "action_log_and_fallback"

    async def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: dict,
    ):
        # 1) Log the fallback event
        user_msg = tracker.latest_message.get("text")
        turn    = tracker.get_slot("turn_counter") or "?"
        logger.warning(f"FALLBACK triggered at turn {turn}: \"{user_msg}\"")

        # 2) Notify the user
        dispatcher.utter_message(response="utter_default")

        # 3)  reset slots to start fresh
        return [AllSlotsReset()]