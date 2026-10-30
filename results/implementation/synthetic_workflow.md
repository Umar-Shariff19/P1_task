# Synthetic runtime smoke path

This synthetic-only workflow exercises `InferenceEngine.predict()` through its explicit in-memory injection path. That path invokes the normal constructor, accepts only `dataset="SYNTHETIC_ONLY"`, has no model-directory argument, and does not load files. It checks the 21-feature schema, frozen preprocessing, RF/MLP fusion arithmetic, model-output validation, SHAP output shape, and a generated-label diagnostic. The test also checks a schema-valid manifest and digests for temporary synthetic outputs.

Run the diagnostic command from the repository root with the existing environment:

```powershell
$env:PYTHONDONTWRITEBYTECODE='1'
.\.venv\Scripts\python.exe -m iot_ids.runtime.synthetic_smoke
```

The test suite can also be run with:

```powershell
$env:PYTHONDONTWRITEBYTECODE='1'
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'
.\.venv\Scripts\python.exe -m pytest -p no:cacheprovider tests/unit/test_runtime_synthetic_workflow.py -q -rs
```

The smoke command and tests create and fit a small Random Forest only on generated samples; the MLP is freshly initialized and untrained. The MLP is an interface fixture, not a trained model. Test output artifacts live in a temporary directory; the command writes no files. The synthetic AUC is a diagnostic only and is not an IDS result, benchmark, reproduction, or evidence about research data. Test-local preflight authorizes only its synthetic case; real-data authorization remains disabled.

Experiment result rows use the undefined-metric contract in [`experiment_result_status.md`](experiment_result_status.md); synthetic diagnostics are not written to the Stage 4 report locations.

Legacy runtime and experiment commands that use configured datasets or checkpoints are outside this path and remain subject to the documented authorization, provenance, privacy, and scientific-evidence blockers.

## Flow aggregation to alert without model fitting

Run the user-facing synthetic packet-to-alert demonstration from the repository root:

```powershell
$env:PYTHONDONTWRITEBYTECODE='1'
.\.venv\Scripts\python.exe -m iot_ids.runtime.synthetic_packet_demo --seed 2026 --flows 3
```

The command generates six packet records, aggregates them into three flows, constructs the current 21 canonical features, and calls `IDSSystemPipeline.process_flow()` for each flow. It writes JSON to standard output and exits nonzero on invalid configuration or an inference-contract failure. Each alert includes the probability value produced by the test double, threshold decision, risk score/level, flow identifiers, and five selected canonical features. The JSON header marks the entire result `SYNTHETIC_ONLY_DIAGNOSTIC` and states that the model is untrained and no artifact was loaded.

The in-memory model is a deterministic duration-threshold rule, not a fitted classifier or confidence estimate. The identity preprocessor, feature builder, schema validator, aggregator, probability-output validation, and alert/risk logic are the interfaces being demonstrated. The output is not research or benchmark evidence and must not be compared with historical metrics. This path does not use packet capture, production model initialization, datasets, checkpoints, CLI authorization, or real-data authorization. Real-data authorization remains disabled.

Regression tests for this command are in `tests/unit/test_synthetic_packet_demo.py`. A separate integration test, `tests/integration/test_pipeline_e2e.py::test_synthetic_packets_aggregate_into_inference_alert`, also covers the component path with test doubles.

```powershell
.\.venv\Scripts\python.exe -m pytest -p no:cacheprovider tests/integration/test_pipeline_e2e.py::test_synthetic_packets_aggregate_into_inference_alert -q
```

The separate `python -m iot_ids.runtime.synthetic_smoke` workflow described above initializes and fits an RF on generated samples; it is not needed to run this packet-to-alert demo.
