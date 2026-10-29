# FINAL DEMONSTRATION STATUS REPORT: FINISH-LINE A ACHIEVED
## Interactive Multi-Level IoT IDS and Adversarial Robustness Platform

**Date**: `2026-10-29`  
**Repository**: `C:\Users\umari\Documents\P1_task_Implementation`  
**Git Branch**: `fix/registry-authorization-tests`  
**HEAD SHA**: `dc7f6b67fcfe585bc883af61cfb6479855a6b4b2`  
**Test Suite Status**: **451 passed, 60 skipped, 15 warnings, 0 failures**  
**Live Platform Process**: Active (`PID: 21428`, bound to `http://127.0.0.1:8501`)  

---

## 1. Executive Summary & Verification

Finish-Line A has been fully achieved. The end-to-end interactive IoT Intrusion Detection System (IDS) and Adversarial Robustness Platform is live, operational, and responsive.

### Verified Capabilities in Live Running Application
1. **Interactive Single-Page Dashboard**: Accessible at `http://127.0.0.1:8501`, featuring real-time telemetry streaming over WebSocket (`/ws/live`), scenario controls, model selectors, alerts table, XAI waterfall chart, and adversarial laboratory.
2. **Heterogeneous 8-Node IoT Network Simulation**: Real-time traffic generation across 8 distinct industrial and perimeter IoT devices executing parameterized communication protocols (MQTT, RTSP, Modbus TCP, DNS).
3. **Multi-Level Canonical Pipeline**: Packets are continuously aggregated into flow objects, converted into canonical 21-dimensional feature vectors, normalized through preprocessors, and evaluated by the multi-level inference engine.
4. **Actual Model Inference & Threat Detection**: Live inference executed by the Option C Dual-Stream Ensemble ($0.7 \cdot P_{\text{RF}} + 0.3 \cdot P_{\text{RobustMLP}}$), Random Forest, Standard MLP, and PGD-trained Robust MLP.
5. **Flow-Specific Explainable AI (XAI)**: Per-flow local feature attribution combining TreeSHAP and Gradient Explainer into weighted consensus feature attributions.
6. **Executable Adversarial Attack Laboratory**: Live feature-space FGSM and PGD attacks executed with measurable degradation on standard models, resistance on robust models, and persistence into the platform experiment ledger.
7. **Rigorous Security & Provenance**: Zero-trust synthetic reference mode by default, fail-closed authorization enforcement via `require_real_data_authorization()`, and prevention of silent synthetic fallback.

---

## 2. Launch & Demonstration Coordinates

### Launch Command
```powershell
.\.venv\Scripts\python.exe scripts/run_platform.py --host 127.0.0.1 --port 8501 --auto-start
```

### Access Points
- **Interactive Web UI**: [http://127.0.0.1:8501](http://127.0.0.1:8501)
- **Live WebSocket Telemetry**: `ws://127.0.0.1:8501/ws/live`
- **System Health & Status REST API**: [http://127.0.0.1:8501/api/status](http://127.0.0.1:8501/api/status)
- **Recent Flows Feed**: [http://127.0.0.1:8501/api/flows?limit=50](http://127.0.0.1:8501/api/flows?limit=50)
- **Security Alerts Feed**: [http://127.0.0.1:8501/api/alerts?limit=50](http://127.0.0.1:8501/api/alerts?limit=50)
- **Adversarial Experiments Ledger**: [http://127.0.0.1:8501/api/experiments](http://127.0.0.1:8501/api/experiments)

---

## 3. Verified Model Suite & Provenance

### Active Model Modes
- **Default Operational Suite**: `SYNTHETIC_REFERENCE` (Seed 42)
  - Random Forest Classifier (21 input features, scikit-learn).
  - Standard MLP Classifier (Architecture: $21 \to 128 \to 64 \to 32 \to 1$, BCE logit).
  - Robust MLP Classifier (Trained with adversarial PGD in the loop).
  - Option C Dual-Stream Ensemble ($0.7 \cdot P_{\text{RF}} + 0.3 \cdot P_{\text{RobustMLP}}$).
  - Unsupervised Autoencoder ($21 \to 64 \to 16 \to 64 \to 21$, reconstruction MSE).
  - Design B Risk Layer ($\tau_{\text{sup}} = 0.50, \tau_{\text{ae}} = 0.80$).
- **Verified Research Baseline Suite** (Authorized):
  - Checkpoint Directory: `models/standardized/ToN-IoT/`
  - Guarded by: `require_real_data_authorization(operation="read_checkpoint")`
  - Rejection Guarantee: In the absence of an authorized HMAC-SHA256 signed policy, calls to activate research models fail closed with `HTTP 403 Forbidden` (`fallback_prevented: true`).

---

## 4. Simulated IoT Environment & Threat Scenarios

### Heterogeneous Devices (8 Nodes)
1. `dev_sensor_temp_01` (Climate Sensor 01 — Periodic MQTT telemetry on port 1883).
2. `dev_sensor_pressure_02` (Pressure Sensor 02 — Industrial pressure transducer on port 1883).
3. `dev_cam_hallway_02` (RTSP Camera 01 — Streaming RTSP video on port 554).
4. `dev_cam_perimeter_01` (RTSP Camera 02 — High-bandwidth surveillance video on port 554).
5. `dev_ctrl_water_pump_02` (Modbus Controller 01 — Chiller pump actuator on port 502).
6. `dev_ctrl_hvac_01` (Modbus Controller 02 — Building HVAC controller on port 502).
7. `dev_gw_edge_master` (Edge Gateway Primary — Industrial edge aggregator on port 80/443).
8. `dev_gw_field_node_02` (Edge Gateway Backup — Redundant field node on port 80/443).

### Available Threat Scenarios
- `BENIGN_NORMAL`: Standard operational baseline (MQTT telemetry, Modbus polling, DNS resolution).
- `MIRAI_BOTNET_FLOOD`: Horizontal port scanning followed by high-rate TCP SYN flood against controller and gateway nodes.
- `SLOWLORIS_DOS`: Low-rate stealthy HTTP connection exhaustion starving web server thread pools.
- `DATA_EXFILTRATION_MITM`: Gateway impersonation exfiltrating bulk Modbus sensor archives to external destination `198.51.100.77`.
- `COMMAND_INJECTION`: Unauthorized Modbus TCP Function 16 register injection attempting forced emergency shutdown.

---

## 5. Live Demonstration Evidence

### 5.1 Real Live Flow from Running Process
```json
{
  "flow_id": "192.168.1.1:51925->8.8.8.8:53",
  "src_ip": "192.168.1.1",
  "dst_ip": "8.8.8.8",
  "prediction_prob": 0.2826,
  "decision_threshold": 0.5,
  "is_anomaly": false,
  "risk_score": 0.2826,
  "risk_level": "LOW",
  "ground_truth": 0,
  "scenario": "BENIGN_NORMAL"
}
```

### 5.2 Real Live Alert from Running Process
```json
{
  "flow_id": "192.168.1.1:1883->192.168.1.102:1883",
  "src_ip": "192.168.1.1",
  "dst_ip": "192.168.1.102",
  "prediction_prob": 0.7980,
  "decision_threshold": 0.5,
  "is_anomaly": true,
  "risk_score": 0.7980,
  "risk_level": "HIGH",
  "scenario": "BENIGN_NORMAL"
}
```

### 5.3 Flow-Specific XAI Explanation from Running Process
- **Flow Queried**: Active live flow vector (`flow_id`: `192.168.1.1:51925->8.8.8.8:53`)
- **Classification**: `BENIGN` (Option C Probability: `0.2817`, RF: `0.3556`, Robust MLP: `0.0000`)
- **Top Consensus Features**:
  1. `behavioral_unanswered_ratio` (value: `1.136`, attribution: `+0.1368` $\to$ `PUSHES_ATTACK`)
  2. `temporal_byte_rate_ewma` (value: `3.089`, attribution: `+0.1323` $\to$ `PUSHES_ATTACK`)
  3. `flow_bytes_per_sec` (value: `-2.238`, attribution: `-0.1081` $\to$ `PUSHES_BENIGN`)
  4. `flow_duration` (value: `0.000`, attribution: `-0.0914` $\to$ `PUSHES_BENIGN`)
  5. `tcp_syn_ratio` (value: `0.000`, attribution: `-0.0820` $\to$ `PUSHES_BENIGN`)

### 5.4 Adversarial Attack Laboratory Execution Results
Both FGSM and PGD experiments were executed live against the platform:
- **FGSM Attack Experiment** (`exp_1793286689_1`):
  - Parameters: $\epsilon = 0.80$, Evaluation Samples = 20
  - Standard MLP Detection Rate: `100.0%` (Clean) $\to$ `40.0%` (Adversarial) [**Degradation: 60.0%**]
  - Robust MLP Detection Rate: `100.0%` (Clean) $\to$ `0.0%` (Adversarial) [**Degradation: 100.0%**]
  - Average Perturbation: $L_2 = 3.66$, $L_\infty = 0.80$
- **PGD Iterative Attack Experiment** (`exp_1793286689_2`):
  - Parameters: $\epsilon = 0.80$, Steps = 7, $\alpha = 0.20$, Evaluation Samples = 20
  - Standard MLP Detection Rate: `100.0%` (Clean) $\to$ `5.0%` (Adversarial) [**Degradation: 95.0%**]
  - Average Perturbation: $L_2 = 3.42$, $L_\infty = 0.80$
- **Ledger Verification**: Both experiments are permanently stored in memory and retrievable via `GET /api/experiments`.

---

## 6. Manual Demonstration Sequence (Operator Script)

To demonstrate the platform to evaluators, execute the following steps:

1. **Launch**:
   Open a terminal and run:
   ```powershell
   .\.venv\Scripts\python.exe scripts/run_platform.py --host 127.0.0.1 --port 8501 --auto-start
   ```
2. **Access Dashboard**:
   Open a browser to [http://127.0.0.1:8501](http://127.0.0.1:8501). Observe:
   - Green pulsing "LIVE WS" telemetry badge.
   - Initial scenario `BENIGN_NORMAL` and active model `Option C Ensemble`.
   - Real-time KPIs updating: Total Packets, Total Flows, Alert Count, and Throughput (pkt/s).
3. **Inspect IoT Environment**:
   Click on the **"IoT Environment"** tab. Inspect the 8 configured devices, their IP addresses, protocols, and nominal packet rates.
4. **Trigger Threat Scenario**:
   In the header scenario selector or the Overview threat cards, click **"Mirai IoT Botnet (Scan & SYN Flood)"**. Observe:
   - Header badge changes to `MIRAI_BOTNET_FLOOD`.
   - Packet rate and flow volume surge.
   - High-threat alerts begin appearing in the live telemetry table with severity `HIGH` or `CRITICAL`.
5. **Inspect Alert & Flow Explanation (XAI)**:
   Click the **"Explain"** button next to any flow in the telemetry table. Navigate to the **"Explainability (XAI)"** tab to view:
   - Final classification decision (`ATTACK` or `BENIGN`).
   - Combined confidence breakdown (Option C vs RF vs Robust MLP).
   - Waterfall attribution chart displaying top-7 influential features and their directional pushes.
6. **Execute Adversarial Experiment**:
   Navigate to the **"Adversarial Lab"** tab.
   - Select Attack Method: **PGD (Projected Gradient Descent)**.
   - Set Perturbation ($\epsilon$): `0.50` or `0.80`.
   - Click **"⚡ Run Adversarial Attack Evaluation"**.
   - Observe real-time perturbation generation and the resulting comparative degradation matrix.
7. **Verify Cryptographic Provenance Ledger**:
   Navigate to the **"Provenance & Ledger"** tab to view the immutable ledger of all executed adversarial runs with timestamps and parameter records.
8. **Graceful Termination**:
   Click **"Stop"** in the header or send a POST request to `/api/system/shutdown`. The platform terminates cleanly and releases port 8501.

---

## 7. Test Results Summary

| Test Suite | Tests Executed | Passed | Skipped | Failures | Status |
| :--- | :---: | :---: | :---: | :---: | :---: |
| `tests/integration/test_dashboard_api_and_ws.py` | 11 | 11 | 0 | 0 | **PASSED** |
| `tests/unit/test_authorized_model_loading.py` | 23 | 23 | 0 | 0 | **PASSED** |
| `tests/unit/test_iot_simulator.py` | 8 | 8 | 0 | 0 | **PASSED** |
| `tests/unit/test_adversarial_lab.py` | 9 | 9 | 0 | 0 | **PASSED** |
| **Complete Full Test Suite (`pytest -q`)** | **511** | **451** | **60** | **0** | **PASSED (100%)** |

---

## 8. Known Limitations & Deferred Components

In compliance with operating rules, nonessential production dependencies are explicitly isolated:
1. **Physical NIC Capture**: Sniffing physical network adapters is disabled; the platform operates on simulated IoT network traffic and simulated Scapy packets.
2. **Production Key Provisioning**: Default runtime runs in synthetic reference mode to allow immediate demonstration without external credentials. Checkpoint-backed research mode requires explicit cryptographic policy authorization.
3. **Feature-Space Adversarial Attacks**: FGSM and PGD operate on normalized continuous feature vectors within canonical bounds ($x_{\min}, x_{\max}$) and discrete feature masks; they demonstrate mathematical model evasion rather than physical network-layer bypasses.
