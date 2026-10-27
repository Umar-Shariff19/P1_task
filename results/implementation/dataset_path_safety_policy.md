# Dataset path-safety policy (partial primitive; real-root enforcement not implemented)

## Status and current evidence

This document records the required policy and the partial implementation in `src/iot_ids/data/path_policy.py`. That module performs lexical checks and requires a caller-supplied identity verifier; it does not inspect the filesystem, contain real approved roots, or integrate with adapters. Therefore it is not effective access control for repository datasets. No training, dataset adapter, audit, inventory, or provenance utility was run to prepare this document or implementation.

The inspected Stage 3 caller hard-codes relative roots under `data/raw/` for ToN-IoT, Edge-IIoTset, NF-ToN-IoT-v2, and `CICIOT23`. `build_default_adapters(raw_dir)` supplies four named child roots, with `CICIoT2023` as the final child. The golden runner uses a fixed Stage 3 root and reads named `train.parquet`, `val.parquet`, and `test.parquet` files. These are existing call-site conventions, not a canonical approved-root policy. The inspected configuration class contains no raw-dataset root policy; the split-provenance record likewise does not define one. The different CICIoT spellings are unresolved and must not be silently normalized into an approved path.

`DatasetAdapter.__init__()` accepts a caller-provided `raw_path`. `DatasetAdapter.audit()` calls `get_source_files()` and then profiles existing paths. `CICIoT2023Adapter.get_source_files()` recursively searches the supplied root for CSV files, without a protected-path check. The lexical authorization primitive is not wired into these components, so they are not safe for provenance inventory use.

## Required policy

1. **Canonical approved roots and configuration.** A future access-policy configuration must list each approved dataset identifier and its canonical absolute root, plus the protected-root set. Each value must be explicitly established by an authorized project configuration or user decision. The repository currently establishes no canonical approved absolute roots and no complete protected-root path; therefore none are invented here. Relative defaults such as `data/raw/...` are not sufficient approval. The current CICIoT path-name discrepancy must be resolved by the repository owner before configuration is authored.

2. **Protected roots before traversal.** Compare the caller's lexical path against the protected-root denylist and reject any path equal to, below, or an ancestor of a protected root before calling `exists`, `stat`, `resolve`, `glob`, `rglob`, `iterdir`, `os.walk`, opening a handle, or reading a directory entry. Deny roots that are unclassified or overlap a protected root. Path exclusion after enumeration is prohibited.

3. **Normalization and containment.** Accept only absolute local paths provided by the approved policy; reject relative paths, drive-relative paths, UNC/network paths, device namespaces, alternate data streams, parent traversal, environment-variable expansion, and unrecognized aliases unless separately approved. Normalize separators and dot segments lexically and compare Windows paths case-insensitively for deny checks. Require the resulting path to match exactly one configured canonical root; verify containment by path components, not string prefix. If Windows per-directory case-sensitive behavior or canonicalization cannot be determined safely, reject the path.

4. **Symlinks, junctions, aliases, and case behavior.** Do not follow symlinks, junctions, mount points, or other reparse points at the root or any ancestor. After lexical deny/allow classification, inspect only the already-classified candidate path components using no-follow handles; reject reparse points and any final handle path that differs from the configured canonical root. Do not accept 8.3 short names, alternate spellings, mapped drives, UNC aliases, or case variants as aliases unless the policy explicitly records and validates them. If the platform cannot distinguish or reject an alias safely, fail closed. For file allowlists, reject hard-linked files where link identity/count cannot be established without ambiguity; do not access a protected target to resolve identity.

5. **Caller-supplied roots.** Replace unrestricted `raw_path` authorization with a policy-bound dataset identifier. Resolve that identifier to the one configured root, then require any caller-supplied path to match that root exactly. Provenance/inventory operations should use explicit file allowlists beneath the approved root, not recursive discovery from a parent directory. The caller must not choose a broader root and rely on later filtering.

6. **Fail closed.** Reject missing configuration, unknown dataset identifiers, malformed or relative paths, multiple allowlist matches, protected overlap, aliases, reparse points, unsupported path semantics, and any classification error before traversal or content access. Do not fall back to the current working directory, a parent directory, or an inferred path.

7. **Synthetic-only validation.** Unit tests for the eventual policy must create a temporary synthetic tree outside all real dataset roots. Cover one explicitly approved synthetic root, an outside root, a synthetic protected root and its child, ancestor/descendant overlap, `..` normalization, case variants, and symlink/junction escapes where the test platform safely supports them. Assert protected/out-of-scope cases are rejected before enumeration or file operations, using stubs/spies for `glob`, `rglob`, `stat`, `open`, and directory listing. Never use real dataset paths or fixtures. If a safe isolated tree cannot be guaranteed, do not run the test.

## Required implementation work and unresolved decisions

- Establish the authoritative root for each supported dataset, resolve `CICIOT23` versus `CICIoT2023`, and define the exact protected-root configuration without probing protected data.
- Define Windows path semantics, including case-sensitive directories, volume aliases, junctions/reparse points, hard links, and permitted absolute-path forms. These decisions require owner approval; this policy does not guess them.
- The policy object and lexical authorization boundary exist. Still required: owner-supplied production configuration, a reviewed Windows identity verifier, and enforcement in `DatasetAdapter.__init__()` or an earlier shared boundary before any filesystem query. Update `DatasetAdapter.audit()` so it cannot profile paths until authorization succeeds.
- Update `CICIoT2023Adapter.get_source_files()` and the other adapters to consume explicit authorized file lists or a constrained discovery interface. Remove unrestricted recursive search from provenance/inventory flows.
- Update `scripts/03_materialize_and_audit_features.py`, `build_default_adapters()`, and any future provenance/manifest utility to pass an authorized dataset identifier and policy. Keep the golden runner's named split inputs explicit and prevent new inventory code from scanning its parent.

Until these decisions are made, a platform identity verifier is implemented and reviewed, and adapter integration is validated, do not use adapter audit or recursive discovery utilities for provenance checks. No production verifier currently exists. The lexical primitive has synthetic test coverage, but no path-safety enforcement for real roots is claimed by this document.

## Authorization sources and proposed configuration

Inspection of `src/iot_ids/config.py`, `src/iot_ids/data/adapters/__init__.py`, the adapter base and CICIoT2023 adapter, the named Stage 3 caller, and `results/provenance/split_provenance.md` found **no authoritative explicit list of approved dataset roots**. `PipelineConfig` configures inference/runtime behavior, not raw dataset authorization. Stage 3's relative path literals and `build_default_adapters(raw_dir)` are caller conventions only; they do not grant access. The spelling mismatch (`CICIOT23` in Stage 3 and `CICIoT2023` in the default adapter builder) is unresolved. No dataset directory was inspected to settle it.

Use a separately reviewed access-policy configuration with this schema shape; the `null` values are intentionally unresolved placeholders, so this is **not deployable configuration**:

```yaml
schema_version: 1
datasets:
  <dataset_id>:
    approved_root: null  # owner-approved canonical absolute path required
protected_roots:
  - id: <protected_root_id>
    path: null           # owner-approved canonical protected root required
```

Classification is explicit and ordered:

- **Protected:** equal to, beneath, or an ancestor of a configured protected root. Reject before filesystem queries or traversal.
- **Authorized:** exactly one configured dataset ID and canonical root match, with no protected overlap and successful identity validation.
- **Unclassified:** absent from both lists, conflicting, or not classifiable safely. Reject before filesystem queries or traversal.
- **Syntactically valid but unauthorized:** a well-formed path that is not the exact configured root for the supplied dataset ID. Reject; existence does not grant authorization.

The owner must identify the supported dataset IDs, canonical absolute roots, protected-root scope, and whether any individual file (rather than a dataset root) must be protected. This policy does not infer these values from source literals, folder names, or directory contents.

## Windows path identity decisions

The proposed guard should apply these deterministic lexical checks before touching the filesystem:

- Require an absolute local drive path whose dataset ID is present in the access policy. Reject relative and drive-relative input; do not resolve it against the current directory. Syntactically valid but unlisted absolute paths remain unauthorized.
- Normalize separators and remove `.` components lexically. Reject any `..` component instead of resolving it. Reject environment expansion, device namespace prefixes, alternate data streams, trailing-dot/space components, and malformed paths.
- Normalize the drive letter for comparison and compare protected-root candidates case-insensitively before any filesystem query. Windows normally preserves case while comparing case-insensitively, but per-directory case-sensitive behavior exists. Require the configured component spelling for authorization; reject a differently cased spelling or any case behavior that cannot be determined safely. Owner approval is needed before accepting case aliases.
- Reject UNC paths and mapped/network drives by default. They may be supported only if an owner-approved policy defines the canonical volume identity and the guard can verify it without following an unapproved alias. Drive letters that cannot be mapped to a known local volume fail closed.
- Do not treat string normalization as alias protection. After lexical protected/allowlist checks succeed, validate path components with Windows handles opened without following reparse points. Reject symlinks, junctions, mount points, and all other reparse points in the root or any ancestor. Compare the handle-resolved final path/volume identity with the configured canonical root. If the platform/API cannot perform this check safely, reject the root.
- Reject 8.3 names, mapped-drive aliases, case aliases, and other alternate spellings unless the owner explicitly configures and validates their canonical identity. A lexical path that looks approved but resolves elsewhere is ambiguous and rejected. For explicit file allowlists, reject hard-link ambiguity; do not inspect or open a protected target to disambiguate it.

The exact Windows API/volume policy, including administrator rights needed to inspect reparse points, case-sensitive directory handling, and whether any network volume is permissible, requires repository-owner/administrator approval. Until then, the only supported implementation behavior is fail closed; this is a proposed policy, not current enforcement.

## Proposed shared guard interface

The shared authorization boundary is implemented as:

```python
authorize_dataset_root(
    dataset_id: str,
    supplied_root: str | Path,
    policy: DatasetAccessPolicy,
) -> AuthorizedDatasetRoot
```

The helper rejects missing policy or dataset authorization, missing protected-root configuration, relative and malformed roots, protected overlap, non-exact approved roots, and absent/ambiguous identity verification before file discovery. It performs no filesystem operations. Its identity-verifier contract requires a trusted platform implementation using no-follow handles and volume/root identity, but no such Windows implementation or approved real-root config exists. The returned value carries the configured lexical path and verifier token; it does not hold an OS handle, so it must not be treated as a production authorization until a safe handle-bound design is implemented.

`DatasetAdapter` should accept an opaque result from the authorized boundary (and dataset ID), not treat an arbitrary `raw_path` as authorization. `audit()` must require that result before calling `get_source_files()` or `FileProfile.from_path()`. `CICIoT2023Adapter.get_source_files()` should consume an explicit file allowlist or a constrained authorized discovery interface; it must not call `rglob()` on a caller-provided parent. `build_default_adapters()` and `scripts/03_materialize_and_audit_features.py` should pass IDs through the same boundary once the exact approved roots are established. The policy object, return type, and lexical gate exist, but their identity evidence is caller-constructible. There is no production policy configuration, platform identity verifier, or adapter integration. Do not claim real-root enforcement.

## Synthetic validation plan and executed scope

Test only inside a newly created temporary synthetic tree outside all real dataset roots:

1. Configure one synthetic authorized root and confirm the exact matching dataset ID/root is accepted.
2. Confirm an existing but unlisted synthetic root and a wrong dataset ID are rejected before any filesystem operation.
3. Configure a synthetic protected root and confirm the root, a child, and any ancestor encompassing it are rejected before enumeration.
4. Confirm relative and drive-relative paths are rejected; test `.` normalization and `..` rejection without resolving against the working directory.
5. Where the temporary filesystem safely supports them, create a synthetic symlink and junction/reparse-point escape from an authorized fixture to a separate synthetic outside fixture; confirm rejection without following the link. Skip unsupported link types rather than weakening the assertion.
6. Confirm case variants, mapped-drive/UNC forms, 8.3 aliases, and unresolved volume identities fail closed unless explicit policy rules authorize them.
7. Use spies/stubs to assert protected, unapproved, and ambiguous cases do not call `exists`, `stat`, `resolve`, `open`, `glob`, `rglob`, or directory listing before rejection. Do not point fixtures at real dataset paths, even as negative-test values.

Synthetic tests now exercise the isolated lexical gate using temporary paths: missing policy/authorization/verifier, approved and unapproved roots, protected root/child/ancestor, relative and absolute parent traversal, dot and drive-letter normalization, component-case alias rejection, ambiguous verifier output, and rejection before the synthetic discovery callback. The symlink test was skipped because directory symlink creation is unavailable in this sandbox. Tests do not validate Windows handle/reparse-point enforcement, adapter integration, or any real dataset path. The earlier Phase I inventory and Scapy-present capture incidents remain unresolved; this implementation supplies no new evidence about either incident.

## Implemented primitive and remaining enforcement boundary

`authorize_dataset_root()` is intentionally a pure pre-discovery lexical gate. It normalizes drive-letter spelling, rejects relative/drive-relative, UNC/device namespace, parent traversal, alternate data streams, and trailing-dot/space components; rejects any case-insensitive component overlap with protected roots; and then requires exact configured root spelling before calling the supplied identity verifier. The function itself does not call `exists`, `stat`, `resolve`, `open`, globbing, or directory listing. Its return value contains a `RootIdentityEvidence` report supplied by a caller; it is not proof of filesystem identity or an authorization token.

This primitive cannot determine whether a drive letter is mapped, identify a volume, detect a junction/symlink hidden inside an otherwise approved path, or determine per-directory case-sensitive behavior. The current helper now requires a `RootIdentityEvidence` record with non-empty identity strings and declared reparse/case checks; this is only a report-shape check. A caller can construct that record, and a verifier can lie. It is not cryptographic, OS-attested, or handle-bound. The synthetic verifier is not production authorization. No adapter accepts `AuthorizedDatasetRoot`, and direct adapter discovery remains possible. Until real roots and a reviewed Windows verifier are supplied, the helper is not a real-data security boundary.

### Current helper contract and limitations (2026-10-27)

The helper rejects absent policy, empty approved-root mapping, missing protected-root tuple, unknown or malformed dataset IDs, malformed/relative/UNC/device/parent-traversal paths, protected overlaps, overlapping approved roots, broad drive roots, non-exact component spelling, and absent or malformed verifier evidence before any file discovery. It performs lexical operations only and calls no filesystem query. Its protected-overlap test is component-based and case-folded, not a string-prefix test. Dot components are normalized by `PureWindowsPath`; parent components are rejected. Drive-letter case is normalized while component spelling is preserved.

The `RootIdentityEvidence` dataclass distinguishes the expected report fields from verified OS identity. The helper cannot enforce the truth of its booleans or identity strings. There is no implementation that verifies volume identity, reparse points, junctions, mapped drives, per-directory case sensitivity, or Windows final-path identity. The returned `AuthorizedDatasetRoot` is an ordinary constructible value without a held OS handle. Treating it as a security token would be a failure mode. A future production implementation must replace this evidence-only contract with reviewed, no-follow handle-based validation and prevent caller construction/bypass at adapter boundaries.

Adapter integration remains intentionally absent. `DatasetAdapter.audit()` and adapter `get_source_files()` methods can be called directly; several use `glob()` or `rglob()` and the base constructor accepts caller-provided paths. Adapter `stream_canonical_flows()` implementations also call their own `get_source_files()`, so guarding only `audit()` or the Stage 3 caller would be bypassable. The smallest future shared boundary is a base-class access context issued only by the approved policy/OS verifier, required by every public audit, discovery, and streaming entrypoint before filesystem access. Subclasses should implement private/protected discovery and streaming hooks that receive that context, never a caller-selected root; default adapter construction and Stage 3 must obtain the same context before invocation. Python visibility alone is not a security boundary, so the context must be bound to validated OS handles/identity and the supported call paths must be tested for rejection-before-discovery.

Do not implement that integration until owner-approved roots, protected-root scope, Windows alias/volume/case decisions, and a trustworthy handle-based verifier exist. Then test the shared boundary synthetically and statically review every direct subclass entrypoint before any authorized real-data validation. Until those prerequisites are met, real-data adapters remain unauthorized by policy and must not be run for provenance work.
