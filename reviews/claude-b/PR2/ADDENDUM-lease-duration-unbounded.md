# Lifecycle gates at `main` `5694ab45` — 13 hold, one lets a worker strand its own task forever

Reproduce with `raw/probe_lifecycle_gates.py`; raw output in
`raw/raw-lifecycle-gates.txt`. **13 checks pass, 3 flag** — and the three are one
finding. Every rejection is asserted on its *message*, so a different gate
firing cannot be mistaken for the one under test, and section A is the positive
control: the honest `claim → start → submit` must succeed before any refusal
below means anything.

## What holds

| Probe | Observed |
|---|---|
| **positive control** — honest claim → start → submit | `state=submitted` |
| `start` before claim | `LeaseError: Task ORD has no active lease` |
| `submit` before claim | `TransitionError: Task ORD must be running before submission` |
| `heartbeat` before claim | `TransitionError: Cannot heartbeat task ORD in state pending` |
| second claim of a claimed task | `TransitionError: Task ORD is claimed, not pending` |
| another agent presenting the real token | `LeaseError: Task ORD lease belongs to another worker` |
| the owner presenting a wrong token | `LeaseError: Task ORD lease token is invalid` |
| `submit` skipping `start` | `TransitionError: Task ORD must be running before submission` |
| a 10s lease after 11s | `lease_expired=True` |
| `start` on an expired lease | `LeaseError: Task EXP lease has expired` |
| `heartbeat` on an expired lease | `LeaseError: Task EXP lease has expired` |
| `recover_expired` on a genuinely expired lease | `EXP:blocked` |
| `lease_seconds=9` | `ConfigurationError: Lease duration must be at least 10 seconds` |

Lease theft is properly closed: `_require_lease` checks owner *and* compares the
token hash with `secrets.compare_digest`, and `heartbeat` cannot revive a lease
that has already lapsed.

## The finding: the floor is enforced, the ceiling does not exist

`lease_expiry` (`model.py:135-143`) rejects anything under 10 seconds and bounds
nothing above. `claim` (`workspace.py:876`) takes `lease_seconds` straight from
the caller — and the caller is the **worker**, not the orchestrator.

```
lease_seconds=9            -> rejected, "Lease duration must be at least 10 seconds"
lease_seconds=315_360_000  -> accepted, expires_at=2036-07-29T18:46:42Z
```

Once that lease exists the task cannot be recovered by anyone:

| Recovery attempt | Observed |
|---|---|
| `recover_expired(actor="antigravity")` | `recovered=[]` — it is gated on expiry |
| `requeue(actor="antigravity", task_id="LONG")` | `TransitionError: Cannot requeue task LONG in state claimed` |

And those are the only two candidates. Every public `Workspace` method whose
name suggests lease recovery, enumerated by the probe rather than by reading:

```
['recover_expired', 'requeue']
```

So a worker can hold one of its own tasks in `claimed` for a decade, and the
orchestrator has no recorded path to take it back. `recover_expired`'s docstring
says it exists to *"Move expired leases to blocked so they cannot run twice
silently"*; a lease that never expires is outside its reach by construction.

### Suggested fix

Bound the duration the same way the floor is bounded — a
`defaults.max_lease_seconds` beside the existing
`defaults.lease_seconds: 1800`, rejected in `lease_expiry` next to the 10-second
check. Alternatively, let the orchestrator break a lease explicitly
(`release(actor, task_id, reason)` committing `task.lease_revoked`), which is
worth having regardless since a crashed worker holding a long-but-legitimate
lease has the same shape.

## Severity, stated plainly

This is not privilege escalation and not an evidence bypass. A worker can only
claim tasks it already owns (`task["owner"] != actor` is refused), so the blast
radius is the worker's own work. What it defeats is *recovery*: the one
mechanism the orchestrator has for a worker that stops responding is gated on a
number that worker chooses. The default is 1800s and nothing in normal operation
sets anything else — this is a missing bound, not an active problem.

## Harness bugs, caught before any conclusion

Two, and only the corrected run is reported. The first run expected
`has no active lease` for both "submit before claim" and "submit skipping
start"; both are in fact refused earlier, by
`must be running before submission`. Correct refusals that my expectation
strings mislabelled — fixed, and the messages above are the real ones.

## Scope

Only the lifecycle path: claim, lease, start, heartbeat, block, submit, expiry
recovery, requeue. Not examined: `verify` beyond what issue #3 covers, `archive`,
`proxy_submit`, `adapter.py`, and the concurrency behaviour under real parallel
claims (the probe is single-threaded).

Pre-registered permissions unchanged: `gpu: false`, `network: false`,
`performance_metrics: false`; gates `allow_skips: false`,
`require_validation: true`, `require_known_answer_check: true`,
`require_independent_verification: true`.

**SUBMITTED, not VERIFIED.**

| Artifact | SHA-256 |
|---|---|
| `raw/probe_lifecycle_gates.py` | `5892ec6a12e4d030eb24b72f8037a188831011709bed3207057dbc57bc0f93fc` |
| `raw/raw-lifecycle-gates.txt` | `7c1b964ae9853f7fbc16e6a70cce237caff01ef41013de5e8ae9a0a9e33954ec` |
