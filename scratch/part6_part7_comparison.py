import json
from pathlib import Path
import pandas as pd

def main():
    print("============================================================")
    print("=== PART 6 & 7: FROZEN VS FRESH COMPARISON & STOCHASTIC ANALYSIS ===")
    print("============================================================\n")

    exp_dir = Path("reproducibility/fresh_retraining_20260821_010000")
    run1_dir = exp_dir / "run1"

    frozen_json = Path("reports/tables/final_evaluation_results.json")
    frozen_data = json.loads(frozen_json.read_text(encoding="utf-8"))

    fresh_in = json.loads((run1_dir / "FRESH_INDOMAIN_RESULTS.json").read_text(encoding="utf-8"))
    fresh_cd = json.loads((run1_dir / "FRESH_CROSS_DOMAIN_RESULTS.json").read_text(encoding="utf-8"))

    # 1. Edge-IIoTset In-Domain
    f_edge = frozen_data["in_domain"]["Edge-IIoTset"]["supervised_metrics"]
    r_edge = fresh_in["Edge-IIoTset"]["supervised_ensemble_metrics"]

    # 2. ToN-IoT In-Domain
    f_ton = frozen_data["in_domain"]["ToN-IoT"]["supervised_metrics"]
    r_ton = fresh_in["ToN-IoT"]["supervised_ensemble_metrics"]

    # 3. Edge -> ToN Cross-Domain
    f_e2t = frozen_data["cross_domain"]["Edge-IIoTset_to_ToN-IoT"]
    r_e2t = fresh_cd["Edge-IIoTset_to_ToN-IoT"]["supervised_ensemble_metrics"]

    # 4. ToN -> Edge Cross-Domain
    f_t2e = frozen_data["cross_domain"]["ToN-IoT_to_Edge-IIoTset"]
    r_t2e = fresh_cd["ToN-IoT_to_Edge-IIoTset"]["supervised_ensemble_metrics"]

    targets = [
        ("Edge-IIoTset In-Domain", f_edge, r_edge),
        ("ToN-IoT In-Domain", f_ton, r_ton),
        ("Edge -> ToN Cross-Domain", f_e2t, r_e2t),
        ("ToN -> Edge Cross-Domain", f_t2e, r_t2e),
    ]

    metrics_list = ["accuracy", "precision", "recall", "f1", "macro_f1", "roc_auc", "pr_auc"]

    rows = []

    for exp_name, f_dict, r_dict in targets:
        for m in metrics_list:
            v_frozen = f_dict[m]
            v_fresh = r_dict[m]

            abs_diff = abs(v_fresh - v_frozen)
            rel_diff = (v_fresh - v_frozen) / v_frozen * 100 if v_frozen != 0 else 0

            # Verdict evaluation
            if abs_diff < 0.0005:
                verdict = "MATCH (Identical)"
            elif abs_diff < 0.005:
                verdict = "MATCH (Within < 0.5% Variation)"
            else:
                verdict = "MINOR STOCHASTIC VARIATION"

            rows.append({
                "Experiment": exp_name,
                "Metric": m,
                "Frozen": f"{v_frozen*100:.2f}%" if m not in ["roc_auc", "pr_auc"] else f"{v_frozen:.4f}",
                "Fresh (Run 1)": f"{v_fresh*100:.2f}%" if m not in ["roc_auc", "pr_auc"] else f"{v_fresh:.4f}",
                "Absolute Diff": f"{abs_diff:.6f}",
                "Relative Diff (%)": f"{rel_diff:+.4f}%",
                "Verdict": verdict
            })

    df_comp = pd.DataFrame(rows)
    print(df_comp.to_string(index=False))

    json_out = exp_dir / "FROZEN_VS_FRESH_COMPARISON.json"
    json_out.write_text(json.dumps(rows, indent=2), encoding="utf-8")
    print(f"\nSaved Comparison JSON: {json_out}\n")

if __name__ == "__main__":
    main()
