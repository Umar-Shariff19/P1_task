import json
from pathlib import Path
import pandas as pd

def main():
    rec_json_path = Path("reports/tables/final_retraining_reconciliation.json")
    data = json.loads(rec_json_path.read_text(encoding="utf-8"))

    matrix = data["reconciliation_matrix"]
    df = pd.DataFrame(matrix)

    print("============================================================")
    print("=== PHASE 7 & 10: RECONCILIATION MATRIX & FORENSIC VERDICT ===")
    print("============================================================\n")

    print(df[["experiment", "metric", "frozen_ground_truth", "frozen_reeval_run", "retrained_fresh_run", "frozen_re_eval_diff", "retrained_fresh_diff", "verdict"]].to_string(index=False))

    print("\n--- Detailed Confusion Matrices & Metrics for Re-evaluation ---")
    frozen_eval = data["frozen_checkpoints_eval"]
    for ds, val in frozen_eval.items():
        sup = val["supervised_ensemble_metrics"]
        print(f"\n[{ds} In-Domain Re-Evaluation]")
        print(f"  Accuracy:  {sup['accuracy']*100:.2f}% ({sup['accuracy']:.6f})")
        print(f"  Precision: {sup['precision']*100:.2f}% ({sup['precision']:.6f})")
        print(f"  Recall:    {sup['recall']*100:.2f}% ({sup['recall']:.6f})")
        print(f"  Attack F1: {sup['f1']*100:.2f}% ({sup['f1']:.6f})")
        print(f"  Macro F1:  {sup['macro_f1']*100:.2f}% ({sup['macro_f1']:.6f})")
        print(f"  ROC AUC:   {sup['roc_auc']:.6f}")
        print(f"  PR AUC:    {sup['pr_auc']:.6f}")
        print(f"  Confusion Matrix: TP={sup['tp']}, FP={sup['fp']}, TN={sup['tn']}, FN={sup['fn']}")
        print(f"  AE Stats: Benign MSE Mean={val['ae_stats']['benign_mse_mean']:.6e}, Attack MSE Mean={val['ae_stats']['attack_mse_mean']:.6e}, Separation Ratio={val['ae_stats']['separation_ratio']:.2f}")

    print("\n--- Detailed Cross-Domain Metrics (6 F_common Features) ---")
    cd_eval = data["cross_domain_eval"]
    for pair, val in cd_eval.items():
        print(f"\n[{pair} Cross-Domain Transfer]")
        print(f"  Accuracy:  {val['accuracy']*100:.2f}% ({val['accuracy']:.6f})")
        print(f"  Precision: {val['precision']*100:.2f}% ({val['precision']:.6f})")
        print(f"  Recall:    {val['recall']*100:.2f}% ({val['recall']:.6f})")
        print(f"  Attack F1: {val['f1']*100:.2f}% ({val['f1']:.6f})")
        print(f"  Macro F1:  {val['macro_f1']*100:.2f}% ({val['macro_f1']:.6f})")
        print(f"  ROC AUC:   {val['roc_auc']:.6f}")
        print(f"  PR AUC:    {val['pr_auc']:.6f}")
        print(f"  Confusion Matrix: TP={val['tp']}, FP={val['fp']}, TN={val['tn']}, FN={val['fn']}")

if __name__ == "__main__":
    main()
