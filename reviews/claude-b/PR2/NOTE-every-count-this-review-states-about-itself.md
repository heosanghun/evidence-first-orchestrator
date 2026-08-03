# The inventory is machine-checked now — and so is the headline count of all 30 write-ups, which nothing had ever verified

Reproduce with `raw/probe_inventory_selfcheck.py`; raw output in
`raw/raw-inventory-selfcheck.txt`. **15 checks, 0 unexpected.** Audits **my own
write-ups**, not EFO.

Queue item 34. `SYNTHESIS.md`'s inventory had been recounted **by hand five
times**, and each time the paragraph said *"not yet machine-checked"* — honest,
and useless. This closes it the way `probe_citation_audit.py` §F and
`probe_quote_accuracy.py` §E were closed: the probe **reads the prose and fails
the run** when it disagrees.

## The bigger gap it turned up

Surveying the branch to build the inventory check showed something worse:

> **Every write-up opens with `N checks, M unexpected`, and nothing had
> ever verified one of them.** There are 30 such claims.

That number is the *headline* of every document here — the first quantitative
claim a reader meets. It was hand-typed in every case. Each is now compared
against the raw output the same sentence names, and the run fails on any
disagreement.

All 30 currently match. That is luck rather than process, exactly as it was for
citations: nothing in the workflow checked them before this probe existed.

## What the recount found

The inventory paragraph was **already stale again** — it said 690 passing
checks where `raw/` holds **692**. Two checks had been added to
`probe_main_regression.py` after the last hand-recount. Sixth drift of the same
kind, and the last one that will go unnoticed.

| Quantity | Measured |
|---|---|
| files in `raw/` | 97 |
| probe scripts | 37 |
| raw outputs | 52 |
| provenance-attack scripts | 8 |
| passing checks | 707 |
| instrumented outputs | 36 |
| `UNEXPECTED` lines | 13, in 5 files |

The classification is checked for **exhaustiveness**, not just computed: a file
matching none of the three prefixes would otherwise vanish from the inventory
silently — the same shape as the module list that missed `errors.py` and the
`grep` that read `__pycache__`.

## A miscount of mine, caught by the probe

I first expected **30** checkable headline claims. The census found **29**, and
the census was right: my 30 came from `grep -l`, which counts *files* containing
the phrase in any form, while the census counts strict occurrences of
``` `raw/NAME.txt`. **N checks, M unexpected.** ```. One document mentions the
phrase without that shape.

Corrected **after** establishing why the two disagreed — not to whichever looked
tidier. And then not pinned at all: a hardcoded `29` would have gone stale the
moment this very note was added, which is the defect the probe exists to catch,
reintroduced inside the probe. The strict census is now checked against a
**loose** one — every `**N checks, M unexpected.**` anywhere must also be
matched by the pattern that pairs it with a raw filename — so both sides are
derived and neither can drift. The count is 30 with this note included. A second, smaller bug in the same round: the
mismatch check printed `len(mismatched)` while comparing against `[]`, so it
could never have passed. Both fixed before the run reported here.

## Scope

Static file reads of `reviews/claude-b/PR2/` at branch `HEAD`. The anchor is
checked (`/tmp/efo-prov` == `5694ab45`, clean) even though this probe audits the
review rather than EFO, because every count below is a count of work done
against it.

Not covered, stated rather than implied:

- It checks that a stated number matches the file it **names**. It does **not**
  check that the raw output was produced by the probe beside it — that is what
  the SHA-256 bindings are for, and those are still verified by hand at commit
  time.
- Documents stating a count without naming a raw output in the same sentence
  are not matched. That is why section D asserts the **claim count**: if a
  document changes shape and drops out of the census, the count falls and the
  run fails.
- Other hand-maintained numbers — issue counts, *"Fifteen components"*,
  per-table tallies — remain unchecked. Named as a gap; the citation and quote
  counts are covered by the other two probes.
- **MEASURED:** everything above. **REASONED:** nothing.

Pre-registered permissions unchanged: `gpu: false`, `network: false`,
`performance_metrics: false`; gates `allow_skips: false`,
`require_validation: true`, `require_known_answer_check: true`,
`require_independent_verification: true`.

**SUBMITTED, not VERIFIED.**

| Artifact | SHA-256 |
|---|---|
| `raw/probe_inventory_selfcheck.py` | `8a26df0326d934db44fba57cc78e6cb74d86970da6dc9785dbfe239c57714d2b` |
| `raw/raw-inventory-selfcheck.txt` | `007509b38aa62b3cd6bed2b1617c00e662b6dcf9a9d5d0527e1ca302e81b716f` |
