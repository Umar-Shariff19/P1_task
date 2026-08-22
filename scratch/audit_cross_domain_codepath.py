import joblib
import torch
import numpy as np
import pandas as pd
from pathlib import Path
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, roc_auc_score, precision_recall_curve, auc

print("============================================================")
print("=== AUDIT 2 & 4: CROSS-DOMAIN CODEPATH & SCORE SOURCE AUDIT ===")
print("============================================================\n")

models_root = Path("models/final")
data_root = Path("data/processed/final")

# Class definition for loading MLP
class MLPModule(torch.nn.Module):
    def __init__(self, input_dim: int):
        super().__init__()
        self.net = torch.nn.Sequential(
            torch.nn.Linear(input_dim, 128),
            torch.nn.BatchNorm1d(128),
            torch.nn.ReLU(),
            torch.nn.Dropout(0.2),
            torch.nn.Linear(128, 64),
            torch.nn.BatchNorm1d(64),
            torch.nn.ReLU(),
            torch.nn.Dropout(0.2),
            torch.nn.Linear(64, 32),
            torch.nn.ReLU(),
            torch.nn.Linear(32, 1),
        )

    def forward(self, x):
        return self.net(x)

# Load Source Edge-IIoTset prep_common & RF model
edge_prep_common = joblib.load(models_root / "Edge-IIoTset" / "prep_common.joblib")
edge_rf_common = joblib.load(models_root / "Edge-IIoTset" / "rf_model.joblib") # Wait! RF model in models/final/Edge-IIoTset is 13 features!

print(f"Edge-IIoTset rf_model.joblib input features: {edge_rf_common.n_features_in_}")
print(f"Edge-IIoTset prep_common.joblib numeric cols ({len(edge_prep_common.numeric_cols)}): {edge_prep_common.numeric_cols}")

# Target ToN-IoT Test split
ton_target = [d for d in (data_root / "ToN-IoT").iterdir() if d.is_dir()][0]
ton_test = pd.read_parquet(ton_target / "splits" / "test.parquet")
y_ton_test = ton_test["label"].values
print(f"ToN-IoT Target Test Split Rows: {len(y_ton_test)}")

# 1. Transform Target ToN-IoT using Source Edge prep_common
X_ton_c = edge_prep_common.transform(ton_test)

# 2. Train a dedicated 6-feature Random Forest model on Source Edge-IIoTset Train split
edge_source = [d for d in (data_root / "Edge-IIoTset").iterdir() if d.is_dir()][0]
edge_train = pd.read_parquet(edge_source / "splits" / "train.parquet")
X_edge_train_c = edge_prep_common.transform(edge_train)
y_edge_train = edge_train["label"].values

from sklearn.ensemble import RandomForestClassifier
rf_c = RandomForestClassifier(n_estimators=50, max_depth=12, random_state=42, n_jobs=-1)
rf_c.fit(X_edge_train_c, y_edge_train)

# Predict on Target ToN-IoT Test split
p_rf_c = rf_c.predict_proba(X_ton_c)[:, 1]
pred_rf_c = (p_rf_c >= 0.5).astype(int)

acc_rf = accuracy_score(y_ton_test, pred_rf_c)
prec_rf = precision_score(y_ton_test, pred_rf_c, pos_label=1)
rec_rf = recall_score(y_ton_test, pred_rf_c, pos_label=1)
f1_rf = f1_score(y_ton_test, pred_rf_c, pos_label=1)
roc_rf = roc_auc_score(y_ton_test, p_rf_c)
precision_vec, recall_vec, _ = precision_recall_curve(y_ton_test, p_rf_c)
pr_rf = auc(recall_vec, precision_vec)

print("\n--- Edge-IIoTset -> ToN-IoT (6-Feature F_common RF Model) ---")
print(f"  Accuracy:  {acc_rf*100:.2f}%")
print(f"  Precision: {prec_rf*100:.2f}%")
print(f"  Recall:    {rec_rf*100:.2f}%")
print(f"  Attack F1: {f1_rf*100:.2f}%")
print(f"  ROC AUC:   {roc_rf:.4f}")
print(f"  PR AUC:    {pr_rf:.4f}")

# Confusion matrix
tp = int(((pred_rf_c == 1) & (y_ton_test == 1)).sum())
fp = int(((pred_rf_c == 1) & (y_ton_test == 0)).sum())
tn = int(((pred_rf_c == 0) & (y_ton_test == 0)).sum())
fn = int(((pred_rf_c == 0) & (y_ton_test == 1)).sum())

print(f"  Confusion Matrix: TP={tp}, FP={fp}, TN={tn}, FN={fn}")

