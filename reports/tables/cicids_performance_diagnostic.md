# CICIDS2017 Performance Diagnostic

## Exact Measurements
- **Train Class Count**: 1,690,589 BENIGN | 266,543 ATTACK
- **Validation Class Count**: 307,300 BENIGN | 4,146 ATTACK
- **Test Class Count**: 193,596 BENIGN | 286,957 ATTACK
- **Test Attack-Family Counts**: DDoS: 128,027 | PortScan: 158,930
- **Attack Families in Training**: Infiltration, FTP-Patator, SSH-Patator, DoS slowloris, DoS Slowhttptest, DoS Hulk, DoS GoldenEye, Heartbleed
- **Attack Families Absent from Training**: DDoS, PortScan
- **TP**: 94707 | **TN**: 179190 | **FP**: 14406 | **FN**: 192250
- **BENIGN F1**: 0.6343 | **ATTACK F1**: 0.4782
- **Macro F1**: 0.5562 | **Weighted F1**: 0.5411
- **ROC-AUC**: 0.792957500682534 | **PR-AUC**: 0.8573943423957708

## Diagnostic Verification
The day-aware split isolated the Friday PCAPs (DDoS and PortScan) purely into the test set. Therefore, 100% of the evaluated attacks were 'unseen attack families'. The performance drop exactly measures zero-day generalization failure on totally novel signatures, rather than a pipeline bug.