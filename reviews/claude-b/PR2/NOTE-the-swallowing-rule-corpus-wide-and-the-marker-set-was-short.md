# The swallowing rule across all 83 outputs — two verdicts move, and the marker set was short

Reproduce with `raw/probe_swallowed_marks_corpus_wide.py`; raw output in
`raw/raw-swallowed-marks-corpus-wide.txt`. **31 checks, 0 unexpected.**
A **map that corrects two rules of mine**. No issue filed, nothing about EFO
claimed.

**Scope, stated first:** 83 outputs, 2 marker sets, 1 swallowing rule, 2
verdict changes under the sweep, 2 under the correction, 1 incomplete marker
class found, 5 doubled slots.

> **Updated 2026-08-03, same day:** item 71's output landed and is placed on the
> anchor's line, so the population is **84** at `HEAD` and the corrected union's
> anchor count **37 → 38**. Everything else below is unchanged, and the pin in
> the probe is what forced this line. **Item 72's output** is undecidable, so
> the population is **85** and the open set **37 → 38**.

## What item 67 left open, in its own words

That round applied the swallowing rule — *a marker occurrence that sits inside
a longer identifier is not evidence* — to **the four mixed outputs only**, and
said plainly that a **corpus-wide sweep was UNCHECKED**. This is that sweep.

## The sweep: 2 of 83

Dropping every marker occurrence whose own edge abuts an identifier character,
exactly two verdicts change:

| output | before | after |
|---|---|---|
| `raw-full-final.txt` | mixed | **divergent** — item 67's result, now reached **by rule** rather than by hand |
| `raw-class2b-census.txt` | anchor | **undecidable** — **new** |

**81 of 83 are unaffected.** The rule is not a rewrite of the classification;
it is a check *on* it, and it fires twice.

## …and the new one is not a mis-placement

`raw-class2b-census.txt` carries exactly two anchor marks and **both are
swallowed**:

```
independence.py       inside: test_independence.py:161  attests 'antigravity' …
submission_snapshot   inside: test_submission_snapshot_prevents_identity_laundering …
```

By the rule, the file loses all anchor evidence. But `test_independence.py` is
an **anchor-only test module** — the file is carrying real anchor evidence, and
the marker that matched was simply the wrong one.

The parsed rule wants a unittest id, `tests.<module>.<class>.<method>`. This
file writes a **path with a line number**. `TEST_ID.findall` returns `[]` here,
measured rather than assumed.

> **A test module can be named two ways and only one of them was matched. The
> marker set was INCOMPLETE — the output was never mis-placed.**

This is the third marker layer at which the same trap has recurred — item 61's
bare module token, item 67's string literals, and now test-module filenames.
Each time the fix has been to widen what counts as a name, and each time the
*previous* layer looked complete.

## Corrected, and re-measured

Adding the anchor-only and divergent-only test-module **filenames** — six
markers, none of them already present:

| | before | after |
|---|---|---|
| anchor's line | 36 | **37** |
| divergent line | 5 | **6** |
| mixed | 4 | **3** |
| **undecidable** | 38 | **37** |

Exactly two outputs move under both corrections together:

- `raw-full-final.txt` — mixed → **divergent** (loses a mixture)
- `raw-proxy-mocks.txt` — undecidable → **anchor** (newly placed)

And `raw-class2b-census.txt` **keeps its verdict and changes its evidence**.
A sweep that reported only changed verdicts would have shown nothing there —
which is the case this round exists to catch.

## A second defect, in the instrument rather than the result

The marker "sets" are **concatenated tuples whose groups overlap**, so their
length counts **slots, not markers**:

| | slots | distinct |
|---|---|---|
| anchor | 162 | **160** |
| divergent | 309 | **306** |

The doubled entries are `transport_independence`, `audit-independence`,
`transfer-orchestrator`, `independence_dimensions` — and `job_runner.py`,
which is doubled **inside the derivation itself**, being both a divergent-only
module filename *and* a string literal in that source. So the overlap is not
only hand-versus-derived; two derived groups intersect, which no count of
either group alone would show.

Of the **six** tokens I had added by hand as "known" markers, **four were
already produced by the derivation**. Only `transfer_orchestrator` and
`orchestrator_transferred` are genuinely hand-supplied. The derivation was
stronger than I had credited it.

De-duplicating changes **no verdict** — 0 of 83, measured rather than assumed,
because presence is presence. It would have mattered to any tally of
**occurrences**, and this review has published such tallies.

I found this only because the two counts disagreed with the 161/306 I had
pre-measured by hand. **Naming what a count counted is what turned a mismatch
into a finding** rather than into a corrected expectation.

## One more, in the write-up rather than the measurement

The check *"one is swallowed inside a test module filename"* first passed the
**entire scanned file** as its observed value. It passed — and dumped another
probe's whole output, including its own `0 unexpected result(s)` banner, into
this raw file. Bounded to the single matching line. A check whose observed
value is the whole haystack is not a check; it is a quotation that cannot fail.

## What this does not establish

- It does **not** retract item 67. That round's four are unchanged, and its
  `raw-full-final.txt` result is reproduced here by rule rather than by hand.
- It does **not** claim the marker set is now complete. It was found short by
  one class, and another class could be short the same way.
- It does **not** decide the **37** still open. They carry no marker of any
  kind, swallowed or live.
- The swallowing rule is a **judgement stated in the source**: a match counts
  as swallowed only where the marker's *own* edge is an identifier character.
  Item 67 measured why the looser version is wrong.
- It does **not** file an issue. Nothing here is about EFO's behaviour; it is
  about the provenance of evidence this review inherited, and about two rules
  of mine.
- No network, no GPU, no workspace built. Two refs read and **both named**.
  The anchor's working tree is untouched, and it does **not** touch `main` or
  another agent's branch.
- **MEASURED:** both marker sets as slots and as markers, the doubled entries,
  the hand-versus-derived split, the corpus-wide sweep, the two verdict
  changes, every swallowed occurrence in the new one, the corrected sets, the
  final union. **REASONED:** nothing.

Pre-registered permissions unchanged: `gpu: false`, `network: false`,
`performance_metrics: false`; gates `allow_skips: false`,
`require_validation: true`, `require_known_answer_check: true`,
`require_independent_verification: true`.

**SUBMITTED, not VERIFIED.** Re-running my own evidence is a re-run, not
independent confirmation.

| Artifact | SHA-256 |
|---|---|
| `raw/probe_swallowed_marks_corpus_wide.py` | `f204ff7507454f211031d4c7b550eae851e81c88f69b80a42485a349f858f2d0` |
| `raw/raw-swallowed-marks-corpus-wide.txt` | `e746253e9d49c0342524a6a51206538d197208e1df9824fae22b9369d88db819` |
