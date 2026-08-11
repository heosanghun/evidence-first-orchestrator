# `ledger.projected_tasks` at `main` `5694ab45` — the fold is loose, every caller is not; no issue filed

Reproduce with `raw/probe_projected_tasks.py`; raw output in
`raw/raw-projected-tasks.txt`. **17 checks, 0 unexpected.**

`get_task`, `list_tasks` and `_audit_projections` all decide whether a
projection is trustworthy by comparing it against `projected_tasks()`. That
makes this eleven-line fold the reference the whole integrity story rests on,
which is the reason to look at it even though nothing pointed here.

## Positive control

Against a real workspace with two tasks and one claim:

```
the fold reconstructs every task            ['T1', 'T2']
matches the on-disk projection byte for byte   match: True
the latest snapshot wins, not the first        state=claimed
```

## The fold does not verify — every caller does

`projected_tasks` calls `read()`, which only refuses malformed JSON, and the
string `verify` does not appear in its body. So the only question that matters
is whether anything can reach it on an unverified chain. Call sites enumerated
from the source, and the run **fails on any site this probe has not
adjudicated**, so a future one cannot slip past unread:

```
call sites found: [468, 489, 1498]
  workspace.py: 468  verify() within 5 lines above: True   get_task            (verify at 467)
  workspace.py: 489  verify() within 5 lines above: True   list_tasks          (verify at 488)
  workspace.py:1498  verify() within 5 lines above: True   _audit_projections  (verify at 1497)
uncovered: 0
all verify: True
other modules reaching it: []
```

Three call sites, all in `workspace.py`, all verifying immediately before.
Nothing else in the package touches it.

## What the fold tolerates, and why none of it is reachable

These are properties of the function, written directly to a scratch ledger.
They are **not reachable states**: every shipped caller verifies first, and
producing a chain that verifies needs the signing key.

| Input | Result |
|---|---|
| an **unknown action** carrying a task payload | folds it — the filter is on payload shape, not on the action name |
| `task_id` and `payload.task.id` disagreeing | keyed under the **envelope's** `task_id`, `id='T2'` under key `'T1'` |
| a `task.verified` with no preceding `task.created` | projects — the fold has no notion of a lifecycle |
| `task_id: null` | ignored |
| `payload.task` not a dict | ignored |
| no task payload at all | ignored |

Three of those are last-write-wins semantics doing exactly what they should. The
id mismatch is the only one worth chasing, because it puts a `T2`-shaped
snapshot under the key `T1`.

## Chasing the id mismatch to the end

Rebuilt with a **valid** chain — a properly hashed and HMAC-signed event
appended with the workspace's own key — so `get_task` actually reaches the
comparison:

| Step | Observed |
|---|---|
| `ledger.verify()` with the mismatched event | **accepted** — `{'valid': True, 'events': 3, 'signed': True}` |
| the fold | keys it under `T1` with `id='T2'` |
| `get_task("T1")` | **rejected** — `ConfigurationError: Unknown task: T1` |

No `tasks/T1.json` exists, so the projection comparison is never reached. To
make the mismatch bite, an attacker would have to plant a matching projection
file *as well as* hold the signing key — which is strictly more than issue #9
already needs, and #9 covers that ground. So this is inert, and it is recorded
rather than filed.

A cheap hardening if anyone touches this file anyway: skip an event whose
`payload["task"]["id"]` disagrees with `event["task_id"]`, or raise. It costs
one comparison and removes the only shape here that is not obviously benign.

## Scope

`Ledger.read`, `Ledger.projected_tasks`, and the three `workspace.py` call
sites. Not examined: `Ledger.append`'s locking under real concurrency, and
`_verify_events` beyond what issue #9 already measured.

Pre-registered permissions unchanged: `gpu: false`, `network: false`,
`performance_metrics: false`; gates `allow_skips: false`,
`require_validation: true`, `require_known_answer_check: true`,
`require_independent_verification: true`.

**SUBMITTED, not VERIFIED.**

| Artifact | SHA-256 |
|---|---|
| `raw/probe_projected_tasks.py` | `cec2b2141fa550bcd0b92804fd5935dac5cc88933a3c8edd22b5f3f8a9a472a6` |
| `raw/raw-projected-tasks.txt` | `cfef8d0a56cd331fed78be7646feca5a0fe9a536f58d17409247f7b268eb5d03` |
