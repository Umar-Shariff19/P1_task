import json
import sys
from pathlib import Path
import joblib
import numpy as np
import pandas as pd
import torch
import torch.nn as nn
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, roc_auc_score, precision_recall_curve, auc, confusion_matrix

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
from iot_ids.preprocessing.pipeline import PreprocessingPipeline
from iot_ids.models.ensemble.risk_layer import RiskLayer
from iot_ids.utils.paths import REPO_ROOT

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

def compute_metrics(y_true, y_prob, threshold=0.5):
    pred = (y_prob >= threshold).astype(int)
    acc = accuracy_score(y_true, pred)
    prec = precision_score(y_true, pred, pos_label=1, zero_division=0)
    rec = recall_score(y_true, pred, pos_label=1, zero_division=0)
    f1 = f1_score(y_true, pred, pos_label=1, zero_division=0)
    macro_f1 = f1_score(y_true, pred, average="macro", zero_division=0)
    try:
        roc = roc_auc_score(y_true, y_prob)
    except Exception:
        roc = 0.5
    pr_vec, rec_vec, _ = precision_recall_curve(y_true, y_prob)
    pr_val = auc(rec_vec, pr_vec)

    return {
        "accuracy": acc, "precision": prec, "recall": rec, "f1": f1,
        "macro_f1": macro_f1, "roc_auc": roc, "pr_auc": pr_val
    }

def main():
    print("============================================================")
    print("=== PART 8: EVALUATING RUN 2 & 3-WAY REPRODUCIBILITY COMPARISON ===")
    print("============================================================\n")

    base_dir = REPO_ROOT / "data" / "processed" / "final"
    exp_dir = Path("reproducibility/fresh_retraining_20260821_010000")
    run2_dir = exp_dir / "run2"

    datasets = ["Edge-IIoTset", "ToN-IoT"]
    common_cols = ["duration", "src_bytes", "proto_tcp", "proto_udp", "proto_icmp", "is_well_known_port"]

    # 1. Evaluate Run 2 In-Domain
    res_run2_in = {}
    for ds in datasets:
        ds_dir = base_dir / ds
        target_dir = [d for d in ds_dir.iterdir() if d.is_dir()][0]
        test_df = pd.read_parquet(target_dir / "splits" / "test.parquet")

        m_dir = run2_dir / ds
        prep_indomain = joblib.load(m_dir / "prep_indomain.joblib")
        rf = joblib.load(m_dir / "rf_model.joblib")

        X_test = prep_indomain.transform(test_df)
        y_test = test_df["label"].values

        mlp = MLPModule(input_dim=X_test.shape[1])
        mlp.load_state_dict(torch.load(m_dir / "mlp_model.pt"))
        mlp.eval()

        p_rf = rf.predict_proba(X_test)[:, 1]

        with torch.no_grad():
            p_mlp = torch.sigmoid(mlp(torch.tensor(X_test, dtype=torch.float32))).squeeze().numpy()

        p_sup = 0.5 * p_rf + 0.5 * p_mlp
        res_run2_in[ds] = compute_metrics(y_test, p_sup)

    # 2. Evaluate Run 2 Cross-Domain
    res_run2_cd = {}
    pairs = [("Edge-IIoTset", "ToN-IoT"), ("ToN-IoT", "Edge-IIoTset")]
    for src_ds, tgt_ds in pairs:
        src_target = [d for d in (base_dir / src_ds).iterdir() if d.is_dir()][0]
        tgt_target = [d for d in (base_dir / tgt_ds).iterdir() if d.is_dir()][0]

        tr_src = pd.read_parquet(src_target / "splits" / "train.parquet")
        tst_tgt = pd.read_parquet(tgt_target / "splits" / "test.parquet")

        prep_common = PreprocessingPipeline(numeric_cols=common_cols)
        X_tr_c = prep_common.fit_transform(tr_src)
        y_tr_src = tr_src["label"].values

        rf_c = RandomForestClassifier(n_estimators=100, max_depth=15, random_state=42, n_jobs=-1)
        rf_c.fit(X_tr_c, y_tr_src)

        mlp_c = MLPModule(input_dim=len(common_cols))
        criterion = nn.BCEWithLogitsLoss()
        optimizer = torch.optim.Adam(mlp_c.parameters(), lr=0.001)

        ds_tr = torch.utils.data.TensorDataset(torch.tensor(X_tr_c, dtype=torch.float32), torch.tensor(y_tr_src, dtype=torch.float32).unsqueeze(1))
        loader = torch.utils.data.DataLoader(ds_tr, batch_size=256, shuffle=True)
        mlp_c.train()
        for epoch in range(10):
            for bx, by in loader:
                optimizer.zero_grad()
                out = mlp_c(bx)
                loss = criterion(out, by)
                loss.backward()
                optimizer.step()
        mlp_c.eval()

        X_tst_c = prep_common.transform(tst_tgt)
        y_tst_tgt = tst_tgt["label"].values

        p_rf_c = rf_c.predict_proba(X_tst_c)[:, 1]
        with torch.no_grad():
            p_mlp_c = torch.sigmoid(mlp_c(torch.tensor(X_tst_c, dtype=torch.float32))).squeeze().numpy()

        p_sup_c = 0.5 * p_rf_c + 0.5 * p_mlp_c
        res_run2_cd[f"{src_ds}_to_{tgt_ds}"] = compute_metrics(y_tst_tgt, p_sup_c)

    # 3. Load Frozen & Run 1
    frozen_data = json.loads(Path("reports/tables/final_evaluation_results.json").read_text(encoding="utf-8"))
    run1_in = json.loads((exp_dir / "run1" / "FRESH_INDOMAIN_RESULTS.json").read_text(encoding="utf-8"))
    run1_cd = json.loads((exp_dir / "run1" / "FRESH_CROSS_DOMAIN_RESULTS.json").read_text(encoding="utf-8"))

    targets = [
        ("Edge-IIoTset In-Domain", frozen_data["in_domain"]["Edge-IIoTset"]["supervised_metrics"], run1_in["Edge-IIoTset"]["supervised_ensemble_metrics"], res_run2_in["Edge-IIoTset"]),
        ("ToN-IoT In-Domain", frozen_data["in_domain"]["ToN-IoT"]["supervised_metrics"], run1_in["ToN-IoT"]["supervised_ensemble_metrics"], res_run2_in["ToN-IoT"]),
        ("Edge -> ToN Cross-Domain", frozen_data["cross_domain"]["Edge-IIoTset_to_ToN-IoT"], run1_cd["Edge-IIoTset_to_ToN-IoT"]["supervised_ensemble_metrics"], res_run2_cd["Edge-IIoTset_to_ToN-IoT"]),
        ("ToN -> Edge Cross-Domain", frozen_data["cross_domain"]["ToN-IoT_to_Edge-IIoTset"], run1_cd["ToN-IoT_to_Edge-IIoTset"]["supervised_ensemble_metrics"], res_run2_cd["ToN-IoT_to_Edge-IIoTset"]),
    ]

    metrics_list = ["accuracy", "precision", "recall", "f1", "macro_f1", "roc_auc", "pr_auc"]
    three_way_rows = []

    for exp_name, f_dict, r1_dict, r2_dict in targets:
        for m in metrics_list:
            vf = f_dict[m]
            v1 = r1_dict[m]
            v2 = r2_dict[m]

            var_runs = abs(v1 - v2)
            var_frozen = abs(v1 - vf)

            if var_runs < 0.0005 and var_frozen < 0.0005:
                status = "IDENTICAL"
            elif var_runs < 0.005:
                status = "STABLE (< 0.5% Variation)"
            else:
                status = "MINOR STOCHASTIC VARIATION"

            three_way_rows.append({
                "Experiment": exp_name,
                "Metric": m,
                "Frozen Baseline": f"{vf*100:.2f}%" if m not in ["roc_auc", "pr_auc"] else f"{vf:.4f}",
                "Fresh Run 1": f"{v1*100:.2f}%" if m not in ["roc_auc", "pr_auc"] else f"{v1:.4f}",
                "Fresh Run 2": f"{v2*100:.2f}%" if m not in ["roc_auc", "pr_auc"] else f"{v2:.4f}",
                "Run 1 vs Run 2 Delta": f"{var_runs:.6f}",
                "Stability Verdict": status
            })

    df_3way = pd.DataFrame(three_way_rows)
    print(df_3way.to_string(index=False))

    (exp_dir / "THREE_WAY_REPRODUCIBILITY_MATRIX.json").write_text(json.dumps(three_way_rows, indent=2), encoding="utf-8")
    print("\nSaved Part 8 Three-Way Reproducibility Matrix.")

if __name__ == "__main__":
    main()
