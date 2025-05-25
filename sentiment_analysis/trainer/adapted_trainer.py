import torch
import torch.nn as nn
from torch.utils.data import DataLoader
from transformers import DataCollatorWithPadding
from torch.utils.tensorboard import SummaryWriter
from tqdm import tqdm
import os

def gaussian_kl_div(outputs, labels):
    mu1, var1, mu2, var2 = outputs[:, 0], outputs[:, 1], labels[:, 0], labels[:, 1]
    log_var1 = torch.log(var1)
    log_var2 = torch.log(var2)
    return 0.5 * (log_var2 - log_var1 + (var1 + (mu1 - mu2) ** 2) / var2 - 1).mean()

def mse(outputs, labels, alpha=2):
    # preds, labels: shape [batch, 2], [:,0]=mean, [:,1]=std
    pred_mean, pred_std   = outputs[:, 0], outputs[:, 1]
    true_mean, true_std   = labels[:, 0], labels[:, 1]
    loss_mean = nn.functional.mse_loss(pred_mean, true_mean)
    loss_std  = nn.functional.mse_loss(pred_std,  true_std)
    return loss_mean + alpha * loss_std

def gaussian_nll_loss(preds, labels, eps=1e-6):
    mu, sigma = preds[:, 0], preds[:, 1].clamp(min=eps)
    y         = labels[:, 0]
    # NLL = 0.5*log(2πσ²) + (y - μ)² / (2σ²)
    loss = 0.5 * torch.log(2 * torch.pi * sigma**2) + (y - mu)**2 / (2 * sigma**2)
    return loss.mean()

class CustomTrainer:
    def __init__(
            self,
            model,
            train_dataset,
            eval_dataset,
            tokenizer,
            data_collator,
            lr=5e-5,
            batch_size=4,
            epochs=3,
            log_dir="./runs",
            seed=42,
            output_dir="./outputs",
            device=None
    ):
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        self.model = model.to(self.device)
        self.tokenizer = tokenizer
        self.train_dataset = train_dataset
        self.eval_dataset = eval_dataset
        self.batch_size = batch_size
        self.epochs = epochs
        
        self.best_eval_mse = float("inf")

        self.optimizer = torch.optim.AdamW(model.parameters(), lr=lr)
        self.loss_fn = gaussian_kl_div
        self.loss_fn_mse = mse
        self.writer = SummaryWriter(log_dir=log_dir)
        self.data_collator = data_collator
        self.output_dir = output_dir

    def train(self):
        train_loader = DataLoader(
            self.train_dataset,
            batch_size=self.batch_size,
            shuffle=True,
            collate_fn=self.data_collator
        )
        self.model.train()
        for epoch in range(self.epochs):
            epoch_loss = 0.0
            loop = tqdm(train_loader, desc=f"Epoch {epoch + 1}/{self.epochs}")
            for step, batch in enumerate(loop):
                batch = {k: v.to(self.device) for k, v in batch.items()}
                labels = batch["labels"]
                inputs = {k: v for k, v in batch.items() if k != "labels"}

                outputs = self.model(**inputs)
                # KL loss
                loss = 1.5*self.loss_fn(outputs, labels) + self.loss_fn_mse(outputs, labels)
                # loss = self.loss_fn_mse(outputs, labels)
                loss.backward()
                self.optimizer.step()
                self.optimizer.zero_grad()
                epoch_loss += loss.item()
                loop.set_postfix(loss=loss.item())
                if step == len(train_loader) - 1:
                    avg_loss = epoch_loss / len(train_loader)
                    mse, preds, labels = self.evaluate()
                    loop.set_postfix({
                        "Train MSE": avg_loss,
                        "Eval MSE": mse.item()
                    })
                    # loop.refresh()

            # avg_loss = epoch_loss / len(train_loader)
            # mse, preds, labels = self.evaluate(epoch)
            self.writer.add_scalars('Loss',
                           {'train': float(avg_loss),
                            'val': float(mse.item()),
                            }, epoch)
            loop.set_postfix({
                "loss": loss.item(),  # 保留最后一个 batch 的 loss（可选）
                "Train MSE": avg_loss,
                "Eval MSE": mse.item()
            })
            loop.refresh()
            if mse.item() < self.best_eval_mse:
                self.best_eval_mse = mse.item()
                os.makedirs(self.output_dir, exist_ok=True)
                save_path = os.path.join(self.output_dir, f"best_model.pt")
                torch.save(self.model.state_dict(), save_path)
                # print(f"Best model saved to: {save_path}")

    def evaluate(self):
        eval_loader = DataLoader(
            self.eval_dataset,
            batch_size=self.batch_size,
            collate_fn=self.data_collator
        )
        self.model.eval()

        all_preds, all_labels = [], []
        with torch.no_grad():
            for batch in eval_loader:
                batch = {k: v.to(self.device) for k, v in batch.items()}
                labels = batch["labels"]
                inputs = {k: v for k, v in batch.items() if k != "labels"}

                outputs = self.model(**inputs)
                all_preds.append(outputs.cpu())
                all_labels.append(labels.cpu())

        preds = torch.cat(all_preds)
        labels = torch.cat(all_labels)
        mse = self.loss_fn_mse(outputs, labels)
        return mse, preds, labels

