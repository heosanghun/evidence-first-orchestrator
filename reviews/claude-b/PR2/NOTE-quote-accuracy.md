# Do the quoted blocks say what the cited lines say? Two did not, and are now verbatim

Reproduce with `raw/probe_quote_accuracy.py`; raw output in
`raw/raw-quote-accuracy.txt`. **12 checks, 0 unexpected.** Audits **my own
write-ups**, not EFO.

`NOTE-citation-audit-of-this-review.md` proved every citation *resolves* to a
real line, and named the next gap in its own scope: **a citation can resolve
and still misquote.** This closes that gap where it is mechanically decidable,
and says plainly why the rest is not.

## Why only a subset — the first attempt was unusable

A first version paired any backticked span with the nearest citation on the
same line. It reported **16 "misses" out of 19**, and **fifteen were the
pairing being wrong, not the quote.** These write-ups routinely put two or
three citations and several inline spans in one sentence, so position does not
determine which span belongs to which citation. Shipping that checker would
have produced a wall of false accusations against my own documents — the
opposite of the point.

The decidable subset is: **exactly one citation on a line, immediately followed
by a fenced block.** There the block is unambiguously a quote of that location.
**27** such pairs exist.

| Disposition | Count |
|---|---|
| verbatim-verified against the cited range | 17 |
| adjudicated non-quotes | 10 |

> **Correction, 2026-08-03.** This section previously read *"Eleven such pairs
> exist"* with a table of 7 and 5 — which do not sum. The committed raw output
> beside it already said **12** pairs: the table had been refreshed when
> `NOTE-remaining-docs-adjudicated.md` added a pair and the prose had not. The
> inline-span count below was stale the same way (194 stated, 215 measured).
> Both were true when written and neither was true when read. Section E of the
> probe now **fails the run** when prose and output disagree, so the numbers
> above are this run's, not a memory of an earlier one.

The eight non-quotes are: two extractor artifacts (the citation sits *inside* a
fenced listing, so the following prose paragraph was captured as the "block");
**five** blocks that are **probe output**, presented as output and not claiming
to be source; and one **deliberate before/after** —
`ADDENDUM-git-replace-regression.md` quotes the argument list that was
*removed*, which is the whole point of the regression.

Probe-output blocks have been flagged **on the round the note was written**
three times now — `NOTE-remaining-docs-adjudicated.md` once and
`NOTE-class-2b-is-a-census-now-seven-of-seven.md` twice. The self-check working
as intended rather than as a historical artifact.

## Two blocks were condensed, and are now verbatim

Before this probe, two fenced blocks read as verbatim source but were reflowed
renderings — accurate in substance, not literally present:

- **`ADDENDUM-git-replace-regression.md`**, `provenance.py:33-42` — a nine-line
  argument list collapsed onto one line, with `repo` / `args` where the source
  says `repository` / `arguments`.
- **`ADDENDUM-proxy-status-freshness.md`**, `monitor/collector.py:893-912` — a
  parenthesised multi-line `elif` flattened to one line.

Neither changed what the finding says. Both are now the verbatim source.

**The fix was to make the document literal, not the checker lenient.**
Whitespace normalisation was tried *first* and did not resolve them — the
difference was tokens, not indentation. Loosening the comparison until the
documents passed would have been the wrong direction, and it is worth naming
because it was the tempting one.

## A probe bug that looked like a document bug

After fixing both quotes, the collector one *still* failed. The document was
right: the quoted line sits at `collector.py:904`, and the citation reads
`:893-912`, but my window was built from the **start line only** — `start-8` to
`start+10`, i.e. 886–903. The range end was parsed and then dropped.

That is the fifth harness bug of this shape in the review, and it is exactly
the class the method warns about: *a result that looks like a code defect is
more often my misclassification.* Here it looked like a **document** defect and
was a **checker** defect. The window now spans `start-8` to `end+10`.

## What stays undecidable, with a count

**268 inline backticked spans share a line with a citation.** They are not
checked, and cannot be by position:

- *"`doctor.py:109` interpolates `agent_id` into a path"* — the span **is** a
  quote from that line.
- *"`workspace.py:1182` reads it by direct index"* — the span is **not**.

Nothing in the text distinguishes them, and guessing produced the 15-in-19
false-positive rate above. Named as a gap rather than papered over. Closing it
would need the write-ups to adopt a convention — a marker for "this span is
verbatim from the cited line" — which is a change to how the documents are
written, not to the checker.

## Scope

Every `(citation, fenced block)` pair in the write-ups where the pairing is
unambiguous, compared whitespace-insensitively against the full cited range at
`main` `5694ab45` (precondition verified: `HEAD` matches, `git status
--porcelain` empty). Static analysis only; nothing was executed against a
workspace.

Not examined: inline spans (268, above); whether a *paraphrase* in prose
accurately characterises the cited code, which is a judgement no string
comparison can make.

Pre-registered permissions unchanged: `gpu: false`, `network: false`,
`performance_metrics: false`; gates `allow_skips: false`,
`require_validation: true`, `require_known_answer_check: true`,
`require_independent_verification: true`.

**SUBMITTED, not VERIFIED.**

| Artifact | SHA-256 |
|---|---|
| `raw/probe_quote_accuracy.py` | `498c8bc3736fd338428d0a169e412348223ecbee2d056bda4bdbe42ccfd2de07` |
| `raw/raw-quote-accuracy.txt` | `8ec3cd7f3b04600e1a776287abcabe12c2a1292ffe8b27766435888dd7eedad0` |
