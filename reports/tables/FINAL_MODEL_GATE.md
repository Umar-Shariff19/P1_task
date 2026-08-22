# FINAL MODEL FORENSIC GATE REPORT

> [!IMPORTANT]
> **VERDICT: MODEL FORENSIC GATE — PASS**
>
> Component models (RF, MLP, Autoencoder) and Design B Risk & Decision Layer successfully trained and calibrated on validation splits for **Edge-IIoTset** and **ToN-IoT Network**.

---

## Component Model & Risk Layer Calibration Summary

| Dataset | Validation Rows | Supervised Val Accuracy | AE Calibration Samples | Tau Supervised | Tau Anomaly | Model Status |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **Edge-IIoTset** | 31,560 | 89.50% | 4,861 | 0.5 | 0.8 | **PASS** |
| **ToN-IoT Network** | 42,209 | 96.41% | 10,000 | 0.5 | 0.8 | **PASS** |

---

## Forensic Integrity Guarantees
- **Benign-Only AE Calibration**: Autoencoder empirical CDF fitted strictly on validation benign samples ($Y=0$).
- **No Test Data Leakage**: Thresholds and calibration parameters frozen without touching Test splits.
- **Verdict**: **MODEL FORENSIC GATE PASSED**.
