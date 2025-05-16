from sklearn.metrics.pairwise import cosine_similarity
import numpy as np
import pandas as pd
from sklearn.decomposition import TruncatedSVD
from sklearn.impute import SimpleImputer, KNNImputer
import matplotlib.pyplot as plt
import random

def svd_predict_ratings(rating_df, target_user, n_components=20,impute_strategy='mean',ascend = False):
    """
    Use SVD collaborative filtering to predict ratings for a target user.
    Parameters:
    - rating_df: user-item rating DataFrame, index is the username
    - target_user: target username
    - n_components: number of SVD dimensions (number of potential factors)
    Returns:
    - Recommended RatingsSeries, sorted by predicted ratings in descending order
    """
    # Fill in missing values
    if impute_strategy == 'knn':
        imputer = KNNImputer(n_neighbors=5)
    else:
        imputer = SimpleImputer(strategy='mean')
    filled = imputer.fit_transform(rating_df)
    # Dimensionality reduction using SVD
    svd = TruncatedSVD(n_components=n_components, random_state=42)
    U = svd.fit_transform(filled)               # 用户-特征矩阵
    VT = svd.components_                        # 特征-物品矩阵
    # Reconstructing the scoring matrix
    reconstructed = np.dot(U, VT)
    reconstructed_df = pd.DataFrame(reconstructed, index=rating_df.index, columns=rating_df.columns)
    # Obtain raw and predicted ratings of target users
    target_original = rating_df.loc[target_user]
    target_pred = reconstructed_df.loc[target_user]
    # Returns predicted scores for unscored items only, sorted in descending order
    unseen_items = target_original[target_original.isna()].index
    recommendations = target_pred[unseen_items].sort_values(ascending=ascend)

    return recommendations, target_pred[unseen_items]


def plot_recommendations_comparison(svd_recommendations, title="Recommendation Comparison", top_k=10):
    """
    Comparison of scores for SVD recommendation results.
    Parameter:
    - svd_recommendations: Series of SVD predicted ratings (unscored items)
    - title: Chart title
    - top_k: Show the number of top recommendations.
    """
    # Preprocessing Recommendation List
    svd_topk = svd_recommendations.head(top_k)

    plt.figure(figsize=(12, 6))

    # Plot a bar chart of the results of the two recommendations
    plt.barh(svd_topk.index[::-1], svd_topk.values[::-1], alpha=0.6, label='SVD')

    plt.xlabel("Predicted Rating")
    plt.title(title)
    plt.legend()
    plt.grid(axis='x', linestyle='--', alpha=0.7)
    plt.tight_layout()
    plt.show()

def plot_prediction_distribution(unseen_preds, title="Distribution of Predicted Ratings"):
    """
    Visualize the distribution of predicted ratings of target users on unrated items.
    """
    plt.figure(figsize=(8, 5))
    unseen_preds.hist(bins=20, edgecolor='black', color='orange')
    plt.title(title)
    plt.xlabel("Predicted Rating")
    plt.ylabel("Frequency")
    plt.grid(True)
    plt.tight_layout()
    plt.show()

def plot_rating_matrix(rating_df, num_rows=50, num_cols=20, title="Rating Matrix (Sample)"):
    """
    Visualize part of the scoring matrix (first num_rows rows, first num_cols columns).
    Missing values are shown in gray.
    """
    sample = rating_df.iloc[:num_rows, :num_cols]
    plt.figure(figsize=(12, 8))
    plt.imshow(sample, aspect='auto', interpolation='nearest', cmap='viridis')
    plt.colorbar(label='Rating')
    plt.title(title)
    plt.xlabel("Items")
    plt.ylabel("Users")
    plt.xticks(ticks=range(num_cols), labels=sample.columns[:num_cols], rotation=90)
    plt.yticks(ticks=range(num_rows), labels=sample.index[:num_rows])
    plt.grid(False)
    plt.tight_layout()
    plt.show()

if __name__ == '__main__':
    file_path = "ratings_matrix.csv"
    rating_df = pd.read_csv(file_path)
    rating_matrix = rating_df.set_index('Unnamed: 0')
    plot_rating_matrix(rating_matrix, num_rows=50, num_cols=15)
    random_users = random.choice(list(rating_matrix.index))
    print(random_users)
    recom_svd,unseen_preds = svd_predict_ratings(rating_matrix, random_users, n_components=20, impute_strategy='knn')
    recom_svd.head(10)
    plot_recommendations_comparison(recom_svd, title="Top-10 Recommendations: SVD", top_k=10)
    plot_prediction_distribution(unseen_preds, title="Distribution of Predicted Ratings (Unseen Items)")
    recom_svd,_ = svd_predict_ratings(rating_matrix, random_users, n_components=20, impute_strategy='knn',ascend = True)
    plot_recommendations_comparison(recom_svd, title="Bottom-10 Least Recommendations: SVD", top_k=10)