# Final P1 Evidence Gate

## Verification Checklist
1. **Methodology verified**: `VERIFIED`
2. **Feature representation verified**: `VERIFIED`
3. **Leakage controls verified**: `VERIFIED`
4. **Split strategy verified**: `VERIFIED`
5. **Model artifacts verified**: `VERIFIED`
6. **Classification metrics verified**: `VERIFIED`
7. **Confusion matrices verified**: `VERIFIED`
8. **ROC/PR evidence verified**: `VERIFIED`
9. **Ensemble benefit verified**: `PARTIALLY VERIFIED` (Robustness over absolute accuracy)
10. **CICIDS limitation verified**: `VERIFIED` (Unseen zero-day evaluation)
11. **BoT-IoT limitation verified**: `VERIFIED` (Extreme volumetric imbalance)

## Claims Status
### 12. P1 paper claims that are safe
- 'Strict dataset decontamination'
- 'Multi-level feature representation capability'
- 'True unseen zero-day generalization penalty in CICIDS2017'

### 13. P1 claims requiring cautious wording
- 'Ensemble achieves superior performance' (Requires caveat: limits false positives but may suppress strong standalone detectors).
- 'Perfect generalization on BoT-IoT' (Requires caveat: tests volumetric distinction of a highly imbalanced dataset).

### 14. Claims that must NOT be made
- 'The ensemble always beats standalone models.'
- 'No metadata leakage means F1 = 1.0 implies perfect adversarial robustness.'
