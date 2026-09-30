# CLAIM EVIDENCE LEDGER

| Section | Claim Text in Manuscript | Implementation Evidence | Experimental Evidence | Status |
| :--- | :--- | :--- | :--- | :--- |
| Abstract / System | Option C combines RF (0.7) + MLP (0.3) | `src/iot_ids/models/ensemble.py` | Option C fusion code explicitly weights 0.7 RF + 0.3 Robust MLP | VERIFIED |
| Feature Rep | Standardized 21-feature statistical profile | `src/iot_ids/features/canonical/flow_builder.py` | Exactly 21 features materialized; raw payloads discarded | VERIFIED |
| Feature Categories | 5 basic flow, 6 protocol flags, 5 temporal, 5 behavioral | `src/iot_ids/features/canonical/schema.py` | Exactly 5 + 6 + 5 + 5 = 21 feature schema | VERIFIED |
| Datasets | Edge-IIoTset, NF-ToN-IoT-v2, ToN-IoT, CICIoT2023 | `data/processed/` | 4 datasets, each 7,000 samples (4,200 train / 1,400 val / 1,400 test) | VERIFIED |
| Split | 60/20/20 chronological split | `src/iot_ids/data/splitters.py` | 60/20/20 chronological split strictly enforced | VERIFIED |
| Detection | Mean ROC-AUC 0.9970 (Option C) | `reports/golden_run_manifest.json` | Edge-IIoTset 0.9988, NF-ToN-IoT-v2 0.9927, ToN-IoT 1.0000, CICIoT2023 0.9965 | VERIFIED |
| Adversarial | NF-ToN-IoT-v2 PGD-10 Option C ASR = 4.0% | `reports/golden_run_manifest.json` | Std MLP 53.8%, Rob MLP 48.0%, Option C 4.0% | VERIFIED |
| Adversarial Scope | PGD-10 attacks generated using neural stream gradients | `FINAL_IEEE_PAPER/main.tex` L178 | PGD-10 gradient attack targets neural stream; evaluated on ensemble | VERIFIED |
| Privacy Scope | DP-SGD applies exclusively to neural stream | `src/iot_ids/privacy/dp_optimizer.py` | DP-SGD applies to MLP weights only, not RF tree construction | VERIFIED |
| Privacy Accounting | (eps=2.37, delta=10^-5) at sigma=1.0 | `reports/golden_run_manifest.json` | Opacus PRV accountant verifies eps=2.37 at sigma=1.0 over 660 steps | VERIFIED |
| XAI Methodology | Weighted Component Attribution Aggregation | `src/iot_ids/xai/` | 0.7 RF TreeSHAP + 0.3 MLP gradient attributions normalized | VERIFIED |
| XAI Attributions | Edge-IIoTset top features: temporal_flow_rate_ewma (0.310), behavioral_port_entropy (0.242), behavioral_unanswered_ratio (0.154) | `reports/xai/xai_evidence_summary.json` | Exact verified values under 0.7 RF + 0.3 MLP attribution aggregation | VERIFIED |
| Runtime Throughput | 16,505 samples/s at batch size N=1024 | `reports/runtime/runtime_overhead_summary.json` | Pure Option C host inference benchmark achieves 16,504.7 samples/s | VERIFIED |
| Hardware Testbed | Socket daemon implemented; hardware testbed is future work | `src/iot_ids/inference/daemon.py` | Socket daemon exists; physical 10Gbps hardware testbed declared in Limitations matrix | VERIFIED |
