# `doctor.py` at `main` `5694ab45` — two defects inside its own scope, and a coverage map for everything else

Reproduce with `raw/probe_doctor_coverage.py`; raw output in
`raw/raw-doctor-coverage.txt`. **19 checks, 0 unexpected.** Section A is the
positive control.

`efo doctor` is the only workspace-wide health command in the CLI, and
`README.md:381` lists it under "Recovery and audit" without enumerating a
scope. So this write-up is careful about the difference between *doctor does
not cover X* — which is not a defect, because nothing promises it does — and
*doctor's own checks are wrong*, which is what the two findings below are.

## What holds

| Probe | Observed |
|---|---|
| **positive control** — a clean workspace | `healthy=True` |
| a credential planted in a task description | `healthy=False  secrets=['api_key']` |
| a projection edited on disk | `healthy=False  error=T1: projection differs from ledger` |
| a projection deleted | `healthy=False  error=T1: projection missing` |
| an expired lease | `healthy=False  expired=['T1']` |
| a missing agent report directory | `healthy=False` |

Each of doctor's four checks fires, and each names what it found.

## Finding 1 — the documented repair path launders a truncated ledger

Issue #9 showed that a truncated ledger verifies clean *if* the projections are
rolled back to match. Left alone, the mismatch **is** caught — that is the one
state where a missing tail is visible:

```
dropped event 8 (task.claimed), projection untouched
doctor              -> healthy=False  error=T1: projection differs from ledger
audit_projections() -> IntegrityError: T1: projection differs from ledger
```

`audit_projections(repair=True)` refuses and redirects the operator to
`repair_projections(actor=...)` (`workspace.py:1475-1478`). That is the
documented remedy. Running it:

| Step | Observed |
|---|---|
| `repair_projections(actor="antigravity")` | `repaired: ['T1']` |
| `doctor` afterwards | **`healthy=True`** |
| the task now reads | `state=pending` — the pre-claim state |
| the dropped event | `task.claimed present: False` → `['task.created']` |

The repair does exactly what its name says: it rebuilds the projection from the
ledger. But the ledger is the thing that was tampered with, so rebuilding *from*
it completes the tamper. One command turns the single detectable symptom of a
missing tail into a workspace that reports healthy, silently reverting a real
`task.claimed` — and it reports `repaired: ['T1']`, which reads as a fix.

`_audit_projections` calls `self.ledger.verify()` first (`workspace.py:1497`),
so it is not that the chain went unchecked. It is that `verify()` cannot see a
missing tail — #9's finding — and repair trusts it completely.

### Suggested fix

Repair is the wrong response to a *disagreement* when the ledger cannot prove
its own completeness. Two changes, either of which helps:

- Persist `{"events": N, "head": H}` after each append (the same anchor #9
  proposes) and refuse to repair when the count regresses. Repair after
  accidental loss still works; repair onto a shortened chain does not.
- Make repair direction-aware: rebuilding a **missing** projection is safe,
  because the ledger is strictly more information than an absent file.
  Overwriting a projection that exists and *disagrees* is a destructive
  operation and should require the operator to see both sides first —
  `repair_projections` currently prints neither.

## Finding 2 — the secret scanner misses the most common credential spelling

`_scan_secrets` looks for `\b(password|passwd|pass|token|secret|api[_-]?key)\b`
followed by a value. `_` is a word character, so `\b` does not fire inside an
underscore-joined name. Measured end to end, through `create_task`, in the one
directory doctor does scan:

| Task description | Observed |
|---|---|
| `api_key=AKIA1234567890EXAMPLE` | `healthy=False  secrets=['api_key']` |
| `export AWS_SECRET_ACCESS_KEY=…` | **`healthy=True  secrets=[]`** |
| `export GITHUB_TOKEN=…` | **`healthy=True  secrets=[]`** |
| `export OPENAI_API_KEY=…` | **`healthy=True  secrets=[]`** |
| `export DB_PASSWORD=…` | **`healthy=True  secrets=[]`** |

Those four are the standard environment-variable spellings for exactly the
credentials this workspace handles. Against `SECRET_RE` directly:

```
MATCHED  api_key=AKIA1234567890EXAMPLE
MATCHED  password: hunter2
MATCHED  token = ghp_0123456789abcdefghij
missed   AWS_SECRET_ACCESS_KEY=wJalrXUtnFEMIK7MDENGbPxRfiC...
missed   Authorization: Bearer eyJhbGciOiJIUzI1NiJ9.eyJzdW...
missed   ghp_0123456789abcdefghijklmnopqrstuvwxyzAB
missed   sk-ant-api03-AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA...
missed   -----BEGIN OPENSSH PRIVATE KEY-----
```

The last four are a keyword-free class the current design cannot reach, and I
am not reporting a keyword scanner for missing them. The underscore cases are
different: the keyword **is present**, and only the boundary assertion excludes
it.

This matters because of what the finding is *for*. When it fires, doctor emits
*"Plaintext secret-like values were found; move credentials to environment
variables or an OS secret store before publishing or mirroring this
workspace."* An operator running `efo doctor` before publishing a workspace,
seeing a clean scan, would reasonably conclude no obvious credential is sitting
in a task description. For the four spellings above, that conclusion is wrong.

### Suggested fix

Replace the leading `\b` with a boundary that treats `_` as a separator —
`(?:^|[^A-Za-z0-9])` — which picks up all four without touching the existing
matches. Optionally add prefix patterns for the keyword-free shapes
(`ghp_`, `sk-ant-`, `AKIA`, `-----BEGIN … PRIVATE KEY-----`), though that is a
different kind of check and belongs in its own pass.

## Scanner coverage, measured — reported as a map, not a defect

`doctor.py:196-201` points the scanner at the config, `agents/*.json` and
`tasks/*.json`. All three are ledger-bound, so a credential has to arrive
through the API rather than by editing the file:

```
tasks/T1.json        via create_task(description=...)  -> SCANNED
.efo/workspace.json  via initialize(name=...)          -> SCANNED
agents/claude.json   no free-text field is reachable through the API;
                     _scan_secrets on a copy -> ['api_key']
```

Everything else is outside the scan, verified by planting the same string and
confirming the scanner itself *would* have matched it:

```
shared/FACTS.md            doctor: not scanned   scanner alone would match: True
reports/claude/notes.md    doctor: not scanned   scanner alone would match: True
runs/claude/stdout.txt     doctor: not scanned   scanner alone would match: True
submissions/T1/bundle.json doctor: not scanned   scanner alone would match: True
archive/T1.json            doctor: not scanned   scanner alone would match: True
```

`runs/<agent>/…/stdout.txt` is where a command adapter's child process output
lands, which is a realistic place for a leaked token — though `initialize`
writes `runs/.gitignore` with `*`, so it is at least not committed. None of
this is filed: the legacy auditor scans `shared/` and the broker one does not,
and no document claims otherwise.

## Coverage map for the open findings

Measured verdicts, recorded so the boundary is written down somewhere:

| End state | `doctor` |
|---|---|
| #7 — a ten-year lease | `healthy=True` |
| #9 — truncation with the projection rolled back | `healthy=True` |
| #10 — a tampered submission bundle | `healthy=True` |

`audit_workspace` returns
`['agent_directories', 'expired_leases', 'integrity', 'secret_findings', 'status']`.
The workspace also exposes `audit_independence` — the check that would speak to
issue #3 — and doctor does not call it. Since nothing documents doctor's scope,
none of this is filed; it is here so the next person does not have to
rediscover it.

## Harness bug, caught before any conclusion

One, mine. The first version of section C planted secrets by editing
`agents/claude.json` and `.efo/workspace.json` directly, then read "not
scanned". Both files are ledger-bound, so the edits aborted `audit_workspace`
before the scan ran — I was measuring an integrity abort and would have
reported two false gaps. Rewritten to plant through the API where that is
possible, and to separate *scanner capability* from *scanner reachability*
where it is not. Only the corrected run is reported.

## Scope

`doctor.audit_workspace`, `_scan_secrets`, `SECRET_RE`,
`repair_projections` / `_audit_projections`. Not examined:
`audit_legacy_workspace` beyond noting that it scans `shared/`, and the
`legacy_write_test` path.

Pre-registered permissions unchanged: `gpu: false`, `network: false`,
`performance_metrics: false`; gates `allow_skips: false`,
`require_validation: true`, `require_known_answer_check: true`,
`require_independent_verification: true`.

**SUBMITTED, not VERIFIED.**

| Artifact | SHA-256 |
|---|---|
| `raw/probe_doctor_coverage.py` | `66a15f74ad67ee1e75c202872a55a95702522ab22d3c4dc53e26189a4b65b7d0` |
| `raw/raw-doctor-coverage.txt` | `cd2436d74ee4bdb00efbf8ccd99b6dae1c514422f0a4a967f1469e421cdfc93e` |
