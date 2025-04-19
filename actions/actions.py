import json
from typing import Any, Text, Dict, List
from rasa_sdk import Action, Tracker
from rasa_sdk.events import AllSlotsReset
from rasa_sdk.executor import CollectingDispatcher
# from rasa_sdk.events import SlotSet
from rasa_sdk.forms import FormValidationAction 
from rasa_sdk.types import DomainDict
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from datetime import datetime
import random

# based on: https://legacy-docs-oss.rasa.com/docs/rasa/forms/#validating-form-input

class ValidateRestaurantForm(FormValidationAction):
    def name(self) -> Text:
        return "validate_restaurant_form"

    @staticmethod
    def cuisine_db() -> List[Text]:
        return ["italian", "mexican", "japanese", "indian", "chinese",
                "french", "fusion", "thai", "korean", "german"]

    @staticmethod
    def dietary_db() -> List[Text]:
        return ["vegan", "vegetarian", "gluten-free", "halal",
                "kosher", "lactose-free", "omnivore", "pescatarian"]

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
            # re‑booking path: only need restaurant name, datetime & guests
            slots += ["past_restaurant_name", "date_and_time", "num_of_guests"]
        elif tracker.get_slot("past_bookings") is False:
            # new booking: all the details
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
        # intent mapping already gives True/False
        # if user said yes but no restaurant yet, ask for it next

         # Get the last intent
        last_intent = tracker.latest_message["intent"].get("name")

        # Set value based on intent
        if last_intent == "affirm":
            return {"past_bookings": True}
        elif last_intent == "deny":
            return {"past_bookings": False}
        
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
        if slot_value:
            return {"past_restaurant_name": slot_value, "past_bookings": True}

    async def validate_cuisine_preferences(
        self,
        slot_value: List[Text],
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: DomainDict,
    ) -> Dict[Text, Any]:
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
        try:
            dt = datetime.fromisoformat(slot_value)
            # print(dt)
            # print(dt.time())
            # print(dt.time().hour)
            # print(dt.time().minute)
        except Exception:
            dispatcher.utter_message(
                response="utter_ask_date_and_time"
            )
            return {"date_and_time": None}
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
    def name(self) -> Text:
        return "action_suggest_restaurant"

    def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> List[Dict[Text, Any]]:

        # load data
        with open("data/restaurants.json", "r") as f:
            restaurants = json.load(f)

        # common helpers
        def is_available(restaurant: Dict, guests: int, day: str, time: str) -> bool:
            try:
                weekday = datetime.fromisoformat(day).strftime("%A")
                available_times = restaurant.get("availability", {}).get(weekday, [])

                if time in available_times and restaurant.get("max_guests", 0) >= guests:
                    return True
                return False
            except Exception as e:
                print(f"Error checking availability: {e}")
                return False

        # pull slots
        past = tracker.get_slot("past_bookings")
        past_name = tracker.get_slot("past_restaurant_name")
        cuisine = tracker.get_slot("cuisine_preferences") or []
        diet = tracker.get_slot("dietary_preferences") or []
        dt = tracker.get_slot("date_and_time")  # ISO string
        guests = int(tracker.get_slot("num_of_guests") or 1)  

        # parse date & time
        day, time = None, None
        if dt:
            obj = datetime.fromisoformat(dt)

        # validate time
        if obj.time().hour == 0 and obj.time().minute == 0:
                dispatcher.utter_message(
                    "It looks like you only gave me a date."
                )
                return {"date_and_time": None}
                
        day = obj.date().isoformat()
        time = obj.time().strftime("%I:%M %p").lstrip("0") 
            # print(time)
        # 1) Re‑booking path
        if past and past_name:
            restaurant = next(
                (r for r in restaurants if r["name"].lower() == past_name.lower()), None
            )
            if restaurant and day and time and is_available(restaurant, guests, day, time):
                response = (
                    f"Great news! {restaurant['name']} is available for {guests} on "
                    f"{day} at {time}. Shall I book it for you?"
                )
            else:
                # try same‑cuisine alternative
                alt_cuisine = restaurant["cuisine"] if restaurant else None
                candidates = [
                    r for r in restaurants
                    if alt_cuisine and r["cuisine"].lower() == alt_cuisine.lower()
                    and is_available(r, guests, day, time)
                ]
                if candidates:
                    alt = random.choice(candidates)
                    response = (
                        f"Sorry, {restaurant['name']} is not available then. How about "
                        f"{alt['name']} instead? It’s the same {alt_cuisine} cuisine."
                    )
                else:
                    response = (
                        f"Looks like {restaurant['name']} (and no other {alt_cuisine}) "
                        f"is available for {guests} on {day} at {time}."
                    )
            dispatcher.utter_message(response)
            return []

        # 2) New booking: content‑based filtering + availability
        # build preference string
        pref_text = " ".join(cuisine + diet).strip()

        
        texts = [
            f"{r['name']} {r['cuisine']} {' '.join(r.get('dietary_options', []))}"
            for r in restaurants
        ]
        # TF‑IDF & cosine similarity
        vec = TfidfVectorizer().fit_transform([pref_text] + texts)
        scores = cosine_similarity(vec[0:1], vec[1:]).flatten()

        # rank & pick first available
        ranked = sorted(zip(restaurants, scores), key=lambda x: -x[1])
        for r, sc in ranked:
            if day and time and is_available(r, guests, day, time):
                dispatcher.utter_message(
                    f"Based on your preferences, I recommend {r['name']}. " 
                    f"It offers {r['cuisine']} cuisine and has {', '.join(r.get('dietary_options', []))} options "
                    f"and has a table for {guests} guests on {day} at {time}. Shall I book it?"
                )
                return []

        # 3) fallback: random available
        available = [
            r for r in restaurants
            if day and time and is_available(r, guests, day, time)
        ]
        if available:
            choice = random.choice(available)
            dispatcher.utter_message(
                f"I couldn’t find an exact match, but {choice['name']} is available at that time. "
                f"Shall I book it for you?"
            )
        else:
            dispatcher.utter_message(
                f"Sorry, I couldn’t find any table for {guests} guests on {day} at {time}."
            )


        return []




class ActionClearSlots(Action):
    def name(self) -> str:
        return "action_clear_slots"

    async def run(self, dispatcher, tracker, domain):
        dispatcher.utter_message(text="All set! I've cleared our previous conversation. Feel free to start a new booking whenever you're ready!☺️")
        return [AllSlotsReset()]
