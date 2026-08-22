# FRESH TRAINING CONFIGURATION MANIFEST

> **Source Scripts**: `scripts/05_train_models.py` & `scripts/06_calibrate_risk.py`  
> **Target Execution Directory**: `reproducibility/fresh_retraining_20260821_010000/`

---

## 1. DATASETS & SPLIT ISOLATION

- **Edge-IIoTset**: 94,680 Train rows (60%) / 31,560 Validation rows (20%) / 31,560 Test rows (20%).
- **ToN-IoT Network**: 126,625 Train rows (60%) / 42,209 Validation rows (20%) / 42,209 Test rows (20%).
- **Split Strategy**: Stratified temporal splitting. Zero target test samples used during training.

---

## 2. FEATURE SCHEMAS & PREPROCESSING PIPELINE

- **Harmonized Cross-Domain Space ($F_{\text{common}}$ - 6 Features)**:
  `['duration', 'src_bytes', 'proto_tcp', 'proto_udp', 'proto_icmp', 'is_well_known_port']`
- **Edge-IIoTset In-Domain (13 Active Numeric Features)**:
  `['duration', 'src_bytes', 'proto_tcp', 'proto_udp', 'proto_icmp', 'is_well_known_port', 'temporal_causal_count', 'temporal_causal_rate', 'temporal_iat_mean', 'behavioral_dest_diversity', 'behavioral_src_activity', 'mqtt_msgtype', 'mbtcp_unit_id']`
- **ToN-IoT Network In-Domain (13 Active Numeric Features)**:
  `['duration', 'src_bytes', 'proto_tcp', 'proto_udp', 'proto_icmp', 'is_well_known_port', 'temporal_causal_count', 'temporal_causal_rate', 'temporal_iat_mean', 'behavioral_dest_diversity', 'behavioral_src_activity', 'conn_state_encoded', 'http_method_encoded']`
- **Preprocessing Pipeline**: `PreprocessingPipeline` (`RobustScaler` quantile scaling + `np.log1p` transfer on positive skewed features).

---

## 3. MODEL ARCHITECTURES & HYPERPARAMETERS

1. **Random Forest Classifier**:
   - `RandomForestClassifier(n_estimators=100, max_depth=15, random_state=42, n_jobs=-1)`
   - Trained on 60% Train split ($X_{\text{train}}$, $y_{\text{train}}$).
2. **PyTorch MLP Classifier**:
   - Architecture: $D_{\text{in}} \rightarrow 128 \rightarrow 64 \rightarrow 32 \rightarrow 1$ with BatchNorm1d, ReLU, and Dropout(0.2).
   - Loss Function: `BCEWithLogitsLoss()`.
   - Optimizer: `Adam(lr=0.001)`.
   - Epochs: 15, Batch Size: 256.
   - Trained on 60% Train split ($X_{\text{train}}$, $y_{\text{train}}$).
3. **PyTorch Benign-Trained Autoencoder (AE)**:
   - Encoder: $D_{\text{in}} \rightarrow 64 \rightarrow 16$ (ReLU).
   - Decoder: $16 \rightarrow 64 \rightarrow D_{\text{in}}$.
   - Loss Function: `MSELoss()`.
   - Optimizer: `Adam(lr=0.001)`.
   - Epochs: 15, Batch Size: 256.
   - Trained **STRICTLY on Benign Train samples** ($y_{\text{train}} == 0$).

---

## 4. DESIGN B RISK LAYER & ANOMALY CALIBRATION

- **Supervised Ensemble**: $P_{\text{sup}} = 0.5 P_{\text{rf}} + 0.5 P_{\text{mlp}}$.
- **Empirical AE Calibration**: Reconstruction MSE computed over **Benign Validation split** ($y_{\text{val}} == 0$). Anomaly score $S_{\text{ae}}$ mapped via empirical CDF percentile ranking lookup.
- **Decision Thresholds**: Supervised threshold $\tau_{\text{sup}} = 0.50$, AE Anomaly threshold $\tau_{\text{ae}} = 0.80$.
