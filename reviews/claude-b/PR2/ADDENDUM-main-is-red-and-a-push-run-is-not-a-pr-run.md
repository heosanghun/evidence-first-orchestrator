# `main` has been red for nine pushes — and my "same commit" reasoning about CI runs was wrong

Reproduce with `raw/probe_main_regression.py`; raw output in
`raw/raw-main-regression.txt`. **11 checks, 0 unexpected.** Filed as **issue
#20**.

A `web-tests` failure arrived on PR #16 at head `2b0ca5c`. My push was
documentation only. Two things about it did not fit, and both were worth
pulling:

1. the failing assertion is a **static string match** against
   `public/assets/app.js` — a thing that cannot flake;
2. the concurrent run on the same head **passed**.

## The defect in my own reasoning, first

Diagnosing the earlier `test_concurrency` divergence I wrote that the `push`
and `pull_request` jobs were *"same commit, OS, Python"*.

**The commit claim is wrong as a general statement.** A push run checks out the
branch head; a pull_request run checks out `refs/pull/N/merge` — the branch
**merged into `main`**. They share a head SHA and do not share a tree. When
`main` moves, they legitimately diverge.

That shortcut reached the right answer for the concurrency case —
`barrier.wait()` sitting outside the `try` at `tests/test_concurrency.py:33`
is real and independent of the base — but it was not a sound argument, and
applied here it would have produced *"flake"* for something that is not one.
Corrected on the PR thread as well as here.

## What is actually broken

`main` is red on **nine consecutive pushes** since `b78c63d` (2026-08-03
06:19Z). The last green run was `30609261383` at `5694ab4` (2026-07-31).

Reproduced in this container, no network:

```
    5694ab45 (anchor)    tests 37  pass 37  fail 0   (exit 0)
    0d67750 (main)       tests 37  pass 35  fail 2   (exit 1)
        not ok 21 - CSP-safe visual fills use native progress and no inline styles
        not ok 25 - browser renders a distinct transport badge on agent cards
```

The 35/2 matches CI's own count for job `91616795908`. The anchor passing 37/37
is the positive control: the harness is not simply broken.

**The test file is byte-identical between the two refs.** Only the source it
reads changed.

### Eight properties lost

| Property | `5694ab45` | `0d67750` | Caught by |
|---|---|---|---|
| `status_source === "transport_assertion"` | 2 | 0 | test 25 |
| `agent-transport-badge` | 1 | 0 | test 25 |
| `status_badge` anywhere in `app.js` | 4 | 0 | test 25 |
| `Content-Security-Policy` | 1 | 0 | test 21 |
| `X-Frame-Options` | 1 | 0 | **nothing** |
| `X-Content-Type-Options` | 1 | 0 | **nothing** |
| `Referrer-Policy` | 1 | 0 | **nothing** |
| `Permissions-Policy` | 1 | 0 | **nothing** |

And what was added — the thing test 21 forbids: inline `style=` goes **0 → 32**
in `app.js` and **0 → 22** in `index.html`.

### Two stages, 32 minutes apart

| commit | CSP | badge | inline `style=` |
|---|---|---|---|
| `5694ab4` | 1 | 1 | 0 |
| **`b78c63d`** | 1 | **0** | **17** |
| `548b616` … `c4d359d` | 1 | 0 | 22–33 |
| **`0d67750`** | **0** | 0 | 32 |

Only the first stage has a test. The four header losses at `0d67750` are caught
by nothing.

## What this connects to

`agent.status_source === "transport_assertion"` is the branch that renders an
agent's status **differently when the claim came from a transport assertion
rather than from the agent itself**. That distinction is the display half of
the property `NOTE-projected-tasks-holds.md` and issue #6 are about. The
`snapshot.js` projection still refuses a transport assertion that contradicts
canonical task state — tests 30–33 still pass — so the **data** contract holds.
What is gone is the **display** that told a reader which kind of claim they were
looking at.

## Scope and refs

This review is anchored at `main` `5694ab45`, and every other write-up on this
branch asserts that anchor. **This document deliberately reads two refs and
names both**, because the finding *is* the difference between them.
`/tmp/efo-prov` was not re-pointed — the probe's positive control asserts it is
still `5694ab45` with an empty `git status --porcelain`, because moving it would
invalidate every SHA-256 binding in the other notes.

**Executed here**, unlike every other probe in this pass: `node --test` over
three files that read local files and a stubbed KV. No network, no GPU, no
performance measurement — the pre-registered permissions are unchanged.

Not established:

- **Why** the rewrite dropped them. The nine commit messages are about gauge
  colours, fill widths and goal text; none mentions the badge, the inline
  styles, or the headers. Whether the loss was intended is **unmeasured** and
  not guessable from a diff.
- **Whether the deployed site actually serves without those headers.**
  `public/_headers` is Cloudflare's mechanism and the Pages project may set
  headers elsewhere. Checking the live site is a **network** operation and
  `network: false` forbids it. What is measured is repository content.
- **Exploitability.** No XSS was demonstrated. `escapeHtml` still appears 31
  times in the new `app.js`, so the escaping path was not removed wholesale —
  only the CSP that backstops it.
- **MEASURED:** every count, the timeline, both suite runs. **REASONED:** that
  losing CSP while gaining 32 inline styles is a weakening rather than a neutral
  refactor.

Pre-registered permissions unchanged: `gpu: false`, `network: false`,
`performance_metrics: false`; gates `allow_skips: false`,
`require_validation: true`, `require_known_answer_check: true`,
`require_independent_verification: true`.

**SUBMITTED, not VERIFIED.** Reproduced by me in one container; CI's nine red
runs on `main` are the independent record.

| Artifact | SHA-256 |
|---|---|
| `raw/probe_main_regression.py` | `5380a439125d987ed74cce047d0aa538baaf522cd30ed576e988ecf13f763400` |
| `raw/raw-main-regression.txt` | `c24fdc3eb3ee45e92f9d0e476e1d7cc0ab42dbbdc9389eee3fb3d9baa74e0ad5` |
