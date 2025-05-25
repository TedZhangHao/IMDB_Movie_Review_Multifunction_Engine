from matplotlib import pyplot as plt
import numpy as np
import torch.nn as nn
import torch
def evaluate_plot(preds, labels):
    true_means, true_stds = labels[:, 0], labels[:, 1]
    pred_means, pred_stds = preds[:, 0], preds[:, 1]
    # Plot mean values
    plt.scatter(true_means, pred_means, color='blue', label='Predicted Mean', marker='x')
    plt.plot([min(true_means.min(), pred_means.min()), max(true_means.max(), pred_means.max())],
             [min(true_means.min(), pred_means.min()), max(true_means.max(), pred_means.max())],
             'b--', linewidth=1, alpha=0.5)

    # Plot std values
    plt.scatter(true_stds, pred_stds, color='green', label='Predicted Std', marker='x')
    plt.plot([min(true_stds.min(), pred_stds.min()), max(true_stds.max(), pred_stds.max())],
             [min(true_stds.min(), pred_stds.min()), max(true_stds.max(), pred_stds.max())],
             'g--', linewidth=1, alpha=0.5)

    # Labels and title
    plt.xlabel('True Values')
    plt.ylabel('Predicted Values')
    plt.title('Predicted vs. True Values (Mean & Std)')
    plt.legend()
    plt.grid(True)
    plt.tight_layout()
    plt.show()

def mse(outputs, labels, alpha=2):
    # preds, labels: shape [batch, 2], [:,0]=mean, [:,1]=std
    pred_mean, pred_std   = outputs[:, 0], outputs[:, 1]
    true_mean, true_std   = labels[:, 0], labels[:, 1]
    loss_mean = nn.functional.mse_loss(pred_mean, true_mean)
    loss_std  = nn.functional.mse_loss(pred_std,  true_std)
    return loss_mean + alpha * loss_std

def gaussian_kl_div(outputs, labels):
    mu1, var1, mu2, var2 = outputs[:, 0], outputs[:, 1], labels[:, 0], labels[:, 1]
    log_var1 = torch.log(var1)
    log_var2 = torch.log(var2)
    return 0.5 * (log_var2 - log_var1 + (var1 + (mu1 - mu2) ** 2) / var2 - 1).mean()

if __name__ == "__main__":  
    data = np.load('results/best_model_53_10_512_withsmall_dropout0_05.npz',allow_pickle=True)
    predictions = data["predictions"]
    preds = data["preds"]
    labels = data["labels"]
    print(predictions)
    preds_tensor = torch.tensor(preds)
    labels_tensor = torch.tensor(labels)
    print('KL:',gaussian_kl_div(preds_tensor, labels_tensor),'MSE:',mse(preds_tensor, labels_tensor))
    evaluate_plot(preds, labels)