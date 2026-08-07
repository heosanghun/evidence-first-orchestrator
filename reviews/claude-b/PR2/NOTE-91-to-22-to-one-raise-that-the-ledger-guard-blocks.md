# 91 → 22 → 16 → one raising function — and the API path is guarded

Reproduce with `raw/probe_cross_module_hop.py`; raw output in
`raw/raw-cross-module-hop.txt`. **21 checks, 0 unexpected.** A **near miss**,
written up and **not filed** — the same standard item 38 applied to its own
`.get` chain.

## The number first

`NOTE-487-is-too-many-and-the-two-that-survive-are-guarded.md` named its own
gap: **91** dict-field arguments go to a callee defined in *another* module and
were not propagated. Queue item 45 asked whether following imports for those 91
is a bounded job.

```
    91  dict-field args to a non-local callee
    22  whose callee RESOLVES to a sibling module (13 call sites, 7 callees)
    69  that do not resolve — stdlib, a method on an object, a builtin
    16  attribute accesses on a parameter tainted across that hop
```

**22 is bounded**, so this does not stop. The **69** are *not cleared* — their
callee is a stdlib function, a method, or a builtin, which is a statement about
this analysis rather than about their safety.

## The 16, and how many are already known

Four of the sixteen are `gates.get` / `permissions.get` inside
`evidence.py::validate_manifest` — that **is #15** (*`permissions`/`gates` are
never type-checked*), reached from a second direction rather than a new result.
The rest are `identity.get`, `verifier.get`, `manifest.get`, and one
`value.replace` in `util.py::parse_utc`.

## Executed, not reasoned

The EFO package imports and runs under plain `python3` here, so the raising
case was **driven**:

| `task["lease"]["expires_at"]` | outcome |
|---|---|
| `"2026-01-01T00:00:00Z"` (past) | `True` — control |
| `"2026-12-01T00:00:00Z"` (future) | `False` — control |
| no lease at all | `False` — control |
| `None` | **`AttributeError`** |
| `123` | **`AttributeError`** |
| `{"a": 1}` | **`AttributeError`** |
| `[]` | **`AttributeError`** |
| `True` | **`AttributeError`** |
| `"not-a-timestamp"` | **`ValueError`** |
| lease present, key missing | **`KeyError`** |

And `validate_task` **never constrains the lease** — it names only `gates`,
`id`, `owner`, `permissions`, `prerequisites`, `revision`, `state`, `title`.

## Why it is a near miss and not a finding

Both readers compare the whole task against the signed ledger before anything
touches the lease:

- `Workspace.get_task` — `validate_task(task)`, then
  `comparable != expected` → `IntegrityError`
- `Workspace.list_tasks` — the same, and `doctor.py:192` reaches
  `lease_expired` *through* `list_tasks`

The comparison covers the entire task minus `last_event_hash`, so a tampered
`lease` raises `IntegrityError` **before** `lease_expired` is called. **I could
not reach the raise through the API**, so it is recorded and not filed. A
finding asserted here would be one I could not demonstrate.

## A harness bug of mine, caught by a positive control

The first driver called `lease_expired(lease, …)` where a **task** belongs, so
`task.get("lease")` was `None` and **every** case returned `False` — including
the control that should have returned `True`. The *control failing* is what
said the driver was wrong rather than the code. Nothing was concluded until the
three controls passed.

A second slip in the same round: an escaping mistake left the lease-mention
filter as `.lease.b`, which returns `0` for the right answer **by accident**.
It is now `\blease\b`, checked against a known answer that must match before
its zero on `validate_task` means anything — and correcting that check
immediately turned up an expectation of mine that was wrong (`lease_expired`
mentions `lease` **5** times, not the 2 I wrote), corrected to the measurement.

## What this does not do

- It does **not** clear the 69 unresolved arguments.
- It does **not** follow hop **three** — a parameter receiving a bare name that
  is itself a tainted parameter is not traced.
- It does **not** file an issue, and neither re-confirms nor retracts #15.
- It did **not** write to any workspace. The drives call two pure functions with
  literal dicts; nothing touched a filesystem.
- **MEASURED:** every count, every listed access, every driven outcome, the
  guard lines. **REASONED:** nothing — the guard was read and the raise was
  executed.

Pre-registered permissions unchanged: `gpu: false`, `network: false`,
`performance_metrics: false`; gates `allow_skips: false`,
`require_validation: true`, `require_known_answer_check: true`,
`require_independent_verification: true`.

**SUBMITTED, not VERIFIED.**

| Artifact | SHA-256 |
|---|---|
| `raw/probe_cross_module_hop.py` | `1485d8af9b470c295259f4cdb93bae553924f90b1024e1b1d8949db0e0c784c3` |
| `raw/raw-cross-module-hop.txt` | `a8367f1aa5e14bd362e5cc4158e47cb8b01b5dc33b129b9aca29a5b417fc2924` |
