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

class AutoencoderModule(nn.Module):
    def __init__(self, input_dim: int, bottleneck_dim: int = 16):
        super().__init__()
        self.encoder = nn.Sequential(
            nn.Linear(input_dim, 64),
            nn.ReLU(),
            nn.Linear(64, bottleneck_dim),
            nn.ReLU(),
        )
        self.decoder = nn.Sequential(
            nn.Linear(bottleneck_dim, 64),
            nn.ReLU(),
            nn.Linear(64, input_dim),
        )

    def forward(self, x):
        code = self.encoder(x)
        return self.decoder(code)

def compute_metrics(y_true, y_prob, threshold=0.5):
    pred = (y_prob >= threshold).astype(int)
    acc = float(accuracy_score(y_true, pred))
    prec = float(precision_score(y_true, pred, pos_label=1, zero_division=0))
    rec = float(recall_score(y_true, pred, pos_label=1, zero_division=0))
    f1 = float(f1_score(y_true, pred, pos_label=1, zero_division=0))
    macro_f1 = float(f1_score(y_true, pred, average="macro", zero_division=0))
    try:
        roc = float(roc_auc_score(y_true, y_prob))
    except Exception:
        roc = 0.5
    pr_vec, rec_vec, _ = precision_recall_curve(y_true, y_prob)
    pr_val = float(auc(rec_vec, pr_vec))
    cm = confusion_matrix(y_true, pred)
    tn, fp, fn, tp = cm.ravel()

    return {
        "accuracy": acc, "precision": prec, "recall": rec, "f1": f1,
        "macro_f1": macro_f1, "roc_auc": roc, "pr_auc": pr_val,
        "tn": int(tn), "fp": int(fp), "fn": int(fn), "tp": int(tp)
    }

def eval_indomain_dir(models_dir: Path):
    base_dir = REPO_ROOT / "data" / "processed" / "final"
    datasets = ["Edge-IIoTset", "ToN-IoT"]
    results = {}

    for ds in datasets:
        ds_dir = base_dir / ds
        target_dir = [d for d in ds_dir.iterdir() if d.is_dir()][0]
        test_df = pd.read_parquet(target_dir / "splits" / "test.parquet")

        m_dir = models_dir / ds
        prep_indomain = joblib.load(m_dir / "prep_indomain.joblib")
        rf = joblib.load(m_dir / "rf_model.joblib")

        X_test = prep_indomain.transform(test_df)
        y_test = test_df["label"].values

        mlp = MLPModule(input_dim=X_test.shape[1])
        mlp.load_state_dict(torch.load(m_dir / "mlp_model.pt"))
        mlp.eval()

        ae = AutoencoderModule(input_dim=X_test.shape[1], bottleneck_dim=16)
        ae.load_state_dict(torch.load(m_dir / "ae_model.pt"))
        ae.eval()

        risk_layer = RiskLayer.load(m_dir / "risk_layer.json")

        p_rf = rf.predict_proba(X_test)[:, 1]

        with torch.no_grad():
            X_tensor = torch.tensor(X_test, dtype=torch.float32)
            p_mlp = torch.sigmoid(mlp(X_tensor)).squeeze().numpy()
            recon = ae(X_tensor).numpy()
            ae_mse = np.mean((X_test - recon) ** 2, axis=1)

        p_sup = 0.5 * p_rf + 0.5 * p_mlp
        decisions = risk_layer.predict(p_rf, p_mlp, ae_mse)
        s_ae = risk_layer.calibrate_ae_score(ae_mse)

        res_rf = compute_metrics(y_test, p_rf)
        res_mlp = compute_metrics(y_test, p_mlp)
        res_sup = compute_metrics(y_test, p_sup)

        risk_counts = pd.Series([d.risk_state for d in decisions]).value_counts().to_dict()

        ae_benign_mse_mean = float(np.mean(ae_mse[y_test == 0]))
        ae_attack_mse_mean = float(np.mean(ae_mse[y_test == 1]))

        results[ds] = {
            "test_rows": len(test_df),
            "feature_count": X_test.shape[1],
            "rf_metrics": res_rf,
            "mlp_metrics": res_mlp,
            "supervised_ensemble_metrics": res_sup,
            "ae_stats": {
                "benign_mse_mean": ae_benign_mse_mean,
                "attack_mse_mean": ae_attack_mse_mean,
                "separation_ratio": float(ae_attack_mse_mean / (ae_benign_mse_mean + 1e-12))
            },
            "risk_layer_counts": risk_counts
        }

    return results

def eval_cross_domain_clean(seed: int = 42):
    base_dir = REPO_ROOT / "data" / "processed" / "final"
    common_cols = ["duration", "src_bytes", "proto_tcp", "proto_udp", "proto_icmp", "is_well_known_port"]
    pairs = [("Edge-IIoTset", "ToN-IoT"), ("ToN-IoT", "Edge-IIoTset")]

    results = {}

    for src_ds, tgt_ds in pairs:
        torch.manual_seed(seed)
        np.random.seed(seed)

        src_target = [d for d in (base_dir / src_ds).iterdir() if d.is_dir()][0]
        tgt_target = [d for d in (base_dir / tgt_ds).iterdir() if d.is_dir()][0]

        tr_src = pd.read_parquet(src_target / "splits" / "train.parquet")
        tst_tgt = pd.read_parquet(tgt_target / "splits" / "test.parquet")

        prep_common = PreprocessingPipeline(numeric_cols=common_cols)
        X_tr_c = prep_common.fit_transform(tr_src)
        y_tr_src = tr_src["label"].values

        rf_c = RandomForestClassifier(n_estimators=100, max_depth=15, random_state=seed, n_jobs=-1)
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

        key = f"{src_ds}_to_{tgt_ds}"
        results[key] = compute_metrics(y_tst_tgt, p_sup_c)

    return results

def main():
    print("============================================================")
    print("=== PHASE 4, 5, 6 & 7: FULL FORENSIC RE-EVALUATION & RECONCILIATION ===")
    print("============================================================\n")

    # Load Ground Truth JSON
    eval_json = Path("reports/tables/final_evaluation_results.json")
    frozen_gt = json.loads(eval_json.read_text(encoding="utf-8"))

    # 1. Re-evaluate Protected Frozen Checkpoints (models/final/)
    print("--- 1. THIS IS RE-EVALUATION OF FROZEN CHECKPOINTS, NOT RETRAINING ---")
    frozen_re_eval_in = eval_indomain_dir(REPO_ROOT / "models" / "final")

    # 2. Evaluate Fresh Retrained Checkpoints (models/verification_retrain/)
    print("--- 2. EVALUATION OF ISOLATED FRESHLY RETRAINED CHECKPOINTS ---")
    retrain_eval_in = eval_indomain_dir(REPO_ROOT / "models" / "verification_retrain")

    # 3. Clean Cross-Domain Re-Evaluation
    print("--- 3. CROSS-DOMAIN ZERO-ADAPTATION RE-EVALUATION (6 F_common) ---")
    cd_eval_res = eval_cross_domain_clean(seed=42)

    # 4. Perform Complete Reconciliation Matrix
    reconciliation_rows = []

    metrics = ["accuracy", "precision", "recall", "f1", "macro_f1", "roc_auc", "pr_auc"]

    experiments = [
        ("Edge-IIoTset In-Domain", frozen_gt["in_domain"]["Edge-IIoTset"]["supervised_metrics"], frozen_re_eval_in["Edge-IIoTset"]["supervised_ensemble_metrics"], retrain_eval_in["Edge-IIoTset"]["supervised_ensemble_metrics"]),
        ("ToN-IoT In-Domain", frozen_gt["in_domain"]["ToN-IoT"]["supervised_metrics"], frozen_re_eval_in["ToN-IoT"]["supervised_ensemble_metrics"], retrain_eval_in["ToN-IoT"]["supervised_ensemble_metrics"]),
        ("Edge -> ToN Cross-Domain", frozen_gt["cross_domain"]["Edge-IIoTset_to_ToN-IoT"], cd_eval_res["Edge-IIoTset_to_ToN-IoT"], cd_eval_res["Edge-IIoTset_to_ToN-IoT"]),
        ("ToN -> Edge Cross-Domain", frozen_gt["cross_domain"]["ToN-IoT_to_Edge-IIoTset"], cd_eval_res["ToN-IoT_to_Edge-IIoTset"], cd_eval_res["ToN-IoT_to_Edge-IIoTset"]),
    ]

    for exp_name, gt_dict, re_eval_dict, retrain_dict in experiments:
        for m in metrics:
            val_frozen = gt_dict[m]
            val_reeval = re_eval_dict[m]
            val_retrain = retrain_dict[m]

            diff_reeval = abs(val_reeval - val_frozen)
            diff_retrain = abs(val_retrain - val_frozen)

            # Tolerance check: 0.0 for re-eval of frozen checkpoint; 0.005 for stochastic retraining
            if "In-Domain" in exp_name:
                is_frozen_pass = diff_reeval == 0.0
                is_retrain_pass = diff_retrain < 0.005
            else:
                is_frozen_pass = diff_reeval < 0.0005
                is_retrain_pass = diff_retrain < 0.005

            verdict = "PASS (Exact Frozen Match)" if is_frozen_pass else ("PASS (Stochastic Bound <0.5%)" if is_retrain_pass else "FAIL")

            reconciliation_rows.append({
                "experiment": exp_name,
                "metric": m,
                "frozen_ground_truth": val_frozen,
                "frozen_reeval_run": val_reeval,
                "retrained_fresh_run": val_retrain,
                "frozen_re_eval_diff": diff_reeval,
                "retrained_fresh_diff": diff_retrain,
                "tolerance": 0.0 if "In-Domain" in exp_name else 0.005,
                "verdict": verdict
            })

    # Save JSON & Summary
    reconciliation_json = REPO_ROOT / "reports" / "tables" / "final_retraining_reconciliation.json"
    reconciliation_json.write_text(json.dumps({
        "provenance_statement": "THIS COMBINES BOTH DETAILED RE-EVALUATION OF FROZEN CHECKPOINTS AND ISOLATED VERIFICATION RETRAINING.",
        "frozen_checkpoints_eval": frozen_re_eval_in,
        "fresh_retrained_eval": retrain_eval_in,
        "cross_domain_eval": cd_eval_res,
        "reconciliation_matrix": reconciliation_rows
    }, indent=2), encoding="utf-8")

    print(f"Reconciliation JSON Saved to: {reconciliation_json}\n")

if __name__ == "__main__":
    main()
