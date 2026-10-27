# Windows Root-Handle Threat Model (Phase V)

## Scope and trust boundaries

This document records the threat model for Phase V identity observation and the subsequent API-contract review. It treats the Phase U child-relative open as a low-level operation only: a supplied parent handle is not proof that the handle refers to an approved root, and no production provider currently has authenticated owner approval or approved research roots.

The implemented primitive observes metadata attached by Windows to an already-open directory handle. The acquisition interface returns `UNAVAILABLE` without coercing or opening its inputs. Neither path-based root acquisition nor dataset authorization is implemented or connected to research-data access. Real-data authorization remains disabled.

## Separate security claims

- **Lexical path check:** can reject malformed or relative path syntax. It does not establish which filesystem object a name reaches.
- **Directory-handle identity:** volume serial and file-index information returned for a live handle identify the object observed by the OS at query time. They do not prove owner approval, path provenance, or dataset identity.
- **Reparse-point check:** observing the final opened object as a reparse point can reject that object. It cannot prove that no earlier path component traversed a junction, symlink, mount point, or other alias.
- **Handle binding:** a live handle continues to refer to its opened object across a rename, subject to OS semantics. That object is not thereby an approved root.
- **File/link identity:** an observed file identifier or link count is not a complete defense against hard links, namespace changes, all races, or malicious filesystem behavior.

## Threats and current limits

| Area | Threat / required behavior | Phase V position |
|---|---|---|
| Local drive paths | Drive-letter case, `.`/`..`, device namespaces, and alternate names can make strings ambiguous. | No path-based acquisition is offered. Lexical normalization is not treated as identity proof. |
| UNC/network paths | Server/share aliases, authentication, remote filesystem semantics, and changing network targets complicate identity. | Unsupported for authorization; any future provider must reject unless explicitly reviewed and approved. |
| Mapped drives | A drive letter may map to a different network target or change over time. | No equivalence between mapped-drive and UNC names is assumed. |
| Volume identity | Volume serial plus file ID is OS-observed metadata, not an owner-approved pin or cryptographic identity. | Observation only; no authorization conclusion. |
| Junctions/reparse points | A final component can be inspected, while an intermediate component may have redirected traversal. Reparse tags vary. | No whole-path no-reparse guarantee. Full path traversal enforcement remains unimplemented. |
| Symlinks | A path component may redirect before a handle is returned. | No path acquisition; synthetic symlink checks are environment-dependent and do not prove general safety. |
| Hard links | Multiple names can refer to one file; link counts can change and directory identity does not establish content provenance. | Not a complete hard-link defense. |
| Case sensitivity | Windows directories may enable per-directory case sensitivity; case-preserving names do not imply case-insensitive identity. | No case-folded path comparison is used as security evidence. |
| Rename/replacement | A name can be replaced after checking; an open handle remains bound to the opened object, not the name. | Handle observation is tied to the supplied live handle only. No check-then-open authorization. |
| Parent traversal | Opening a root by a full path traverses ancestors; final-component flags do not prove every ancestor was traversed safely. | No production root opener. A future design must open from a trusted volume/root handle component by component and retain handles. |
| TOCTOU | Name-based checks followed by later opens permit substitution. | No authorization uses a prior path check. A future boundary must perform operations relative to retained, validated handles or use a reviewed equivalent. |
| API errors | Access denied, unsupported filesystems, unexpected statuses, and partial API support must not fall back to weaker checks. | Stable fail-closed results; no portable fallback is considered equivalent. |
| API compatibility | `ctypes` structures, flags, and native calls can differ by Windows version/architecture and filesystem. | Current code does not claim OS-version or filesystem coverage; independent Windows security review is required. |

## Authoritative API documentation review

Microsoft's user-mode [`NtCreateFile` documentation](https://learn.microsoft.com/en-us/windows/win32/api/winternl/nf-winternl-ntcreatefile) documents relative names through `OBJECT_ATTRIBUTES.RootDirectory`, and describes `FILE_OPEN_REPARSE_POINT` as opening the final reparse-point file itself without normal final-component processing. Its `Attributes` parameter description says the supported values can be zero or `OBJ_CASE_INSENSITIVE`. The general [`OBJECT_ATTRIBUTES` documentation](https://learn.microsoft.com/en-us/windows/win32/api/ntdef/ns-ntdef-_object_attributes) separately describes `OBJ_DONT_REPARSE` as failing if reparses are encountered while parsing the object name. The published pages therefore do not provide an unambiguous user-mode `NtCreateFile` contract for combining `RootDirectory` and `OBJ_DONT_REPARSE` to reject every intermediate reparse point.

The [`CreateFileW` documentation](https://learn.microsoft.com/en-us/windows/win32/api/fileapi/nf-fileapi-createfilew) describes `FILE_FLAG_OPEN_REPARSE_POINT` for opening the final symbolic link itself; it does not establish that earlier path components were not traversed through aliases. The documented ability to open a directory handle does not supply a trusted initial volume-root handle or owner-approved root identity. No Q&A report or synthetic test is treated as a substitute for a normative API contract or security review.

Given this gap, Phase V does not implement a path opener or component walk. A future provider must first identify a documented, supported API sequence that starts from an independently trusted anchor, refuses reparse traversal at every component, preserves those handles, and has a reviewed namespace/volume policy. If that sequence cannot be established for the supported Windows/filesystem matrix, acquisition must continue to return `UNAVAILABLE`.

## Phase V implementation boundary

The implementation accepts an already-open handle for metadata observation, reports only an `OBSERVED_UNVERIFIED` result, and leaves handle ownership with its caller. `WindowsRootHandleAcquisitionProvider.acquire()` currently returns `UNAVAILABLE / SAFE_ACQUISITION_UNAVAILABLE` and performs no path coercion or filesystem operation. The production authorization provider returns a stable denial because approved roots and authenticated approval evidence are absent. A caller-created observation, identity tuple, or schema-valid policy document cannot authorize access.

Synthetic tests may acquire handles only for temporary test-owned directories. Passing those tests establishes only behavior on the test host and synthetic objects. It does not establish safe traversal from an owner-approved root.

## Requirements before real-data authorization

1. Owner-approved logical dataset identities, canonical roots, protected-root scope, permitted operations, and policy revision.
2. An authenticated approval source and trust-anchor/key lifecycle; schema validity alone is insufficient.
3. A reviewed Windows implementation that binds each traversal component to retained handles, handles reparse tags and volume identity, and defines local/UNC/mapped-drive policy.
4. TOCTOU, rename, replacement, hard-link, case-sensitive directory, junction, and filesystem compatibility review and tests on supported Windows versions.
5. Integration at every direct adapter, split loader, training/evaluation, checkpoint, and child-process boundary; dispatcher-only enforcement is insufficient.
6. Independent security review and owner approval before enabling any real-data access.

Until these prerequisites are met, real-data authorization must remain denied.
