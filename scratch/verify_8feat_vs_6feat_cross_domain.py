import joblib
import torch
import torch.nn as nn
import numpy as np
import pandas as pd
from pathlib import Path
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, roc_auc_score, precision_recall_curve, auc
from sklearn.ensemble import RandomForestClassifier

from iot_ids.preprocessing.pipeline import PreprocessingPipeline

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

    def forward(self, x):
        return self.net(x)


def eval_cross_domain(src_train, tgt_test, common_cols, seed=42):
    torch.manual_seed(seed)
    np.random.seed(seed)

    prep = PreprocessingPipeline(numeric_cols=common_cols)
    X_tr = prep.fit_transform(src_train)
    y_tr = src_train["label"].values

    X_tst = prep.transform(tgt_test)
    y_tst = tgt_test["label"].values

    rf = RandomForestClassifier(n_estimators=100, max_depth=15, random_state=seed, n_jobs=-1)
    rf.fit(X_tr, y_tr)

    mlp = MLPModule(input_dim=len(common_cols))
    criterion = nn.BCEWithLogitsLoss()
    optimizer = torch.optim.Adam(mlp.parameters(), lr=0.001)

    ds_tr = torch.utils.data.TensorDataset(torch.tensor(X_tr, dtype=torch.float32), torch.tensor(y_tr, dtype=torch.float32).unsqueeze(1))
    loader = torch.utils.data.DataLoader(ds_tr, batch_size=256, shuffle=True)
    mlp.train()
    for epoch in range(10):
        for bx, by in loader:
            optimizer.zero_grad()
            out = mlp(bx)
            loss = criterion(out, by)
            loss.backward()
            optimizer.step()
    mlp.eval()

    p_rf = rf.predict_proba(X_tst)[:, 1]
    with torch.no_grad():
        p_mlp = torch.sigmoid(mlp(torch.tensor(X_tst, dtype=torch.float32))).squeeze().numpy()

    p_sup = 0.5 * p_rf + 0.5 * p_mlp
    pred_sup = (p_sup >= 0.5).astype(int)

    acc = accuracy_score(y_tst, pred_sup)
    prec = precision_score(y_tst, pred_sup, pos_label=1)
    rec = recall_score(y_tst, pred_sup, pos_label=1)
    f1 = f1_score(y_tst, pred_sup, pos_label=1)
    roc = roc_auc_score(y_tst, p_sup)
    pr_vec, rec_vec, _ = precision_recall_curve(y_tst, p_sup)
    pr = auc(rec_vec, pr_vec)

    tp = int(((pred_sup == 1) & (y_tst == 1)).sum())
    fp = int(((pred_sup == 1) & (y_tst == 0)).sum())
    tn = int(((pred_sup == 0) & (y_tst == 0)).sum())
    fn = int(((pred_sup == 0) & (y_tst == 1)).sum())

    return {
        "accuracy": acc, "precision": prec, "recall": rec, "f1": f1,
        "roc_auc": roc, "pr_auc": pr, "tp": tp, "fp": fp, "tn": tn, "fn": fn
    }

models_root = Path("models/final")
data_root = Path("data/processed/final")

edge_dir = [d for d in (data_root / "Edge-IIoTset").iterdir() if d.is_dir()][0]
ton_dir = [d for d in (data_root / "ToN-IoT").iterdir() if d.is_dir()][0]

tr_edge = pd.read_parquet(edge_dir / "splits" / "train.parquet")
tst_edge = pd.read_parquet(edge_dir / "splits" / "test.parquet")

tr_ton = pd.read_parquet(ton_dir / "splits" / "train.parquet")
tst_ton = pd.read_parquet(ton_dir / "splits" / "test.parquet")

f_8 = ["duration", "src_bytes", "src_pkts", "dst_pkts", "proto_tcp", "proto_udp", "proto_icmp", "is_well_known_port"]
f_6 = ["duration", "src_bytes", "proto_tcp", "proto_udp", "proto_icmp", "is_well_known_port"]

print("--- Edge-IIoTset -> ToN-IoT ---")
res_e2t_8 = eval_cross_domain(tr_edge, tst_ton, f_8)
res_e2t_6 = eval_cross_domain(tr_edge, tst_ton, f_6)
print(f"  Old 8-Feature F_common: Acc={res_e2t_8['accuracy']*100:.2f}%, F1={res_e2t_8['f1']*100:.2f}%, ROC={res_e2t_8['roc_auc']:.4f}, PR={res_e2t_8['pr_auc']:.4f}")
print(f"  Clean 6-Feature F_common: Acc={res_e2t_6['accuracy']*100:.2f}%, F1={res_e2t_6['f1']*100:.2f}%, ROC={res_e2t_6['roc_auc']:.4f}, PR={res_e2t_6['pr_auc']:.4f}")

print("\n--- ToN-IoT -> Edge-IIoTset ---")
res_t2e_8 = eval_cross_domain(tr_ton, tst_edge, f_8)
res_t2e_6 = eval_cross_domain(tr_ton, tst_edge, f_6)
print(f"  Old 8-Feature F_common: Acc={res_t2e_8['accuracy']*100:.2f}%, F1={res_t2e_8['f1']*100:.2f}%, ROC={res_t2e_8['roc_auc']:.4f}, PR={res_t2e_8['pr_auc']:.4f}")
print(f"  Clean 6-Feature F_common: Acc={res_t2e_6['accuracy']*100:.2f}%, F1={res_t2e_6['f1']*100:.2f}%, ROC={res_t2e_6['roc_auc']:.4f}, PR={res_t2e_6['pr_auc']:.4f}")

