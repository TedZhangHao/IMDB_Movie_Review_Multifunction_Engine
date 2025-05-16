"""
This document provides a data processing method
"""
import json
import emoji
import torch
from torch.utils.data import Dataset
import numpy as np
from transformers import AutoTokenizer

tokenizer = AutoTokenizer.from_pretrained("google/mobilebert-uncased")

# emojis removal
def demojis(movie):
    for review in movie['reviews']:
            review['title'] = emoji.replace_emoji(review['title'], '')
            review['content'] = emoji.replace_emoji(review['content'], '')
# custom dataset
class MovieReviewDataset(Dataset):
    def __init__(self, json_path):
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        if isinstance(data, dict):
            self.movies = list(data.values())
        else:
            self.movies = data
        self.samples = []
        for movie in self.movies:
            demojis(movie)  # eliminate emojis
            reviews = movie.get("reviews", [])
            # if len(reviews) < 100:
            #     continue
            review_texts, ratings = [], []
            review_count = 0
            for review in reviews:
                if review['rating'] and review_count < 25:
                    review_texts.append(review["content"])
                    ratings.append(float(review["rating"]))
                    review_count += 1
            if len(ratings) > 0:
                mean_rating = float(np.mean(ratings))
                std_rating = float(np.std(ratings, ddof=0))
            else:
                mean_rating = 0.0
                std_rating = 0.0
            self.samples.append({
                "reviews": review_texts,
                "label": (mean_rating, std_rating)
            })
    def __len__(self):
        return len(self.samples)
    def __getitem__(self, idx):
        sample = self.samples[idx]
        return sample["reviews"], sample["label"]


# custom collate_fn
def collate_fn(batch):
    batch_reviews = [item['reviews'] for item in batch]
    batch_labels = [item['label'] for item in batch]
    max_reviews = max(len(reviews) for reviews in batch_reviews)
    input_ids_list = []
    attention_mask_list = []
    review_mask_list = []
    for reviews in batch_reviews:
        encoding = tokenizer(
            reviews,
            padding='max_length',
            truncation=True,
            max_length=256,
            return_tensors='pt'
        )
        ids = encoding["input_ids"]
        mask = encoding["attention_mask"]
        num_reviews = ids.size(0)
        if num_reviews < max_reviews:
            pad_reviews = max_reviews - num_reviews
            pad_token_id = tokenizer.pad_token_id or 0 # 0
            pad_ids = torch.full((pad_reviews, ids.size(1)), pad_token_id, dtype=torch.long)
            pad_mask = torch.zeros((pad_reviews, mask.size(1)), dtype=torch.long)
            ids = torch.cat([ids, pad_ids], dim=0)
            mask = torch.cat([mask, pad_mask], dim=0)
        input_ids_list.append(ids)
        attention_mask_list.append(mask)
        valid_reviews = [1] * min(len(reviews), max_reviews)
        valid_reviews += [0] * (max_reviews - len(reviews))
        review_mask_list.append(torch.tensor(valid_reviews, dtype=torch.long))
    batch_input_ids = torch.stack(input_ids_list)
    batch_attention_masks = torch.stack(attention_mask_list)
    batch_review_mask = torch.stack(review_mask_list)
    batch_labels = torch.tensor(batch_labels, dtype=torch.float32)
    return {
        "input_ids": batch_input_ids,
        "attention_mask": batch_attention_masks,
        "review_mask": batch_review_mask,
        "labels": batch_labels
    }


