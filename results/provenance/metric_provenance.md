# Historical metric provenance

| Model/result | Historical mean ROC-AUC | Existing support | Status |
|---|---:|---|---|
| Random Forest | 0.997568 | Golden manifest aggregate 0.9975684375; repeated in authoritative numerical ledger. | `HISTORICAL_REPORTED` |
| Option C | 0.996982 | Golden manifest aggregate 0.9969815625; repeated in authoritative numerical ledger. | `HISTORICAL_REPORTED` |
| Standard MLP | 0.859050 | Golden manifest aggregate 0.8590496875; repeated in authoritative numerical ledger. | `HISTORICAL_REPORTED` |
| Robust MLP | 0.856209 | Golden manifest aggregate 0.85620875; repeated in authoritative numerical ledger. | `HISTORICAL_REPORTED` |

These values are supported as previously reported numbers, not as newly reproduced measurements. The manifest supplies per-dataset values, seed 42, dataset names, and feature count 21. It does not link the run to source commit, split hashes, individual checkpoint hashes, or a specific environment. Model files under `models/golden_run/` include RF/scaler/standard and robust MLP artifacts but no complete run metadata. The final deployable artifact is a distinct artifact family and cannot substitute as provenance for golden metrics. No evaluation was rerun.

See [`historical_provenance_matrix.md`](historical_provenance_matrix.md) for a field-by-field separation of direct manifest statements, filename/code inferences, and missing metric-to-artifact links.
