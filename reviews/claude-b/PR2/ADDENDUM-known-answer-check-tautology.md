# `evidence.py` at `main` `5694ab45` — 17 gates hold, the known-answer check can be a tautology

This is the file the whole premise rests on: it decides what counts as evidence.
It is the strongest code I have probed in this repository, and the two gaps are
narrow. Both statements are measured.

Reproduce with `raw/probe_evidence_gates.py`; raw output in
`raw/raw-evidence-gates.txt`. **17 checks pass, 5 flag** — the five are two
findings. Every rejection is asserted on its *message*, and section A is the
positive control.

## What holds

| Probe | Observed |
|---|---|
| **positive control** — an honest manifest | accepted, `passed=12 failed=0 skipped=0` |
| nonzero exit code | `validations[0] did not pass: exit_code=1, failed=0` |
| a failure with exit code 0 | `did not pass: exit_code=0, failed=2` |
| a skip while `allow_skips` is false | `has 1 skipped checks; skip is not pass` |
| skips without a reason for each | `has 2 skipped checks but lacks a reason for each` |
| an unmeasured claim carrying a number | `is unmeasured and must use the exact value [FILL]` |
| an unmeasured claim using `[FILL]` | accepted, `unmeasured_claims=1` |
| a measured performance claim under `performance_metrics: false` | `Measured performance claims are forbidden by this task's permissions` |
| a claim citing evidence never bound | `references evidence not bound in artifacts or raw output: ['ghost.txt']` |
| an artifact whose sha does not match | `Evidence artifact SHA mismatch` |
| a known-answer check whose values differ | `expected and observed values differ` |
| a known-answer check not marked passed | `is not explicitly passed` |
| no known-answer check at all | `At least one known-answer comparison is required` |
| a report with unmeasured claims and no `[FILL]` | `The manifest declares unmeasured claims but the report has no [FILL] marker` |
| a bare `## 1.` heading | `Report section 1 is empty` |

`exit_code != 0 or failed` in one condition, skip refused unless explicitly
allowed *and* individually justified, `[FILL]` required exactly, and every
measured claim bound to a hashed artifact — the doctrine is enforced, not
described.

## Finding 1 — a known-answer check is only tested for self-consistency

`evidence.py:190-201` requires `passed is True`, requires both keys, and
compares them. Nothing requires the pair to be non-trivial:

| Manifest | Verdict |
|---|---|
| `{"expected": null, "observed": null, "passed": true}` | **accepted** |
| `{"expected": "", "observed": "", "passed": true}` | **accepted** |
| `{"expected": 0, "observed": 0, "passed": true}` | **accepted** |
| `{"expected": "[FILL]", "observed": "[FILL]", "passed": true}` | **accepted** |

The summary then reports `known_answer_checks: 1` with nothing to distinguish it
from the honest `expected: 4, observed: 4`.

The last row is the pointed one. `[FILL]` is this system's marker for *"this was
not measured"*, and a check that compares the marker against itself satisfies
`require_known_answer_check` — the gate whose purpose is to demonstrate that the
harness can tell a right answer from a wrong one.

Context rather than a separate defect: a validation with
`passed=0, failed=0, skipped=0, exit_code=0` is also accepted. That one is
**disclosed** — the summary carries `passed: 0`, so an auditor sees it. Together
they mean a submission can satisfy every gate having asserted nothing, and only
the `passed: 0` half of that is visible.

### Suggested fix

Refuse a check whose `expected` is `None`, an empty string, or the literal
`[FILL]`, and count non-trivial checks separately in the summary so
`known_answer_checks` cannot be padded. Requiring `expected` to be present *and*
meaningful is the cheap half; the honest version of this gate would also want
the check to have been run against a deliberately wrong input at least once, but
that is a protocol change, not a validation change.

## Finding 2 — the empty-section guard cannot fire for a titled section

`SECTION_RE = ^##\s+([1-6])(?:[.)]|\s)` ends the match immediately after the
section number, so the body is measured from there — and the heading's own words
count as content. Measured directly:

```
'## 1. Files changed' -> body = 'Files changed'
'## 1.'               -> body = ''
'## 1 x'              -> body = 'x'
'## 1)'               -> body = ''
```

So a report whose section 1 is a title and nothing else validates:

| Probe | Observed |
|---|---|
| `## 1. Files changed` followed by nothing | **accepted** |
| `## 1.` followed by nothing | rejected — `Report section 1 is empty` |

The check works only for a heading with no title. Any real report has titles, so
in practice the guard never fires.

### Suggested fix

Take the body from the end of the heading *line* rather than the end of the
number match — `text[text.index("\n", match.end()):]` or a regex that consumes
the rest of the line.

## What I got wrong, and corrected

The probe first asked whether `contains_fill_marker` is enforced, treating an
all-`[FILL]` report as a defect. It is enforced, at `evidence.py:293`, and the
rule runs the *other* way: a manifest with unmeasured claims whose report lacks
`[FILL]` is refused. That is correct, and an all-`[FILL]` report is legitimate.
A positive control for the real rule was added and it fires. Only the corrected
run is reported.

## Severity, plainly

Neither finding lets a false *measured* claim through — those still need a
hashed artifact, a matching sha, and a bound reference, and all of that holds.
Finding 1 lets the known-answer gate be satisfied without a real comparison, so
a submission can carry the appearance of a verified harness while proving
nothing. Finding 2 is cosmetic in isolation, but it is the guard that would
otherwise catch a report skeleton submitted with no content in a section.

## Scope

`validate_report`, `validate_manifest`, `validate_submission`. Not examined:
`archive.py`, `adapter.py`, `proxy_submit`, and how `doctor.py` reports on any
of this.

Pre-registered permissions unchanged: `gpu: false`, `network: false`,
`performance_metrics: false`; gates `allow_skips: false`,
`require_validation: true`, `require_known_answer_check: true`,
`require_independent_verification: true`.

**SUBMITTED, not VERIFIED.**

| Artifact | SHA-256 |
|---|---|
| `raw/probe_evidence_gates.py` | `7ba3b90e4ba1eee619defd4a4eb11d8619eb9100ee613165a6be87e72497ad8d` |
| `raw/raw-evidence-gates.txt` | `52a0bae519a59eee1b9fab0b454c0a0d60b13318a5ec47d75f6689ddd18219c4` |
