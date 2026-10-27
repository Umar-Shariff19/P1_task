# Phase H — Research Provenance and Evidence Recovery

Date: 2026-10-27

> **Phase I archival addendum:** The manuscript-only assets located in Phase H were moved out of both repository trees into `C:\Users\umari\Documents\IDS_Manuscript_Archive\2026-10-27\`. The detailed file inventory and retained context are recorded in `results/implementation/manuscript_cleanup_inventory.md`; the findings below remain historical evidence and the source manuscript was not edited.

## 1. Working-tree baseline and preservation

- Repository: `C:\Users\umari\Documents\P1_task_Implementation`
- Branch/HEAD: `master`, `5117df8bbd969544786a750ef6993b958f1655a0`; one commit ahead of `origin/master`.
- Phase H initial status: Phase G changes remained present (`src/iot_ids/data/flow_aggregator.py`, `tests/unit/data/test_flow_aggregator.py`, `PHASE_G_IMPLEMENTATION_AUDIT.md`); the pre-existing modified `src/iot_ids/cli.py` and untracked `tests/integration/test_cli_missing_scapy.py` / `tests/integration/test_cli_validate_config.py` were preserved. No staged changes were present.
- The Phase G flow change only adds constructor validation for finite positive timeouts and a positive integer active-flow cap. It does not alter valid aggregation, expiration, or eviction behavior; the prior focused test run covered valid flow reconstruction and invalid/valid constructor limits.
- The candidate checkout remained a read-only reference. Its Git metadata is inaccessible under current filesystem permissions.

## 2. Split-provenance determination

There are two distinct split paths in the repository:

1. The four-dataset golden path reads `data/processed/stage3/{dataset}/{train,val,test}.parquet`. `scripts/run_golden_pipeline.py` consumes those files directly and does not verify their generation method, hashes, or temporal order.
2. `scripts/03_create_splits.py` calls seeded stratified `train_test_split` on the separate `data/processed/final` path for the older Edge-IIoTset/ToN-IoT structural pipeline. It is not the generator for the golden Stage 3 files.

The source generator for golden Stage 3 is `scripts/03_materialize_and_audit_features.py`. It takes up to 2,000 benign and 5,000 attack flows from each adapter stream, partitions each class separately by stream order into 60/20/20 groups, sorts rows inside each completed split by `timestamp_start`, and resets feature-builder state at each split. This is not a global chronological partition with shared train/validation/test time cutoffs. In addition, the ToN-IoT and NF-ToN-IoT-v2 adapters synthesize timestamps by incrementing a baseline as rows are read; those timestamps do not establish source event-time chronology.

The Stage 3 parquet files are tracked and were included with the model files and golden manifest in release commit `53efe08` (2026-10-01). The golden manifest records a run timestamp of 2026-09-14, seed 42, four dataset names, feature count 21, and aggregate/per-dataset results. It does not record a source commit, split-generator version, dataset/split hashes, artifact hashes, or environment identifier. Git shows the golden pipeline source and these split/model/manifest artifacts first in the October 1 release history; the code commit and artifact commit therefore postdate the manifest's internal run timestamp. Co-release in Git is useful packaging evidence, but it does not prove which exact split or source bytes produced the historical run.

| Claim | Current source evidence | Artifact/provenance evidence | Conclusion | Required next action |
|---|---|---|---|---|
| Four final datasets were intended | `scripts/run_golden_pipeline.py` and the golden manifest name Edge-IIoTset, NF-ToN-IoT-v2, ToN-IoT, CICIoT2023 | Manifest records these four names | Supported as declared scope | Keep the final paper scoped to these four. |
| Historical golden scores used a global chronological 60/20/20 holdout | Stage 3 partitions each class by adapter stream order; it sorts within split, not across global time boundaries. ToN-IoT and NF-ToN-IoT-v2 timestamps are synthesized from row order. | Existing parquet files have no split manifest or hash binding them to the generator/run. | Unverified for the files; the global chronological wording is contradicted by the available procedure. | Remove “chronological” as a global-holdout claim. State the precise procedure only if provenance is supplied; otherwise mark temporal generalization unverified. |
| 4,200/1,400/1,400 counts | Stage 3 materializer targets 2,000 benign plus 5,000 attack records, then class-wise 60/20/20; golden script reads train/val/test | Golden manifest and numerical ledger record 4,200 train and 1,400 test; secondary ledger records 1,400 validation | Counts match the reported 7,000 total, but do not establish split provenance | Retain as historical counts; bind future runs to source/data hashes. |
| Standardized feature schema has 21 inputs | `runtime/schema.py` and golden pipeline list 21 ordered features | Golden manifest says `feature_count: 21`; deployable artifact metadata has a 21-name list but describes a separate deployment model | Supported for code schema; golden checkpoint lineage remains incomplete | Record ordered feature names and hashes with future model metadata. |
| Golden RF is 100 trees, depth 15 | Golden training source constructs `RandomForestClassifier(n_estimators=100, max_depth=15, random_state=42)` | Golden artifact files have no per-model configuration or hash mapping in the metrics manifest. `models/final/deployable_artifact/pipeline_metadata.json` says depth 12 and belongs to a different deployable artifact. | Source configuration supported; settings of each historical metric artifact not conclusively bound | Keep the golden and deployable configurations distinct; add model provenance to future runs. |
| Standard and robust MLP training settings | Golden source uses 15 epochs, batch size 256; robust stream calls adversarial training with PGD-7, epsilon 0.10 | Model files are co-released but have no manifest tying them to those settings or the September 14 metric run | Current source is supported; exact historical model provenance unverified | Record artifact hashes/configuration with future results. |

The Phase G note incorrectly used the older `03_create_splits.py` implementation as evidence about the golden Stage 3 split. That conclusion is corrected here and in the Phase G note. No split files were opened or regenerated in this phase.

## 3. Differential-privacy audit

### Training and evaluation path

`src/iot_ids/privacy/dp_sgd.py` implements per-example gradients, clipping, Gaussian noise, and an accountant call, but the full path does not establish the formal assumptions of the reported accountant value:

- `train_robust_mlp_dp` fixes NumPy and PyTorch seeds to `dp_config.seed` (default 42), and noise is generated by `torch.randn_like`; this is ordinary seeded PRNG use, not a demonstrated cryptographically secure noise source.
- Poisson inclusion is sampled with `np.random.binomial`, but an empty selection is replaced with a selected subset of up to four records. That is not the accounted-for independent Poisson sampling mechanism.
- The sampled clipped-gradient sum plus noise is divided by the realized sampled batch size. The accountant is passed fixed `q = batch_size / dataset_size`; this does not account for a data-dependent denominator under the stated Poisson mechanism.
- The helper returns `final_loss` and per-epoch raw loss history. Those outputs are not privatized; publishing them would be an additional release outside the model-update accountant.
- `compute_dp_epsilon` tries Opacus PRV and then RDP by directly setting accountant history; if Opacus is absent it uses a hand-coded approximate RDP fallback. `pyproject.toml` declares neither Opacus nor PyTorch in the base dependency list (PyTorch is only under the optional `models` extra; no privacy extra or lockfile pins the accountant). The checked-in environment snapshot records Opacus 1.6.0, but the golden metrics manifest does not link that snapshot to its run. In the current `.venv`, Opacus is not installed; this current state does not identify the historical run environment.
- Validation is not passed into the DP trainer. The golden pipeline trains the separate DP analysis model from `X_tr`, then evaluates it on `X_te`; it records metrics but does not save the DP model checkpoint or per-run training configuration.
- Most consequentially, the golden Option C prediction is `0.7 * p_rf + 0.3 * p_mlp_rob`, where `mlp_rob` was trained by the ordinary adversarial-training function, not DP-SGD. The separate `model_dp` experiment is not fused into Option C and its checkpoint is not saved. The released `mlp_adversarial.pt` is written from the non-private `mlp_rob` state.
- The test `tests/unit/test_dp_privacy.py` checks that an epsilon number is returned and decreases with more noise. That is a numerical smoke check, not a proof that the mechanism/accountant match.

**Conclusion:** the current code does not substantiate an `(epsilon=2.37, delta=1e-5)` guarantee for the Option C model. The historical privacy table values are not valid formal privacy evidence as currently linked. A corrected mechanism and accountant would change the training process and require fresh authorized training/evaluation, a new DP checkpoint, end-to-end release review, and new provenance. No retraining was performed.

### Safe correction made

Updated the privacy module documentation to identify the trainer and epsilon field as experimental/unverified and enumerate the sampling, randomness, normalization, and raw-loss problems. No runtime behavior, optimizer, model, training parameter, artifact, or reported value was changed.

## 4. Manuscript discovery and reconciliation

The manuscript was not absent; Phase G missed sources packaged in ZIP files. The authoritative repository has two existing paper archives:

- `FINAL_IEEE_PAPER.zip` contains `main.tex` dated 2026-09-22.
- `FINAL_IEEE_PAPER_Overleaf.zip` contains a different `main.tex` dated 2026-09-26.

The candidate checkout also contains `final_ieee_paper/main.tex` and `An_Adversarially_Robust_and_Privacy_Preserving_AI_Framework_Final_Publication.docx`. I cannot establish which one was submitted, so none was edited or rewritten.

Key discrepancies for author review:

- The September 22 TeX says 70/30 train/test splits, and describes a 64/32 MLP; the current golden source reads train/validation/test splits and uses a 128/64/32 hidden architecture. The September 26 version changes those values to 60/20/20 and 128/64/32, but calls the split globally chronological; current source/artifacts do not substantiate that wording.
- Both TeX versions describe the fused neural stream as jointly DP-SGD and PGD trained and claim epsilon 2.37. Current golden source fuses the non-private adversarial MLP. Its DP-trained model is separate and unsaved; the mechanism and accountant assumptions are not validly established.
- The papers report 0.9976 RF / 0.8590 standard MLP / 0.8562 robust MLP / 0.9970 Option C. These rounded values match the historical golden manifest, but no hashes bind the metrics to split bytes, source commit, or model artifacts. They are historical report values only.
- The September 22 source says scaling parameters were fitted on benign training distributions; golden code fits the RobustScaler on all training rows. This is another methods wording discrepancy for author correction.
- The Option C mean AUC (0.996982) is slightly below the RF mean (0.997568); the evidence does not support saying fusion improved clean AUC.
- PGD settings and Option C 0.7/0.3 match the current golden source, but historic test metrics were not reproduced here and retain the split/artifact lineage caveat.
- The weighted RF/MLP attribution formula matches local-XAI source, but historical numeric attribution values were not recomputed.
- The 16,504.7 samples/s throughput appears in the manifest/report and manuscript, but no fresh benchmark was run; it is a classifier-only figure, not packet-ingress throughput.
- The candidate long-form paper includes additional seed sensitivity, adaptive attack, and black-box attack claims. Their source/reports are outside this focused phase and were not rerun; they need their own provenance review before final acceptance.

No manuscript archive, DOCX, figure, bibliography, or historical report was modified. Suggested paper correction: remove the DP guarantee and describe the DP branch only as an unverified exploratory implementation until corrected experiments exist; state the split procedure and its timestamp limitations without calling it a global chronological holdout; identify the authoritative paper version before editing.

## 5. Historical metric provenance

The four requested values match `reports/golden_run_manifest.json` and are repeated in `reports/final_forensic_audit/authoritative_numerical_ledger.json`:

| Metric | Manifest value | Assessment |
|---|---:|---|
| RF mean ROC-AUC | 0.9975684375 | Historical reported value; rounds to 0.997568. |
| Option C mean ROC-AUC | 0.9969815625 | Historical reported value; rounds to 0.996982. |
| Standard MLP mean ROC-AUC | 0.8590496875 | Historical reported value; rounds to 0.859050. |
| Robust MLP mean ROC-AUC | 0.85620875 | Historical reported value; rounds to 0.856209. |

The manifest records per-dataset AUCs, seed 42, sample counts, four dataset names, and feature count. It does not bind the results to split hashes, a run-time Git commit, model hashes, or its environment. Model binaries and split parquet files are included in the October 1 release commit, but the metrics manifest's internal time is September 14 and provides no artifact linkage. The current source is a plausible description of intended settings, not proof of which code or exact data produced that earlier run. No official metric was recomputed.

## 6. BCL safety and evidence

- The original repository does not contain the candidate `BehavioralConsistencyLayer` or `BCLInferenceEngine`. It has a distinct `RiskLayer` for supervised probability plus autoencoder anomaly scoring.
- Original `scripts/06_calibrate_risk.py` fits the autoencoder empirical CDF from validation benign samples. Original `scripts/07_evaluate.py` later loads that frozen risk layer and scores a test split. This is not evidence for the candidate behavioral-consistency method or any BCL result.
- The candidate evaluator first calibrates its BCL on validation inputs/labels, then scores test inputs and writes calibration/evaluation JSON. It offers a ToN-IoT option and explicitly states that its scoring rule followed earlier inspection of the ToN-IoT test split; it marks the results `exploratory_not_confirmatory`. It also shuffles and re-scores test order, while the engine maintains one global stream history and the evaluator admits order is not necessarily chronological.
- The candidate evaluator and its tests were not executed. The previously exposed ToN-IoT test split was not read or evaluated. The golden manifest contains no BCL metrics.

**Conclusion:** there is no safe, independent, confirmatory BCL evidence for paper claims. Candidate BCL results require a fresh protocol designed before seeing test outcomes, with data paths and ordering boundaries explicitly specified. Do not report them as real-data validated.

## 7. Documentation corrections and files changed

Phase H makes documentation-only corrections; no algorithm or scientific result changed:

- `README.md`: replaced the global chronological split claim with the implemented class-wise stream-order procedure, synthetic timestamp caveat, and missing split-run provenance.
- `src/iot_ids/data/adapters/base.py`: corrected the adapter interface promise from strict chronological stream to dataset-specific stream order/timestamp semantics.
- `scripts/03_materialize_and_audit_features.py`: corrected description and progress wording to class-wise stream-order partitioning; executable split behavior is unchanged.
- `src/iot_ids/privacy/dp_sgd.py`: removed documentation language asserting a formal guarantee and marked returned epsilon as unverified.
- `FINAL_IMPLEMENTATION_STATUS.md` and `FINAL_RELEASE_VERIFICATION.md`: added dated evidence-status addenda, preserving original content as historical snapshots.
- `PHASE_G_IMPLEMENTATION_AUDIT.md`: corrected Phase G's split conclusion and manuscript inventory.
- Added this report, `PHASE_H_RESEARCH_PROVENANCE.md`.
- No source manuscript archive, dataset, model, checkpoint, benchmark, metric, or BCL artifact was modified.

## 8. Validation and commands

Static review covered the original split source/callers, all four dataset adapters needed to establish timestamp semantics, the golden training/fusion/save path, DP implementation/callers/dependencies, current split and model metadata filenames, historical manifests/ledgers, current and archived manuscript sources, original risk calibration/evaluation, and candidate BCL source/evaluator. Scripts were read but not executed.

Commands executed for validation in this phase:

- `.\.venv\Scripts\python.exe -m py_compile src/iot_ids/data/adapters/base.py scripts/03_materialize_and_audit_features.py src/iot_ids/privacy/dp_sgd.py` — exit 0; syntax-only; no dataset/artifact access.
- `.\.venv\Scripts\python.exe -m pytest tests/unit/data/test_flow_aggregator.py -q` — exit 0; 10 passed in 1.05s; synthetic unit tests for the preserved Phase G behavior; no dataset/checkpoint access.
- `git -c safe.directory=C:/Users/umari/Documents/P1_task_Implementation -C . diff --check` — whitespace/conflict-marker check only.

No DP training test, BCL test/evaluator, training pipeline, benchmark, or real-data evaluation was run. This phase produced no test evidence about real detection, privacy guarantees, split quality, or BCL performance.

## 9. Remaining limitations and readiness

Author decisions and new experiments are required before final paper review:

1. Identify the authoritative submission version and correct its false 70/30 statement (older TeX), global chronological claim, DP-trained Option C claim, epsilon guarantee, and benign-only scaler-fit description.
2. Supply the actual run/split manifest and source commit for the historical metric run, if they exist; otherwise label all metrics historical and provenance-incomplete.
3. Design and implement a formally supported DP mechanism, accountant, secure randomness, and release policy; retrain only under an authorized new experiment and preserve the old artifacts.
4. Establish a clean BCL protocol without reusing the previously inspected ToN-IoT test split; keep current BCL numbers exploratory or omit them.
5. Independently review the candidate paper's additional seed, adaptive-attack, and black-box claims.

Readiness: **Still blocked by critical issues.** The original code and historical evidence do not substantiate the DP claim or global chronological split claim, the exact provenance of historical metrics is incomplete, and the authoritative manuscript version is not identified. No commit or push was made.

Recommended commit message: `docs(research): correct split and privacy evidence claims`
