# Hop three closes: 21 → +4 → 0, and the one unguarded validator is unreachable

Reproduce with `raw/probe_hop_three_closure.py`; raw output in
`raw/raw-hop-three-closure.txt`. **18 checks, 0 unexpected.** A **map and a near
miss** — no issue filed.

**Scope, stated first:** 15 modules, 25 closure triples, 3 attribute accesses,
10 call sites.

## The closure terminates

`NOTE-91-to-22-to-one-raise-that-the-ledger-guard-blocks.md` named its own gap:
hop **three** — a parameter receiving a bare *name* that is itself a tainted
parameter — was unfollowed. Item 48 asked whether that closure is bounded.

```
    21  tainted (module, function, parameter) triples at hop 1+2
    +4  added by hop three
     0  added by hop four   ← the closure TERMINATES
    25  total
```

Bounded, and small enough that all **3** attribute accesses on the four new
parameters are adjudicated *and* driven.

| new parameter | tainted at |
|---|---|
| `independence.validate_identity_value(value)` | `independence.py:49` via `build_identity(model_family)` |
| `provenance._validate_remote_url(value)` | `provenance.py:75` via `validate_git_source_claim(remote_url)` |
| `util.validate_agent_id(value)` | `workspace.py:216` via `_agent_path(agent_id)` |
| `util.validate_task_id(value)` | `workspace.py:219` via `_task_path(task_id)` |

The last two are the very functions item 47 drove — hop three reaches them by a
different road.

## One guarded, one not

Controls first, then the non-string class:

| Call | Outcome |
|---|---|
| `validate_identity_value("claude-b", field="x")` | `'claude-b'` — **control** |
| `_validate_remote_url("https://example.com/r.git")` | accepted — **control** |
| `validate_identity_value(None / 123 / [] / {})` | **`AttributeError`** ×4 |
| `_validate_remote_url(None / 123 / [] / {})` | **`ConfigurationError`** ×4 |

```python
    if not isinstance(value, str) or not value.strip():
```

`provenance._validate_remote_url` is the **only** function found across items
45, 47 and 48 that converts a non-string into the package's own
`ConfigurationError`. `independence.validate_identity_value`, in another module,
calls `value.strip()` with no `isinstance` check at all.

## But it is unreachable — for a reason syntax cannot see

Of **10** `build_identity` call sites passing `control_principal`:

| category | count |
|---|---|
| `str()`-coerced dict read | 2 |
| **dict subscript, no coercion** | **2** |
| bare name or literal | 6 |

A syntactic census flags the two subscripts — `independence.py:165` and
`workspace.py:382` — as uncoerced. **They are safe anyway**, and not because of
the call site: `target` is the *return* of a prior `build_identity`, and
`target_identity` the return of `identity_snapshot`, both of which run every
field through `validate_identity_value`, which returns a `str`. The value is a
string **by construction**.

That is the same lesson as `ledger.py`'s near miss, inverted: a census over
syntax cannot see a *value*, and here the blindness runs in the safe direction.

Recorded, **not filed**, on the standard items 38, 45 and 47 all applied.

## A harness bug of mine, caught by a positive control

The first driver called `validate_identity_value(bad)` and got a `TypeError` on
**every** input — including the good one. The signature is
`(value, *, field)`. The **control failing** is what said the driver was wrong
rather than the code. Nothing was concluded until both controls passed.

A second slip in the same section: the call-site census first asked only *"does
the line contain `str(`?"* and reported 10 sites / 8 bare, lumping literals and
bare names in with the dict subscripts that are the actual question. It now
**classifies** into three categories, and only the third is what the section is
about.

## What this does not do

- It does **not** file an issue.
- It does **not** clear item 45's **69** unresolved cross-module arguments —
  they have no resolvable callee, and no number of hops changes that.
- It did **not** write to any workspace: four pure functions driven with literal
  values.
- **MEASURED:** the closure and its termination, all three accesses, all ten
  driven outcomes, the guard line, the call-site census. **REASONED:** nothing —
  the by-construction argument is read off `build_identity`'s return, which the
  drives exercised.

Pre-registered permissions unchanged: `gpu: false`, `network: false`,
`performance_metrics: false`; gates `allow_skips: false`,
`require_validation: true`, `require_known_answer_check: true`,
`require_independent_verification: true`.

**SUBMITTED, not VERIFIED.**

| Artifact | SHA-256 |
|---|---|
| `raw/probe_hop_three_closure.py` | `d75d3dabb5274d3001d5fcbcb4b1eb196d632cca16d5ec72579bc8bbd889bcf5` |
| `raw/raw-hop-three-closure.txt` | `5574b5425593102bb82e57d0cb84b138fdd445477d8c4d592ee9cc75439f70e9` |
