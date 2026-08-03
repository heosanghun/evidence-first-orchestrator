# Which line produced which output — and why the cheap test is one-way

Reproduce with `raw/probe_output_provenance_lines.py`; raw output in
`raw/raw-output-provenance-lines.txt`. **26 checks, 0 unexpected** *(21 as
published; the corrected probe adds five)*. A **map with a negative result** —
no issue filed, nothing retracted.

**Scope, stated first:** 77 outputs, 6 cited by `REPORT.md`, 2 derived marker
sets, 3 candidate discriminators, 1 known answer.

> **CORRECTED 2026-08-03 by item 61 — this note's headline result was wrong.**
> The marker set below ended with a **bare `"independence"`** substring beside
> the precise `independence.py`. It matches `independence_dimensions`, a key
> that appears in **no commit of the anchor's ancestry** and is introduced by
> `7a9553b` itself, and `test_known_independence_cases`, a method in the
> divergent-line module `test_meta_orchestration.py`. Eleven of the 35 outputs
> placed on the anchor rested on that token alone, and **four were placed
> backwards**.
>
> | | published here | corrected |
> |---|---|---|
> | anchor's line | 35 | **27** |
> | divergent line | 1 | **5** |
> | undecidable | 41 | **45** |
>
> **Updated again 2026-08-03:** item 62's output landed, so the population
> moves **77 → 78** and undecidable **45 → 46**; item 63's pushes it to
> **79 / 47**. The pin is what said so, twice.
>
> **Item 64 narrowed the open set** without changing this test: a corrected
> string-literal difference places **12** of the 47 (9 anchor, 2 divergent, 1
> mixed), agreeing with **19 of 19** placements here and contradicting none.
> **35 remain unplaceable by any class measured.** This probe's own numbers
> are unchanged — item 64 is an additional test, reported beside it.
>
> **Item 65's output** moves the population to **80** and the anchor placement
> to **28**; the undecidable count is unchanged at **47**. The pin said so
> again.
>
> **Every table below is superseded by
> `NOTE-the-suite-size-decided-it-and-a-substring-reversed-four.md`**, which
> carries the measurement. Two things here survive unchanged: the test still
> has the proven false negative (§ *"…and the test has a proven false
> negative"*), and both extra discriminators were measured rather than
> assumed. The probe is corrected in place, not superseded.
>
> The known answer that would have caught it was inside the document being
> classified: `REPORT.md:437-438` names `4aa47ca6` as its subject, a commit on
> the divergent line. The corrected placement agrees with that declaration;
> this one contradicted it.

> **Updated 2026-08-03.** The corpus grew by one when item 59 landed, so the
> population moved **75 → 77** outputs and **39 → 41** undecidable (items 59 and 60). Those two
> counts are **pinned on purpose** — the population is the thing under
> discussion, so a corpus that grows must force this note to be re-read rather
> than silently re-measured. The pin is what said so. Item 61's output is
> **excluded** rather than counted, for the same reason this note's own output
> is: it prints both marker sets. The population therefore stays **77**, and
> the corrected undecidable count is **45**.

## The question

Item 55 established that `raw-attack4.txt` **mixes two lines of history** — its
W1/W2/W2b compare against `f827f29`, the anchor's ancestor, while W4–W6b drive
`transfer_orchestrator`, which exists only at `7a9553b`, a commit that is **not**
an ancestor of the anchor. Item 46 catalogued `REPORT.md`'s six cited outputs
and re-ran two; none of that asked **which v2 produced them**.

## The markers, derived rather than named

The module-set difference between the two trees:

```
    only at 7a9553b : identity.py, job_runner.py
    only at anchor  : independence.py
```

A **two-way** discriminator — stronger than the one-way test the item proposed,
because an output can be placed on *either* line rather than merely flagged as
belonging to the other one.

## The scan

| | outputs (**as published — see the correction above**) |
|---|---|
| carry an **anchor-only** token → placed on the anchor's line | ~~**35**~~ → **27** → **28** at `HEAD` |
| carry a **`7a9553b`-only** token | ~~**1**~~ → **5**; `raw-w4-replay.txt` names both refs by design, and the other four were placed backwards here |
| carry **neither** → **undecidable** | ~~**41**~~ → **45** → **47** at `HEAD` |

## …and the test has a proven false negative

**`raw-attack4.txt` is in the undecidable set** — yet item 55 placed its
W4–W6b on `7a9553b`'s line, by the **absent API and the ancestry**, not by any
token appearing in the output. The file says *"signed orchestrator handoff"* in
prose and never names the identifier.

> **So "no marker" does not mean "the anchor's line."** The test **narrows** the
> population; it does not decide it. A filter checked in only one direction is
> exactly what item 50 refuted, and here the ground truth to check it against
> already existed.

## `REPORT.md`'s six

| output | placed here | **corrected (item 61)** |
|---|---|---|
| `raw-attack2.txt` | anchor | **divergent** |
| `raw-attack2-cef5623.txt` | anchor | **divergent** |
| `raw-attack3.txt` | anchor | **divergent** |
| `raw-full-final.txt` | anchor | **divergent** — its 70 test ids match `7a9553b`/`4aa47ca` exactly |
| `raw-attack4.txt` | undecidable | **mixed** — unchanged, item 55 |
| `raw-recheck-cef5623.txt` | undecidable | **`cef5623`** — by its suite size, `Ran 77 tests` |

This note said **four of six are positively placed** on the anchor's line.
The corrected answer is **none of them are** — which is what `REPORT.md`
declares about itself. The second undecidable one is no longer open: item 61
decided it from the one thing this scan could not see, a **suite size**.

## Two more discriminators, measured rather than assumed

| candidate | result |
|---|---|
| the CLI `status` JSON shape | **identical on both lines** (`['status', 'tasks']`) — **ruled out by measurement**, not by guessing |
| the CLI subcommand list | **is** a discriminator (`workspace` and `audit` exist only at `7a9553b`) but appears in only **2 of 77** outputs, neither of them `raw-attack4.txt` |

## The self-reference, excluded and counted

This probe's own output lives **inside the corpus it scans**, and it **prints
the `7a9553b`-only tokens** — so an unexcluded run classifies *itself* as coming
from the other line. Measured, not theorised: the first run reported one **extra**
output and **2** carrying other-line tokens.

Excluded **structurally**, from this script's own filename rather than a
hardcoded string, and the exclusion is **counted** so a second cannot appear
unnoticed. **This probe's own classification is therefore the one number here
that is not machine-checked**, and it is read off the section beside it — the
same treatment `probe_inventory_selfcheck.py`'s tally got.

## What this does not do

- It does **not** decide the ~~41~~ ~~45~~ **47**. It says which ~~35~~ **27** sit on
  the anchor's line and which **5** on the divergent one, and that the rest are
  **open** — including one already known to be mixed.
- It does **not** re-run any catalogued output, and does **not** retract item
  46's catalogue or its two re-runs.
- It does **not** claim the token sets are the only possible markers. Two more
  were considered; one was **ruled out by measurement** and one is real but
  almost never present.
- It does **not** file an issue. Nothing here is a defect in EFO — it is a fact
  about the **provenance of evidence this review inherited**.
- No network. Two local checkouts and one `tempfile` workspace pair, removed
  before the results print. The anchor's working tree is untouched, and it does
  **not** touch `main` or another agent's branch.
- **MEASURED:** both marker sets over the whole of each line, the four-way
  scan of all 80 outputs,
  `REPORT.md`'s six, both `status` shapes, the usage-line census, item 55's two
  quoted sentences, the self-exclusion. **REASONED:** nothing.

Pre-registered permissions unchanged: `gpu: false`, `network: false`,
`performance_metrics: false`; gates `allow_skips: false`,
`require_validation: true`, `require_known_answer_check: true`,
`require_independent_verification: true`.

**SUBMITTED, not VERIFIED.** Re-running my own evidence is a re-run, not
independent confirmation.

| Artifact | SHA-256 |
|---|---|
| `raw/probe_output_provenance_lines.py` | `511cadbef74fd414701748eaf954b152efc5e1a632413fc91962552f06185d9f` |
| `raw/raw-output-provenance-lines.txt` | `afd98f4d8a9ad589f125bc34f80d806bb6d153eb8b21687e0b829ac93c93c918` |
