from joblib import dump
from sklearn.feature_extraction.text import TfidfVectorizer
import json

# Preprocessed restaurant verctors to reduce computation time

# Load restaurant data from JSON file
with open("data/restaurants.json") as f:
    restaurants = json.load(f)

# Create and save preprocessed texts
# creates a query string for each restaurant e.g. La Bella Italia Italian Vegetarian Gluten-Free Omnivore
restaurant_texts = [
    f"{r['name']} {r['cuisine']} {' '.join(r.get('dietary_options', []))}"
    for r in restaurants
]
dump(restaurant_texts, "restaurant_texts.pkl")

# Fit and save TF-IDF vectorizer and vectors for comparison with user input
# Initialize the vectorizer and fit/transform the data
vectorizer = TfidfVectorizer()
vectors = vectorizer.fit_transform(restaurant_texts)

# Save the vectorizer and the transformed vectors
dump(vectorizer, "vectorizer/vectorizer.joblib")
dump(vectors, "vectorizer/restaurant_vectors.joblib")

print("Vectorizer and restaurant vectors saved successfully.")


