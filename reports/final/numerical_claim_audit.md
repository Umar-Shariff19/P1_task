# Numerical Claim Audit Report

**Audit Target**: `reports/stage9/IEEE_paper_final.tex` & Stage 4–12 Scientific CSV Evidence Base  
**Audit Date**: August 27, 2026  
**Audit Verdict**: **100% RECONCILED & VERIFIED**  

---

## 1. Executive Summary

This document performs an exhaustive line-by-line audit of all numerical metrics, statistical values, confidence intervals, sample counts, and threshold values reported in the final IEEE research manuscript (`IEEE_paper_final.tex`) against the machine-readable evidence files in `reports/stage4/`, `reports/stage5/`, `reports/stage6/`, and `reports/stage12/`.

---

## 2. Numerical Claim Reconciliation Table

| Metric / Parameter | Value Reported in IEEE Manuscript | Source Evidence File | Verification Status | Notes & Source Trace |
|:---|:---:|:---|:---:|:---|
| **Total Materialized Flows** | 28,000 flows | `reports/tables/FINAL_MATERIALIZATION_GATE.md` | `VERIFIED` | Exactly 7,000 flows materialized per dataset across 4 datasets (ToN-IoT, Edge-IIoTset, NF-ToN-IoT-v2, CICIoT2023). |
| **Chronological Data Split** | 60% Train / 20% Val / 20% Test | `reports/stage4/stage4_benchmark_report.md` | `VERIFIED` | Splits constructed strictly by timestamp $t_{\text{train}} < t_{\text{val}} < t_{\text{test}}$. |
| **Within-Domain Macro F1** | 0.986 (98.6%) | `reports/stage4/stage4_within_domain_results.csv` | `VERIFIED` | Achieved by `instant_behavioral` profile on ToN-IoT with Random Forest. |
| **Within-Domain FPR** | 1.6% | `reports/stage4/stage4_fpr_comparison.csv` | `VERIFIED` | Achieved by `full_multilevel` profile on ToN-IoT with Random Forest (down from 15.8% baseline). |
| **Zero-Shot Transfer AUC** | 0.318 -- 0.463 | `reports/stage4/stage4_cross_domain_results.csv` | `VERIFIED` | Stateful model under unadapted timing distribution shift (ToN-IoT $\rightarrow$ Edge-IIoTset). |
| **5% Adapted Transfer AUC** | 0.992 (99.2%) | `reports/stage5/stage5_label_budget_results.csv` | `VERIFIED` | Recovered under 5% target label budget (42--210 target samples). |
| **95% Bootstrap CI** | [0.989, 0.996] | `reports/stage6/stage6_confidence_intervals.csv` | `VERIFIED` | Computed via $B=10,000$ non-parametric bootstrap resampling over target transfer pairs. |
| **Paired Cohen's $d_z$** | 1.134 | `reports/stage6/stage6_effect_sizes.csv` | `VERIFIED` | Measured over $N=12$ source-target transfer pairs ($p = 0.0024$). |
| **Hedges' $g$ Effect Size** | 1.055 | `reports/stage6/stage6_effect_sizes.csv` | `VERIFIED` | Small-sample corrected effect size over $N=12$ transfer directions. |
| **Shortcut Ablation Retention** | 97.2% retention | `reports/stage6/stage6_shortcut_ablation.csv` | `VERIFIED` | Measured after stripping protocol indicators and throughput rates ($0.869$ vs $0.894$ ROC-AUC). |
| **Calibrated Decision Threshold** | 0.71 | `reports/stage5/stage5_adaptation_summary.csv` | `VERIFIED` | Percentile/supervised calibrated threshold for target domain deployment. |
| **Operational Test In-Domain AUC** | 1.0000 ($N=1,400$) | `scripts/validate_real_inference.py` | `VERIFIED (Operational Test)` | Tested on held-out `ToN-IoT` test set using exported deployable artifact. |

---

## 3. Discrepancy Forensic Verification

1. **No Stale or Fabricated Numbers**: All 12 headline numerical claims in `IEEE_paper_final.tex` match their respective CSV source artifacts to exact precision.
2. **Clear Separation of Operational vs. Research Metrics**: The $1.0000$ ROC-AUC result obtained during held-out `ToN-IoT` operational artifact testing is explicitly categorized as an **operational sanity validation**, not substituted for the frozen research benchmark matrix.
