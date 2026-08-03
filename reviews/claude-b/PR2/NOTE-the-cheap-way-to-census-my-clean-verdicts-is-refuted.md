# The cheap way to census my own `clean` verdicts is refuted — by a case I had already measured by hand

Reproduce with `raw/probe_clean_verdict_census.py`; raw output in
`raw/raw-clean-verdict-census.txt`. **16 checks, 0 unexpected.** A **lead**, not
a verdict — **no issue filed, and not one `clean` verdict retracted.**

**Scope, stated first:** **21** rows in SYNTHESIS whose verdict is `clean`,
**24** distinct notes they cite, **22** whose probe file can be located. Nothing
in EFO is executed here; this reads my own probe sources and my own SYNTHESIS.

> **Updated 2026-08-03.** Every number in this note moves as the seven are
> adjudicated. **Items 53, 56, 59, 62 and 65** have now taken five of them, and each
> amended its clean row to cite a second note, so the set cites **27** notes
> over **24** locatable probes, **20** of which drive; fourteen sit on a component
> with an open issue, **twelve** are adjudicated and **two** remain. The probe
> re-derives all of them — none is left at the value this note first published.

## The question, and why one round is not enough for it

Item 47 narrowed *"`util.py` is clean"* by asking a single question of it: **what
input class did its 46 checks actually feed?** The answer — all strings, zero
non-strings — did not retract the verdict, but it said what the verdict rested
on. Item 50 asked the same question of **every** `clean` row.

Twenty-two notes adjudicated one at a time, by hand, is more than one round. The
item anticipated that and said to scope first and, if the population is too
large, take the subset whose component carries an open issue. So this round
tried the cheap way first.

## Four of the twenty-two are not even candidates

A probe that never calls into the package has no input class to feed. Parsing
each probe's **real** `ast.Import` / `ImportFrom` nodes splits the twenty-two:

| | probes |
|---|---|
| **static census** — reads the AST, executes nothing | `probe_dynamic_stores.py`, `probe_dynamic_subscripts.py`, `probe_implicit_exceptions_all_modules.py`, `probe_parameter_subset.py` |
| **drives the component** | the other **18** |

> **A filter bug of mine, caught before it shipped.** The first version
> regex-matched `import evidence_orchestrator` *anywhere* in the source and so
> classified all twenty-two as executing — including these four, which only
> **quote** that line inside the census they perform. Matching syntax by text
> when the question is about syntax is exactly the substring trap; parsed
> instead. **0 static → 4 static.**

## The cheap proxy, and the known answer that kills it

The proxy: does the probe contain a call passing `None`, a bare int, an empty
list or an empty dict? It flags **18 of 18** driving probes — a filter that
selects everything is already suspicious, and there is a case where the truth is
known.

```
    probe_util_and_lock.py     proxy score: 5 non-string arguments
    item 47, measured by hand: NOT ONE of its 46 checks feeds a
                               non-string to a util function
```

The five `None`s the proxy counts are `re.search(..., None)` and default
arguments — **the probe's own plumbing**, not input handed to the component. One
hand-checked case is enough to refute a filter, and this is the one case I had
already hand-checked.

So the honest result of item 50 is that **the cheap census cannot answer it.**
Shipping eighteen verdicts derived from a filter I can show to be wrong on its
single checkable case would be precisely the failure this review exists to
prevent. *Checking a filter against ground truth in both directions* is the rule;
here ground truth existed, and the filter failed it.

## What the round delivers instead: the population, named

| component | issue | probe |
|---|---|---|
| `dashboard.py`, `errors.py` | #19 | `probe_dashboard_and_errors.py` |
| `workspace.py` implicit exceptions | #19 | `probe_implicit_exceptions.py` |
| ~~`ledger.projected_tasks`~~ | *(done — item 62)* | `probe_projected_tasks.py`, `probe_projected_tasks_input_class.py` |
| ~~`proxy_submit` + grant~~ | *(done — item 65)* | `probe_proxy_grant.py`, `probe_proxy_grant_duration_class.py` |
| ~~`util.py`, `lock.py`~~ | *(done — item 47)* | `probe_util_and_lock.py`, `probe_util_uncovered_input.py` |
| ~~`provenance.py` byte-exactness~~ | *(done — item 53)* | `probe_byte_exactness.py`, `probe_byte_exactness_input_class.py` |
| ~~`cli.py`~~ | *(done — item 56)* | `probe_cli_surface.py`, `probe_cli_typed_options.py` |
| ~~`monitor/collector.py` (redaction)~~ | *(done — item 59)* | `probe_collector_redaction.py`, `probe_collector_malformed_output.py` |

**Fourteen** driving probes sit on a component with an open issue — more than
the eight components, because `util.py`/`lock.py`, `provenance.py`
byte-exactness, `cli.py` and the collector are each **one** component with
**two** probes. Twelve are already adjudicated. **Two remain**, and that is the population for the next rounds: one at a time, by
hand, which is the only method shown here to work.

## The self-reference, excluded and asserted

This note gets a SYNTHESIS row of its own, and a census of `clean` rows that
counted itself would be the self-reference defect all over again. It does not
get counted — its verdict is a **lead**, not `clean`. That is a fact about the
row rather than a convenience, so the probe **asserts** it: exactly one row
names this note, and it is not in the censused set.

## What this does not do

- It does **not** retract any `clean` verdict. Nothing here measures a
  component; it measures which of my probes could be censused cheaply, and the
  answer is none of them.
- It does **not** claim the 18 fed only well-formed input, nor that they did
  not. **That question is left open**, with its population named.
- It does **not** file an issue, and does **not** touch `main`, the anchor's
  working tree, or another agent's branch.
- It did **not** execute any EFO component — static AST reads of my own probe
  sources and of `SYNTHESIS.md` only.
- **MEASURED:** every count, the static/driving split, the proxy's score for the
  known-answer case, the self-exclusion. **REASONED:** nothing — the refutation
  is item 47's hand measurement, already published.

Pre-registered permissions unchanged: `gpu: false`, `network: false`,
`performance_metrics: false`; gates `allow_skips: false`,
`require_validation: true`, `require_known_answer_check: true`,
`require_independent_verification: true`.

**SUBMITTED, not VERIFIED.** Re-running my own evidence is a re-run, not
independent confirmation.

| Artifact | SHA-256 |
|---|---|
| `raw/probe_clean_verdict_census.py` | `32eeb31b5c9ed2ce3a16589857e753f644927f5705ae8cc89b9a78e36f025722` |
| `raw/raw-clean-verdict-census.txt` | `5de2bf31c41cc00ea0b095169db40d25551bb2ff346acc8c31003e55aa4c3a25` |
