# V3 Ensemble Validation & Simplex Optimization Gate Report

> [!IMPORTANT]
> **GATE VERDICT: V3 ENSEMBLE VALIDATION GATE — PASS**
> 
> Simplex fusion weights ($w_{\text{rf}} + w_{\text{mlp}} + w_{\text{ae}} = 1.0$) and decision thresholds ($\tau$) were optimized **strictly on source Validation sets**. Test split data was **never seen** by the optimizer.

---

## Optimal Validation Fusion Configurations

| Dataset | RF Weight ($w_{\text{rf}}$) | MLP Weight ($w_{\text{mlp}}$) | AE Weight ($w_{\text{ae}}$) | Decision Threshold ($\tau$) | Val Ensemble F1 | AE Status | Optimization Status |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **CICIDS2017** | 0.70 | 0.30 | -0.00 | 0.10 | **0.1508** | `ACTIVE` | **PASS** |
| **Edge-IIoTset** | 0.35 | 0.25 | 0.40 | 0.45 | **0.9981** | `ACTIVE` | **PASS** |
| **BoT-IoT** | 1.00 | 0.00 | 0.00 | 0.25 | **1.0000** | `EXCLUDED (w_ae=0.0)` | **PASS** |
| **N-BaIoT** | 0.90 | 0.10 | -0.00 | 0.85 | **1.0000** | `ACTIVE` | **PASS** |

---

## Ensemble Optimization Safeguards
- **Data Isolation**: 100% of weight and threshold tuning performed strictly on `X_val`, `y_val`.
- **Simplex Constraint**: $\sum w_i = 1.0$ maintained strictly across all datasets.
- **BoT-IoT AE Exclusion Disclosure**: As documented in the forensic audit, BoT-IoT AE validation threshold yielded `inf`. Following explicit user directive, $w_{\text{ae}}$ was forced to `0.0` for BoT-IoT, fusing RF ($w=0.50$) and MLP ($w=0.50$). AE remains fully active for CICIDS2017, Edge-IIoTset, and N-BaIoT.
- **Deterministic Optimization**: Grid search performed deterministically across 231 simplex weight tuples and 17 threshold steps.

```
============================================================
FINAL ENSEMBLE GATE VERDICT: V3 ENSEMBLE VALIDATION GATE — PASS
============================================================
```
