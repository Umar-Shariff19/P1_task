# Multi-Level Feature Recovery Plan

## 1. Why Recovery is Necessary
The current implementation enforces a strict 4-feature intersection (the `FLOW_COMPATIBLE_C_E_B` profile) across all datasets (except N-BaIoT) to ensure cross-domain comparability. While this is valid for transfer evaluation, restricting the models to just these 4 features during in-domain training sacrifices the primary architectural innovation of the project: the Multi-Level Feature Representation.

## 2. What the Methodology Requires
The authoritative methodology (as defined in `RefinedMethodology_and_ExpectedOutcomes.docx` and `objectives.docx`) explicitly requires a Multi-Level Feature Representation comprising:
1. **Instant Features:** Current network state (e.g., packet size, duration, counts)
2. **Temporal Features:** Traffic evolution (e.g., flow inter-arrival times, trends)
3. **Behavioral Features:** Long-term communication behavior (e.g., traffic asymmetry, packet direction ratios)

This representation is the core novelty of Paper 1 and forms the foundation for the hybrid ensemble (Random Forest, MLP, Autoencoder).

## 3. What the Current Implementation Does
**CURRENT:** 
26 canonical features → strict 4-feature profile (`FLOW_COMPATIBLE_C_E_B`) → all models (C/E/B datasets).

The pipeline extracts up to 26 canonical features during dataset materialization but discards 80-90% of them during training, including all temporal and behavioral features.

## 4. Exact Architectural Discrepancy
The methodology claims a multi-level feature representation, but the experimental design strictly limits models to a single-level (instant) 4-feature subset. An IEEE reviewer would correctly note that the methodology's novelty claim is completely unsupported by the implementation.

## 5. What Remains Unchanged
- The canonical materialization engine and generated parquets (datasets).
- Train/validation/test split manifests and decontamination.
- `FittedPreprocessor` pipeline logic (imputation and scaling).
- N-BaIoT handling (already uses its full 115-feature source aggregate profile).
- Existing evaluation methodology (transparent weighted fusion).

## 6. What Will Change
**TARGET:**
26 canonical multi-level representation → dataset-specific richest valid in-domain profile → RF / MLP / AE / ensemble (for in-domain reporting).

**AND:**
26 canonical representation → `FLOW_COMPATIBLE_C_E_B` → cross-domain experiments (for transfer generalization).

The feature resolver will support dual-track profiles. Models will be evaluated in-domain using the rich, dataset-specific profiles, and cross-domain using the universal 4-feature profile.

## 7. Profile Architecture
- **`IN_DOMAIN_CICIDS2017`**: Uses all 18 valid numeric canonical features for CICIDS2017, maintaining all three levels.
- **`IN_DOMAIN_EDGE_IIOT`**: Uses all 7 valid numeric canonical features for Edge-IIoTset.
- **`IN_DOMAIN_BOT_IOT`**: Uses all 18 valid numeric canonical features for BoT-IoT.
- **`NBAIOT_SOURCE_AGGREGATE`**: Uses 115 features for N-BaIoT (unchanged).
- **`FLOW_COMPATIBLE_C_E_B`**: Uses the strict 4-feature intersection (unchanged, strictly for cross-domain experiments).

## 8. Training/Evaluation Experiment Matrix
- **In-Domain Training**: Train RF, MLP, and AE on each dataset using its respective `IN_DOMAIN_*` profile.
- **In-Domain Evaluation**: Evaluate the ensemble on the validation/test splits using the `IN_DOMAIN_*` models.
- **Cross-Domain Validation**: Existing `FLOW_COMPATIBLE_C_E_B` results serve as the baseline for cross-domain transfer learning experiments.

## 9. Validation Gates
- Ensure zero missing features requested by the new profiles during materialization.
- Verify exact semantic levels (instant/temporal/behavioral) in profile metadata.
- Preprocessor must handle imputation identically.
- Ensure the feature resolver strictly rejects invalid profiles and avoids accidental 4-feature fallback.
- Reproducibility test and smoke test must pass before any full-scale retraining.

## 10. Rollback Strategy
The recovery utilizes separate artifact naming conventions (e.g., `_indomain` suffix). If the in-domain training fails, the original model artifacts, registry checkpoints, and cross-domain results are untouched. The rollback is to revert `canonical_schema.json`, `pipeline.py`, and remove the newly generated artifacts.

## 11. P4 Integration Implications
The dual-track approach cleanly separates tasks. The P4 BCL (Behavioral Consistency Layer) can consume the strongest in-domain models for adversarial analysis, which have been trained on the full multi-level representation. P4's detection of feature manipulation will be richer because the models observe temporal and behavioral features.

## 12. Explicit Non-Goals
- Inventing new features that aren't already defined in the 26-feature canonical schema.
- Rematerializing datasets (the required features are already in the parquets).
- Rewriting working RF/MLP/AE architectures.
- Changing the experimental focus to anything other than the IEEE baseline.
