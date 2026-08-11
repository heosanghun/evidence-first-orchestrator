# `archive.py` at `main` `5694ab45` — every copy guard holds; nothing ever looks at the copy again

Issue #9 closed with `archive.py` named as the one thing still open: *"what
archival does to the chain is still open."* This is that measurement.

Reproduce with `raw/probe_archive_bundle.py`; raw output in
`raw/raw-archive-bundle.txt`. **34 checks, 0 unexpected.** Section A is the
positive control — an honest `claim → start → submit` must archive cleanly
before any refusal below means anything — and every rejection is asserted on
its *message*, by substring.

## The copy guards hold

| Probe | Observed |
|---|---|
| **positive control** — an honest submit | `retained=4 external=0`, report + manifest + artifact + raw output |
| every file stored under its own content hash | `1ef9875005db492e…_artifact.txt`, `f51bbdf181bfee70…_report.md`, … |
| evidence swapped between hashing and archival | `EvidenceError: Evidence changed while being archived` |
| a source that no longer exists | `EvidenceError: Evidence disappeared before archival` |
| a negative byte bound | `EvidenceError: max_artifact_bytes cannot be negative` |
| a destination already holding different content | `EvidenceError: Archived evidence path already has different content` |
| a task id that would escape the submissions root | `ConfigurationError: Task id must start with an alphanumeric character` |

`docs/ARCHITECTURE.md:138-144` is accurate as written: reports and manifests are
always copied, artifacts and raw outputs are copied up to the limit, and the
re-hash after copying does reject mutation between validation and archival.

Filename handling is sound. The archived name comes from `path.name`, so no
separator can survive, and `_safe_name` collapses the rest:

```
_safe_name('...')            -> 'artifact'
_safe_name('..')             -> 'artifact'
_safe_name('x;rm -rf /.txt') -> 'txt'
```

One note rather than a finding: the destination-collision guard is nearly
unreachable through this API, because the destination path already embeds the
content hash — `files/<sha256>_<name>`. It can only fire for a writer coming
from outside `archive_evidence_bundle`. That is defence in depth, and it works.

## The finding: retention has no verifier

`archive.py`'s own first line calls this *"Immutable-ish local retention"*. It
is neither immutable nor checked. The ledger holds every per-file hash — the
data needed to check is already there:

```
ledger: report     f51bbdf181bfee70... retained=True
ledger: manifest   6ca3b7ca12554fd4... retained=True
ledger: artifact   1ef9875005db492e... retained=True
ledger: raw_output 877905694edf8b70... retained=True
```

Rewrite the archived artifact in place, and the recorded hash and the on-disk
hash diverge with nothing to say so:

```
recorded sha = 1ef9875005db492e...
on-disk sha  = 2489b7e1ba304ad1...
```

| After tampering | Observed |
|---|---|
| `ledger.verify()` | **accepted** — `{'valid': True, 'events': 13, 'signed': True}` |
| `get_task("T1")` | **accepted**, `state=submitted` |
| `audit_projections()` | **accepted**, `mismatches=[]` |
| `doctor` | **`healthy=True`** |

Replacing `bundle.json` with `{"files": []}` — the index of what was retained —
is likewise invisible. So is deleting the entire bundle directory:

| After `rm -rf` of the bundle | Observed |
|---|---|
| `ledger.verify()` | **accepted** — same head, `events: 13` |
| `get_task("T1")` | **accepted**, `state=submitted` |
| `doctor` | **`healthy=True`** |

Every public `Workspace` method that could plausibly re-check it, enumerated by
the probe rather than by reading:

```
['archive', 'audit_independence', 'audit_projections',
 'authorize_proxy_submission', 'verify']
```

None of them reads `submissions/`. `audit_workspace` (`doctor.py:162-211`)
covers the config, the agent records, the task projections, expired leases and
a secret scan; the string `submissions` does not appear in `doctor.py` at all.

### The same shape in `archive/`

`Workspace.archive()` (`workspace.py:1435`) writes a second copy of the
projection to `archive/<task_id>.json`. Nothing reads it back — the probe
enumerated every public method whose name touches it:

```
public Workspace methods touching archive/: ['archive']
```

Rewriting that copy to `state: verified, owner: someone-else` leaves `get_task`
returning `archived` and `doctor` `healthy=True`. The live projection is
correctly cross-checked; its archived twin is not covered by anything.

### What the fix costs

Small, because the expected hashes are already signed into the ledger. An
`audit_archive()` that walks `submissions/<task>/<attempt>/*/bundle.json`,
recomputes each `retained: true` file, compares against the shas in the
`task.submitted` / `task.verified` events, and cross-checks
`archive/<id>.json` against the projection — then wire it into
`audit_workspace` beside `audit_projections`. That closes accidental loss and
any writer with partial access. It does not close a writer with full workspace
access, which needs the external anchor `README.md:424` already recommends.

## What is documented, and therefore not reported as a defect

An artifact larger than the retention limit is **not** copied. Measured through
the real API with a 50 MiB + 1 artifact:

```
artifact   retained=False size=52428801 archive_path=None
-> retained=3 external=1, submission ACCEPTED
```

Deleting that artifact afterwards leaves `get_task` clean, `doctor healthy=True`,
and a verifier able to accept the task. That is exactly what `README.md:392-394`
describes — *"Larger artifacts such as checkpoints stay external; their absolute
path, byte size, and SHA-256 remain in the signed record"* — so it is recorded
here as measured behaviour matching the documentation, not as a finding.

## A premise of mine that was wrong, and the result is in the code's favour

I assumed the retention limit could be lowered by editing
`.efo/workspace.json`, and built the section that way. It cannot:

```
POSITIVE CONTROL - can the bound be lowered by editing the config?
  -> rejected (IntegrityError: Workspace configuration differs from the signed ledger)
public Workspace methods that could change it: []
```

The workspace configuration is bound to the signed ledger, and no API changes
`max_evidence_bytes` after `initialize`. The section was rewritten to use a
genuinely oversized artifact, and the corrected run is the one reported.

## Harness bugs, caught before any conclusion

Three, all mine, only the corrected run reported. `claim` returns
`{"task": …, "lease_token": …}`, not a nested `lease` dict. The manifest schema
is `raw_output_path` / `raw_output_sha256`, not a nested `raw_output` object —
my first fixture silently declared no raw output, so section A read
`retained=3` and I would have mistaken that for archival dropping raw outputs.
And five expectation strings in section E named the wrong refusal (`Invalid
transition` for `cannot transition pending -> archived`, `Only the
orchestrator` for `Only orchestrator 'antigravity' may perform this action`).
All were correct refusals mislabelled by me.

## Severity, plainly

This needs filesystem write access to the workspace, and `SECURITY.md:34`
already says application-level ownership does not stop a process editing files
directly. So the exposure sits adjacent to a stated limitation, and this is a
documentation-and-hardening gap, not a new vulnerability class — the same
posture as issue #9.

What makes it worth a line in the failure table: `submissions/` is the
*retention* mechanism, the thing that exists so evidence outlives the run, and
it is the one part of the workspace with no integrity check at all — not even
the projection cross-check that does catch tampering under `tasks/`. An
operator reading "Immutable-ish local retention" and running `efo doctor` would
reasonably believe the archive is covered. It is not.

## Scope

`archive.py` in full, `Workspace.archive()`, and the reach of
`doctor.audit_workspace` over `submissions/` and `archive/`. Not examined:
`adapter.py`, `proxy_submit`'s own archival path (`workspace.py:1220`, which
adds a forced `provenance_manifest`), and concurrent archival of the same
bundle.

Pre-registered permissions unchanged: `gpu: false`, `network: false`,
`performance_metrics: false`; gates `allow_skips: false`,
`require_validation: true`, `require_known_answer_check: true`,
`require_independent_verification: true`.

**SUBMITTED, not VERIFIED.**

| Artifact | SHA-256 |
|---|---|
| `raw/probe_archive_bundle.py` | `2dd7932c2db2e3311f51fd0dc81ece6e1b3d1a09390b0b6536406b8c191f3709` |
| `raw/raw-archive-bundle.txt` | `912aaa02fd25c34e61a1251b41cd4bef9d94f97df31c1f00bcbd355b5b22f210` |
