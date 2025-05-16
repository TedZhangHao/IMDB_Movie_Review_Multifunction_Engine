from matplotlib import pyplot as plt
import numpy as np
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
    
if __name__ == "__main__":  
    data = np.load('results/best_model_53_50_128_withsmall_a_2.npz',allow_pickle=True)
    predictions = data["predictions"]
    preds = data["preds"]
    labels = data["labels"]
    print(predictions)
    evaluate_plot(preds, labels)