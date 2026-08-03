# The suite size decided it — and finding out showed a substring had reversed four

Reproduce with `raw/probe_recheck_line_and_the_substring_that_reversed_four.py`;
raw output in `raw/raw-recheck-line-and-the-substring-that-reversed-four.txt`.
**58 checks, 0 unexpected.** A **correction to my own published note** —
no issue filed, and no finding of this review retracted.

**Scope, stated first:** 77 outputs, 6 cited by `REPORT.md`, 20 commits swept,
3 suites run, 2 marker sets derived, 1 known answer, 4 reversals.

## The defect is mine, and it comes first

Item 58 ended its anchor marker set with a **bare `"independence"`** — a
substring, sitting beside the precise `independence.py`:

```python
ANCHOR_TOKENS = tuple(only_anchor) + ("audit-independence", "independence")
```

That token matches two things that belong to the **other** line:

| string it matches | where it actually lives |
|---|---|
| `independence_dimensions` | a JSON key appearing in **no commit of the anchor's ancestry**, introduced by `7a9553b` itself |
| `test_known_independence_cases` | a method in `test_meta_orchestration.py`, a module **only** the divergent line ever had |

Of the 35 outputs item 58 placed on the anchor's line, **11 rest on that bare
token alone**. Four of them are placed **backwards**, and seven more had no
line evidence at all.

| | item 58 published | corrected |
|---|---|---|
| anchor's line | 35 | **27** |
| divergent line | 1 | **5** |
| undecidable | 41 | **45** |

## The known answer was inside the document being classified

`REPORT.md:437-438` names its own subject:

```
Subject under review: `heosanghun/evidence-first-orchestrator` @
4aa47ca602d36c22cbaf2ce63fa442ee398c317e, working tree clean.
```

`4aa47ca` is an **ancestor of `cef5623`** and **not an ancestor of the
anchor** — it is on the divergent line. So the corrected placement **agrees**
with what that report declares about itself, and item 58's placement
**contradicted** it. *Checking a filter against ground truth in both
directions* is the rule item 50 established; here the ground truth was three
lines from the manifest item 46 had already read, and I did not check against
it.

That also settles what this is **not**: `REPORT.md` producing its outputs on
the line it names is the report being **consistent**. The error is mine, not
its.

## `REPORT.md`'s six, re-placed

| output | item 58 said | corrected |
|---|---|---|
| `raw-attack2.txt` | anchor | **divergent** (`independence_dimensions`) |
| `raw-attack2-cef5623.txt` | anchor | **divergent** |
| `raw-attack3.txt` | anchor | **divergent** |
| `raw-full-final.txt` | anchor | **divergent** (`test_meta_orchestration`) |
| `raw-attack4.txt` | undecidable | **mixed** — unchanged, item 55 |
| `raw-recheck-cef5623.txt` | undecidable | **`cef5623`** — by suite size, below |

**Not one is on the anchor's line.** Item 58 said four were.

## The question item 61 actually asked, and its answer

Does `raw-recheck-cef5623.txt` name anything that exists on only one line? It
does, in plain sight, and item 58 was structurally unable to see it because it
scanned for **module-name tokens**:

```
Ran 77 tests in 13.628s
```

A **suite size**. Swept over **every one of the 20 commits** reachable from
either ref — 15 on the anchor's line, 6 on the divergent one, sharing their
root `f827f29`, which is the very commit item 55 found `raw-attack4.txt`'s
W1/W2 comparing against:

```
    anchor     27 33 33 34 36 37 50 67 67 78 79 79 85 87 93
    divergent  27 70 70 73 76 77
```

**No count is shared between the two lines**, and exactly one commit anywhere
has a 77-test suite: **`cef5623`**, a *descendant* of `7a9553b` and, like it,
no ancestor of the anchor. (The shared `27` is the root `f827f29`, counted once
and attributed to the line swept first.)

Driven, not read off — all three suites actually run:

```
    anchor     Ran 93 tests   OK
    cef5623    Ran 77 tests   OK
    7a9553b    Ran 70 tests   FAILED
```

So item 46 re-ran that section (77/77, `OK`, exit 0) against a tree the
anchor never took. The re-run is not retracted — it reproduced what it
claimed to reproduce — but **it did not exercise the code under review**.

> The `7a9553b` verdict is recorded and **not used as a discriminator**. One
> run does not establish determinism, and whether that failure is stable is
> `unmeasured`.

## And my first correction repeated the trap

Adding the anchor-only test module `test_proxy_submission` as a literal made
`raw-full-final.txt` look **mixed** — because line 26 of it is

```
test_proxy_submission_records_author_proxy_and_git_commit
    (tests.test_meta_orchestration.GitProxySubmissionTests....)
```

**Module names are prefixes of method names.** A literal scan cannot tell the
two apart; parsing the unittest id `tests.<module>.<class>.<method>` can. Two
substring traps in one round, the second one mine while I was fixing the
first.

Parsed, `raw-full-final.txt` names **seven** test modules, of which the only
line-distinguishing one is `test_meta_orchestration` and **no** anchor-only
module appears. The stronger check agrees: its **70 test ids are an exact set
match with `7a9553b`'s suite, 0 outside and 0 missing**, and **43 of them do
not exist at the anchor at all**.

> **How far that narrows — asked, not assumed.** `4aa47ca`, the commit
> `REPORT.md` names as its own subject, has the **identical** 70-id set. So the
> match places the file on the **divergent line** and **cannot pick between the
> two commits**. The reading that needs no extra assumption is that it came from
> the declared subject — but this test does not establish that, and saying it
> did would claim more than the measurement carries.

## What this does not do

- It does **not** retract any **finding** of this review. Every probe of mine
  runs against `/tmp/efo-prov`, verified clean at the anchor in section A of
  every round. What moves is the placement of **inherited** outputs.
- It does **not** decide the 45. A suite size places an output only if the
  output prints one, and **7 of 77** do.
- It does **not** claim `cef5623` is the only commit with 77 tests in
  existence — only across the **20** reachable from the two refs this
  repository has. A commit reachable from neither is **unswept**.
- It does **not** re-open whether `REPORT.md`'s findings apply to the anchor.
  `NOTE-raw-attack4-is-unreproducible-and-my-manifest-was-wrong.md` measured
  that for P2-1/P2-2/P2-3 and this round neither extends nor narrows it.
- It does **not** file an issue. Nothing here is a defect in EFO.
- No network. Three suites run from unmodified checkouts, no workspace built.
  It does **not** touch `main` or another agent's branch.
- **MEASURED:** the graph, both marker sets over full ancestry, the 20-commit
  sweep, three suite runs, the id-set match, the token directions, both
  classifications, `REPORT.md`'s six and its declared subject. **REASONED:**
  nothing.

> Two expectations of mine failed in the first run and were corrected to the
> measurement: I predicted **21** commits (the two lines share their root, so
> the union is **20**) and that `raw-full-final.txt` would name **one** test
> module (it is a full-suite run and names **seven**). Both are recorded above
> as measured, not as predicted.

Item 58's probe and note are **corrected in place** rather than superseded —
its sections D and F stand as published, its pins are re-derived, and the
bare token is gone. The defect is asserted against **git history**
(`git log -S`, one commit: `78989d7`), not against the working tree, so
correcting the file cannot erase the evidence that it was wrong.

Pre-registered permissions unchanged: `gpu: false`, `network: false`,
`performance_metrics: false`; gates `allow_skips: false`,
`require_validation: true`, `require_known_answer_check: true`,
`require_independent_verification: true`.

**SUBMITTED, not VERIFIED.** Re-running my own evidence is a re-run, not
independent confirmation.

| Artifact | SHA-256 |
|---|---|
| `raw/probe_recheck_line_and_the_substring_that_reversed_four.py` | `06f42c9a9345bde46793c58052a704d6ec357fa7a3bb8b90580ccb75dc7f65ce` |
| `raw/raw-recheck-line-and-the-substring-that-reversed-four.txt` | `587efdebb60570779eb2d8d0bea52b78d690795a19e2d96f846cee15f4d169c1` |
