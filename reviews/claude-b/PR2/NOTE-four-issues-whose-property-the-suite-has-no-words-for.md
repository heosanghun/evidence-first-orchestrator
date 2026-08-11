# #4, #5, #8 and #18: the components are driven hard — the properties are not

Reproduce with `raw/probe_proxy_mocks.py`; raw output in
`raw/raw-proxy-mocks.txt`. **17 checks, 0 unexpected.** A **map**, not a
finding — no issue filed, and nothing here re-confirms or retracts #4, #5, #8
or #18.

**Scope, stated before starting:** 12 test files, 3 components, 4 issues, 6
call sites. Small enough to adjudicate every hit by hand, and every hit below
**is** adjudicated rather than counted.

## The question's premise was wrong

Queue item 42 asked whether `test_proxy_status.py`'s three package mocks —
`validate_submission`, `validate_git_provenance`, `archive_evidence_bundle` —
stub out the **only** end-to-end path through the components carrying these
four issues.

They do not. That file is **one of twelve**:

- `test_proxy_submission.py` drives `proxy_submit` with **zero patches of any
  kind** — not `patch`, not `monkeypatch`.
- `test_independence.py` drives `submit` and `verify` the same way.
- Enumerated from the AST, the three functions are called from exactly three
  entry points, **unconditionally** — no guard, no feature flag:

```
    workspace.proxy_submit   validate_submission:1141  validate_git_provenance:1153  archive_evidence_bundle:1220
    workspace.submit         validate_submission:1026  archive_evidence_bundle:1054
    workspace.verify         archive_evidence_bundle:1355
```

driven by **10 / 16 / 14** test call sites respectively. All three functions
execute for real many times per run.

## The useful question, and what it measures

The component is reached. Is the **property the issue objects to** ever fed to
it?

| Issue | Property | Occurrences in the whole suite |
|---|---|---|
| **#4** | `git replace` forging byte-exact provenance | **0** |
| **#5** | a never-pushed commit passing | **0** |
| **#18** | `max_evidence_bytes` as threshold on one path, ceiling on the other | **0** |
| **#8** | `[FILL]` compared with itself | guard exercised, **never with `[FILL]`** |

### #4 — adjudicated, not counted

No test mentions `git replace`, `replace-ref` or `refs/replace`. The bare word
`replace` has **three** whole-word hits, listed in the raw output so the
adjudication can be checked rather than trusted — all three are
`str.replace` / `bytes.replace`.

A **substring** search would have returned **five**. The two extra are
identifier-internal: the test names
`test_ready_does_not_replace_proxy_submission_requirements` and
`test_active_proxy_grant_cannot_be_replaced`. Five leads, zero real — the trap
this review has fallen into twice, which is why every count here is tokenised
on a word boundary.

I expected five whole-word hits going in. There are three. Corrected to the
measurement.

### #5 and #18 — the same shape as #6

Nothing in the suite **pushes**, so no test can distinguish a pushed commit
from a never-pushed one. And `max_evidence_bytes` / `max_blob_bytes` are never
**set** by any test, so both call sites always take the 50 MiB default and the
threshold-vs-ceiling divergence cannot appear.

That is the #6 answer — *"the property has no vocabulary anywhere in the
component"* — rather than *"the suite forgot a case"*. The second is a gap; the
first means a regression here could not be detected by this suite at all.

### #8 — the guard has tests, fed only the input it already handles

`evidence.py:200` is a bare inequality:

```python
        if check["expected"] != check["observed"]:
```

The only fixture (`tests/helpers.py`) feeds it **integers** — `expected: 4`,
`observed: 4 if known_answer_passed else 5` — so **both branches are covered**:
`4 == 4` passes, `4 != 5` raises. What is never fed is #8's input: the **same
string on both sides**.

And the one `[FILL]` rejection in `evidence.py` is at **`:235`, in the *claims*
loop** — the known-answer loop at `:190-201` has no `[FILL]` check at all. The
single test that names `[FILL]` (`test_evidence.py:89`) sets
`claims[-1]["value"] = 0.7`, so it guards a **different loop** than the one #8
objects to.

Same shape as `NOTE-the-node-tests-exercise-only-the-covered-input.md` found
for #13 and #14, reached from the opposite direction.

## What this does not do

- It does **not** run the Python suite. `pytest` is not installed in this
  container; every result is a static read of `tests/` and the package at
  `main` `5694ab45`.
- It does **not** claim the components are untested. They are driven heavily.
  The claim is narrower and is the whole point.
- It does **not** re-confirm or retract #4, #5, #8 or #18. Those were
  established by executed attacks against pinned refs and are cited in the
  issues.
- **MEASURED:** every occurrence count, every adjudication, the AST call graph,
  the comparison line, the fixture values. **REASONED:** that a property with
  no vocabulary cannot regress detectably — which follows from the absence, not
  from running anything.

Pre-registered permissions unchanged: `gpu: false`, `network: false`,
`performance_metrics: false`; gates `allow_skips: false`,
`require_validation: true`, `require_known_answer_check: true`,
`require_independent_verification: true`.

**SUBMITTED, not VERIFIED.**

| Artifact | SHA-256 |
|---|---|
| `raw/probe_proxy_mocks.py` | `1cdaa0f969f8e2f697f2ab66e2c12fc49faae089fac22e8f1ee845073a8ea55a` |
| `raw/raw-proxy-mocks.txt` | `3ba8dab12be1f5e2c1a5cf54baa7fc4c033ef3ea9d6c26ff4c0e6230b402b6cb` |
