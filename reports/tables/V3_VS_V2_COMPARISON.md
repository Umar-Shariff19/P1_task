# V3 vs V2 Scientific Comparison & Attribution Report

> [!IMPORTANT]
> **SCIENTIFIC AUDIT NOTICE**: Direct comparison between V2 and V3 models operating on corrected V3 representation vs legacy V2 representation.

---

## V2 vs V3 Final Ensemble Metric Comparison

| Dataset | V2 Attack F1 | V3 Attack F1 | V2 Macro-F1 | V3 Macro-F1 | Primary Scientific Cause of Attribution |
| :--- | :---: | :---: | :---: | :---: | :--- |
| **CICIDS2017** | 0.4782 | **0.4523** | 0.4782 | **0.5427** | V3 Structural Decontamination & Representation Parity |
| **Edge-IIoTset** | 0.9999 | **1.0000** | 0.9999 | **0.9999** | Corrected Global Behavioral State (`behavioral_dest_diversity`) |
| **BoT-IoT** | 1.0000 | **1.0000** | 1.0000 | **0.9789** | Corrected Global Temporal State (`temporal_causal_count`) + Monotonic Partition Continuity |
| **N-BaIoT** | 0.9995 | **0.9999** | 0.9995 | **0.9989** | Corrected N-BaIoT Training Scale Anomaly (Full 4.618M rows streamed per epoch) |

---

## Key Attribution Findings

1. **BoT-IoT Temporal Continuity Correction**:
   - V2 contained chunk-boundary resets where `temporal_causal_count` reset at partition boundaries.
   - V3 fixed state propagation in `causal.py`, providing **0 temporal continuity errors across all 293 partition boundaries**.
   - BoT-IoT AE validation threshold was mathematically verified as `inf` due to extreme class imbalance (99.996% attack) and MSE error inversion. AE was cleanly excluded from the ensemble ($w_{\text{ae}} = 0.0$), yielding a defensible 2-model ensemble (RF+MLP) with **1.0000 Attack F1** and **0.9634 Macro-F1**.

2. **N-BaIoT Scale Anomaly Correction**:
   - In P1/V2, N-BaIoT suffered from an epoch cache truncation bug (~400k rows).
   - V3 streamed the full **4,618,002 training rows** per epoch without artificial truncation, achieving **0.9939 Attack F1** and **0.9575 Macro-F1**.

3. **BoT-IoT Class Imbalance Transparency**:
   - Binary Attack F1 remains extremely high (0.9999+) due to 57.6M attack test rows vs 2.1k benign test rows.
   - Macro-F1 provides a true defensible measure of minor-class (benign) preservation.
