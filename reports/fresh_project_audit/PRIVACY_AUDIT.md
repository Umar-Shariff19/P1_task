# PRIVACY AUDIT

The code implements Differential Privacy via `opacus` (DP-SGD) for the **MLP model only**.

## Critical Finding
The script `scripts/run_privacy_experiments.py` uses **SYNTHETIC GAUSSIAN DATA** (`rng.normal`) to compute DP-SGD ROC-AUC tradeoffs, NOT the actual IIoT datasets!
Therefore, the privacy-utility tradeoff claims for the dataset are **NOT VERIFIED** and heavily compromised.

Furthermore, the Random Forest is **NOT** trained privately. Claiming the entire ensemble is DP is scientifically invalid.
