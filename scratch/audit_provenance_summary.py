import json
from pathlib import Path

print("============================================================")
print("=== FORENSIC AUDIT 2 & 3: RECONCILED METRICS INSPECTION ===")
print("============================================================\n")

json_path = Path("reports/tables/final_evaluation_results.json")
data = json.loads(json_path.read_text(encoding="utf-8"))

print(f"{'Experiment':<35} | {'Feat Count':<10} | {'Accuracy':<8} | {'Precision':<9} | {'Recall':<8} | {'Attack F1':<9} | {'ROC AUC':<8} | {'PR AUC':<8}")
print("-" * 110)

for k, v in data.items():
    if "ablation" in k:
        continue
    fc = v.get("feature_count", 0)
    acc = v.get("accuracy", 0.0)
    prec = v.get("precision", 0.0)
    rec = v.get("recall", 0.0)
    f1 = v.get("f1_attack", 0.0)
    roc = v.get("roc_auc", 0.0)
    pr = v.get("pr_auc", 0.0)
    print(f"{k:<35} | {fc:<10} | {acc*100:<7.2f}% | {prec*100:<8.2f}% | {rec*100:<7.2f}% | {f1*100:<8.2f}% | {roc:<8.4f} | {pr:<8.4f}")

