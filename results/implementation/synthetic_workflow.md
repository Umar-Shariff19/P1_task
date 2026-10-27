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
