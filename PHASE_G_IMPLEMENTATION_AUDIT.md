# Phase G Implementation and Evidence Review

Date: 2026-10-27

## Baseline

- Authoritative repository: `C:\Users\umari\Documents\P1_task_Implementation`.
- Branch/HEAD: `master`, `5117df8bbd969544786a750ef6993b958f1655a0` (`5117df8`, “Remove paper artifacts and retain project context”). The branch was one commit ahead of `origin/master` at inspection.
- Initial working tree: `src/iot_ids/cli.py` modified; `tests/integration/test_cli_missing_scapy.py` and `tests/integration/test_cli_validate_config.py` untracked. These are pre-existing user changes and were preserved.
- Candidate path exists and source files were readable. Git metadata commands against the candidate were denied by the filesystem boundary, so its branch, HEAD, and status could not be verified.
- Main code is under `src/iot_ids/`; focused tests under `tests/unit/` and `tests/integration/`; experiment outputs and claim ledgers under `reports/`; data and model artifacts under `data/` and `models/`.
- The prior inventory missed manuscript sources inside root ZIP archives. Phase H located `main.tex` in both `FINAL_IEEE_PAPER.zip` and `FINAL_IEEE_PAPER_Overleaf.zip`, plus a fuller TeX manuscript and publication DOCX in the candidate checkout. Their canonical submission status is unknown; see the Phase H audit.

## Candidate changes assessed

| Candidate addition/change | Decision | Reason |
|---|---|---|
| `src/iot_ids/experiments/provenance.py` and candidate split manifests | Defer | The helper explicitly accepts BoT-IoT and expects `seeded_stratified_random` for several datasets. This conflicts with the final four-dataset scope and cannot justify changing the original split design. No dataset-backed test was run. |
| `src/iot_ids/models/ensemble/bcl.py`, `src/iot_ids/runtime/bcl_engine.py`, `scripts/15_evaluate_bcl.py`, and BCL tests | Defer; do not execute | Candidate evaluator accepts BoT-IoT and opens validation and test splits; it writes calibration and evaluation artifacts. Its own output caveat says the two-sided scoring rule followed inspection of an earlier ToN-IoT test result. This is unsuitable as confirmatory evaluation and risks prohibited/protected data access. |
| Candidate `src/iot_ids/privacy/dp_sgd.py` / privacy changes | Reject as a finished DP implementation | Candidate code still requires full accountant and sampling review. The original already contains DP code; porting candidate files would not resolve that. No privacy experiments were run. |
| `src/iot_ids/data/sampling.py` | Keep experimental | Sampling changes can change dataset composition and results; insufficient validation and would change research design. |
| `src/iot_ids/adversarial/black_box.py` | Keep experimental | New attack behavior requires separate evaluation and paper provenance; not adopted or run. |
| Candidate CLI/runtime/tests | Selectively adopt only established safe behavior | Original already has Scapy import guards in the pre-existing user diff. No candidate change demonstrated a better compatible runtime behavior than the original current implementation. |

## Improvements implemented

- Added early validation to `FlowAggregator` constructor limits in `src/iot_ids/data/flow_aggregator.py`: both time limits must be finite and positive; `max_active_flows` must be a positive integer. This prevents nonsensical configurations and the empty-eviction failure when capacity is zero. Valid timeout/eviction behavior is unchanged.
- Added synthetic unit cases in `tests/unit/data/test_flow_aggregator.py` for zero, negative, NaN, infinite, fractional, boolean, and valid constructor settings.
- No scientific methodology, feature definitions, models, weights, attacks, thresholds, BCL, DP training, or official artifacts were modified.

## Research claims and evidence status

| Claim | Evidence inspected | Status |
|---|---|---|
| Four official datasets | `scripts/run_golden_pipeline.py` names Edge-IIoTset, NF-ToN-IoT-v2, ToN-IoT, CICIoT2023; golden manifest records the same four | Supported as recorded scope. |
| Chronological 60/20/20 split for the official golden metrics | The golden Stage 3 materializer (`scripts/03_materialize_and_audit_features.py`) partitions each class by adapter stream order, sorts rows inside each split by timestamp, and resets feature state at boundaries. ToN-IoT and NF-ToN-IoT-v2 adapters synthesize timestamps from row order. `scripts/03_create_splits.py` is a separate stratified generator for the older `data/processed/final` path, not the golden Stage 3 path. | A class-wise source-order procedure is present, but the checked-in split files lack a manifest linking them to a particular run. Global event-time chronology and exact historical split provenance are unverified. |
| Feature dimensions/order | `src/iot_ids/runtime/schema.py` defines 21 names; golden pipeline explicitly uses 21 ordered names and checks data columns before preprocessing | Supported by current inference/training source; historical feature metadata names should be reconciled before publication. |
| RF configuration | `scripts/run_golden_pipeline.py` uses 100 estimators, max depth 15, seed 42 | Supported as script configuration, not independent evidence of which settings produced every saved artifact. |
| Robust MLP / PGD training | Golden pipeline calls robust training with 7 steps and epsilon 0.10; attack evaluation code uses PGD-10 with alpha 0.025 in the evaluation section | Supported as source configuration. Results remain historical manifest values, not newly reproduced. |
| Option C | Golden pipeline computes `0.7 * p_rf + 0.3 * p_mlp_rob` | Supported by executable source. Manifest historical mean ROC-AUC is RF 0.997568 and Option C 0.996982; it does not support “fusion improves clean AUC.” |
| BCL | The original has risk-layer code, but candidate calibration/evaluation is new and explicitly exploratory after prior ToN-IoT test inspection | Not verified for a confirmatory paper claim. No BCL evaluation was run. |
| Differential privacy | Original `src/iot_ids/privacy/dp_sgd.py` seeds NumPy/PyTorch RNGs; adds noise with `torch.randn_like`; uses ordinary binomial sampling but forces at least four records for empty draws; divides by realized batch size; computes epsilon assuming a fixed Poisson sample rate. An approximate custom fallback is used if Opacus is unavailable. | The implementation does not support the existing “guaranteed DP” / epsilon claims as written. Sampling, randomness, normalization, and accountant assumptions need specialist correction and new experiments. Historical epsilon values are unverified, not newly validated. |
| Explainability | `src/iot_ids/xai/local_xai.py` describes and computes normalized 0.7 RF + 0.3 MLP attribution; golden pipeline uses RF/MLP fusion | Source supports the documented weight scheme. The historical numeric feature values were not independently recomputed. |
| Manuscript consistency | Two root ZIP archives contain distinct `main.tex` files; the later Overleaf archive is dated 2026-09-26. Candidate checkout also has a longer TeX manuscript and publication DOCX. | Submission version is not identified. The archives contain unsupported DP and split claims; see Phase H. |

## Validation performed

- Command: `.\.venv\Scripts\python.exe -m pytest tests/unit/data/test_flow_aggregator.py -q`
- Result: `10 passed in 4.16s`.
- Purpose: focused regression coverage for flow aggregation and new constructor validation.
- Data: synthetic unit test values only; no real datasets, model checkpoints, BoT-IoT file 4, or ToN-IoT BCL evaluation accessed.
- File effects: pytest may update ignored `.pytest_cache`/bytecode only; no official report, dataset, or model artifact was written.
- No other test, training, evaluator, or report-generation command was run.

## Deferrals and next actions

1. Have the author identify the authoritative submission manuscript among the located archives and candidate sources, then correct the unsupported claims.
2. Preserve the split-provenance distinction: the generator is class-wise source-order, but it does not establish global event-time holdout or tie the tracked split artifacts to a run.
3. Suspend differential-privacy guarantee language until the model path, Poisson sampling, cryptographic randomness, fixed normalization, accountant, and released outputs are corrected and validated with new authorized experiments.
4. Keep BCL findings exploratory; any confirmatory evaluation needs a fresh untouched holdout/nested protocol and a path that excludes protected ToN-IoT test data and all BoT-IoT data.
5. Preserve the historical golden manifest as historical evidence; do not rerun the full pipeline or overwrite it for software validation.

## Final disposition

Implementation status: **still blocked by critical research-evidence issues** for final paper review, specifically unsupported DP guarantees, split-method contradiction, and missing current manuscript source. Engineering changes in this pass are narrowly complete and synthetically validated. No commit or push was made.

Recommended commit message: `fix(runtime): validate flow aggregation limits`
