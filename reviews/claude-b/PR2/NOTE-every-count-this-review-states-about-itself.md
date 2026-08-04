# The inventory is machine-checked now — and so is the headline count of every write-up, which nothing had ever verified

Reproduce with `raw/probe_inventory_selfcheck.py`; raw output in
`raw/raw-inventory-selfcheck.txt`. **25 checks, 0 unexpected.** Audits **my own
write-ups**, not EFO.

Queue item 34. `SYNTHESIS.md`'s inventory had been recounted **by hand five
times**, and each time the paragraph said *"not yet machine-checked"* — honest,
and useless. This closes it the way `probe_citation_audit.py` §F and
`probe_quote_accuracy.py` §E were closed: the probe **reads the prose and fails
the run** when it disagrees.

## The bigger gap it turned up

Surveying the branch to build the inventory check showed something worse:

> **Every write-up opens with `N checks, M unexpected`, and nothing had
> ever verified one of them.** There are 56 such claims.

That number is the *headline* of every document here — the first quantitative
claim a reader meets. It was hand-typed in every case. Each is now compared
against the raw output the same sentence names, and the run fails on any
disagreement.

All 56 currently match. That is luck rather than process, exactly as it was for
citations: nothing in the workflow checked them before this probe existed.

## What the recount found

The inventory paragraph was **already stale again** — it said 690 passing
checks where `raw/` holds **692**. Two checks had been added to
`probe_main_regression.py` after the last hand-recount. Sixth drift of the same
kind, and the last one that will go unnoticed.

| Quantity | Measured, 2026-08-03 (this run) |
|---|---|
| files in `raw/` | 149 |
| probe scripts | 63 |
| raw outputs | 78 |
| provenance-attack scripts | 8 |
| passing checks | 1117 |
| instrumented outputs | 61 |
| `UNEXPECTED` lines | 12, in 5 files |

> **Correction, 2026-08-03.** The `UNEXPECTED` row read **13**, and so did every
> earlier round of this table. The tally counted the marker as a **substring**,
> so a legend line in `raw-attack-prov5-main.txt` reading *"Any
> `'!! UNEXPECTED !!'` above is a finding"* was itself counted as a finding. It
> is now counted by **position** — bracketed at the start of a line, or bare at
> the end — and the total is 12. No finding changed; a sentence *about* a marker
> had been counted as the marker.
>
> The same rule had a second victim in the same run: a probe with a check
> *named* after the `[ok]` token reported its 10 checks as 12. And the first fix
> was worse than the bug — `endswith` on both markers matched 163 sentences
> ending in the letters `ok` and took this table's 740 to 922. Caught by a
> known-answer check before it was believed. Detail in
> `NOTE-two-attack-scripts-ran-against-the-stale-base.md`.

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
derived and neither can drift. The count is 56 as of this round. A second, smaller bug in the same round: the
mismatch check printed `len(mismatched)` while comparing against `[]`, so it
could never have passed. Both fixed before the run reported here.

## The prose counts, closed in the same probe

The gap named above was the last population, and measuring it found **three
stale numbers** — one of them in the very section that describes the drift
pattern:

| Claim | Stated | Measured |
|---|---|---|
| *"Fifteen components were probed and found sound"* | 15 | **16** clean rows |
| class 2b's *"Two instances now"* | 2 | **7** rows in its own census table |
| *"Four classes that repeat"* | 4 | **6** `###` subsections |

All three are now **derived from SYNTHESIS's own tables** and fail the run when
the prose disagrees. The class-2b one is the sharpest: I turned that section
into a seven-instance census in the previous round and left its opening
sentence saying two.

The `Four` → `Six` change is a real reclassification, not a typo: sections `2b`
and `3b` were sub-cases when written and have since grown into classes of their
own — `2b` is now a seven-instance census — so the heading counts them.

**A checker bug of mine in the same section:** the heading test first searched
for the **digit** `6` in a heading that spells its number as a **word**, so it
could never pass. Third instance of a checker defect wearing the costume of a
document defect. Fixed by resolving the word.

**Every number in this review is now either machine-checked or carries a date.**

## A self-reference this probe could not check, and does not pretend to

The probe's own raw output lives **inside the corpus it measures**, and that
breaks two things:

- **The tally.** When the tally is computed, `raw-inventory-selfcheck.txt` still
  holds the *previous* run's text, so the probe measures a stale self. Iterating
  copy-and-recount **five times never converged**: each failing run wrote
  `UNEXPECTED` lines that then broke the next run's tally.
- **The headline census.** This note claims *"N checks, 0 unexpected"* about the
  run now executing, against the file that run is about to write. It settled at
  a stable **17 ok / 1 unexpected** — a failure no amount of re-running clears.

Both are now excluded, structurally rather than conveniently, and both
exclusions are **counted** so a second cannot appear unnoticed:

- the tally skips this probe's own output — SYNTHESIS's inventory paragraph
  says so;
- the headline census skips the one self-referential claim, and asserts that
  **exactly one** is skipped, naming it.

**So this note's own headline is the single number in the review that is not
machine-checked.** It is verified by reading the raw output beside it, the way
every number here was verified before this probe existed. Saying that is the
point; a self-check that quietly graded its own report would be worse than none.

The probe reaches a clean fixpoint: two consecutive runs agree at **25 checks,
0 unexpected**.

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
- ~~Other hand-maintained numbers — issue counts, *"Fifteen components"*,
  per-table tallies — remain unchecked.~~ **Closed 2026-08-03**, see below.
- **MEASURED:** everything above. **REASONED:** nothing.

Pre-registered permissions unchanged: `gpu: false`, `network: false`,
`performance_metrics: false`; gates `allow_skips: false`,
`require_validation: true`, `require_known_answer_check: true`,
`require_independent_verification: true`.

**SUBMITTED, not VERIFIED.**

| Artifact | SHA-256 |
|---|---|
| `raw/probe_inventory_selfcheck.py` | `9abb9ad8b22bed303339d5bdc4a2edea57581e116b9e6c6214992e2b3a9ce9f5` |
| `raw/raw-inventory-selfcheck.txt` | `f19fd988c05f3b8308636704ec0ddab46d12699d859bcad750fcc63d08cd3192` |
