# `model.py` at `main` `5694ab45` — the state machine is exact; the pre-registered permissions are never type-checked, and the confusion only ever opens gates

Reproduce with `raw/probe_model_gates.py`; raw output in
`raw/raw-model-gates.txt`. **29 checks, 0 unexpected.**

## The state machine is exact

`transition` was checked against the **full 8×8 matrix**, not a sample:

```
8x8 = 64 edges
transition agrees with TRANSITIONS on every edge: mismatches: []

the 11 legal edges:
  pending->claimed    pending->submitted    claimed->running   claimed->blocked
  running->blocked    running->submitted    blocked->pending   rejected->pending
  submitted->verified submitted->rejected   verified->archived
```

`archived` is terminal (`set()`), and `pending -> submitted` exists exactly as
`model.py:24-25` documents — reserved for `proxy_submit`, which records a
distinct author and transport actor instead of fabricating a worker lease.

The lease helpers behave: the 10-second floor is enforced, a lease expiring
*exactly now* counts as expired (`>=`, the conservative direction), and a task
with no lease is never expired. The absent ceiling is issue #7 and is not
re-filed here — the probe records `lease_expiry(315_360_000)` →
`2036-07-30T00:00:00Z` only to keep the measurement in one place.

## The finding: `permissions` and `gates` carry whatever they are given

`validate_task` (`model.py:104-107`) checks that both **are** objects and
nothing about what is in them:

```python
if not isinstance(task.get("permissions"), dict):
    raise ConfigurationError("Task permissions must be an object")
if not isinstance(task.get("gates"), dict):
    raise ConfigurationError("Task gates must be an object")
```

Every later reader uses `.get(name, default)` in a boolean context. Measured
end to end through `validate_manifest`, with a manifest carrying a measured
performance claim:

| `permissions["performance_metrics"]` | Verdict |
|---|---|
| `False` (boolean) | refused |
| `0` | refused |
| `[]` | refused |
| **`"false"`** | **ALLOWED** |
| **`"no"`** | **ALLOWED** |
| **`"0"`** | **ALLOWED** |
| `"true"` | ALLOWED |

Same for the one gate that grants when truthy:

| `gates["allow_skips"]` | Verdict |
|---|---|
| `False` | skips refused |
| **`"false"`** | **skips ALLOWED** |
| `True` | skips ALLOWED |

So a task pre-registered with `permissions={"performance_metrics": "false"}`
permits exactly the measured performance claim the field name says it forbids,
and `gates={"allow_skips": "false"}` permits exactly the skip that
`README.md`'s own doctrine calls "not a pass".

### The asymmetry is what makes it worth filing

The `require_*` gates **restrict** when truthy, so the same confusion fails
safe there — measured:

```
require_known_answer_check = "false"  ->  still required
require_known_answer_check = False    ->  no known-answer check needed
```

Every flag in this schema is one of two kinds, and the type confusion moves
each of them in the same direction: **toward permission**. A stray string opens
`gpu`, `network`, `performance_metrics` and `allow_skips`; it cannot close
`require_validation`, `require_known_answer_check` or
`require_independent_verification`. There is no spelling of the mistake that
makes a task stricter than intended.

### Reachability

Not through the CLI. `cli.py:96-107` builds both dicts from `argparse`
`store_true` flags, so it can only ever pass real booleans — enumerated from
the source in the raw output.

The reachable path is the **public Python API**: `Workspace.create_task` takes
`permissions=` and `gates=` and passes them straight to `new_task`, which
merges them over the deny-by-default base without inspecting the values. This
project drives EFO programmatically as well as through the CLI, and a
configuration loaded from YAML or JSON — where `false` unquoted is a boolean
but `"false"` quoted is a string — is exactly where this arises.

### Suggested fix

In `new_task`, coerce and refuse rather than merge blindly:

```python
for name, value in (permissions or {}).items():
    if not isinstance(value, bool):
        raise ConfigurationError(
            f"Task permission {name!r} must be true or false, not {type(value).__name__}"
        )
```

and the same for `gates`, with `allow_skips` / `require_*` restricted to
booleans. Refusing at creation is better than coercing, because a caller who
wrote `"false"` meant something and should be told the value was not
understood. An unknown *key* is worth refusing too — `permissions={"gpo": True}`
currently rides along silently and grants nothing, which is the safe direction
but still a typo that nobody hears about.

## Recorded, not filed: `transition` can be made to ignore its own check

`model.py:117-120` sets the state, then applies `**updates` **after** it:

```python
result["state"] = target
result["revision"] += 1
result["updated_at"] = utc_now()
result.update(updates)
```

Measured:

```
transition(task, "claimed", state="verified")  ->  lands on "verified"
transition(task, "verified")                   ->  Task T1 cannot transition pending -> verified
```

Call sites in `workspace.py` that pass `state=` into `transition`, enumerated
from the source: **`[]`**. So it is unreachable through the broker, and it is
recorded rather than filed. It is worth a line to whoever owns the file because
the docstring says *"after a legal state transition"* and the function's own
last statement can undo the check that makes it legal — `updates` exists for
`attempt`, `lease`, `result` and `verification`, and popping `state` out of it
would cost nothing.

## Scope

`new_task`, `validate_task`, `transition`, `TRANSITIONS`, `lease_expired`,
`lease_expiry`, and the permission/gate reads in `evidence.py`. Not examined:
`errors.py`, `cli.py` beyond the `task add` permission construction, and
`dashboard.py`.

Pre-registered permissions unchanged: `gpu: false`, `network: false`,
`performance_metrics: false`; gates `allow_skips: false`,
`require_validation: true`, `require_known_answer_check: true`,
`require_independent_verification: true`.

**SUBMITTED, not VERIFIED.**

| Artifact | SHA-256 |
|---|---|
| `raw/probe_model_gates.py` | `d147430efad45b795cccb3adcfdd7d2ac6dcdcb33654dcc2167027bbeb62b7a5` |
| `raw/raw-model-gates.txt` | `bf543ebf94e98e1d144c99fd25fd606e389ce88cddfe43cd09e0ca4bb68d32ba` |
