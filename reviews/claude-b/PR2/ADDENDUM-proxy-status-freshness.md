# Transport-attested progress at `main` `5694ab45` — the machine holds, the clock does not

Third pass over the surfaces I had listed as unexamined. Most of this code is
tight and I want to say so before the one gap.

Reproduce with `raw/probe_proxy_status_freshness.py`; raw output in
`raw/raw-proxy-status-freshness.txt`. **0 unexpected results** — every line below
is measured, and the stale-lease case is carried as a positive control.

## What holds

| Probe | Observed |
|---|---|
| first phase must be `dispatched` | rejected — `The first proxy status phase must be dispatched` |
| the transport actor needs its own signed identity | rejected — `Transport actor 'antigravity' needs a signed identity attestation` |
| reference swapped mid-dispatch | rejected — `Proxy status reference cannot change during a dispatch` |
| `working → ready` skipping `reviewing` | rejected — `reviewing` is mandatory |
| phase regression `ready → working` | rejected — `Proxy status phase cannot regress` |
| canonical state after a full dispatch→ready run | still `pending` |
| the monitor labels the override | `status_source=transport_assertion`, `status_badge=운반자 보고`, `canonical_state=pending` |
| the monitor ignores the report once the task leaves `pending` | claimed task renders `progress_percent=25`, `status_source=canonical` |
| `requeue` clears the projection | `external_status=None`, progress back to canonical `10` |

`functions/api/snapshot.js:264-296` also cross-checks a published projection:
an `external_phase` is only accepted together with `state === "pending"`,
`status_source === "transport_assertion"`, the badge, `lease_active === false`,
and the exact progress and next-action string for that phase. A projection
claiming `ready` on a `verified` task is rejected. That is a real control and it
works.

## The gap: a transport observation never goes stale, and a lease does

`monitor/collector.py:893-912` decides the portfolio tallies:

```python
elif state == "pending" and external_phase in PORTFOLIO_EXTERNAL_ACTIVE_PHASES:
    active_count += 1
elif state in PORTFOLIO_ACTIVE_STATES and (
    state == "submitted" or task.get("lease_active") is True
):
    active_count += 1
```

The lease branch is guarded by `lease_active`. The external-phase branch is
guarded by nothing.

Measured, same probe, side by side:

| Case | `active` count | progress |
|---|---|---|
| **positive control** — task `running` on a 30-day-old lease | **0** (`lease_is_active=False`; it falls through to `blocked`) | canonical |
| task `pending` with a 30-day-old `ready` transport report | **1** | **85** |

`MAX_CLOCK_SKEW_SECONDS = 300` in `snapshot.js` bounds the *upload request*, not
the age of the observation inside it. The collector re-uploads every cycle, so a
month-old report keeps being published inside a freshly signed snapshot. The
only tell is `updated_at`, which carries `reported_at` — a human reading the
timestamp can see it; the `85` and the active tally cannot.

`4871867 fix: expire proxy status and reject forged projections` is in `main`
(ancestor of `5694ab45`, confirmed). Its "expire" is the requeue path
(`workspace.py:1415`, `pending.pop("external_status", None)`) plus the
`snapshot.js` cross-checks. It is not a time bound, and the naming invites the
reading that staleness is handled.

**And the clearing path does not reach the stale case.** `requeue` accepts only
`blocked` or `rejected` (`workspace.py:1403`), while a proxy status requires
`pending` (`workspace.py:652`). A task left `pending` with a `ready` report —
exactly the case that goes stale — cannot be requeued at all. Reaching the
clearing path takes `claim → start → block → requeue`, which is what the probe
had to do.

### Suggested fix

Give the external phase the same treatment the lease already gets: bound
`reported_at` and drop the task out of the active tally past that bound, or
surface `external_status_stale: true` so the badge can say so. Either keeps the
disclosure honest without changing the phase machine, which is fine as it is.

## Severity, stated plainly

This is not an authentication or evidence bypass. Canonical state is never
touched, the override is labelled everywhere I could find it, and the published
projection is cross-validated. What it affects is the operational picture: one
transport report on a task nobody ever claimed holds that task at 85% and inside
the active count indefinitely, and the number that would reveal it — the age —
is the one thing the tally ignores. In a system whose premise is that an
affirmative signal must not be trusted without evidence, a progress figure that
cannot expire is worth closing.

## Harness bugs, all caught before any conclusion

Four, and only the corrected run is reported:

1. `importlib` loaded `collector.py` without registering it in `sys.modules`;
   its frozen dataclasses fail to resolve annotations. Registered first.
2. The fixture never attested the orchestrator's own identity, so every call
   rejected with `Transport actor … needs a signed identity attestation` — a
   different gate than the one under test.
3. The fixture drove `working → ready`, which the machine refuses; `reviewing`
   is mandatory. This one is a finding *in the code's favour*.
4. The fixture called `requeue` on a `pending` and then a `claimed` task, both
   refused. That mistake is what exposed the unreachable clearing path above.

## Scope

Only proxy status, the monitor's task view, and the portfolio tally. Not
examined: the rest of `monitor/collector.py` (GPU, Docker, host metrics), the
`functions/api/chat.js` and `local-health.js` endpoints, and the `workspace.py`
lifecycle gates beyond what this path touches.

Pre-registered permissions unchanged: `gpu: false`, `network: false`,
`performance_metrics: false`; gates `allow_skips: false`,
`require_validation: true`, `require_known_answer_check: true`,
`require_independent_verification: true`.

**SUBMITTED, not VERIFIED.**

| Artifact | SHA-256 |
|---|---|
| `raw/probe_proxy_status_freshness.py` | `715a51d80bdc1e4a80a4a1469860c2d20fdeab68c010b535e5ee680210d160e4` |
| `raw/raw-proxy-status-freshness.txt` | `15e73aff33e2be2cf5d673867d9e9e60be91cd91af2464810017d2b7690df0c4` |
