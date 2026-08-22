import json
from pathlib import Path
import joblib
import numpy as np
import pandas as pd
import torch
import torch.nn as nn
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score,
    roc_auc_score, average_precision_score, confusion_matrix
)

sys_path = Path("src")
import sys
sys.path.insert(0, str(sys_path))

from iot_ids.utils.paths import REPO_ROOT

print("============================================================")
print("=== AUTHORITATIVE FROZEN RESULTS MATHEMATICAL CHECK ===")
print("============================================================\n")

base_dir = REPO_ROOT / "data" / "processed" / "final"
models_base = REPO_ROOT / "models" / "final"

class MLPModule(nn.Module):
    def __init__(self, input_dim: int):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(input_dim, 128),
            nn.BatchNorm1d(128),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(128, 64),
            nn.BatchNorm1d(64),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(64, 32),
            nn.ReLU(),
            nn.Linear(32, 1),
        )
    def forward(self, x): return self.net(x)

def check_metrics(y_true, y_prob):
    y_pred = (y_prob >= 0.5).astype(int)
    cm = confusion_matrix(y_true, y_pred, labels=[0, 1])
    tn, fp, fn, tp = cm.ravel()
    acc = accuracy_score(y_true, y_pred)
    prec = precision_score(y_true, y_pred, zero_division=0)
    rec = recall_score(y_true, y_pred, zero_division=0)
    f1 = f1_score(y_true, y_pred, zero_division=0)
    macro_f1 = f1_score(y_true, y_pred, average="macro", zero_division=0)
    roc = roc_auc_score(y_true, y_prob)
    pr = average_precision_score(y_true, y_prob)

    print(f"  Confusion Matrix: TN={tn:,}, FP={fp:,}, FN={fn:,}, TP={tp:,}")
    print(f"  Accuracy:  {acc*100:.4f}% ({acc:.6f})")
    print(f"  Precision: {prec*100:.4f}% ({prec:.6f})")
    print(f"  Recall:    {rec*100:.4f}% ({rec:.6f})")
    print(f"  Attack F1: {f1*100:.4f}% ({f1:.6f})")
    print(f"  Macro F1:  {macro_f1*100:.4f}% ({macro_f1:.6f})")
    print(f"  ROC AUC:   {roc:.6f}")
    print(f"  PR AUC:    {pr:.6f}")

    # Mathematical reconciliation check: F1 = 2*P*R / (P+R)
    expected_f1 = 2 * prec * rec / (prec + rec) if (prec + rec) > 0 else 0.0
    print(f"  Mathematical F1 Reconciliation Check: Calculated={f1:.6f}, Expected 2PR/(P+R)={expected_f1:.6f} -> {'PASS' if abs(f1-expected_f1)<1e-5 else 'FAIL'}")
    return {
        "accuracy": acc, "precision": prec, "recall": rec, "f1": f1,
        "macro_f1": macro_f1, "roc_auc": roc, "pr_auc": pr,
        "tn": int(tn), "fp": int(fp), "fn": int(fn), "tp": int(tp)
    }

# 1. Edge-IIoTset In-Domain
print("--- 1. Edge-IIoTset In-Domain Test ---")
ds_dir = base_dir / "Edge-IIoTset"
t_dir = [d for d in ds_dir.iterdir() if d.is_dir()][0]
tst_edge = pd.read_parquet(t_dir / "splits" / "test.parquet")
m_edge = models_base / "Edge-IIoTset"

prep_e = joblib.load(m_edge / "prep_indomain.joblib")
rf_e = joblib.load(m_edge / "rf_model.joblib")
X_e = prep_e.transform(tst_edge)
y_e = tst_edge["label"].values

mlp_e = MLPModule(input_dim=X_e.shape[1])
mlp_e.load_state_dict(torch.load(m_edge / "mlp_model.pt"))
mlp_e.eval()

p_rf_e = rf_e.predict_proba(X_e)[:, 1]
with torch.no_grad():
    p_mlp_e = torch.sigmoid(mlp_e(torch.tensor(X_e, dtype=torch.float32))).squeeze().numpy()
p_sup_e = 0.5 * p_rf_e + 0.5 * p_mlp_e
check_metrics(y_e, p_sup_e)

# 2. ToN-IoT In-Domain
print("\n--- 2. ToN-IoT Network In-Domain Test ---")
ds_dir = base_dir / "ToN-IoT"
t_dir = [d for d in ds_dir.iterdir() if d.is_dir()][0]
tst_ton = pd.read_parquet(t_dir / "splits" / "test.parquet")
m_ton = models_base / "ToN-IoT"

prep_t = joblib.load(m_ton / "prep_indomain.joblib")
rf_t = joblib.load(m_ton / "rf_model.joblib")
X_t = prep_t.transform(tst_ton)
y_t = tst_ton["label"].values

mlp_t = MLPModule(input_dim=X_t.shape[1])
mlp_t.load_state_dict(torch.load(m_ton / "mlp_model.pt"))
mlp_t.eval()

p_rf_t = rf_t.predict_proba(X_t)[:, 1]
with torch.no_grad():
    p_mlp_t = torch.sigmoid(mlp_t(torch.tensor(X_t, dtype=torch.float32))).squeeze().numpy()
p_sup_t = 0.5 * p_rf_t + 0.5 * p_mlp_t
check_metrics(y_t, p_sup_t)

