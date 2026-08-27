# Stage 9 Paper-Ready Artifact Index

---

## Paper Artifact Mapping & Verification Matrix

| Paper Element | Description | Primary Source CSV / Report | Generating Script | Core Code Implementation |
|:---|:---|:---|:---|:---|
| **Title & Abstract** | Title, Abstract, Keywords | `reports/stage9/IEEE_paper_final.tex` | Handcrafted LaTeX | N/A |
| **Section I** | Introduction & 5 Core Contributions (C1–C5) | `reports/stage9/IEEE_paper_final.tex` | Handcrafted LaTeX | N/A |
| **Section II** | Related Work Category Analysis | `reports/stage9/IEEE_paper_final.tex`, `references.bib` | Handcrafted LaTeX | N/A |
| **Section III / Table I** | Dataset Ingestion & Telemetry Characteristics | `reports/stage1_ingestion_audit.md` | `03_materialize_and_audit_features.py` | `src/iot_ids/data/adapters/` |
| **Section IV / Table II** | Candidate 18-Feature Specification | `reports/stage2_temporal_semantics.md` | `03_materialize_and_audit_features.py` | `src/iot_ids/features/canonical/` |
| **Section V / Table III, V** | Within-Domain Benchmark Results | `reports/stage4/stage4_within_domain_results.csv` | `scripts/04_benchmark_models.py` | `src/iot_ids/experiments/` |
| **Section VI / Table IV, VI** | Zero-Shot & Adapted Cross-Domain Results | `reports/stage5/stage5_adaptation_summary.csv` | `scripts/05_domain_adaptation.py` | `src/iot_ids/adaptation/` |
| **Section VII / Table VII** | Paired Effect Sizes & 95% Bootstrap CIs | `reports/stage6/stage6_effect_sizes.csv`, `reports/stage6/stage6_confidence_intervals.csv` | `scripts/06_statistical_robustness.py` | `src/iot_ids/statistics/` |
| **Section VIII / Table VIII** | Domain Shortcut Feature Ablation Audit | `reports/stage6/stage6_shortcut_ablation.csv` | `scripts/06_statistical_robustness.py` | `src/iot_ids/statistics/robustness.py` |
| **BibTeX Database** | Scholarly References File | `reports/stage9/references.bib` | `09_run_submission_compilation.py` | `reports/stage9/references.bib` |
