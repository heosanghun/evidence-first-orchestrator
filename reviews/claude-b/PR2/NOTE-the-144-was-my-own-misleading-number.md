# The "144 dynamic-key subscripts" I published is misleading — 128 are type annotations, 9 are stores, and **7** are runtime reads

Reproduce with `raw/probe_dynamic_subscripts.py`; raw output in
`raw/raw-dynamic-subscripts.txt`. **14 checks, 0 unexpected.** No issue filed
against EFO — **the defect this note reports is in my own review.**

`NOTE-implicit-exceptions-package-wide.md` closed the constant-key census and
named its own next gap in a table:

> | dynamic-key subscripts, `x[variable]` | **unmeasured** — 144 sites |

Closing that gap was queue item 29. The first thing it found was the 144.

## The number reproduces exactly, which is what makes it worse

The count is not an arithmetic error. Run against the same thirteen modules
with the same rule — every `Subscript` whose slice is not an `ast.Constant` —
it comes back **144**, and the probe checks that reproduction rather than
asserting it. But `x[variable]` reads as *a runtime dict lookup that could
`KeyError`*, and that is not what 144 counts:

| Disposition | Count |
|---|---|
| type annotations — `dict[str, Any]`, `list[dict[str, Any]]` | 128 |
| stores — `d[k] = v`, which **creates** the key | 9 |
| deletes — `del d[k]`, which would count | 0 |
| **runtime reads** | **7** |

The four dispositions sum to 144 with nothing double-counted; that is a check,
not an assertion. So a reader of that table would have taken the uncovered
surface to be twenty times its real size, and would have been reassured for the
wrong reason when it was closed.

**This is the fifth time a filter I wrote by hand was the bug**, after the
`raise`-statement census that could not see a dict index (#19), the
variable-name filter that missed `task_for_validation`, the module list that
missed `errors.py`, and the quote-accuracy window built from a range's start
only. It is the **second** time the bug was in a number I had already
published, after `README.md:590` [retracted].

## Checking my own exclusion against ground truth

An exclusion I wrote is the thing most likely to be wrong here, so it is
checked from two directions and the run fails on either:

- **Nothing foreign is excluded.** The bases of all 128 excluded subscripts are
  `dict` (87), `list` (31), `tuple` (5), `set` (3), `type` (1), `Sequence` (1)
  — typing constructors, every one. A base outside that set fails the run.
- **Nothing typing-shaped is retained.** None of the 7 kept sites has a typing
  constructor as its base, so the filter did not silently *miss* an annotation
  and leave it in the runtime population.

The annotation positions are collected structurally — `AnnAssign.annotation`,
both function forms' `returns`, and every `arg.annotation`, which `ast.walk`
yields for positional, positional-only, keyword-only, `*args` and `**kwargs`
alike — rather than from a list I would have to remember to maintain. Nested
subscripts inside an annotation are collected too.

**Twelve of the thirteen modules** carry `from __future__ import annotations`,
so their annotations never evaluate. The exception is `errors.py`, whose
annotations **do** evaluate at import. That does not change the verdict — a
type expression is still not a key lookup — but the reason differs per module,
so it is stated rather than glossed.

## The 7, by key provenance — the total is deliberately not the answer

| Class | Count | Sites |
|---|---|---|
| **parsed input** | **1** | `provenance.py:295` |
| own keyspace | 2 | `independence.py:148`, `:177` |
| slice (cannot raise) | 2 | `evidence.py:38`, `archive.py:66` |
| local literal | 1 | `ledger.py:82` |
| local arithmetic | 1 | `evidence.py:37` |

The queue item asked for this split rather than a bare total, and the split is
the finding: **exactly one** of the seven is indexed by a value that comes from
outside the process.

### The one that comes from parsed input

`provenance.py:295`:

```
        if submitted_sha != expected_files[submitted]:
```

`submitted` is `(provenance.parent / record["submitted_path"]).resolve()` — a
path a **worker writes into the provenance document**. Indexing a dict with it
is the #19 shape exactly: a supplied value used as a key.

It holds. The membership test is at `provenance.py:241`, in the same loop
iteration:

```
        if submitted not in expected_files:
            raise EvidenceError(
                f"{context}.submitted_path is not claim-bearing evidence: {submitted}"
            )
```

and `expected_files`, built once at `:218`, is never mutated afterwards —
checked from the AST for subscript stores, deletes, and `pop`/`clear`/`update`/
`setdefault`/`popitem` calls, not by reading.

### Guard distance, measured

| Site | Class | Guard → use |
|---|---|---|
| `ledger.py:82` | local literal | 0 lines — same conditional expression |
| `evidence.py:37` | local arithmetic | 0 lines — same conditional expression |
| `independence.py:148` | own keyspace | 0 lines — same statement |
| `independence.py:177` | own keyspace | 1 line — reads the key assigned above |
| **`provenance.py:295`** | **parsed input** | **54 lines** |

Four of the five index reads are guarded *inside the expression that reads*.
The parsed-input one is guarded fifty-four lines earlier. **It is correct
today.** The distance is what makes it the fragile one, and it is the same
structural shape as #19 — a guard and a use that a refactor can separate
without either side looking wrong on its own. That is an observation about
maintenance, not a defect, and it is not filed as one.

## `workspace.py` — a negative result worth publishing

Counted separately, since the earlier note excluded it:

```
total dynamic-key subscripts   61
  annotation                   60
  store                         1
  read                          0
```

**Zero runtime dynamic-key reads in the module that carried #19.** Every dict
index there uses a constant key — precisely the population
`NOTE-issue19-is-the-only-one.md` enumerated. So that note's coverage of
`workspace.py` turns out to have been complete, not by design but because the
gap it warned about is empty in that file. Nothing about #19 changes: #19 is a
constant-key read.

## Scope

Static analysis of the thirteen non-`workspace.py` modules plus `workspace.py`
at `main` `5694ab45` (precondition verified: `HEAD` matches, `git status
--porcelain` empty). Nothing was executed against a live workspace.

Not examined, with counts where they exist:

- the **9** dynamic-key **stores**, excluded because a store creates its key. A
  store into a dict that some *later* read depends on is a different question,
  not asked here.
- `AttributeError` / `TypeError` shapes — still unmeasured, for the reason the
  previous note gave: they need type inference this probe does not have.
- whether any of the 7 guards can be **bypassed at runtime**. This is static
  ordering analysis. The behavioural half would need a crafted provenance
  document driven through `verify_git_provenance`.

Pre-registered permissions unchanged: `gpu: false`, `network: false`,
`performance_metrics: false`; gates `allow_skips: false`,
`require_validation: true`, `require_known_answer_check: true`,
`require_independent_verification: true`.

**SUBMITTED, not VERIFIED.**

| Artifact | SHA-256 |
|---|---|
| `raw/probe_dynamic_subscripts.py` | `0f30108ccc4a44eca814ba177c57b5ab529dd747656cb08a4164c6372f8dc291` |
| `raw/raw-dynamic-subscripts.txt` | `efb9116cf3a88578a3b4c19165895682bf5b7410b730995952535fb2d45d6270` |
