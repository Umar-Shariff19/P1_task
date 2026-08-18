# BoT-IoT Performance Diagnostic

## Exact Measurements
- **Test BENIGN Count**: 29.0
- **Test ATTACK Count**: 1001045.0
- **Attack Prevalence**: 99.997103%
- **BENIGN Precision**: 0.8286
- **BENIGN Recall**: 1.0000
- **BENIGN F1**: 0.9062
- **ATTACK Precision**: 1.0000
- **ATTACK Recall**: 1.0000
- **ATTACK F1**: 1.0000
- **Macro F1**: 0.9531
- **Weighted F1**: 1.0000
- **TP**: 1001039
- **TN**: 29
- **FP**: 0
- **FN**: 6

## Diagnostic Answers
1. **Does the model detect the tiny benign class correctly?** Yes, it perfectly identifies them.
2. **How many benign samples are misclassified?** 0.
3. **Is the perfect F1 driven primarily by attack dominance?** Yes, the 99.997% attack prevalence severely inflates weighted F1 and accuracy.
4. **Are the volumetric features responsible for easy separation?** Yes. Feature importances confirm volumetric counts (`bwd_packets`, `duration_seconds`) and state (`connection_state`) drive the separation rather than deep payload inspection.
5. **Is there evidence of explicit metadata leakage?** No. Duplicate/Leakage controls dropped IP/MACs.
6. **Is the result better described as 'excellent performance on this dataset' rather than 'strong generalization'?** It is strictly 'excellent performance on this dataset' because extreme homogeneity prevents true generalization testing.