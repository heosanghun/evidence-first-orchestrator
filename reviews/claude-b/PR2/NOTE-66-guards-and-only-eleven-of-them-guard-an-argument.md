# EFO type-checks in 66 places — and only **eleven** of them check an argument

Reproduce with `raw/probe_isinstance_census.py`; raw output in
`raw/raw-isinstance-census.txt`. **26 checks, 0 unexpected.** A **map with one
positive finding** — no issue filed, and nothing retracted.

**Scope, stated first:** 16 `.py` files under `src/evidence_orchestrator/`,
**147** functions, **66** `isinstance` call sites, **5** driven calls.

## Why census the guard instead of its absence

Items 45, 47 and 48 each ended in the same place: a function handed a
non-string raises a raw Python `AttributeError` or `TypeError` rather than an
`EFOError`. Item 48 found `provenance._validate_remote_url` to be the only
function across those three populations that converts one into a
`ConfigurationError` and called that a **positive** pattern.

Three items reaching the same wall is a fact about the wall. So this round
measured the guard itself.

## The package guards sparsely — and that is the least interesting number

| | |
|---|---|
| functions in the package | **147** |
| containing an `isinstance` | **24** (16%) |
| `isinstance` call sites in those 24 | **66** |
| modules with functions and **no** `isinstance` at all | `archive.py`, `dashboard.py`, `doctor.py`, `lock.py` |

Sixteen per cent says nothing on its own. The question is what the checks are
**on**.

## The finding: 43 guard data, 11 guard an argument

Classifying each call site by what its **first argument** is — the categories
the question needs, not present-or-absent:

| what is type-checked | count |
|---|---|
| a **LOCAL** — a value the function itself read, parsed or assigned | **43** |
| a **PARAMETER** — the caller's input | **11** |
| a dict **FIELD** (`d.get(...)`, `d[...]`) | 8 |
| a name bound by an outer loop or comprehension | 4 |

The table is asserted **exhaustive**: all 66 land in a named class, so a shape
I did not anticipate fails the run instead of vanishing.

> **EFO type-checks the data it reads, not the arguments it is handed.**

That is not a defect. This review's threat model is a **tampered file**, and the
guards sit on the tampered-file path. It is also the one sentence that explains
every *"raw Python exception"* result items 45, 47 and 48 recorded: those items
drove **arguments**, and arguments are the 11, not the 43.

The eleven, named in full — eight distinct functions, four of them in
`provenance.py`:

```
    evidence.py:64,66,69   _reject_non_finite(value)
    independence.py:64     identity_snapshot(identity)
    provenance.py:57       _validate_remote_url(value)
    provenance.py:76       validate_git_source_claim(branch)
    provenance.py:98       _validate_source_path(value)
    provenance.py:170      validate_git_provenance(max_blob_bytes)
    workspace.py:326       add_agent(command)
    workspace.py:618,625   report_proxy_status(reference / note)
```

## Where it does guard, it converts properly

| what happens when the check fails | count |
|---|---|
| **rejects with an `EFOError`** | **35** — `EvidenceError` 17, `ConfigurationError` 16, `IntegrityError` 1, `AuthorizationError` 1 |
| branches, no rejection path | 12 |
| ternary | 6 |
| comprehension filter | 5 |
| rejects by skipping or defaulting | 5 — `return None` ×1, `continue` ×2, set to `None` ×2 |
| rejects with a builtin exception | 2 |
| `assert` | 1 |

**35 of the 37 that raise** raise the package's own type. So the thing items 45,
47 and 48 kept hitting was never the *conversion* of a bad value — it was the
*position* of the check.

## Driven, not inferred — the split measured at both ends

A census over syntax cannot see a value, so both halves were executed against a
temporary directory:

| call | outcome |
|---|---|
| `read_json(a JSON object)` | `{'a': 1}` — **control** |
| `read_json(a file holding `[]`)` | **`ConfigurationError`** — the LOCAL guard |
| `read_json(None)` | **`AttributeError`** — no parameter guard |
| `_validate_source_path("x")` | `'x'` — **control** |
| `_validate_source_path(123)` | **`ConfigurationError`** — the PARAMETER guard |

`util.read_json` is the cleanest single instance: its **one** `isinstance` is on
`value`, the result of `json.loads`, not on `path`. It rejects a tampered file
with the package's own error and lets a bad argument fall through to
`AttributeError` — exactly what item 47 measured by hand, now explained rather
than merely observed.

## What this reframes — and does not correct

Item 48's sentence reads *"the **only** function found across items 45, 47 and
48"*. That wording is **correct as written**, and the probe asserts it verbatim
rather than paraphrasing it. But it reads like a statement about EFO, and the
package-wide picture is 35 rejecting sites, 16 of them `ConfigurationError`,
with `_validate_remote_url` one of **four** parameter guards in `provenance.py`
alone. What made it singular was the **population those three items walked** —
values reachable from a document — not scarcity in the package.

## Two expectations of mine, corrected to the measurement

- I wrote **15** modules from habit; `src/evidence_orchestrator/` holds **16**
  `.py` files, 13 of which declare a function.
- I derived **38** `EFOError` rejections from an exploratory pass that
  double-counted a branch reached through an `else`. The measured figure is
  **35**, and the prose *"38 of 40"* was corrected to *"35 of the 37 that
  raise"* before the run reported here.

## Why its SYNTHESIS row says `map` and not `clean`

Because it adjudicates no component. It measures where a mechanism is used, not
whether anything is sound — the same shape as the `tests/` and `web_tests/`
rows. So item 50's population is **unchanged at 21 clean rows**, and
`probe_clean_verdict_census.py` still pins 21. Saying that here matters more
than the label: a row worded to keep a pin quiet would be the defect that probe
exists to catch.

## What this does not do

- It does **not** file an issue. Nothing here is a defect; the guards sit where
  this review's threat model needs them.
- It does **not** claim the 43 are sufficient or the 11 too few. It says which
  is which.
- `isinstance` is **one** mechanism. A `try/except TypeError`, a `str()`
  coercion or a schema check would not be counted, and this says so rather than
  implying a total.
- A census over syntax cannot see a value: a LOCAL assigned from an already
  validated return is safe regardless, and a PARAMETER may be private. Section D
  drives both ends instead of inferring them.
- It did **not** touch `main`, the anchor's working tree, or another agent's
  branch. The five drives run against a `tempfile.TemporaryDirectory()`.
- **MEASURED:** every count, both exhaustiveness assertions, all five driven
  outcomes, item 48's wording. **REASONED:** nothing.

Pre-registered permissions unchanged: `gpu: false`, `network: false`,
`performance_metrics: false`; gates `allow_skips: false`,
`require_validation: true`, `require_known_answer_check: true`,
`require_independent_verification: true`.

**SUBMITTED, not VERIFIED.** Re-running my own evidence is a re-run, not
independent confirmation.

| Artifact | SHA-256 |
|---|---|
| `raw/probe_isinstance_census.py` | `79bb230e5db78de6971407da875db2634928b9726af974b6ef1afa05710cd737` |
| `raw/raw-isinstance-census.txt` | `b3eec27498e8141d1b353665ac8a8d12409cb1d2ff61a3c55e636fb3050834cd` |
