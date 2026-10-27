# Windows filesystem authorization and shared access-boundary specification

**Status:** design plus fail-closed lexical/schema primitives and a low-level handle-relative child-file primitive in `src/iot_ids/provenance/windows_access.py` and `windows_handle.py`; no OS-bound authorization provider or production enforcement exists. The policy provider validates lexical path syntax and schema shape, performs a component-aware lexical protected-root comparison, and always refuses access. The handle helper operates only from an already-open directory HANDLE and does not establish its authorization. This specification does not approve a dataset, root, protected scope, or real-data operation. The provenance preflight still returns `REAL_DATA_AUTHORIZATION_UNAVAILABLE` for a real-data decision.

## 1. Security objective and trust model

Authorization must bind an owner-approved logical resource and operation to the exact filesystem objects that will be read or written. A JSON policy, valid schema, normalized path, caller-provided identity string, `AuthorizedDatasetRoot`, open/closed status flag, or matching digest is not by itself authorization.

The trusted chain is: externally authenticated owner approval → validated immutable policy revision → lexical deny/allow classification → OS-observed filesystem identity → access through the same verified OS handles → scoped access context. If any stage is unavailable, contradictory, unsupported, or cannot be bound to the next stage, refuse access. The provider must never silently downgrade to path-string checks or caller-supplied identity evidence.

## 2. Owner-supplied policy contract

The structural contract is [dataset_access_policy.schema.json](dataset_access_policy.schema.json), with a deliberately non-authorizing [draft example](dataset_access_policy.example.json). The example contains only null roots, no operations, no approvals, and `example_only: true`; no dataset is marked approved.

Policy semantics required before activation:

- `policy_revision` is unique, immutable, and monotonically advanced by the owner. `filesystem_policy_version` names the reviewed enforcement semantics.
- Dataset map keys and each record's `dataset_id` must match exactly. Dataset roots authorize only the listed operations for that dataset. A dataset root does not implicitly authorize model/checkpoint or output roots.
- `artifact_roots` is a separate map for checkpoint reads/writes and experiment-output writes. The provider must reject an operation when its resource root or operation is missing.
- `protected_roots` has an owner-defined coverage (`exact`, `descendants`, or `ancestors_and_descendants`). Protected roots take precedence over approved roots. Any overlap, duplicate identity, or unclassified alias is a policy conflict and blocks activation.
- An `ACTIVE` schema-valid file is still not approval. A trusted verifier must canonicalize and authenticate the signed policy payload against an owner/admin trust anchor supplied out of band; validate signature, signer authority, revision, timestamp/expiry and revocation; and bind the signature to every dataset root, artifact root, protected root, operation, identity pin, and policy version. `signature_reference` is a locator, not a signature. The trust-anchor store and signature format remain owner/admin decisions.
- Missing, expired, revoked, malformed, contradictory, unsupported, or unauthenticated entries block the complete affected policy. No partial activation and no fallback to the working directory, environment variables, CLI roots, or old policy revision.

The schema checks shape only. It does not check `dataset_id`/map-key equality, root overlap, actual path semantics, approval authenticity, signer authority, expiry/revocation, or whether the recorded file identities still exist. Those checks belong to the independent policy and OS provider.

## 3. Windows path and filesystem identity decision sequence

### 3.1 Logical identity and policy selection

The caller supplies a logical dataset/resource ID and requested operation. The caller does not select an arbitrary root. The provider finds exactly one active signed entry; it rejects absent IDs, duplicate/overlapping roots, unsupported operations, stale policy revisions and ambiguous policy matches before filesystem traversal.

### 3.2 Lexical input checks

Before opening or querying a path, validate that the configured root is absolute and has a supported spelling. Reject relative and drive-relative paths, `.`/`..` ambiguity (normalization rules must be versioned), device namespace paths, alternate data streams, invalid/reserved components, unsupported environment expansion, and unapproved aliases. Keep both the owner-recorded spelling and a parsed component sequence; string-prefix checks are prohibited.

Local drive paths are the only candidate default until owner/admin approval. UNC paths and mapped drives are unsupported by default. If later allowed, the owner must specify the server/share identity, authentication context, remote filesystem guarantees, reconnect behavior, and how a drive letter maps to that canonical share/volume. A drive letter alone is not a volume identity and can be remapped. If a volume GUID or other canonical device identity cannot be mapped and pinned, reject.

Normalize drive-letter case for lexical comparison, but preserve component spelling. Perform conservative case-folded component overlap checks against all protected roots before any handle access. Exact owner-configured spelling is required for allow matching. Windows supports per-directory case-sensitive behavior, so a provider must query and verify case mode for each traversed directory; if it cannot prove lookup semantics compatible with the policy, reject. A case-insensitive comparison is a deny-list precaution, not proof that two names identify one object.

### 3.3 Protected-root overlap

Apply protected-root checks twice:

1. Pure lexical component comparison against the signed protected-root set, rejecting equality, protected descendants, or ancestors according to each root's declared coverage. This occurs before filesystem queries.
2. OS-identity checks while traversing handles. Verify volume/file identities and component ancestry against approved and protected identities. Do not follow a reparse point to decide whether it is safe. Any unknown parent, alias, or identity relation blocks access.

If protected scope includes individual files, policy must pin their filesystem identities or use an explicit protected-file list. Do not probe a protected target to resolve an alias.

### 3.4 OS-bound traversal and alias handling

`Path.resolve()`, `Path.is_relative_to()`, `PureWindowsPath`, `exists()`, `lstat()`, `FILE_ATTRIBUTE_REPARSE_POINT` observed before open, and final-path string comparisons are useful checks but do not alone bind later access to the same object.

The provider must use a Windows-native reviewed component-walk implementation. Candidate design: open each directory component relative to an already-held parent directory handle, request reparse-point-safe opens, and reject any reparse encountered; obtain volume serial and file ID from the resulting handle, verify expected identities and case semantics, and retain handles. The exact native API/helper and supported filesystems require platform/security review. `CreateFile`'s `FILE_FLAG_OPEN_REPARSE_POINT` addresses a reparse point at the opened component; callers must not assume it makes an entire multi-component path traversal safe. Handle-relative native opens and no-follow semantics must be independently validated.

Junctions, symbolic links, mount points, cloud/file-system filter reparse tags, and unknown reparse tags all fail closed. Do not call a path-based `open()` after checking the handle. For regular files, detect hard-link ambiguity where the filesystem exposes a trustworthy link count; where safe containment cannot be established, require an approved file-ID allowlist or refuse the operation. A directory's path containment does not prevent an in-root hard link from naming file content also reachable outside the root.

Drive aliases, 8.3 short names, UNC/mapped aliases, volume mount points, and case aliases must either resolve to an owner-pinned volume+file identity through the approved handle chain or be rejected. The provider must not infer aliases by probing arbitrary or protected paths.

### 3.5 TOCTOU and access-context lifetime

The provider must hold the verified root handle and open descendants relative to verified parent handles. Reads/writes operate through the returned file handles, not by reopening a previously checked string path. A successful check followed by a path-based parser open is a TOCTOU regression. Root/file replacement, rename, reparse retagging, or volume remapping must not redirect an already-open handle to a different object; if a filesystem/API cannot provide that guarantee, it is unsupported.

The final `AuthorizedAccessContext` is opaque, non-serializable, process-bound and owns the OS handles. It carries policy revision, logical resource ID, allowed operations and verified OS identities as metadata, but metadata alone is not the authority: open handles are. Contexts expire on close, process exit, policy revocation notification, or loss of required handle guarantees. Never pass a plain path or identity string as a substitute. For multiprocessing, either broker all file operations through the process holding the context or explicitly duplicate restricted handles and revalidate them in the child; an environment variable or pickled Python object is not authorization.

Prefer direct parsing from a safe handle-backed stream. If a library only accepts pathnames, do not pass the original research path after validation. A private, access-controlled staging copy made by reading the already-open authorized handle is a possible fallback only after separate approval of storage, cleanup, atomicity, and leakage behavior; otherwise that library path is unsupported.

If signature verification, volume identity, handle-relative no-follow traversal, file identity, case-mode checks, hard-link policy, or handle-backed parsing is unavailable, the provider must return a stable refusal and perform no content reads.

## 4. Shared access-boundary design

The minimum future architecture has four layers:

1. **Policy loader/verifier:** reads the explicit policy file, validates the schema, verifies detached signed approval with an out-of-band trust anchor, checks revision/expiry/revocation, rejects contradictions, and produces an immutable internal policy.
2. **OS resource provider:** maps logical resource+operation to the approved root; performs lexical protected/allow checks; walks and holds verified Windows handles; returns an opaque `AuthorizedAccessContext`. It never returns an unrestricted root path as the authorization token.
3. **Access broker:** provides `open_child(relative_name, operation)` and controlled directory enumeration through the held context. It checks operation scope, protected identity, file type/link policy and policy revision at every access. Relative names come from allowed discovery within the authorized root, not arbitrary manifest paths.
4. **Consumers:** adapters, split loaders, model/checkpoint loaders, trainers, evaluators, benchmarks and output writers accept the access context and file-handle streams. Each public operation refuses missing, expired, wrong-resource, wrong-operation or wrong-process contexts before the first data/model/output filesystem access.

`DatasetAdapter.__init__` must not authorize a raw `Path`; constructors should receive a context or be inert until one is supplied. `audit()`, every `get_source_files()`/discovery method, and every streaming method must use the same broker. Subclass implementations should be private hooks taking broker-issued entries/handles, not call `glob()`/`rglob()` on raw roots. `CICIoT2023Adapter` and all sibling adapters must be migrated together. `src/iot_ids/data/audit.py` and `p1-audit-datasets` must require the context before `run_audit()` creates outputs or asks adapters to discover files.

Split loaders (`scripts/03_create_splits.py`, `scripts/run_milestone3a.py`, `scripts/05_train_models.py`, and `scripts/train_{rf,mlp,ae}.py`) must use scoped split-file streams. Checkpoint and output operations use separate artifact-root contexts. `src/iot_ids/training/train.py`, `src/iot_ids/registry/manager.py`, `src/iot_ids/runtime/engine.py`, and `IDSPredictor.from_artifact()` must not path-load before context validation.

Every direct CLI/script entrypoint must establish or receive a context before calling lower-level operations. `run_master.py` may orchestrate context creation, but cannot be the only gate: direct child invocation must refuse without independently obtaining an OS-bound context. The same applies to `iot-ids` console commands, `p1-audit-datasets`, scripts called via `python scripts/name.py`, and importable library APIs. Context propagation through subprocess should use OS-restricted handle transfer or a broker channel, never a self-asserted token string. Tests must call each direct entrypoint with absent/malformed contexts and prove rejection occurs before the first data/model/output open.

The Phase R provenance coordinator remains orthogonal: schema validation is structural; an approval verifier supplies a policy decision; the OS provider enforces object identity; digest checks are optional byte-integrity checks. No single result can replace the others. Do not wire the coordinator into production until it can consume a non-forgeable provider result bound to held OS handles and all callers are migrated.

## 5. Owner and platform decisions still required

- Owner: logical dataset IDs, exact canonical roots, protected roots and coverage, permitted read/write operations, checkpoint/output roots, approval lifecycle and retention.
- Owner/admin: whether local, UNC, mapped-drive, removable, cloud-sync, or network filesystems are permitted; trust-anchor custodians, signature scheme, expiry/revocation, emergency denial and policy revision process.
- Windows security reviewer: handle-relative no-follow API, reparse-tag behavior, volume/file ID guarantees, per-directory case queries, hard-link strategy, concurrent rename/retag race tests, process-handle transfer, and supported filesystem/OS matrix.
- Maintainers: parser/Arrow/Pandas handle-backed interfaces; worker-process strategy; output atomicity and cleanup; migration of all direct APIs and commands.
- Privacy/science owners: data-use approvals, split protocol, DP mechanism/accountant review, BCL exclusion policy, claim-specific experiment plan. Filesystem authorization does not settle these scientific approvals.

## 6. Prioritized implementation sequence

| Priority | Work | Gate |
|---|---|---|
| P0 — safe now | Maintain source-only entrypoint inventory; add schema conformance tests for the DRAFT example and reject an ACTIVE-but-unsigned example; add pure policy consistency checks and synthetic broker tests; keep real-data status permanently unavailable. | No real paths or access; tests use temporary synthetic roots only. |
| P1 — owner decisions | Approve dataset/resource IDs, canonical roots, protected scope, operations, identity pins, trust anchor, signature/expiry/revocation process and supported storage classes. | Signed owner record; no inferred roots. |
| P2 — Windows prototype | Implement a native handle-walk proof of concept and race tests for reparse, junction, mount, rename/replace, case-sensitive components, volume aliases and file IDs. Validate parser handle streams. | Windows security review; fail closed on unsupported cases. |
| P3 — shared boundary | Introduce OS-backed contexts and broker; migrate adapters, audit/discovery/streaming, split loaders, checkpoint/runtime and output paths. Require context at library APIs and direct commands. | Static call graph plus rejection-before-open tests for every direct entrypoint and subprocess path. |
| P4 — controlled synthetic qualification | Cross-platform synthetic policy/schema tests and Windows-only synthetic filesystem adversarial tests. Keep real data denied. | All required tests and independent review. |
| P5 — separately approved research | Only after all safety gates, authorize a specific protocol and dataset run; privacy specialist and scientific owners separately approve relevant claims. | Explicit written authorization and new experiment manifests; never infer historical provenance. |

This design does not resolve split provenance, formal DP guarantees, BCL evidence, historical artifact/metric linkage, manuscript authority, or the Phase I/Phase J incidents.

## 8. Phase T implementation boundary and verified limits

`windows_access.py` now represents lexical path status, policy-schema status, approval authenticity, filesystem identity, protected-root check, and access refusal as distinct result fields. Its canonical-schema validator uses the repository schema and rejects schema references that are not local JSON pointers. A schema-valid policy—including a structurally complete synthetic `ACTIVE` document with fabricated approval fields—still reports approval as `UNVERIFIED`, does not check filesystem identity, and cannot yield an access context. The module has no open/read/discovery method and is not imported by runners or adapters.

The implemented path classifier is lexical syntax only. It normalizes drive-letter case, preserves component case, rejects relative/drive-relative forms, dot or parent components, UNC/device namespaces, alternate streams, and selected ambiguous components. Protected-root comparison is component-aware and case-folded as a conservative lexical deny check. Neither result proves canonical identity, actual Windows case behavior, reparse status, volume identity, hard-link status, or resistance to concurrent replacement. Protected-root policy entries with unresolved paths remain unavailable; a lexical-clear status is not a complete protected-root clearance.

Synthetic tests exercise parsing of Windows path strings on the current Windows host and an isolated temporary-directory policy fixture. The test-local fixture is deliberately not shipped as a production provider. The directory-symlink case was skipped because the sandbox denied symlink creation, so symlink behavior was not tested. Junctions, other reparse tags, hard links, UNC/mapped-drive resolution, per-directory case flags, handle-relative opens, and path replacement/TOCTOU are not established by these tests. Missing or inaccessible objects are not opened or probed by the production placeholder; access remains refused before that stage.

No production behavior changed. Owner-approved roots/protected scope and authentic approval remain absent. A Windows security review and a separately validated handle-bound implementation are still required before integrating access into any adapter, loader, runner, dispatcher, or direct child script.

## 9. Phase U handle-bound primitive and limits

`src/iot_ids/provenance/windows_handle.py` adds `open_child_file_readonly(directory_handle, child_name)`. It accepts an existing Windows directory HANDLE and exactly one validated child component; it does not accept or resolve a path. It uses `NtCreateFile` with `OBJECT_ATTRIBUTES.RootDirectory` set to the held directory HANDLE and `FILE_OPEN_REPARSE_POINT` for the leaf. It inspects the resulting open handle with `GetFileInformationByHandle`, rejects a reparse-tagged leaf, directories, and files whose reported hard-link count is not exactly one. `WindowsReadHandle.read()` reads from that same handle and reports volume serial/file index obtained from it. Errors are stable categories without paths or native messages.

Synthetic Windows tests successfully read a temporary file via the returned HANDLE and then rename/replaced its name; the held handle continued to return the original bytes and a newly opened child returned the replacement bytes with a different file identity. This demonstrates handle binding for that tested local filesystem scenario only. Relative traversal names and missing children fail closed. The tests do not prove concurrent adversary behavior across filesystems or Windows versions.

The handle primitive is not an authorization provider. It does not verify how the directory HANDLE was obtained, compare it to an authenticated owner identity pin, verify all ancestors used to obtain it, verify filesystem type, inspect protected-root identities, or prevent every mutation of link relationships. It is not used by `WindowsAuthorizationProvider`, which remains unconditionally refusing. The test opens only directories created under `tests/unit`; production call paths are unchanged.

The leaf symlink and hard-link tests were skipped because this sandbox/filesystem denied creating those fixtures. Junctions, volume mount points, other reparse tags, path-case modes, UNC/mapped-drive behavior, ACL-denied objects, and race windows before the directory HANDLE is opened remain untested. Windows documentation describes `NtCreateFile` relative-name and `FILE_OPEN_REPARSE_POINT` behavior, but its use in this user-mode security boundary still needs independent Windows security review and compatibility testing. No guarantee should be inferred from the empirical synthetic test alone.

## 10. Phase V directory-handle observation and boundary

`src/iot_ids/provenance/windows_root.py` adds `observe_directory_handle(handle)`. It accepts an already-open HANDLE supplied by the caller, queries `GetFileInformationByHandle`, requires the observed object to have the directory attribute, rejects an object reported as a reparse point, and returns the OS-reported volume serial, file index, attributes, and link count under status `OBSERVED_UNVERIFIED`. Invalid inputs, non-Windows execution, API errors, non-directories, and final-object reparse attributes have stable typed statuses/codes without exposing raw paths or native error text. The observer neither opens nor closes the HANDLE; the caller retains lifetime/cleanup responsibility.

This is an identity observation from an open object, not a verified root identity. It does not know the name used to acquire the handle, whether ancestors traversed aliases, whether a drive is mapped, what filesystem is mounted, or whether any reported identity matches an authenticated owner-approved pin. A caller can construct an identity record, so neither the record nor `OBSERVED_UNVERIFIED` is an authorization token. `WindowsRealRootAuthorizationProvider.authorize()` unconditionally returns `DENIED / REAL_AUTHORIZATION_DISABLED`, even when passed fabricated identity or approval-like values. No path-based root acquisition was added. Production runners, adapters, and the existing `WindowsAuthorizationProvider` are unchanged.

Focused tests create native handles only for temporary directories/files under `tests/unit`. They cover a normal directory observation, a regular file rejected as a root, invalid handle input, mocked metadata API failure, and the observed identity remaining associated with a held handle after the synthetic directory is renamed and a replacement is created at the old name. The exception-path test verifies that the test fixture's caller-owned handle is closed in its `finally` block; it does not claim the observer owns handles. These tests do not prove ancestor traversal safety, reparse behavior in preceding components, hard-link or mount-point policy, a race-free root acquisition, Windows-version compatibility, or owner authorization. Reparse/junction creation and access-denied behavior were not natively tested; API failure is mocked.

The root acquisition prerequisite therefore remains unimplemented. Before an access context can be issued, the owner must supply roots/protected scope and authenticated approval, and a Windows reviewer must approve an all-component handle-walk or equivalent design that keeps validated parent handles alive through access. Final-component `FILE_FLAG_OPEN_REPARSE_POINT`, `Path.resolve()`, volume/file IDs, or this observation helper alone cannot satisfy that requirement. Real-data authorization remains unavailable.

## 11. Phase V root-acquisition API review

The user-mode `NtCreateFile` contract documents names relative to a held `RootDirectory` handle and documents `FILE_OPEN_REPARSE_POINT` for opening the final reparse-point object without normal final-component processing. Separately, the general `OBJECT_ATTRIBUTES` documentation describes `OBJ_DONT_REPARSE` as rejecting reparses encountered while parsing a name. The user-mode `NtCreateFile` page's `Attributes` description lists zero or `OBJ_CASE_INSENSITIVE`; it does not clearly establish `OBJ_DONT_REPARSE` as a supported flag for that call. The documentation is therefore insufficient to claim a supported, all-component no-reparse path walk from a user-mode initial root. `FILE_FLAG_OPEN_REPARSE_POINT` on a full path would only address final-component behavior and is not accepted as a substitute.

The code exposes `WindowsRootHandleAcquisitionProvider.acquire(supplied_path, policy_selected_root, approval_evidence)`. Its current implementation intentionally does not coerce or inspect any argument and returns `RootAcquisitionStatus.UNAVAILABLE` with `SAFE_ACQUISITION_UNAVAILABLE`, no handle, and no identity. This is a typed refusal interface, not a simulated acquisition. `observe_directory_handle()` remains a separate metadata stage for a caller-owned handle. `WindowsRealRootAuthorizationProvider` separately returns `DENIED / REAL_AUTHORIZATION_DISABLED` for every input.

No root acquisition or component walk was executed or added. Before a prototype can replace the unavailable result, Windows security review must establish a normative and supported approach for: the initial trusted volume/root anchor; all-component reparse rejection; drive/device-map and mount-point handling; identity comparison against an authenticated owner-approved root pin; component-wise handle retention; rename/replacement behavior; and supported Windows/filesystem versions. The implementation must then test those specific native behaviors on isolated synthetic trees. If no documented/supported approach exists for any required environment, that environment remains unsupported and denied.

### Claim-to-evidence review

| Claim | Implementation | Test evidence | Native vs mocked | Remaining limit |
|---|---|---|---|---|
| Root path acquisition is unavailable | `WindowsRootHandleAcquisitionProvider.acquire()` returns no handle/identity and does not coerce inputs. | Poisoned `__fspath__`, synthetic missing-path, and fabricated-approval cases return `UNAVAILABLE`. | Python test; no OS file API invoked by provider. | Does not implement acquisition. |
| OS metadata can be observed from an already-open directory handle | `observe_directory_handle()` calls `GetFileInformationByHandle` and returns `OBSERVED_UNVERIFIED`. | Temporary synthetic directory handle produces volume/file identity. | Native Windows API on the current synthetic local filesystem. | Does not prove how any ancestor was traversed or bind identity to policy. |
| Observer rejects a final object reported as reparse | It checks `FILE_ATTRIBUTE_REPARSE_POINT` on metadata returned for the supplied handle. | New directory-symlink fixture attempts to open the link itself with `OPEN_REPARSE_POINT`. | Native only if symlink creation succeeds; otherwise skipped with explicit reason. | Does not detect reparse traversal in earlier components; no general junction/mount/third-party-tag guarantee. |
| A held handle remains bound across a directory rename/replacement | The observer reads identity from the same supplied HANDLE on each call. | Test renames a synthetic directory, creates a new directory at the former name, and compares observed IDs. | Native Windows handle metadata on the current filesystem. | Demonstrates that fixture only; not a root-acquisition race test. |
| API failures fail closed without exposing raw error text | Observer maps native errors to stable codes; public result carries no exception text. | Injected `OSError` and `RuntimeError` cases return unavailable. | Mocked failures, not native access-denied evidence. | Native access-denied/API-version behavior remains untested. |
| Observed or fabricated identity cannot authorize real data | `WindowsRealRootAuthorizationProvider` always returns `DENIED / REAL_AUTHORIZATION_DISABLED`. | Missing, fabricated, and mismatched claims are denied. | Pure Python logic; no approval verifier exists. | No approved roots or authentic approval mechanism have been supplied. |

## 7. Windows implementation references

These Microsoft references describe individual API behaviors; they do not certify the proposed provider or remove the need for security review:

- [Reparse point operations](https://learn.microsoft.com/en-us/windows/win32/fileio/reparse-point-operations) and [reparse points and file operations](https://learn.microsoft.com/en-us/windows/win32/fileio/reparse-points-and-file-operations).
- [`FILE_FLAG_OPEN_REPARSE_POINT` in CreateFile](https://learn.microsoft.com/en-us/windows/win32/api/fileapi/nf-fileapi-createfilea).
- [`FILE_ID_INFO`](https://learn.microsoft.com/en-us/windows/win32/api/winbase/ns-winbase-file_id_info) identifies open files by volume serial and file ID.
- [Windows directory case sensitivity](https://learn.microsoft.com/en-us/windows/wsl/case-sensitivity).
- [`NtCreateFile` root-relative naming and reparse behavior](https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/ntifs/nf-ntifs-ntcreatefile) and [`OBJ_DONT_REPARSE`](https://learn.microsoft.com/en-us/windows/win32/api/ntdef/ns-ntdef-_object_attributes). The exact supported user-mode implementation and race properties remain to be reviewed.
