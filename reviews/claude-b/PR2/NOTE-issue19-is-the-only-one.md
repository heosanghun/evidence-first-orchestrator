# The implicit-exception blind spot has exactly one instance: `repair_projections` drops one key and only one; no issue filed

Reproduce with `raw/probe_implicit_exceptions.py`; raw output in
`raw/raw-implicit-exceptions.txt`. **10 checks, 0 unexpected.**

Issue #19 is a `KeyError` from `task_for_validation["last_event_hash"]` that
escapes `cli.main` as a traceback. It was found by accident while reading
`ARCHITECTURE.md`, and it disproved an earlier clean result of mine
(`NOTE-dashboard-and-errors-hold.md`'s `escapes: []`, which censused `raise`
**statements** and so could not see an exception arriving from a dict index).

The obvious next question is whether #19 is the first of many. **It is not.**
This note is a negative result, and that is its value: a reviewer does not need
to re-walk the repair path looking for siblings.

## The gap is real, and six exception types wide

`cli.main` catches `(EFOError, OSError, ValueError, json.JSONDecodeError)`.
Of the implicit exceptions Python raises from ordinary expressions,
`KeyError`, `IndexError`, `AttributeError`, `TypeError`, `ZeroDivisionError`
and `StopIteration` are **all** outside those four families. (`ValueError` *is*
caught, so e.g. a `UnicodeDecodeError` would not escape — that is the shape of
the gap, not its size.)

## What repair actually drops

Measured by diffing a real repaired projection against a real normal one, after
walking a task through `pending → claimed → running → blocked`:

```
a task carries 21 distinct keys across its lifecycle
repair drops exactly one key   dropped: ['last_event_hash']
and invents none               added: []
```

One key. #19 is the sole instance of its class.

## Every string-key read in `workspace.py`, by AST

**133 read sites across 52 distinct expressions on 21 base objects**, walked
from the syntax tree with **no name filter at all**, and the run fails on any
base object the map does not cover. `uncovered: []`, `stale: []`.

Each base carries the reason a missing key is impossible, or where it is
handled: task projections (section D proves the keys are guaranteed), dicts
that a validator *returns* rather than accepts (`provenance`, `evidence`,
`independence`), dicts this process just built (`grant`, `renewed`, `event`,
`verification`), agent records, and the ledger-bound config.

The name filter matters. **My first census in this round used a hand-written
list of variable names and missed `task_for_validation` — the very variable
#19 lives on.** That is the same trap the earlier `raise`-statement census fell
into, one round later, so the final version filters by nothing.

## Task keys, as a set difference

```
keys read off a task projection:
  ['attempt', 'gates', 'id', 'idempotency_key', 'last_event_hash',
   'owner', 'permissions', 'prerequisites', 'state']

present on a NORMAL projection      absent: []
present on a REPAIRED projection    absent: ['last_event_hash']
```

That is the whole of #19 in two lines, and it confirms there is no second key
in the same position.

## Config reads

`['defaults', 'name', 'orchestrator', 'workspace_id']`, all present. The
workspace config is bound to the signed ledger — editing it is refused with
`Workspace configuration differs from the signed ledger`, measured previously
in `probe_doctor_coverage.py` — so a hand-removed key cannot reach these reads.
The nested reads use `.get(...)` with a default (`workspace.py:736`, `:1147`).

## What is measured versus reasoned

Stated plainly rather than blurred: **sections B, D and E are measured against
a live workspace.** Section C's per-base reasons are read from the source and
are **not individually executed** — each says why a missing key is impossible
or where it is handled. Only #19's row was ever driven to an actual traceback,
in `probe_architecture_claims.py`.

So the honest claim is: *the one mechanism that demonstrably produces an
incomplete projection produces exactly one missing key*, and no other base
object in `workspace.py` indexes a dict whose provenance is unvalidated. It is
not: *no implicit exception can ever escape*.

## Harness bugs, disclosed

Three, all mine, only the corrected run reported — and two were the same
mistake in different clothes:

- I classified `existing` as a task projection. `workspace.py:750` assigns it
  `task.get("proxy_grant")` — it is a **grant**, guarded by an `isinstance`
  check, and its `expires_at` is not a task key at all. Lumping it in produced
  a false "absent" I would have had to explain away.
- I took the **innermost** literal of a nested subscript, so
  `self.config["defaults"]["lease_seconds"]` was counted as a config key named
  `lease_seconds`, inventing a second false absence.
- Two map entries (`disk_task`, `authorship`) were stale: those sites use
  `.items()` and `.get()`, so they are not subscript reads and never appear in
  the census.

None was a code defect. All three were my classification, which is the same
failure mode this review keeps finding in its own harness: a category that
looks like one thing and is another.

## Scope

`workspace.py` at `5694ab45`: the full AST census of string-key reads, the
repaired-versus-normal projection key diff, and the task and config key
guarantees. Not examined: `IndexError` / `AttributeError` / `TypeError` sites
(this probe covers subscript reads only, so the same gap could still hold an
instance of a different exception type), and the other modules — `adapter.py`,
`ledger.py`, `evidence.py` and `provenance.py` were not censused this way.

Pre-registered permissions unchanged: `gpu: false`, `network: false`,
`performance_metrics: false`; gates `allow_skips: false`,
`require_validation: true`, `require_known_answer_check: true`,
`require_independent_verification: true`.

**SUBMITTED, not VERIFIED.**

| Artifact | SHA-256 |
|---|---|
| `raw/probe_implicit_exceptions.py` | `bb9793126a8e63dd887a9ecc20dd26045587168e5275b6aeb17ffc402c92b8b0` |
| `raw/raw-implicit-exceptions.txt` | `589af787b9b51a6c351af03c46d22e137d36ed726a4e4683f85b96fdbc6bdfe1` |
