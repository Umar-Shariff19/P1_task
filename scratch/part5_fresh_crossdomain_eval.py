import json
import sys
from pathlib import Path

def main():
    exp_dir = Path("reproducibility/fresh_retraining_20260821_010000/run1")
    json_path = exp_dir / "FRESH_CROSS_DOMAIN_RESULTS.json"
    data = json.loads(json_path.read_text(encoding="utf-8"))

    e2t = data["Edge-IIoTset_to_ToN-IoT"]["supervised_ensemble_metrics"]
    t2e = data["ToN-IoT_to_Edge-IIoTset"]["supervised_ensemble_metrics"]

    e2t_rf = data["Edge-IIoTset_to_ToN-IoT"]["rf_metrics"]
    e2t_mlp = data["Edge-IIoTset_to_ToN-IoT"]["mlp_metrics"]

    t2e_rf = data["ToN-IoT_to_Edge-IIoTset"]["rf_metrics"]
    t2e_mlp = data["ToN-IoT_to_Edge-IIoTset"]["mlp_metrics"]

    md_content = """# FRESH CROSS-DOMAIN EVALUATION RESULTS

> **Evaluation Pathway**: Zero-adaptation cross-domain evaluation using clean 6-feature F_common space (`duration`, `src_bytes`, `proto_tcp`, `proto_udp`, `proto_icmp`, `is_well_known_port`). No target labels, target retraining, or target adaptation.

---

## 1. EDGE-IIOTSET -> TON-IOT CROSS-DOMAIN FRESH RESULTS (6 Features, N=42,209)

- **Random Forest Only**: Accuracy = {rf_acc_e2t:.2f}%, F1 = {rf_f1_e2t:.2f}%, ROC AUC = {rf_roc_e2t:.4f}
- **MLP Only**: Accuracy = {mlp_acc_e2t:.2f}%, F1 = {mlp_f1_e2t:.2f}%, ROC AUC = {mlp_roc_e2t:.4f}
- **Supervised Ensemble (P_sup)**:
  - **Accuracy**: {acc_e2t_4:.4f}% (Rounded: **{acc_e2t:.2f}%**)
  - **Precision**: {prec_e2t_4:.4f}% (Rounded: **{prec_e2t:.2f}%**)
  - **Recall**: {rec_e2t_4:.4f}% (Rounded: **{rec_e2t:.2f}%**)
  - **Attack F1**: {f1_e2t_4:.4f}% (Rounded: **{f1_e2t:.2f}%**)
  - **Macro F1**: {macro_f1_e2t_4:.4f}% (Rounded: **{macro_f1_e2t:.2f}%**)
  - **ROC AUC**: {roc_e2t_6:.6f} (Rounded: **{roc_e2t:.4f}**)
  - **PR AUC**: {pr_e2t_6:.6f} (Rounded: **{pr_e2t:.4f}**)
  - **Confusion Matrix**: TP={tp_e2t}, FP={fp_e2t}, TN={tn_e2t}, FN={fn_e2t}

---

## 2. TON-IOT -> EDGE-IIOTSET CROSS-DOMAIN FRESH RESULTS (6 Features, N=31,560)

- **Random Forest Only**: Accuracy = {rf_acc_t2e:.2f}%, F1 = {rf_f1_t2e:.2f}%, ROC AUC = {rf_roc_t2e:.4f}
- **MLP Only**: Accuracy = {mlp_acc_t2e:.2f}%, F1 = {mlp_f1_t2e:.2f}%, ROC AUC = {mlp_roc_t2e:.4f}
- **Supervised Ensemble (P_sup)**:
  - **Accuracy**: {acc_t2e_4:.4f}% (Rounded: **{acc_t2e:.2f}%**)
  - **Precision**: {prec_t2e_4:.4f}% (Rounded: **{prec_t2e:.2f}%**)
  - **Recall**: {rec_t2e_4:.4f}% (Rounded: **{rec_t2e:.2f}%**)
  - **Attack F1**: {f1_t2e_4:.4f}% (Rounded: **{f1_t2e:.2f}%**)
  - **Macro F1**: {macro_f1_t2e_4:.4f}% (Rounded: **{macro_f1_t2e:.2f}%**)
  - **ROC AUC**: {roc_t2e_6:.6f} (Rounded: **{roc_t2e:.4f}**)
  - **PR AUC**: {pr_t2e_6:.6f} (Rounded: **{pr_t2e:.4f}**)
  - **Confusion Matrix**: TP={tp_t2e}, FP={fp_t2e}, TN={tn_t2e}, FN={fn_t2e}
""".format(
        rf_acc_e2t=e2t_rf["accuracy"]*100, rf_f1_e2t=e2t_rf["f1"]*100, rf_roc_e2t=e2t_rf["roc_auc"],
        mlp_acc_e2t=e2t_mlp["accuracy"]*100, mlp_f1_e2t=e2t_mlp["f1"]*100, mlp_roc_e2t=e2t_mlp["roc_auc"],
        acc_e2t_4=e2t["accuracy"]*100, prec_e2t_4=e2t["precision"]*100, rec_e2t_4=e2t["recall"]*100, f1_e2t_4=e2t["f1"]*100, macro_f1_e2t_4=e2t["macro_f1"]*100, roc_e2t_6=e2t["roc_auc"], pr_e2t_6=e2t["pr_auc"],
        acc_e2t=e2t["accuracy"]*100, prec_e2t=e2t["precision"]*100, rec_e2t=e2t["recall"]*100, f1_e2t=e2t["f1"]*100, macro_f1_e2t=e2t["macro_f1"]*100, roc_e2t=e2t["roc_auc"], pr_e2t=e2t["pr_auc"],
        tp_e2t=e2t["confusion_matrix"]["tp"], fp_e2t=e2t["confusion_matrix"]["fp"], tn_e2t=e2t["confusion_matrix"]["tn"], fn_e2t=e2t["confusion_matrix"]["fn"],
        rf_acc_t2e=t2e_rf["accuracy"]*100, rf_f1_t2e=t2e_rf["f1"]*100, rf_roc_t2e=t2e_rf["roc_auc"],
        mlp_acc_t2e=t2e_mlp["accuracy"]*100, mlp_f1_t2e=t2e_mlp["f1"]*100, mlp_roc_t2e=t2e_mlp["roc_auc"],
        acc_t2e_4=t2e["accuracy"]*100, prec_t2e_4=t2e["precision"]*100, rec_t2e_4=t2e["recall"]*100, f1_t2e_4=t2e["f1"]*100, macro_f1_t2e_4=t2e["macro_f1"]*100, roc_t2e_6=t2e["roc_auc"], pr_t2e_6=t2e["pr_auc"],
        acc_t2e=t2e["accuracy"]*100, prec_t2e=t2e["precision"]*100, rec_t2e=t2e["recall"]*100, f1_t2e=t2e["f1"]*100, macro_f1_t2e=t2e["macro_f1"]*100, roc_t2e=t2e["roc_auc"], pr_t2e=t2e["pr_auc"],
        tp_t2e=t2e["confusion_matrix"]["tp"], fp_t2e=t2e["confusion_matrix"]["fp"], tn_t2e=t2e["confusion_matrix"]["tn"], fn_t2e=t2e["confusion_matrix"]["fn"]
    )

    md_out = exp_dir / "FRESH_CROSS_DOMAIN_RESULTS.md"
    md_out.write_text(md_content, encoding="utf-8")
    print(f"Saved Markdown: {md_out}\n")

if __name__ == "__main__":
    main()
