# Research entrypoint refusal matrix

## Policy

Research-data access remains disabled. `require_real_data_authorization()` in
`src/iot_ids/provenance/windows_access.py` always raises the typed
`RealDataAuthorizationUnavailable` with code `REAL_AUTHORIZATION_DISABLED`.
It performs no path lookup and accepts no manifest, environment variable, CLI
flag, or caller-constructed identity as an override. This is a refusal
boundary, not a functioning authorization provider.

## Guarded project-owned script paths

The guarded callable list and AST placement regression check are maintained in
`tests/unit/test_research_entrypoint_guards.py`. It covers the directly
identified materialization, dataset audit, split generation/validation,
Stage 4–7 analysis, training, evaluation, XAI, privacy, adversarial, ensemble,
federated, robustness, benchmark, evidence, and dispatcher scripts. The
historical and paper-evidence packaging scripts that perform top-level output
or archive operations are also stopped before those operations.

The following shared boundaries also refuse before access: concrete dataset
adapter discovery/streaming and audit, `data.audit.run_audit`,
`data.materialize.materialize_dataset`, split loading/training in
`training.train`, `ModelRegistry.load_pipeline` and `save_pipeline`, production
`InferenceEngine.__init__`, and the production CLI dispatch after argument
parsing. A real-data constructor call is refused before checkpoint loading.

`InferenceEngine.for_synthetic_components()` remains available only through
its existing explicit in-memory contract (`dataset="SYNTHETIC_ONLY"`, no
model directory). This path uses newly generated objects and does not relax
the real-data authorization decision. The synthetic smoke module is not
guarded and is not a benchmark entrypoint.

## Evidence and limitations

`test_research_entrypoint_guards.py` statically checks the first operation in
the bounded script-callable inventory and dynamically verifies refusal before
selected read/discovery/write/training/checkpoint spies. These tests do not
prove Windows filesystem identity, owner approval, or security against an
in-process caller deliberately bypassing Python APIs.

This is not a proof that every possible project-owned callable is covered.
The source search was limited to Python files under `scripts/` and
`src/iot_ids/` with filesystem, checkpoint, fitting, dispatch, and output
operations. Dynamic imports, unsearched third-party entrypoints, notebooks,
and arbitrary Python code can bypass script-level guards. The public
`publish_stage4_reports` interface now refuses before creating staging files;
the private `_publish_stage4_reports_unchecked_for_synthetic_tests` helper is
used only by synthetic temporary-output tests. Python does not provide a
security boundary against deliberate in-process calls to private functions.
Other pure helpers that accept already-loaded frames or arbitrary paths
likewise are not an OS-bound access context. Further production-wide
integration remains blocked on approved roots, protected-root scope,
authenticated approval, and reviewed Windows handle-bound access.

No Phase I or Phase J incident status is changed. Historical benchmark values
remain `HISTORICAL_REPORTED`; synthetic checks do not reproduce them.
