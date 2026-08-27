# Stage 9 Final Reproducibility Manifest & Pipeline Inventory

---

## 1. System Environment & Dependency Manifest

- **Operating System**: Microsoft Windows 11 (`win32`)
- **Python Executable**: `.venv\Scripts\python.exe` (Python 3.12.13)
- **Verified Package Manifest**:
  - `pandas == 2.2.3`
  - `numpy == 1.26.4`
  - `scikit-learn == 1.5.2`
  - `scipy == 1.14.1`
  - `pyarrow == 17.0.0`
  - `pytest == 8.4.2`
  - `matplotlib == 3.9.2`
  - `seaborn == 0.13.2`
- **Global Random Seed**: `seed = 42` (Enforced across numpy, scikit-learn, split partitioning, and target label budget sampling).

---

## 2. Complete Execution Command Chain

All experimental scripts, statistical engines, figure generators, and publication audit scripts are fully deterministic and executable in sequence:

```bash
# Step 1: Telemetry Ingestion & Flow Materialization (Stage 1 - 3)
.venv\Scripts\python.exe scripts/03_materialize_and_audit_features.py

# Step 2: Controlled Supervised Model Benchmarking (Stage 4)
.venv\Scripts\python.exe scripts/04_benchmark_models.py
.venv\Scripts\python.exe scripts/04_analyze_ablations.py

# Step 3: Domain Adaptation & Target Calibration (Stage 5)
.venv\Scripts\python.exe scripts/05_domain_adaptation.py
.venv\Scripts\python.exe scripts/05_analyze_adaptation.py
.venv\Scripts\python.exe scripts/05_generate_stage5_plots.py

# Step 4: Statistical Robustness, Effect Sizes & Shortcut Ablation Engine (Stage 6)
.venv\Scripts\python.exe scripts/06_statistical_robustness.py
.venv\Scripts\python.exe scripts/06_generate_stage6_plots.py

# Step 5: Paper Draft Evidence Reconciliation & Claim-Evidence Matrix (Stage 7)
.venv\Scripts\python.exe scripts/07_generate_claim_evidence_matrix.py

# Step 6: Master Publication & Integrity Audit Engine (Stage 8)
.venv\Scripts\python.exe scripts/08_run_publication_audit.py

# Step 7: Final IEEE Submission Package Compilation Engine (Stage 9)
.venv\Scripts\python.exe scripts/09_run_submission_compilation.py

# Step 8: Execute Master Unit Test Suite (34 Unit Tests Across All Modules)
.venv\Scripts\python.exe -m pytest tests/unit/data/ tests/unit/features/ tests/unit/experiments/ tests/unit/adaptation/ tests/unit/statistics/ tests/unit/publication/
```

---

## 3. Artifact Index & Materialized Outputs

- **LaTeX Source Package**: `reports/stage9/IEEE_paper_final.tex`, `reports/stage9/references.bib`
- **Citation Audit Matrix**: `reports/stage9/stage9_citation_audit.csv`
- **Figure & Table Audit Matrix**: `reports/stage9/stage9_figure_table_audit.csv`
- **Numerical Reconciliation Matrix**: `reports/stage9/stage9_numerical_reconciliation.csv`
- **Submission Audit Report**: `reports/stage9/stage9_submission_audit.md`
- **Materialized Parquet Testbed**: `data/processed/stage3/` (28,000 total flows)
- **Publication PNG Plots**: `reports/stage6/plots/` (7 PNG figures)
