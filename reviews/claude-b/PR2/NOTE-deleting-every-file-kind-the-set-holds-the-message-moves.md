# Deleting each file kind — the caught set holds, and every message moves

Reproduce with `raw/probe_delete_every_file_kind.py`; raw output in
`raw/raw-delete-every-file-kind.txt`. **17 checks, 0 unexpected.** A **map**
that widens an open issue — **no issue filed**, nothing retracted.

**Scope, stated first:** 27 files, 17 kinds, 17 edits, 17 deletes, 35
workspaces, 1 exhaustiveness assertion.

> **EXTENDED 2026-08-03 by item 72 — nothing here is retracted.** This round
> said plainly that deleting **all** instances of a kind was UNCHECKED. It has
> now been driven: of the **9** multi-instance kinds, **0** change verdict or
> message when every instance goes, and the whole
> `submissions/T1/attempt-001/` tree (9 files) can be removed in one operation
> with `doctor` healthy and the task still `archived`. See
> `NOTE-deleting-every-instance-of-a-kind-and-the-whole-attempt-tree.md` —
> which also un-truncates this round's 40-character audit message, since that
> truncation would have hidden the very difference being tested for.

## What item 66 left open

That round drove an **edit** of each of the 17 file kinds and said plainly it
did **not** drive a **delete** of each; item 63 deleted three things at
*directory* level only. Item 63 had already shown the two can differ —
replacing `.efo/ledger.key` gives a signature mismatch, deleting it gives a
missing key — so the question is which **other** kinds behave differently when
the file is *gone* rather than *wrong*.

Both operations are driven here **in one run**, on a fresh workspace each, so
the comparison stands on this run rather than on item 66's table plus this one.

## The caught set does not move

```
    edit caught     : .efo/ledger.key  .efo/workspace.json  agents/*.json
                      ledger/events.jsonl  tasks/*.json
    delete caught   : .efo/ledger.key  .efo/workspace.json  agents/*.json
                      ledger/events.jsonl  tasks/*.json

    caught ONLY when deleted : []
    caught ONLY when edited  : []
```

**5 caught, 12 unnoticed**, both ways — and the edit column reproduces item
66's count exactly, which is what makes the delete column readable.

## But every message does

| kind | edited | deleted |
|---|---|---|
| `.efo/ledger.key` | `Ledger signature mismatch at event 1` | `Ledger signing key is missing: …` |
| `.efo/workspace.json` | `Workspace configuration differs from the…` | `Not an Evidence First Orchestrator works…` |
| `agents/*.json` | `Agent 'antigravity' registration differs…` | `One or more signed agent projections are…` |
| `ledger/events.jsonl` | `Malformed ledger JSON at line 13` | `T1: no ledger event` |
| `tasks/*.json` | `T1: projection differs from ledger` | `T1: projection missing` |

**Five of five.** Not four — I predicted four and the measurement says the
change is **universal** across the caught set, which is asserted rather than
described.

> **A count of `caught` alone would have reported these as identical.** The
> set is the same; what the operator is *told* is not — and for
> `.efo/workspace.json` the difference is categorical: an edit is reported as a
> *configuration mismatch*, a deletion as *not a workspace at all*.

## What this does not do

- It does **not** file an issue. This widens the measured width of **#10** from
  edits to deletes; quantifying an open issue is not opening another.
- It does **not** claim deletion is equivalent to editing. The caught **set** is
  identical and **all five messages** differ — both measured.
- The 12 kinds unnoticed under edit are unnoticed under delete too: a whole
  **archived bundle**, every **report**, and every **submission copy** can be
  *removed* with `doctor` still reporting healthy — measured under the threat
  model `SECURITY.md:38` declares.
- It deletes **one instance** of each kind, not every instance. Deleting all
  three `agents/*.json` at once is **unchecked**, not shown safe.
- No network, no GPU. Thirty-five `tempfile` workspaces, removed before the
  results print. The anchor's working tree is untouched, and it does **not**
  touch `main` or another agent's branch.
- **MEASURED:** the file enumeration, the kind collapse, all 17 edits, all 17
  deletes, both caught sets, every differing message, the lifecycle control.
  **REASONED:** nothing.

Pre-registered permissions unchanged: `gpu: false`, `network: false`,
`performance_metrics: false`; gates `allow_skips: false`,
`require_validation: true`, `require_known_answer_check: true`,
`require_independent_verification: true`.

**SUBMITTED, not VERIFIED.** Re-running my own evidence is a re-run, not
independent confirmation.

| Artifact | SHA-256 |
|---|---|
| `raw/probe_delete_every_file_kind.py` | `9e36c00a134ffaa9dcdd08569bb8f1ee9d24c3f2f866118e8984904f59ed6214` |
| `raw/raw-delete-every-file-kind.txt` | `0a21509faf41261a005eb1eb65c32fa8ee04a2efeeaf545a9224c195b20e57dc` |
