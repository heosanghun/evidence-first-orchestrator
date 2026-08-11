# The four modules with no `isinstance`: the absence is real in one, reachable in none

Reproduce with `raw/probe_unguarded_modules.py`; raw output in
`raw/raw-unguarded-modules.txt`. **21 checks, 0 unexpected.** A **map with a
near miss recorded** — no issue filed, nothing retracted.

**Scope, stated first:** 4 modules, **693** lines, **13** driven inputs, **2**
controls.

## The question

Item 51 measured that four modules hold functions and **not one `isinstance`** —
`archive.py`, `dashboard.py`, `doctor.py`, `lock.py`. Three already carry an
issue (#10, #12/#17, #19-adjacent). Item 54 asks whether that absence has a
**reachable consequence**, or whether those modules simply never touch untrusted
input.

Item 51's premise is **re-derived here**, not carried over: if a guard were
added to one of the four, the run fails and the question changes.

## Two of the four cannot see a document at all

| module | string-key subscripts | `.get()` | file reads |
|---|---|---|---|
| `archive.py` | **15** | 5 | 0 |
| `doctor.py` | **23** | 0 | **4** |
| `dashboard.py` | 0 | 0 | 0 |
| `lock.py` | 0 | 0 | 0 |

> **A `grep` for `["` finds five in `dashboard.py`.** All five are **JavaScript
> array literals** — `["Running", states.running]` — inside the embedded HTML
> string constant. Parsed, the count is **zero**; they are not Python subscripts
> at all. Never match syntax by text when the question is about syntax.

## `archive.py` — the absence is **real**

`archive_evidence_bundle` is driven directly, control first:

| input | outcome |
|---|---|
| a well-formed manifest | **accepted** — control |
| `manifest = {}` (no `sha256`) | **`KeyError`** |
| `manifest = None` | **`TypeError`** |
| `manifest['sha256'] = 123` | **`TypeError`** |
| `manifest['path'] = None` | **`TypeError`** |
| `manifest['artifacts'] = 'x'` | **`TypeError`** |
| `manifest['artifacts'] = [None]` | **`TypeError`** |
| `manifest['validations'] = [None]` | **`AttributeError`** |
| `report = {}` (no `path`) | **`KeyError`** |

**8 driven, 8 raw Python exceptions, 0 `EFOError`, 0 accepted.** The same answer
item 47 got for `util.py`: the package's own error type never appears.

## …and unreachable, at all three call sites

```
    manifest=evidence['manifest']        workspace.py:1054
    manifest=evidence['manifest']        workspace.py:1220
    manifest=verification['evidence']    workspace.py:1355
```

`evidence` is assigned from **`validate_submission`** (`:1026`, `:1141`) and
`verification['evidence']` from **`validate_manifest`** (`:1340`) — and those
two are the *only* names in `workspace.py` assigned from an `evidence.py`
validator, which the probe asserts rather than assumes. Item 51 measured
`evidence.py` rejecting with 17 `EvidenceError` sites.

So `archive.py` is **safe by construction, not by its own guarding** — the same
shape as item 48's `build_identity` returns.

## `doctor.py` — 23 unguarded subscripts, none reachable

Five tampered documents, control first:

| input | outcome |
|---|---|
| an untouched workspace | **healthy** — control |
| task record with no `state` | caught: *"C1: projection differs from ledger"* |
| task record with no `id` | caught: same |
| task `lease` replaced by a string | caught: same |
| task `state` flipped to `claimed` | caught: same |
| a rogue agent file never in the ledger | caught: *"Agent None registration differs from the signed ledger"* |

**5 driven, 0 escaped, 5 caught and reported as `healthy: false` + `error`.**

And that is *not* the handler's doing. `audit_workspace` catches
`(EFOError, OSError)` — measured, and **narrow enough that a `KeyError` would
escape**. Nothing reaches it because the **ledger signature** and the
**projection comparison** both run before any field is read, and a tampered file
fails one of them first.

Same shape as item 45's near miss: a census over syntax would flag 23 unguarded
subscripts, and every one sits behind a guard the syntax cannot see.

## The answer, and why it is not filed

- `lock.py`, `dashboard.py` — the question does not arise; **zero** document
  field reads between them.
- `archive.py` — the absence is **real** and **unreachable**.
- `doctor.py` — 23 unguarded reads, **all** behind the ledger/projection guard.

**Not filed**, on the standard items 38, 45, 47 and 53 all applied: nothing was
accepted that should not have been.

## What this does not do

- It does **not** claim the four modules are correct — only that their missing
  `isinstance` has no reachable consequence **through a document**. Programmatic
  misuse of `archive_evidence_bundle` is a different threat model and not this
  review's.
- It does **not** enumerate every tamper. Five were driven; **a tamper that
  keeps the ledger signature valid was not constructed, and whether one exists
  is unmeasured.**
- It does **not** re-run or retract #10, #12, #17 or #19.
- It does **not** touch `main`, the anchor's working tree, or another agent's
  branch. Every workspace is a `tempfile` directory, removed before the answer
  prints. No network.
- **MEASURED:** the four-module census, the AST-versus-`grep` gap, all eight
  `archive` drives, all five `doctor` drives, both controls, the three call
  sites, the handler tuple. **REASONED:** nothing.

Pre-registered permissions unchanged: `gpu: false`, `network: false`,
`performance_metrics: false`; gates `allow_skips: false`,
`require_validation: true`, `require_known_answer_check: true`,
`require_independent_verification: true`.

**SUBMITTED, not VERIFIED.** Re-running my own evidence is a re-run, not
independent confirmation.

| Artifact | SHA-256 |
|---|---|
| `raw/probe_unguarded_modules.py` | `688dd4b86f378de7db47d9edd38133f2b31e2c1f5d6061d2de1f3ec284e33619` |
| `raw/raw-unguarded-modules.txt` | `531adc70bdc53f4fe8ba5dda197d03c13249e7afbd4b6f1a27599890de6ee682` |
