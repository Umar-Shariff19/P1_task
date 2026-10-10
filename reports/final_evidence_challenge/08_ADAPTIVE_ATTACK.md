# ADAPTIVE SURROGATE ATTACK VERIFICATION

- **Surrogate Architecture**: `RFSurrogateModule` (128 -> 64 -> 32 -> 1, Sigmoid).
- **Training Data**: Train set split only (`train.parquet`).
- **Targets**: `rf_model.predict_proba(X_tr)[:, 1]`
- **Loss**: MSELoss
- **Optimizer**: Adam
- **Attack Objective**: Backpropagates through `P_surrogate = 0.7 * S_RF(x) + 0.3 * P_RobustMLP(x)`
- **Evaluation**: The generated adversarial examples are evaluated against the true frozen Option C pipeline (`P_actual = 0.7 * P_RF(x) + 0.3 * P_RobustMLP(x)`).

*(Status: SOURCE-VERIFIED)*

### TERMINOLOGY
The attack is NOT a true differentiable gradient through the RF. It is an **adaptive surrogate-based attack**.
