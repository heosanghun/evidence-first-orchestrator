# Which line produced which output — and why the cheap test is one-way

Reproduce with `raw/probe_output_provenance_lines.py`; raw output in
`raw/raw-output-provenance-lines.txt`. **21 checks, 0 unexpected.** A **map with
a negative result** — no issue filed, nothing retracted.

**Scope, stated first:** 77 outputs, 6 cited by `REPORT.md`, 2 derived marker
sets, 3 candidate discriminators, 1 known answer.

> **Updated 2026-08-03.** The corpus grew by one when item 59 landed, so the
> population moved **75 → 77** outputs and **39 → 41** undecidable (items 59 and 60). Those two
> counts are **pinned on purpose** — the population is the thing under
> discussion, so a corpus that grows must force this note to be re-read rather
> than silently re-measured. The pin is what said so.

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

| | outputs |
|---|---|
| carry an **anchor-only** token → placed on the anchor's line | **35** |
| carry a **`7a9553b`-only** token | **1** — `raw-w4-replay.txt`, my own item-55 probe, which names both refs by design |
| carry **neither** → **undecidable** | **41** |

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

| output | placed |
|---|---|
| `raw-attack2.txt` | **anchor** |
| `raw-attack2-cef5623.txt` | **anchor** |
| `raw-attack3.txt` | **anchor** |
| `raw-full-final.txt` | **anchor** |
| `raw-attack4.txt` | **undecidable** — and known from item 55 to be **mixed** |
| `raw-recheck-cef5623.txt` | **undecidable** |

Four of six are positively placed. The second undecidable one is left open:
item 46 re-ran its suite section (77/77, `OK`, exit 0) without asking which v2
produced it, and **this round does not answer that either**.

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

- It does **not** decide the 41. It says which 35 are placed, which one is
  mine, and that the rest are **open** — including one already known to be
  mixed.
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
- **MEASURED:** both module sets, the three-way scan of all 77 outputs,
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
| `raw/probe_output_provenance_lines.py` | `809c4cf3b1b29e3c134b52a37724db3b4a3e6b36e9b5331c1b6b1b35dcd82a57` |
| `raw/raw-output-provenance-lines.txt` | `4619f94324a4600460ebc67119917bb594aeff1de1d1db70612ada8b2760b847` |
