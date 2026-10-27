"""Stage 4 Ablation Analyzer and Statistical Report Generator.

Computes incremental representation contributions (Δ ROC-AUC, Δ PR-AUC, Δ F1, Δ FPR)
and generates reports/stage4_ablation_summary.csv and reports/stage4_benchmark_report.md.
"""
from __future__ import annotations

from pathlib import Path
import pandas as pd


def summarize_metric(frame: pd.DataFrame, column: str) -> tuple[float | None, int, int]:
    """Return (mean, defined_count, undefined_count) without inventing zeroes."""
    if column not in frame.columns:
        raise KeyError(f"Required metric column is missing: {column}")
    values = pd.to_numeric(frame[column], errors="raise")
    defined = values.dropna()
    mean = float(defined.mean()) if not defined.empty else None
    return mean, int(defined.size), int(values.isna().sum())


def _difference(left: float | None, right: float | None) -> float | None:
    if left is None or right is None:
        return None
    return float(left - right)


def analyze_ablations(reports_dir: str | Path = Path("reports")):
    from iot_ids.provenance.windows_access import require_real_data_authorization
    require_real_data_authorization()
    reports_dir = Path(reports_dir)
    df_within = pd.read_csv(reports_dir / "stage4_results.csv")
    df_cross = pd.read_csv(reports_dir / "stage4_cross_domain.csv")

    print("=== Analyzing Within-Domain & Cross-Domain Incremental Ablations ===")

    profiles = ["baseline_common", "instant_only", "instant_temporal", "instant_behavioral", "full_multilevel"]
    models = df_within["model_name"].unique()

    ablation_rows = []

    for model in models:
        sub_within = df_within[df_within["model_name"] == model]
        sub_cross = df_cross[df_cross["model_name"] == model]

        # Get baseline_common metrics
        base_within = sub_within[sub_within["feature_profile"] == "baseline_common"]
        base_cross = sub_cross[sub_cross["feature_profile"] == "baseline_common"]

        base_within_f1, _, _ = summarize_metric(base_within, "macro_f1")
        base_within_fpr, _, _ = summarize_metric(base_within, "fpr")
        base_cross_f1, _, _ = summarize_metric(base_cross, "macro_f1")
        base_cross_fpr, _, _ = summarize_metric(base_cross, "fpr")
        base_cross_auc, _, _ = summarize_metric(base_cross, "roc_auc")

        for p in profiles:
            p_within = sub_within[sub_within["feature_profile"] == p]
            p_cross = sub_cross[sub_cross["feature_profile"] == p]
            w_auc, w_auc_defined, w_auc_undefined = summarize_metric(p_within, "roc_auc")
            w_pr, _, _ = summarize_metric(p_within, "pr_auc")
            w_f1, _, _ = summarize_metric(p_within, "macro_f1")
            w_fpr, _, _ = summarize_metric(p_within, "fpr")
            c_auc, c_auc_defined, c_auc_undefined = summarize_metric(p_cross, "roc_auc")
            c_pr, _, _ = summarize_metric(p_cross, "pr_auc")
            c_f1, _, _ = summarize_metric(p_cross, "macro_f1")
            c_fpr, _, _ = summarize_metric(p_cross, "fpr")

            ablation_rows.append({
                "model_name": model,
                "feature_profile": p,
                "within_roc_auc_mean": w_auc,
                "within_roc_auc_defined_count": w_auc_defined,
                "within_roc_auc_undefined_count": w_auc_undefined,
                "within_pr_auc_mean": w_pr,
                "within_macro_f1_mean": w_f1,
                "within_fpr_mean": w_fpr,
                "cross_roc_auc_mean": c_auc,
                "cross_roc_auc_defined_count": c_auc_defined,
                "cross_roc_auc_undefined_count": c_auc_undefined,
                "cross_pr_auc_mean": c_pr,
                "cross_macro_f1_mean": c_f1,
                "cross_fpr_mean": c_fpr,
                "delta_cross_auc_vs_baseline": _difference(c_auc, base_cross_auc),
                "delta_cross_f1_vs_baseline": _difference(c_f1, base_cross_f1),
                "delta_cross_fpr_vs_baseline": _difference(c_fpr, base_cross_fpr),
                # The input CSVs are not bound to authenticated provenance.
                "evidence_status": "UNVERIFIED",
            })

    df_ablation = pd.DataFrame(ablation_rows)
    df_ablation.to_csv(reports_dir / "stage4_ablation_summary.csv", index=False)
    print(f"Saved ablation summary matrix to {reports_dir / 'stage4_ablation_summary.csv'}")


if __name__ == "__main__":
    analyze_ablations()
