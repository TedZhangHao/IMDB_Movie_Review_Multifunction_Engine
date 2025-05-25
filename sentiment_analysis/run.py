import random
import torch
import shutil
from torch.utils.data import random_split
from transformers import AutoTokenizer, AutoConfig, AutoModel
from models.Mobilebert_based import MobileBertRegressor, MobileBertRegressor_V1
from pipeline.data_processing import MovieReviewDataset, collate_fn
from trainer.adapted_trainer import CustomTrainer
from evaluation_visualization import evaluate_plot
import os
import numpy as np

torch.manual_seed(42)
generator = torch.Generator().manual_seed(42)

batch_size = 4
Model_ID = "google/mobilebert-uncased"
train_ratio = 0.8
lr = 5e-4
training_resume = False
current_dir = os.path.dirname(os.path.abspath(__file__))
data_path = os.path.join(current_dir,"dataset/imdb_action_movies_full.json")
output_dir = os.path.join(current_dir,"saved_checkpoints")
log_dir = os.path.join(current_dir,f"runs_log/exp_full_data_{lr}_{batch_size}") 
# if not training_resume:
#     shutil.rmtree(log_dir) 
#     log_dir.mkdir(parents=True, exist_ok=True)
dataset = MovieReviewDataset(data_path)
processed_data = dataset.samples

train_size = int(train_ratio * len(processed_data))
eval_size = len(processed_data) - train_size
train_dataset, eval_dataset = random_split(processed_data, [train_size, eval_size], generator=generator)
train_dataset = processed_data[:int(0.8 * len(processed_data))]
eval_dataset = processed_data[int(0.8 * len(processed_data)):]
# eval_dataset = train_dataset

config = AutoConfig.from_pretrained(Model_ID)
tokenizer = AutoTokenizer.from_pretrained(Model_ID)
base_model = AutoModel.from_config(config)
model = MobileBertRegressor_V1(base_model, config.hidden_size)
trainer = CustomTrainer(
    model=model,
    train_dataset=train_dataset,
    eval_dataset=eval_dataset,
    tokenizer=tokenizer,
    data_collator=collate_fn,
    lr=lr,
    batch_size=batch_size,
    epochs=200,
    log_dir=log_dir,
    output_dir=output_dir,
)
if __name__ == "__main__":

    # model.load_state_dict(torch.load(f"{current_dir}/saved_checkpoints/best_model.pt"))
    trainer.train()
    predictions, preds, labels = trainer.evaluate()
    print(predictions)


    for i in range(len(preds)):
        print(f"prediction mean: {preds[i][0]:.2f}, label mean: {labels[i][0]:.2f}")
        print("-" * 15)
        print(f"prediction stds: {preds[i][1]:.2f}, label stds: {labels[i][1]:.2f}")
        print("-" * 30)
    evaluate_plot(preds, labels)
    # np.savez("best_model_53_50_128_withsmall.npz",predictions=predictions,preds=preds,labels=labels)#_dropout0_05