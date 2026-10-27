# Controlled future experiment plan

**Status:** proposed only; not authorized or executed. This protocol does not reproduce or validate historical results. Historical split and metric provenance remain unresolved. The two prior safety incidents remain unresolved; see `../validation/safety_and_data_access.md`.

**Current implementation boundary:** the canonical manifest validator and synthetic-only preflight are available. `execute_after_preflight()` prevents its callback from running unless schema, injected synthetic-only authorization, and any required explicit artifact checks pass; it never authorizes research data. The two Stage 4 benchmark entrypoints and their direct split/audit helpers now refuse before data or output access. Other direct research scripts are not yet covered by a common boundary and remain disabled operationally. Stage 4 report bundles include an evidence-status sidecar; even a schema-valid manifest leaves authorization, artifact integrity, provenance, and scientific validity unverified.

## 1. Prerequisites and approvals

- Repository owner approves the research question, dataset identities, access purpose, protocol, output retention, and stopping rules.
- Owner supplies canonical approved roots and protected-root policy through an authoritative configuration. No paths are inferred from folder names or callers.
- Windows security/platform review approves volume identity, mapped/UNC-drive handling, case semantics, reparse-point policy, and no-follow handle implementation.
- A clean, selected manuscript version and claim list are identified by the author. The archive is not presumed authoritative.
- Privacy specialist reviews the privacy unit, adjacency, mechanism, sampler, clipping, noise, accountant, composition, and released outputs before any DP run.
- Each run receives a separate manifest and destination. Existing reports/checkpoints are immutable inputs for this plan.

## 2. Authorized roots and access controls

Use only owner-approved absolute roots recorded in an explicit policy, with dataset IDs, protected roots, approval references, and policy version. Reject unlisted, relative, aliased, ambiguous, protected, or out-of-scope paths before any filesystem traversal. Until the policy and a reviewed Windows identity verifier exist, all real-data adapters remain unauthorized. Do not use recursive inventory or parent-directory discovery to classify paths. Never access the prohibited BoT-IoT file 4 or the previously exposed ToN-IoT test split; never run the prohibited BCL evaluator.

## 3. Split protocol

### Historical method (source-level description only)

The inspected Stage 3 generator partitions each label class in adapter stream order into nominal 60/20/20 train/validation/test portions, then sorts rows within each resulting split by timestamp. Adapter timestamps are not uniformly source event time. Existing artifacts are not tied to this exact generator/version/configuration, so this description is not a reconstruction of their provenance.

### Proposed future method (requires approval; not historical reproduction)

For each authorized dataset, preregister a stable event-time split with explicit timestamp source, timezone, tie-breaking key, grouping unit (device/session/flow family), class-support rule, and boundary policy. Assign groups/events chronologically to train, validation, and test in 60/20/20 target proportions; never sort first and then randomly distribute. Resolve duplicate timestamps deterministically, prevent group overlap, record exact row/group counts and split IDs, and keep a split manifest with generator revision/configuration. If trustworthy event time or grouping is unavailable, stop and request a separately approved non-temporal protocol; do not silently substitute the historical source implementation. Fit all learned preprocessing only on train.

## 4. Train/validation/test separation

Train is for fitting parameters and preprocessing. Validation is for model selection, calibration, thresholds, and protocol tuning. Test is sealed until model/configuration selection is frozen and is evaluated once for the preregistered primary analysis. No test-driven feature engineering, calibration, attack tuning, or repeated selection. Record split access and evaluation events. Do not use the exposed ToN-IoT split.

## 5. Baselines and fusion

Pre-register Random Forest, standard MLP, and robust MLP configurations, feature order, preprocessing, seeds, stopping rules, and metric definitions. Evaluate Option C only as a separately specified score fusion of RF and robust MLP with the intended 0.7/0.3 weights, after each model is frozen. The historical code formula is not proof that old metrics used these exact artifacts. Do not label Option C differentially private unless its actual branches and release mechanism satisfy a reviewed guarantee; current historical fusion uses the non-private robust MLP branch.

## 6. Robust-training protocol

Specify the threat model, attacker access, perturbable feature constraints, epsilon/norm units, attack algorithm/steps/step size/restarts, training attack mixture, seeds, early stopping, and clean/adversarial evaluation before training. Validate that perturbations remain feasible for flow features. Report clean and attack outcomes separately with uncertainty. Robustness results require new authorized training/evaluation and do not repair historical provenance.

## 7. Differential privacy

Treat the existing implementation and epsilon fields as unverified. Before a new DP run, obtain specialist review of privacy unit/adjacency, Poisson or other sampler assumptions, empty draws, per-example gradients, clipping, noise source, normalization, accountant inputs/composition, delta, and all released outputs. Use a secure randomness source and pinned, reviewed dependencies. Ensure the exact DP checkpoint is the checkpoint evaluated and reported; audit logs, losses, gradients, and validation outputs for leakage. Do not report epsilon until the mechanism-accountant match and implementation have been independently validated. A corrected mechanism requires a new, separately manifested training run.

## 8. Explainability

Pre-register explainers, target outputs, background/reference data, feature grouping, fidelity and stability measures, repeated seeds, and subgroup analysis. Fit/select explanation settings on permitted train/validation data; reserve test for the frozen analysis. Bind explanations to checkpoint, feature schema, and configuration. Do not use synthetic explanation tests as evidence of real-world explanation validity.

## 9. BCL evidence policy

Do not run the prohibited ToN-IoT BCL evaluator or access the previously exposed ToN-IoT test split. Do not use candidate BCL reports as confirmatory evidence. Any future BCL study requires a clean approved dataset/test source with documented temporal boundaries, calibrator-fit partition, scoring partition, no test leakage, and independent static review before execution. If an uncontaminated permitted test source cannot be established, omit confirmatory BCL performance claims.

## 10. Metrics, uncertainty, reproducibility, and retention

Predefine ROC-AUC, PR-AUC, class-wise precision/recall/F1, macro-F1, calibration, recall at fixed false-positive rates, runtime, and memory as appropriate. Report counts and uncertainty intervals, using group-aware bootstrap when observations are clustered. Use multiple declared seeds for training variability. Retain exact configs, source/diff ID, safe split manifest, environment lock, logs, metric definitions/outputs, and model/checkpoint digests in an approved access-controlled location. Never place protected raw paths or data in public manifests.

## 11. Manifest validation

Validate each future record against `../provenance/experiment_manifest.schema.json` using the declared local validator and record its exact installed version in the manifest. Include source revision and dirty-tree diff reference, dataset/split/generator identity, model/checkpoint identity, training/evaluation config, dependency/environment versions, metric definitions/outputs, timestamp, safety-policy version, and artifact digests. A schema-valid record is a structured claim, not proof of authorization or provenance; retain the external approval and run evidence separately. Never backfill historical records with guesses.

## 12. Acceptance criteria and stop conditions

Proceed only when roots and path identity are approved/enforced; split specification and leakage controls are reviewed; methods/configs are preregistered; test access is controlled; DP specialist approval exists for any privacy claim; manifests validate; and output destinations are isolated from historical artifacts. Stop immediately on an unclassified/ambiguous path, protected overlap, alias/reparse-point uncertainty, unexpected test access, group leakage, schema failure, unexplained checkpoint/config mismatch, evaluator/capture path, output overwrite risk, or privacy-accounting discrepancy. A successful future run may support only the claims its manifest and independent evidence directly establish; it does not automatically reproduce the historical numbers.

## 13. Provenance utility scope and runner integration

The standalone manifest validator checks structure only. The digest helper, if used in a future prospective workflow, reads one explicit relative artifact beneath an explicit caller-selected base and reports byte equality only. Neither establishes dataset authorization, truth of recorded provenance, scientific validity, or a safe research-data base. Neither is wired into any experiment runner. Static review found `run_master.py` launches training/evaluation children via subprocess, while those children and other direct training/evaluation scripts can be invoked independently. `run_golden_pipeline.py` reads split files and writes checkpoints plus a legacy summary manifest; `run_privacy_experiments.py` trains/evaluates synthetic samples and writes privacy outputs without a prospective manifest. These paths lack a shared authorization/provenance preflight. Runner-wide integration must cover the dispatcher and every direct entrypoint before any real-data run; no runner is authorized by this plan.

The standalone coordinator in `src/iot_ids/provenance/preflight.py` composes schema validation, an injected policy decision, and optional explicit artifact checks. It emits stable reason codes, does not infer artifact paths from the manifest, and allows only synthetic scope. No production authorization provider exists; the policy implementation used in tests is local to the test module. `READY_SYNTHETIC` is not authorization to access research data or run an IDS experiment. Real-data authorization is deliberately unavailable in this implementation until canonical roots and reviewed Windows filesystem identity enforcement are established.

### Static entrypoint and bypass inventory

| Group | Reviewed entrypoints/access boundary | Current bypass and preflight state |
|---|---|---|
| Dispatcher | `scripts/run_master.py` starts `train_rf.py`, `train_mlp.py`, `train_ae.py`, and `evaluate_cross_domain.py` through subprocess calls. | No common preflight. Each child can be called directly, bypassing dispatcher checks. No manifest validation, authorization, or artifact-integrity enforcement. |
| Direct training | `scripts/train_rf.py`, `scripts/train_mlp.py`, `scripts/train_ae.py`, `scripts/05_train_models.py`, `scripts/13_run_adversarial_training.py`, `scripts/run_golden_pipeline.py`, `scripts/run_privacy_experiments.py`. | Direct entrypoints. Source reads split data; some load preprocessing/checkpoints; golden runner loads train/validation/test splits and writes checkpoints. They can access files before a future dispatcher-only check. No preflight enforcement. Privacy runner's sample loader is synthetic, but its main still starts training/evaluation. |
| Direct evaluation | `scripts/evaluate_v2.py`, `scripts/evaluate_cross_domain.py`, `scripts/07_evaluate.py`, `scripts/10_run_adversarial_evaluation.py`, `scripts/14_run_ensemble_experiments.py`, `scripts/12_run_shap_experiments.py`. | Independently invokable; source reads splits and/or loads checkpoints before scoring/analysis. No preflight enforcement. |
| Benchmarks | `scripts/04_run_benchmarks.py`, `scripts/04_benchmark_models.py`, `scripts/benchmark_runtime_xai_privacy.py`. | Independently invokable; source reads split data or model/runtime inputs and writes benchmark outputs. No preflight enforcement. |
| Data adapters | `DatasetAdapter.audit()`, subclass `get_source_files()` and stream methods, including `CICIoT2023Adapter.get_source_files()`. | Direct method calls bypass runner dispatch; audit/discovery/stream can touch files before any prospective runner-level validation. No adapter authorization boundary exists. |

This is a targeted source review, not an exhaustive enumeration of every script. Before future integration, inventory every command and direct method that can reach data, model loading, scoring, or output writes. Shared enforcement must occur before file access at both runner and adapter boundaries; adding a check only to `run_master.py` is insufficient.

## Real-data preflight checklist (must all pass before execution)

- [ ] Dataset roots are explicit and owner-approved for the named dataset identities.
- [ ] Windows path-identity enforcement has passed platform/security review, including reparse points, volume identity, mapped drives, and case semantics.
- [ ] The shared adapter authorization boundary is integrated and tested to reject unauthorized roots before any discovery or access.
- [ ] Prohibited paths and splits, including the protected file and exposed test split named in the safety record, are unreachable through the selected source and call paths.
- [ ] The split-generation specification, timestamp source, boundaries, groups, and train/validation/test separation are documented and approved.
- [ ] The prospective manifest validates against the canonical schema and external approval/evidence records are checked independently.
- [ ] Model configurations and evaluation protocols are approved and frozen before test access.
- [ ] A privacy specialist has reviewed the complete mechanism/accountant/output path if any privacy claim is intended.
- [ ] A written BCL policy excludes the prohibited evaluator and exposed test split; if no clean permitted test source exists, BCL claims are omitted.
- [ ] A named stop-condition owner and isolated output destination are recorded; any failed or ambiguous authorization/provenance check stops the run before data access.

This checklist is prospective. It was not executed and its completion is not implied by a passing synthetic test or schema validation.
