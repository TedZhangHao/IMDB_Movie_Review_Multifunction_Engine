"""
This document provides two MobileBert-based models.
(1) MobileBertRegressor: input -> integrate all the review into a long text
(2) MobileBertRegressor_V1: input -> each review being processed separately
"""
import torch
import torch.nn as nn

class MobileBertRegressor(nn.Module):
    def __init__(self, base_model, hidden_size):
        super().__init__()
        self.base = base_model
        self.regressor = nn.Linear(hidden_size, 2)  # output mean and std

    def forward(self, input_ids, attention_mask, **kwargs):
        # (batch, seq_len)
        outputs = self.base(input_ids=input_ids, attention_mask=attention_mask, **kwargs)
        cls = outputs.last_hidden_state[:, 0, :]  # [CLS] (batch_size, sequnce_length, hidden_size)
        raw_out = self.regressor(cls)  # shape: (batch_size, 2)
        mean = torch.sigmoid(raw_out[:, 0]) * 10  # [0, 10]
        std = nn.functional.softplus(raw_out[:, 1])  # [0, ∞)
        return torch.stack([mean, std], dim=1)  # shape: (batch_size, 2)


class MobileBertRegressor_V1(nn.Module):
    def __init__(self, base_model, hidden_size):
        super(MobileBertRegressor_V1, self).__init__()
        self.base = base_model  # "bert-base-uncased"
        self.dropout = nn.Dropout(0.05)
        self.regressor = nn.Linear(hidden_size, 2)  # regressor output (mean, std)

    def forward(self, input_ids, attention_mask, review_mask=None):  # **kwargs
        batch_size, n_reviews, seq_len = input_ids.size()
        # (batch, n_reviews, seq_len) -> (batch*n_reviews, seq_len)
        flat_input_ids = input_ids.view(batch_size * n_reviews, seq_len)
        flat_attention_mask = attention_mask.view(batch_size * n_reviews, seq_len)

        # feed to base model
        outputs = self.base(flat_input_ids, attention_mask=flat_attention_mask)
        # [CLS]
        cls = outputs.last_hidden_state[:, 0, :]  # shape: (batch*n_reviews, hidden_size)
        # (batch_size, n_reviews, hidden_size)
        cls = cls.view(batch_size, n_reviews, -1)

        # Compute the average representation for each movie using review_mask
        if review_mask is not None:
            # Expand review_mask to match the shape of the representation tensor
            mask = review_mask.unsqueeze(-1).to(cls.dtype)  # shape: (batch_size, n_reviews, 1)
            # Zero out the representations of the padded reviews
            cls = cls * mask
            # Count the number of valid reviews for each sample (avoid division by zero)
            valid_counts = mask.sum(dim=1)  # shape: (batch_size, 1)
            valid_counts = torch.clamp(valid_counts, min=1e-9)  # Avoid division by zero
            # Compute the average review representation
            avg_cls = cls.sum(dim=1) / valid_counts  # shape: (batch_size, hidden_size)
        else:
            # If no review_mask is provided, take the mean across the n_reviews dimension
            avg_cls = cls.mean(dim=1)

        # Pass the averaged representation through the regressor to get the output
        avg_cls = self.dropout(avg_cls)  # (optional dropout)
        logits = self.regressor(avg_cls)  # shape: (batch_size, 2)

        return logits
