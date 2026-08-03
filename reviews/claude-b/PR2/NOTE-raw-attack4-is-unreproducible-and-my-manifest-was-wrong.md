# `raw-attack4.txt` is unreproducible — and my own manifest says something untrue about it

Reproduce with `raw/probe_attack4_provenance.py`; raw output in
`raw/raw-attack4-provenance.txt`. **15 checks, 0 unexpected.** No issue filed —
the defect here is in **my own bookkeeping**, not in EFO.

**Scope, stated first:** one output file (191 lines), one `REPORT.md` section,
four git-history queries. Small enough to read end to end, and it was read.

Queue item 43 asked whether the missing `attack4` script is recoverable from
git history, or whether the output should be marked unreproducible. Three
answers, in increasing order of how much they matter.

## 1. No script ever existed

```
    a820891 review(claude-b): independent verification of PR #2
    reviews/claude-b/PR2/raw/raw-attack4.txt
```

`git log --all --diff-filter=D -- '*attack4*'` returns **nothing**, and **zero
attack4 *scripts* have ever been committed** — the output was added in
`a820891` (2026-07-30), the branch's first review commit.

> **Correction, 2026-08-03.** This first read *"the only path that has ever
> matched the name is the output"*, which stopped being true the moment this
> note, its probe and its raw output were committed — all three match
> `*attack4*`. The census now **classifies** instead of counting: under `raw/`
> a file is a script unless it is `raw-*.txt` or `probe_*.py`. The four
> self-references are named in the output. Same self-reference the attack-script
> census hit one round earlier, one directory up.

So "recover it from history" is not one of the options. There is nothing to
recover.

## 2. `REPORT.md` says where it came from, and that is false

The evidence manifest states the output *"was produced by the inline command
blocks quoted in §3 ④"*.

§3 ④ spans `REPORT.md:194-232` and contains **2 fenced blocks and 0
command-shaped lines**. Both blocks are *results* — a `sha256(...)` line with
its README comparison, and a two-line `config file orchestrator` /
`effective orchestrator` pair.

**There are no command blocks there.** A statement about the provenance of my
own artifact that does not hold, in the section of the report whose entire job
is provenance. Said first rather than folded into the verdict.

`REPORT.md` now carries a dated correction at that line.

## 3. The input is gone too, which settles it

```
    7a9553b Add evidence-gated meta-orchestration v2
    tests/fixtures/evidence_first_orchestrator-0.1.0-py3-none-any.whl
```

| At `main` `5694ab45` | |
|---|---|
| the wheel fixture | **absent** |
| `tests/fixtures/` | **does not exist** |
| the README hash claim W1 checked | **gone** |

W1 hashes that wheel; W2 diffs its 14 modules against `git archive f827f29`.
Neither can run at the anchor **no matter what drives them**. The output is
unreproducible for a reason stronger than the missing script: *the artifact
under test is not in the tree.*

**Verdict: mark it unreproducible.**

## What still rests on it

Three `REPORT.md` claims cite it as *measured*:

```
      REPORT.md:305  *measured.* `raw/raw-attack4.txt`, W6 / W6b.
      REPORT.md:322  *measured.* `raw/raw-attack4.txt`, W3.
      REPORT.md:342  *measured.* `raw/raw-attack4.txt`, W2 / W2b.
```

These are findings **P2-1**, **P2-2** and **P2-3** — the fourth P2 finding does
not cite it. They are **not retracted**. They were measured when they were made,
against a ref `REPORT.md` itself names as `4aa47ca6` — not this review's anchor.
What is recorded now is that they **cannot be re-derived on this branch**.

`SYNTHESIS.md` and `NOTE-two-attack-scripts-ran-against-the-stale-base.md` also
mention the file; both already describe it as the orphan.

## An expectation of mine, corrected

I expected the manifest sentence to span **2** lines, because both of my match
patterns fired. They fired on the **same wrapped line** — it is **1**. Corrected
to the measurement, not the other way round.

## What this does not do

- It does **not** retract P2-1, P2-2 or P2-3, and does not re-run them.
  *Unreproducible at the anchor* is not the same as *wrong*.
- It does **not** reconstruct the commands. Writing a plausible `attack4` now
  and calling it the original would be **inventing provenance** — the exact
  thing this review exists to catch.
- It does **not** touch `main` or any other agent's branch. `REPORT.md` is this
  review's own document and is corrected in place, dated.
- **MEASURED:** every git query, the section bounds, the fenced-block and
  command counts, the fixture's absence, the citation census. **REASONED:**
  nothing.

Pre-registered permissions unchanged: `gpu: false`, `network: false`,
`performance_metrics: false`; gates `allow_skips: false`,
`require_validation: true`, `require_known_answer_check: true`,
`require_independent_verification: true`.

**SUBMITTED, not VERIFIED.**

| Artifact | SHA-256 |
|---|---|
| `raw/probe_attack4_provenance.py` | `8e8b2b3aa9a7bfc1ca1cfd7f3703df0e42f81acb375eaa3e73543b64e7f28a60` |
| `raw/raw-attack4-provenance.txt` | `f1705df7aff062a439d10e65b487ab78abd09ab3ca1ebd6282524507845c37e7` |
