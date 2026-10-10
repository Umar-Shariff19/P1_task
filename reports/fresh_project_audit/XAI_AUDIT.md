# XAI AUDIT

The project uses TreeSHAP for RF and Gradient-based attribution for the MLP.
The fusion attributes combine them linearly (`0.7 * RF_SHAP_norm + 0.3 * MLP_SHAP_norm`).
This is a **custom weighted attribution**, NOT "exact SHAP". Claiming exact SHAP for the non-linear fused ensemble is incorrect.
