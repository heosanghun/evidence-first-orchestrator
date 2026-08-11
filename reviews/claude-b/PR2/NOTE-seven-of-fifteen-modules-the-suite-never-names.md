# Seven of fifteen modules are never named by the suite — and five issues live there

Reproduce with `raw/probe_module_exercise.py`; raw output in
`raw/raw-module-exercise.txt`. **14 checks, 0 unexpected.** A **map**, not a
finding — no issue filed, and nothing here re-confirms or retracts anything.

**Scope, stated first:** 15 modules, 95 top-level names, 12 test files. Small
enough to adjudicate every name, and every one is adjudicated in the raw output.

## The question

`NOTE-four-issues-whose-property-the-suite-has-no-words-for.md` found that
`provenance.py` and `archive.py` are never *called* by any test — each appears
exactly once, as a **patch target**. Queue item 44 asked whether that is a
structural fact about the suite or a coincidence about the two components
carrying #4, #5, #10 and #18.

**It is structural, and the set is larger.**

| | |
|---|---|
| top-level modules | **15** |
| exercised by name — called, `assertRaises`d, or reached through a `Workspace` attribute | **8** |
| **never exercised by name** | **7** |

```
    module           defs  called  raised  named  verdict
    __main__.py         0       0       0      0  NEVER NAMED
    adapter.py          6       1       0      1  exercised by name
    archive.py          3       0       0      1  PATCH TARGET ONLY
    cli.py             36       2       0      2  exercised by name
    dashboard.py        2       0       0      0  NEVER NAMED
    doctor.py           3       1       0      1  exercised by name
    errors.py           8       0       6      6  exercised by name
    evidence.py         6       1       0      1  exercised by name
    independence.py     7       5       0      5  exercised by name
    ledger.py           1       0       0      1  exercised via attribute
    lock.py             1       0       0      0  NEVER NAMED
    model.py            5       0       0      0  NEVER NAMED
    provenance.py       7       0       0      1  PATCH TARGET ONLY
    util.py             9       0       0      0  NEVER NAMED
    workspace.py        1       1       0      1  exercised by name
```

`errors.py` is the counter-example that shows this is not just counting
silence: **zero calls**, but six of its eight classes appear inside
`assertRaises`, so it lands in *exercised*.

## Five issues live in the unexercised set

| Module | Issues |
|---|---|
| `provenance.py` | **#4**, **#5**, #18 |
| `archive.py` | **#10**, #18 |
| `model.py` | **#15** |
| `__main__.py`, `dashboard.py`, `lock.py`, `util.py` | *(no issue filed)* |

Item 42 predicted four. The fifth is **`model.py`** — and `validate_task`, the
exact function #15 is about, appears **0 times** in the whole suite, along with
`new_task`, `transition`, `lease_expired` and `lease_expiry`.

## The near miss — recorded, because it nearly became a wrong finding

A pure name census scored `ledger.py` as never-exercised on a single hit, and
that hit is `tests/test_ledger.py:19`:

```
                title="Ledger test",
```

— a **string in a fixture**, not the class. The real exercise is
`workspace.ledger.verify()` and `.append()`, reached **8 times** through the
attribute `Workspace.__init__` assigns:

```
    self.config     = read_json  tests reach `.config`: 0
    self.ledger     = Ledger     tests reach `.ledger`: 8
```

**A census over NAMES cannot see a value reached through an ATTRIBUTE** — the
same shape as #6's `.get` chain. Had I shipped the name census alone,
`ledger.py` would have been reported as untested and that would have been
wrong. Stated here rather than quietly corrected.

## What this does not claim

- **Not that the code is unexecuted.** Item 42 measured the opposite: `submit`,
  `verify` and `proxy_submit` are driven by **40** test call sites and reach
  `archive.py` and `provenance.py` **unconditionally** on every run. The claim
  is narrower and is the point: no test *names* them, so none can fail *about
  their own contract*.
- **Not that a name census is sufficient.** `ledger.py` proves it is not.
- **Not a finding.** #4, #5, #10, #15 and #18 are neither re-confirmed nor
  retracted here.
- It does **not** run the Python suite — `pytest` is not installed in this
  container. Every result is a static read at `main` `5694ab45`.
- **MEASURED:** every count, every verdict, the attribute table, the per-name
  listings. **REASONED:** that a module no test names cannot have a failing test
  about its contract — which follows from the absence, not from running
  anything.

Pre-registered permissions unchanged: `gpu: false`, `network: false`,
`performance_metrics: false`; gates `allow_skips: false`,
`require_validation: true`, `require_known_answer_check: true`,
`require_independent_verification: true`.

**SUBMITTED, not VERIFIED.**

| Artifact | SHA-256 |
|---|---|
| `raw/probe_module_exercise.py` | `da6f273e51e17ede0b31bde0f29c8caabe0197339c4367e05338568343f94f66` |
| `raw/raw-module-exercise.txt` | `c3ed91fe7dcc9fb4e0a49c654bd1515a51525d030b2e76a21c536b9afdeadd5d` |
