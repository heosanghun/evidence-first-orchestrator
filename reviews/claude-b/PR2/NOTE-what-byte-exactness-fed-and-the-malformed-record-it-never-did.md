# What "`provenance.py` byte-exactness is clean" fed — and the class it never did

Reproduce with `raw/probe_byte_exactness_input_class.py`; raw output in
`raw/raw-byte-exactness-input-class.txt`. **15 checks, 0 unexpected.** A **map**
— no issue filed, and `NOTE-byte-exactness-holds.md`'s verdict is **not
retracted**, only narrowed.

**Scope, stated first:** 1 note, 20 checks, 3 un-fed guards, 7 driven inputs.

## The question, and why by hand

Item 47 narrowed *"`util.py` is clean"* by asking one thing: **what input class
did its checks actually feed?** Item 50 showed the cheap mechanical way to ask
that of every clean note is **refuted**, and named **seven** notes to do by hand
instead. This is the first, taken in the order item 50 listed them.

## The twenty, classified one at a time

| class | count |
|---|---|
| a **byte-level mutation** of a well-formed file | **11** |
| an untouched, structurally valid submission (the controls) | 4 |
| a **well-formed** provenance list with the wrong **membership** | **3** |
| a report whose prose was altered | 2 |
| | **20** |

The mapping is asserted **exhaustive** — a label I failed to classify fails the
run rather than dropping out of the tally, which is the lookup-table lesson from
item 34 applied before it could bite.

All three membership cases are a `list[dict[str, str]]`. Only *which* entries
are present changes — **never the shape of an entry**.

## Zero fed a malformed record, and three guards exist for exactly that

```
    provenance.py:216   if not isinstance(declared_files, list) or not declared_files:
    provenance.py:230   if not isinstance(record, dict):
    provenance.py:234   if not isinstance(submitted_value, str) or not submitted_value:
```

Same shape as issues #8, #13 and #14 and as item 47: **the guard has a test, and
the test feeds it only the input it already handles** — found again in **my own
clean note**.

## Driven, so the gap is closed rather than merely named

Positive control first; the workspace, the delivery repo and the grant are the
same fixture the original probe builds.

| input | outcome |
|---|---|
| the untouched envelope | **accepted**, `state: submitted` — control |
| `files = null` | **`EvidenceError`** |
| `files = {}` (an object, not a list) | **`EvidenceError`** |
| `files = []` (empty) | **`EvidenceError`** |
| `files = ["a string"]` | **`EvidenceError`** |
| `files = [null]` | **`EvidenceError`** |
| `submitted_path = 123` | **`ConfigurationError`** |
| `submitted_path = ""` | **`ConfigurationError`** |

**Seven driven, seven refused, seven `EFOError`s — zero raw Python exceptions,
zero accepted.**

That is the **opposite** of item 47's answer, where 17 driven inputs gave 17 raw
Python exceptions and 0 `EFOError`. Item 51 says why: these guards sit on a
value **parsed from a document**, which is the class EFO does guard;
`util.py`'s were on **arguments**, which is the class it does not. Three items
now agree on the same distinction from three different directions.

## The verdict, narrowed and not retracted

- *"`provenance.py` byte-exactness is clean"* **stands**. All 20 checks still
  pass and nothing here contradicts one of them.
- What is now **stated**: those 20 fed byte mutations and membership errors,
  never a malformed record. The gap was real and invisible until asked.
- Driving the gap found EFO sound there too, so this **closes** rather than
  opens. A negative result, and worth publishing as one.

## What this does not do

- It does **not** re-run the original twenty checks; it classifies them from the
  **committed** output and drives what they missed.
- It does **not** adjudicate the other six notes item 50 named. Six remain.
- It does **not** reach `provenance.py:294-297`, the TOCTOU backstop the
  original note already recorded as unmeasured. **Still unmeasured.**
- It does **not** cover a malformed `source_path`, `commit`, `branch` or
  `remote_url` — item 48 drove `_validate_remote_url` and item 51 censused the
  guards package-wide; this is about the `files` list.
- It does **not** file an issue, and nothing was accepted that should not have
  been.
- No network — the remote is `example.invalid` and proxy submission never
  fetches. Workspaces are `tempfile` directories, removed before the results
  print. It does **not** touch `main`, the anchor's working tree, or another
  agent's branch.
- **MEASURED:** the 20-label classification and its exhaustiveness, the three
  guard lines, the control, all seven driven outcomes. **REASONED:** nothing.

Pre-registered permissions unchanged: `gpu: false`, `network: false`,
`performance_metrics: false`; gates `allow_skips: false`,
`require_validation: true`, `require_known_answer_check: true`,
`require_independent_verification: true`.

**SUBMITTED, not VERIFIED.** Re-running my own evidence is a re-run, not
independent confirmation.

| Artifact | SHA-256 |
|---|---|
| `raw/probe_byte_exactness_input_class.py` | `2772e38612269e681d42419eedb34b99e85834aaa68a05bb17c01a26e18aafac` |
| `raw/raw-byte-exactness-input-class.txt` | `78b93fef8ed4d31bf48dd369e624465142a99a9086dc4bc7c1750a6f2d187544` |
