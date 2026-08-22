import json
from pathlib import Path
import joblib
import numpy as np
import pandas as pd
import torch

from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, roc_auc_score

sys_path = Path("src")
import sys
sys.path.insert(0, str(sys_path))

from iot_ids.preprocessing.pipeline import PreprocessingPipeline
from iot_ids.utils.paths import REPO_ROOT

print("============================================================")
print("=== CLEAN 6-FEATURE F_common EVALUATION FORENSIC TEST ===")
print("============================================================\n")

base_dir = REPO_ROOT / "data" / "processed" / "final"

# Clean 6-feature F_common
clean_f_common = [
    "duration", "src_bytes", "proto_tcp", "proto_udp", "proto_icmp", "is_well_known_port"
]

print(f"Corrected Frozen F_common (6 Features): {clean_f_common}\n")

# Cross-Domain Evaluation using Clean 6-feature F_common
for src_ds, tgt_ds in [("Edge-IIoTset", "ToN-IoT"), ("ToN-IoT", "Edge-IIoTset")]:
    src_target = [d for d in (base_dir / src_ds).iterdir() if d.is_dir()][0]
    tgt_target = [d for d in (base_dir / tgt_ds).iterdir() if d.is_dir()][0]

    tr_src = pd.read_parquet(src_target / "splits" / "train.parquet")
    tst_tgt = pd.read_parquet(tgt_target / "splits" / "test.parquet")

    prep = PreprocessingPipeline(numeric_cols=clean_f_common)
    X_tr = prep.fit_transform(tr_src)
    y_tr = tr_src["label"].values

    rf = RandomForestClassifier(n_estimators=100, max_depth=15, random_state=42, n_jobs=-1)
    rf.fit(X_tr, y_tr)

    X_tst = prep.transform(tst_tgt)
    y_tst = tst_tgt["label"].values

    p_rf = rf.predict_proba(X_tst)[:, 1]
    y_pred = (p_rf >= 0.5).astype(int)

    acc = accuracy_score(y_tst, y_pred)
    f1 = f1_score(y_tst, y_pred, zero_division=0)
    prec = precision_score(y_tst, y_pred, zero_division=0)
    rec = recall_score(y_tst, y_pred, zero_division=0)
    auc = roc_auc_score(y_tst, p_rf)

    print(f"Cross-Domain {src_ds} -> {tgt_ds} (Clean 6-Feature F_common):")
    print(f"  Accuracy: {acc*100:.2f}% | Precision: {prec*100:.2f}% | Recall: {rec*100:.2f}% | Attack F1: {f1*100:.2f}% | ROC AUC: {auc:.4f}\n")

