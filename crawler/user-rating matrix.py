import json
import pandas as pd

with open("imdb_action_movies_full.json", "r", encoding="utf-8") as f:
    data = json.load(f)

user_ratings = {}
for movie in data[:200]:
    title = movie.get("title", "")
    for review in movie.get("reviews", []):
        user = review.get("user", "")
        rating = review.get("rating", "")
        if rating:
            user_ratings.setdefault(user, {})[title] = int(rating)

ratings_df = pd.DataFrame.from_dict(user_ratings, orient="index")
ratings_df.to_csv("ratings_matrix.csv")
print(ratings_df.head())
