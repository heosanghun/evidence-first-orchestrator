# Every citation this review makes, audited — three were wrong, all three now corrected

Reproduce with `raw/probe_citation_audit.py`; raw output in
`raw/raw-citation-audit.txt`. **26 checks, 0 unexpected.**

This audits **my own write-ups**, not EFO. Every defect it reports is a defect
in the review.

## How it started

Queue item 24 was "read `README.md` end to end". Step one was checking the four
anchors the queue listed. Two did not resolve, and one of them could not
possibly resolve: `README.md:590` [retracted], in a file of 452 lines.

A citation that does not resolve is the exact failure this project exists to
prevent — a claim attributed to a source that does not say it. So instead of
reading one document, I audited every citation on the branch.

## The audit

**266 live citations across 81 documents, over 25 distinct files.**
(126 across 30 when first written; re-run after every write-up change, and
section F now **fails the run** if this sentence and the output disagree.) Every cited
file exists at `main`; every cited line is within its file. The run fails on
any that is not.

**15** more citations appear inside dated correction banners or carry an
inline `[retracted]` marker. Those are excluded
as *retractions rather than claims* — a banner quotes the citation it is
retracting, so counting it as live would make a correction indistinguishable
from the error it corrects, and no document could ever be fixed. The exclusion
is stated in the probe rather than applied silently.

The heaviest-cited files are the ones the findings rest on:
`workspace.py` (34), `README.md` (20), `provenance.py` (11),
`docs/ARCHITECTURE.md` (7), `doctor.py` (6), `adapter.py` (6).

## The three errors

### 1. `README.md:590` [retracted] → `cli.py:590` (`NOTE-cli-surface-holds.md`)

The phrase *"Validate a submission bundle"* appears in **no Markdown file** in
the repository. It is an argparse `help=` string at `cli.py:590`.

**The line number was right and the file was wrong**, which is exactly why it
read as plausible for eleven rounds. It matters for the argument: I cited it as
*documented intent*, and a `help=` string is a weaker basis than README prose.
The conclusion — that `evidence check`'s looser path handling is a convenience
and not a bypass — is unchanged, because it never rested on the quote. It rests
on the measurement that the command appends nothing to the ledger.

### 2. `README.md:336-337` → `README.md:335-336` (`NOTE-dashboard-and-errors-hold.md`)

Off by one. The bind-guard sentence is real and says what the note says it
says; only the span was wrong. Corrected because a reader following the
citation lands one line late.

### 3. `REPORT.md` reviews a different branch and never said so

Two of its citations resolve against **neither** `main` **nor** the branch's
former base:

| Ref | `workspace.py` |
|---|---|
| `origin/main` | 1562 lines |
| `dad3f4c4` (former base) | 920 lines |
| **`origin/codex/meta-orchestration-v2`** | **2528 lines** |

`workspace.py:2366` [retracted against main] is real on the third. `docs/META_ORCHESTRATION_V2.md`
exists there and nowhere else.

So `REPORT.md` reviewed `codex/meta-orchestration-v2`. **Its citations were
correct for their subject all along** — what was missing was the subject.
Fixed by labelling the document, not by editing citations that were right.

This is the second time in two rounds that an unnamed commit produced a
mystery: last round it was my branch silently based on an ancestor of main.
Naming the ref you are reviewing is cheap; not naming it makes correct work
look invented.

## What this says about the process

The two errors in section 1 and 2 were both in **NOTEs**, not in filed issues.
Section D of the probe spot-checks the nine anchors the filed issues rest on —
`#17`, `#18`, `#19` and the byte-exactness NOTE — and all nine contain their
quoted fragment within a two-line window.

That is luck, not process. **Nothing in my workflow checked a citation before
this probe existed.** It does now, and it is cheap to re-run.

## A convention this note introduces

A document that reports on bad citations necessarily *contains* them, and
`probe_citation_audit.py` would flag its own report. Rather than exempting a
filename — which would be self-serving and would hide a real error if one
appeared here later — a retracted or other-ref citation is marked inline with
**`[retracted]`**, and the probe skips citations on a line carrying that
marker. The marker is visible to a reader, so nothing is hidden; it is
mechanical, so nothing is judged by filename; and it fails loudly if I mark a
citation that is actually live, because the audit then stops checking a claim
I am still making.

## Scope

Every `path:line` and `path:a-b` in the Markdown write-ups on this branch,
resolved against `main` `5694ab45` (precondition verified: `HEAD` matches and
`git status --porcelain` is empty). Bare module names are resolved against the
package, docs, functions, assets, monitor and tests directories, the way a
reader would read them.

Fragment accuracy was **not** examined here — only the nine finding-bearing
anchors in section D. That gap is now closed for the decidable subset by
`NOTE-quote-accuracy.md`, which found two condensed quotes and made them
verbatim; 347 inline spans remain undecidable by position.

Pre-registered permissions unchanged: `gpu: false`, `network: false`,
`performance_metrics: false`; gates `allow_skips: false`,
`require_validation: true`, `require_known_answer_check: true`,
`require_independent_verification: true`.

**SUBMITTED, not VERIFIED.**

| Artifact | SHA-256 |
|---|---|
| `raw/probe_citation_audit.py` | `062dc7b8a2eb4fdeb82f05e33d0fe7d08c97c9133222e31241d590e6af2ad9f9` |
| `raw/raw-citation-audit.txt` | `c8433c594a874517098b21da9cea9bca631238653df462e362aea078a454c282` |
