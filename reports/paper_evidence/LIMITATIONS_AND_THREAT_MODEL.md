# Formal Research Limitations and Threat Model Statement

## 1. Threat Model Scoping & Definitions

### A. Neural-Stream PGD Evasion Attack
- **Attacker Knowledge:** Complete white-box access to neural stream weights ($	ext{MLP}_{	ext{rob}}$) and standard scaler parameters.
- **Gradient Backpropagation:** Gradients $
abla_x \mathcal{L}_{	ext{MLP}}$ computed exclusively through the differentiable neural stream.
- **Ensemble Evaluation:** Perturbed samples passed to discrete Random Forest and Option C ensemble.

### B. Adaptive Surrogate-Gradient Attack
- **Attacker Knowledge:** Access to feature representation, training telemetry, and query access to frozen RF predictions $\mathcal{P}_{	ext{RF}}(X_{	ext{train}})$.
- **Surrogate Fitting:** Neural surrogate $\mathcal{S}_{	ext{RF}}$ trained on training split ONLY ($N=4,200$).
- **Gradient Backpropagation:** Gradients computed through joint target $\mathcal{P}_{	ext{surrogate}} = 0.7 \cdot \mathcal{S}_{	ext{RF}} + 0.3 \cdot 	ext{MLP}_{	ext{rob}}$.
- **Ensemble Evaluation:** Perturbed samples evaluated against **ACTUAL** frozen Option C ($	ext{RF} + 	ext{MLP}_{	ext{rob}}$).

---

## 2. Non-Negotiable Scientific Scope Boundaries

1. **Non-Differentiable Tree Boundary:** Discrete decision trees prevent exact white-box gradient backpropagation. Surrogate fidelity varies across datasets ($R^2 = -0.59$ on Edge-IIoTset to $+0.95$ on NF-ToN-IoT-v2).
2. **Neural-Stream Privacy Bound:** Differential privacy ($arepsilon=2.37, \delta=10^{-5}$) applies strictly to the neural stream. The Random Forest stream is non-private.
3. **In-Distribution Evaluation:** Benchmarks evaluate standardized 60/20/20 chronological test splits ($N=1,400$). Strict unseen-domain generalization is not claimed.
4. **Classifier-Only Host Runtime:** Latency benchmarks (16,505 samples/sec at batch 1024 on CPU) measure classifier execution, excluding packet capture, flow reconstruction, feature extraction, and XAI.
5. **Component-Level Attribution:** XAI attributions represent linear weighted component aggregations ($0.7 	ext{RF}_{	ext{norm}} + 0.3 	ext{MLP}_{	ext{norm}}$), not exact game-theoretic SHAP for the non-linear fused predictor.
6. **Small Category Sample Counts:** CICIoT2023 sub-categories ($N \le 11$) are descriptive sample observations, not statistically generalizable findings.
