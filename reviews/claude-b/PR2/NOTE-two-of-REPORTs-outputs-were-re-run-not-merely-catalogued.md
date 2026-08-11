# Two of `REPORT.md`'s outputs are not unreproducible — they were re-run here

Reproduce with `raw/probe_report_reproducibility.py`; raw output in
`raw/raw-report-reproducibility.txt`. **18 checks, 0 unexpected.** No issue
filed — this audits **my own evidence**, not EFO.

**Scope, stated first:** 6 cited outputs, 4 cited scripts, 6 `*measured.*`
claim lines, 2 named refs. Each is adjudicated.

## The question, and why the answer is better than it expected

Item 43 established that `raw-attack4.txt` is unreproducible. Queue item 46
asked which **other** `REPORT.md` claims cite raw outputs whose inputs are
absent at the anchor.

**Both refs `REPORT.md` names exist:**

```
    4aa47ca6  exists=True  2026-07-29 Make adapter evidence assertion portable
    cef56234  exists=True  2026-07-30 feat: add source-bound module entrypoint
```

Neither is the review's anchor and no other write-up asserts them — that part
of the item holds. But **"not the anchor" is not "unreachable"**, and that
difference is the whole result.

## Three orphans, only one of them unreproducible

| Cited output | Producer in `raw/` |
|---|---|
| `raw-attack2.txt`, `raw-attack2-cef5623.txt` | `attack2.sh`, `attack2_cef.sh` |
| `raw-attack3.txt` | `attack3.sh` |
| `raw-attack4.txt` | **none** |
| `raw-full-final.txt` | **none** |
| `raw-recheck-cef5623.txt` | **none** |

Item 43 covered `attack4`. For the other two I stopped guessing and ran them.

## Executed — `unittest` is stdlib, so "no pytest" never mattered

| Output | Ref | Committed | This run | Exit | Skips |
|---|---|---|---|---|---|
| `raw-full-final.txt` | `4aa47ca6` | `Ran 70 tests` | **`Ran 70 tests`, OK** | 0 | 0 |
| `raw-recheck-cef5623.txt` | `cef56234` | `Ran 77 tests` | **`Ran 77 tests`, OK** | 0 | 0 |

Neither number was typed in by me: the **committed output** supplies the
expectation and the **fresh run** the observation. Saying these could not be
reproduced *without trying* would have been the error — the container has no
`pytest`, but `unittest` is in the standard library and always was.

`OK` carries no `(skipped=N)` suffix in either run, which is what makes
"zero skips" a measurement rather than a hope.

## What is still unreproducible, and why

`raw-recheck-cef5623.txt` has **three** sections. The **suite** section is the
one re-run above. Its `P2-1 recheck` and `P2-2 recheck` sections drive the
**v0.1 client**, which comes from the wheel fixture that is **absent at the
anchor** — the same reason item 43 gave for `raw-attack4.txt`.

So that file is **partly** reproducible: one section re-run, two that cannot be.
That distinction did not exist before this pass.

`attack2.sh` and `attack3.sh` do ship on the branch, but they declare the
branch's own **unpinned** tree (item 40) — so they run, just not against the ref
`REPORT.md` names.

## What this does not do

- It does **not** re-run the attack scripts. Item 40 measured that two target an
  unpinned tree; re-running them now would measure *today's* branch, not the ref
  under review.
- It does **not** retract or re-confirm P2-1 … P2-4. Two **suite** runs were
  reproduced; the findings rest on the recheck and attack sections, which is a
  different question.
- It does **not** touch `main` or any other agent's branch. Both checkouts are
  local clones under `/tmp` and nothing was written to either working tree.
- **MEASURED:** every count, both ref lookups, the producer census, both re-runs
  with their exit codes and skip counts, the wheel's absence, the section split.
  **REASONED:** nothing.

Pre-registered permissions unchanged: `gpu: false`, `network: false`,
`performance_metrics: false`; gates `allow_skips: false`,
`require_validation: true`, `require_known_answer_check: true`,
`require_independent_verification: true`.

**SUBMITTED, not VERIFIED.** I re-ran my own evidence; that is a re-run, not
independent confirmation.

| Artifact | SHA-256 |
|---|---|
| `raw/probe_report_reproducibility.py` | `ede0173df188c54d0d842b2243e36d4905d20aa23e8cf078904ac0b58ba1dab2` |
| `raw/raw-report-reproducibility.txt` | `1e9e2c44c4d4453ce05b893f05f9b442ac074c24d5a18b0c103971ee82cd4e67` |
