# What "`util.py` is clean" rested on — and the input class it never fed

Reproduce with `raw/probe_util_uncovered_input.py`; raw output in
`raw/raw-util-uncovered-input.txt`. **17 checks, 0 unexpected.** A **map**, not
a finding — no issue filed, and `NOTE-util-and-lock-hold.md`'s verdict is **not
retracted**, only narrowed.

**Scope, stated first:** 9 functions, 1 probe, 1 note, 23 in-package call sites.

## The question

`util.py` has **nine** top-level functions, the EFO suite names **none** of them
(item 44), and it is imported by nine of fifteen modules — the widest fan-in in
the package. `NOTE-util-and-lock-hold.md` calls it clean over 46 checks. Item 47
asked what that note actually measured.

## 1. It rested on *my* probe, not on EFO's tests

`probe_util_and_lock.py` names **all nine**. So `util.py is clean` is a claim
about **my** evidence — which is what the note is for, but had never been said
in as many words.

## 2. The coverage is uneven, and its own raw output shows it

| function | mentions in my probe | in its raw output |
|---|---|---|
| `is_relative_to` | 9 | **17** |
| `canonical_json` | 17 | 3 |
| `utc_now` | 5 | 2 |
| `parse_utc` | 6 | 1 |
| `atomic_write_json`, `sha256_file` | 3 | 1 |
| `read_json`, `validate_task_id`, `validate_agent_id` | 2 | **0** |

Two of the three silent ones are a **naming artifact, not a gap**: the
validators are driven through a `lambda v=value:` inside loops whose check names
read *"task id …"* rather than the function name — **14 driven values** between
them.

> A first version counted **24** by matching every `("label", value, ok)` row
> anywhere in the probe. The count now comes only from the two loops that feed
> the validators — the substring trap, one level up.

**`read_json` is the real one.** It appears inside exactly **one** check, as a
*helper* in `atomic_write_json round-trips`, and is the subject of **zero**.

## 3. Not one of the 46 checks fed a non-string

Driven here — the package imports and runs under plain `python3`:

| Call | Outcome |
|---|---|
| `parse_utc(None / 123 / [] / {})` | **`AttributeError`** ×4 |
| `validate_task_id(None / 123 / [])` | **`TypeError`** ×3 |
| `validate_agent_id(None / 123 / [])` | **`TypeError`** ×3 |
| `sha256_file(None / 123)` | **`AttributeError`** ×2 |
| `read_json(None / 123)` | **`AttributeError`** ×2 |
| `is_relative_to(None / 123, "/tmp")` | **`AttributeError`** ×2 |
| `canonical_json(object())` | **`TypeError`** |

**17 driven, 17 raw Python exceptions, 0 `EFOError`.** Not one of the nine
converts a non-string into the package's own error type.

`parse_utc`'s three checks all pass a well-formed string; the validators' 14
values are all strings. The class was simply absent — the same shape as #8, #13
and #14 (*"the guard has a test, fed only the input it already handles"*), found
this time in **my own** clean note.

## Reachability — why this is a map and not a finding

Of **23** in-package validator call sites, **3** read a dict field, and **every
one of those coerces**:

```
    str() independence.py:122   validate_agent_id(str(agent_id))
    str() independence.py:159   target_id = validate_agent_id(str(alias_of))
    str() model.py:93           validate_task_id(str(task.get("id", "")))
    str() model.py:94           validate_agent_id(str(task.get("owner", "")))
    str() provenance.py:156     author = validate_agent_id(str(payload.get("author", "")))
```

So a **tampered file cannot deliver a non-string**. The **18** bare call sites
take an *API argument* — programmatic misuse rather than the threat model this
review is about.

Not filed, on the standard items 38 and 45 both applied.

## What this does not do

- It does **not** retract *"`util.py` is clean"*. All 46 checks still pass; what
  changes is that the note now states which input class it never fed.
- It does **not** cover `lock.py`, the same note's other subject.
- It did **not** write to any workspace — the drives pass literal values, and
  `read_json` / `sha256_file` raise before touching a filesystem.
- **MEASURED:** every count, every coverage number, all 17 driven outcomes, the
  caller census. **REASONED:** nothing.

Pre-registered permissions unchanged: `gpu: false`, `network: false`,
`performance_metrics: false`; gates `allow_skips: false`,
`require_validation: true`, `require_known_answer_check: true`,
`require_independent_verification: true`.

**SUBMITTED, not VERIFIED.**

| Artifact | SHA-256 |
|---|---|
| `raw/probe_util_uncovered_input.py` | `8f878cdc16b1c08f8b1880d20b54e3d81bbeb04cb6c274f90c7b4f4bbda636df` |
| `raw/raw-util-uncovered-input.txt` | `33273818813ceae3657b0d196eec128c39d8c6a43b9c9f9e58d4c3f36605711f` |
