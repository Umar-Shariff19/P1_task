import json
import sys
from pathlib import Path
import joblib
import numpy as np
import pandas as pd
import torch
import torch.nn as nn
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, roc_auc_score, precision_recall_curve, auc, confusion_matrix

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
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
    cm = confusion_matrix(y_true, pred)
    tn, fp, fn, tp = cm.ravel()

    return {
        "accuracy": acc, "precision": prec, "recall": rec, "f1": f1,
        "macro_f1": macro_f1, "roc_auc": roc, "pr_auc": pr_val,
        "confusion_matrix": {"tn": int(tn), "fp": int(fp), "fn": int(fn), "tp": int(tp)}
    }

def main():
    print("============================================================")
    print("=== PART 4: FRESH IN-DOMAIN EVALUATION (RUN 1) ===")
    print("============================================================\n")

    base_dir = REPO_ROOT / "data" / "processed" / "final"
    exp_dir = Path("reproducibility/fresh_retraining_20260821_010000/run1")
    datasets = ["Edge-IIoTset", "ToN-IoT"]

    fresh_indomain_results = {}

    for ds in datasets:
        print(f"Evaluating Freshly Trained Models on {ds} Test Split...")
        ds_dir = base_dir / ds
        target_dir = [d for d in ds_dir.iterdir() if d.is_dir()][0]
        test_df = pd.read_parquet(target_dir / "splits" / "test.parquet")

        m_dir = exp_dir / ds
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

        fresh_indomain_results[ds] = {
            "test_rows": len(test_df),
            "feature_count": X_test.shape[1],
            "rf_metrics": res_rf,
            "mlp_metrics": res_mlp,
            "supervised_ensemble_metrics": res_sup,
            "risk_layer_counts": risk_counts
        }

        print(f"  -> {ds} Fresh Ensemble F1: {res_sup['f1']*100:.2f}%, Accuracy: {res_sup['accuracy']*100:.2f}%, ROC: {res_sup['roc_auc']:.4f}\n")

    json_out = exp_dir / "FRESH_INDOMAIN_RESULTS.json"
    json_out.write_text(json.dumps(fresh_indomain_results, indent=2), encoding="utf-8")
    print(f"Saved JSON: {json_out}")

    # Generate Markdown Summary
    md_content = """# FRESH IN-DOMAIN EVALUATION RESULTS

> **Evaluation Pathway**: Freshly trained models from `reproducibility/fresh_retraining_20260821_010000/run1/` evaluated on untouched Test split parquets (`data/processed/final/`).

---

## 1. EDGE-IIOTSET IN-DOMAIN FRESH RESULTS (13 Features, N=31,560)

- **Random Forest Only**: Accuracy = `{rf_acc_edge:.2f}%`, F1 = `{rf_f1_edge:.2f}%`, ROC AUC = `{rf_roc_edge:.4f}`
- **MLP Only**: Accuracy = `{mlp_acc_edge:.2f}%`, F1 = `{mlp_f1_edge:.2f}%`, ROC AUC = `{mlp_roc_edge:.4f}`
- **Supervised Ensemble (P_sup)**:
  - **Accuracy**: `{acc_edge:.4f}%` (Rounded: **{acc_edge:.2f}%**)
  - **Precision**: `{prec_edge:.4f}%` (Rounded: **{prec_edge:.2f}%**)
  - **Recall**: `{rec_edge:.4f}%` (Rounded: **{rec_edge:.2f}%**)
  - **Attack F1**: `{f1_edge:.4f}%` (Rounded: **{f1_edge:.2f}%**)
  - **Macro F1**: `{macro_f1_edge:.4f}%` (Rounded: **{macro_f1_edge:.2f}%**)
  - **ROC AUC**: `{roc_edge:.6f}` (Rounded: **{roc_edge:.4f}**)
  - **PR AUC**: `{pr_edge:.6f}` (Rounded: **{pr_edge:.4f}**)
  - **Confusion Matrix**: TP={tp_edge}, FP={fp_edge}, TN={tn_edge}, FN={fn_edge}

---

## 2. TON-IOT NETWORK IN-DOMAIN FRESH RESULTS (13 Features, N=42,209)

- **Random Forest Only**: Accuracy = `{rf_acc_ton:.2f}%`, F1 = `{rf_f1_ton:.2f}%`, ROC AUC = `{rf_roc_ton:.4f}`
- **MLP Only**: Accuracy = `{mlp_acc_ton:.2f}%`, F1 = `{mlp_f1_ton:.2f}%`, ROC AUC = `{mlp_roc_ton:.4f}`
- **Supervised Ensemble (P_sup)**:
  - **Accuracy**: `{acc_ton:.4f}%` (Rounded: **{acc_ton:.2f}%**)
  - **Precision**: `{prec_ton:.4f}%` (Rounded: **{prec_ton:.2f}%**)
  - **Recall**: `{rec_ton:.4f}%` (Rounded: **{rec_ton:.2f}%**)
  - **Attack F1**: `{f1_ton:.4f}%` (Rounded: **{f1_ton:.2f}%**)
  - **Macro F1**: `{macro_f1_ton:.4f}%` (Rounded: **{macro_f1_ton:.2f}%**)
  - **ROC AUC**: `{roc_ton:.6f}` (Rounded: **{roc_ton:.4f}**)
  - **PR AUC**: `{pr_ton:.6f}` (Rounded: **{pr_ton:.4f}**)
  - **Confusion Matrix**: TP={tp_ton}, FP={fp_ton}, TN={tn_ton}, FN={fn_ton}
""".format(
        rf_acc_edge=fresh_indomain_results["Edge-IIoTset"]["rf_metrics"]["accuracy"]*100, rf_f1_edge=fresh_indomain_results["Edge-IIoTset"]["rf_metrics"]["f1"]*100, rf_roc_edge=fresh_indomain_results["Edge-IIoTset"]["rf_metrics"]["roc_auc"],
        mlp_acc_edge=fresh_indomain_results["Edge-IIoTset"]["mlp_metrics"]["accuracy"]*100, mlp_f1_edge=fresh_indomain_results["Edge-IIoTset"]["mlp_metrics"]["f1"]*100, mlp_roc_edge=fresh_indomain_results["Edge-IIoTset"]["mlp_metrics"]["roc_auc"],
        acc_edge=fresh_indomain_results["Edge-IIoTset"]["supervised_ensemble_metrics"]["accuracy"]*100, prec_edge=fresh_indomain_results["Edge-IIoTset"]["supervised_ensemble_metrics"]["precision"]*100, rec_edge=fresh_indomain_results["Edge-IIoTset"]["supervised_ensemble_metrics"]["recall"]*100, f1_edge=fresh_indomain_results["Edge-IIoTset"]["supervised_ensemble_metrics"]["f1"]*100, macro_f1_edge=fresh_indomain_results["Edge-IIoTset"]["supervised_ensemble_metrics"]["macro_f1"]*100, roc_edge=fresh_indomain_results["Edge-IIoTset"]["supervised_ensemble_metrics"]["roc_auc"], pr_edge=fresh_indomain_results["Edge-IIoTset"]["supervised_ensemble_metrics"]["pr_auc"],
        tp_edge=fresh_indomain_results["Edge-IIoTset"]["supervised_ensemble_metrics"]["confusion_matrix"]["tp"], fp_edge=fresh_indomain_results["Edge-IIoTset"]["supervised_ensemble_metrics"]["confusion_matrix"]["fp"], tn_edge=fresh_indomain_results["Edge-IIoTset"]["supervised_ensemble_metrics"]["confusion_matrix"]["tn"], fn_edge=fresh_indomain_results["Edge-IIoTset"]["supervised_ensemble_metrics"]["confusion_matrix"]["fn"],
        rf_acc_ton=fresh_indomain_results["ToN-IoT"]["rf_metrics"]["accuracy"]*100, rf_f1_ton=fresh_indomain_results["ToN-IoT"]["rf_metrics"]["f1"]*100, rf_roc_ton=fresh_indomain_results["ToN-IoT"]["rf_metrics"]["roc_auc"],
        mlp_acc_ton=fresh_indomain_results["ToN-IoT"]["mlp_metrics"]["accuracy"]*100, mlp_f1_ton=fresh_indomain_results["ToN-IoT"]["mlp_metrics"]["f1"]*100, mlp_roc_ton=fresh_indomain_results["ToN-IoT"]["mlp_metrics"]["roc_auc"],
        acc_ton=fresh_indomain_results["ToN-IoT"]["supervised_ensemble_metrics"]["accuracy"]*100, prec_ton=fresh_indomain_results["ToN-IoT"]["supervised_ensemble_metrics"]["precision"]*100, rec_ton=fresh_indomain_results["ToN-IoT"]["supervised_ensemble_metrics"]["recall"]*100, f1_ton=fresh_indomain_results["ToN-IoT"]["supervised_ensemble_metrics"]["f1"]*100, macro_f1_ton=fresh_indomain_results["ToN-IoT"]["supervised_ensemble_metrics"]["macro_f1"]*100, roc_ton=fresh_indomain_results["ToN-IoT"]["supervised_ensemble_metrics"]["roc_auc"], pr_ton=fresh_indomain_results["ToN-IoT"]["supervised_ensemble_metrics"]["pr_auc"],
        tp_ton=fresh_indomain_results["ToN-IoT"]["supervised_ensemble_metrics"]["confusion_matrix"]["tp"], fp_ton=fresh_indomain_results["ToN-IoT"]["supervised_ensemble_metrics"]["confusion_matrix"]["fp"], tn_ton=fresh_indomain_results["ToN-IoT"]["supervised_ensemble_metrics"]["confusion_matrix"]["tn"], fn_ton=fresh_indomain_results["ToN-IoT"]["supervised_ensemble_metrics"]["confusion_matrix"]["fn"]
    )

    md_out = exp_dir / "FRESH_INDOMAIN_RESULTS.md"
    md_out.write_text(md_content, encoding="utf-8")
    print(f"Saved Markdown: {md_out}\n")

if __name__ == "__main__":
    main()
