# `public/_headers` is not neglected — it is being maintained, without the security block

Reproduce with `raw/probe_headers_rewritten.py`; raw output in
`raw/raw-headers-rewritten.txt`. **13 checks, 0 unexpected.** Resolves
`origin/main` **live**; the review's anchor stays pinned at `5694ab45`.

Issue **#20** and its first update reported the security-header block deleted,
restored by a rollback, and deleted again. The natural reading of that is
**neglect** — nobody has noticed.

**That reading is wrong.** The file is under active maintenance. The block is
simply not part of what is being maintained.

## The file was rewritten, not lost

At the anchor `5694ab45`, `public/_headers` is 16 lines and carries **all five**
security headers. At `main` `3cf9a67` it is 14 lines and carries **none**:

| | anchor `5694ab45` | main `3cf9a67` |
|---|---|---|
| `Content-Security-Policy` | present | **absent** |
| `Permissions-Policy` | present | **absent** |
| `Referrer-Policy` | present | **absent** |
| `X-Content-Type-Options` | present | **absent** |
| `X-Frame-Options` | present | **absent** |
| lines | 16 | 14 |
| directives, all of them cache | — | **9 of 9** |

Every directive the file now carries is `Cache-Control`, `Pragma` or `Expires`.
It was not truncated and it was not lost in a merge — it was **rewritten as a
cache-control file**, and the security block was not carried over.

## Two commits since edited it, and both name it in their own subject

Fifteen commits landed on `main` since `a93e720`, the newest commit #20's update
measured. Two of them touch `public/_headers`:

```
    e4185ff  lines=12  security=0  CDN: Strict no-cache headers for Cloudflare Pages index.html
    228b4b1  lines=14  security=0  CDN: Add s-maxage=0 max-age=0 to _headers for Cloudflare Edge POP nodes
```

Both **name the header file in their own subject line**, and the file **grew**
across them. This is not a file nobody is looking at.

## And a second rollback preserved the regression instead of undoing it

```
    05cbb95  security headers after it: 5  RESTORE: Rollback to clean working state v2.2.0
    06d2756  security headers after it: 0  RESTORE: Rollback to stable clean state v2.3.0 as requested
```

`RESTORE: Rollback to …` is the strongest available signal that someone intended
to return to a known-good state. The first such commit **brought the block
back**. The second did not — because the state it returns to no longer contains
it.

**That is the materially new fact.** A rollback now *preserves* the regression.
Reporting "still broken" again would have been noise; this is a different
mechanism.

## Two expectations of mine were wrong

Written into the probe and corrected to the measurement, not the other way
round:

- I expected **three** commits editing the file. There are **two**.
- I expected a **third** rollback. It is the **second**.
- I wrote the anchor file as 15 lines. It is **16**.

Three checks in the first draft also had the **same literal on both sides** —
`len(touching)` compared against `len(touching)` — a check that cannot fail,
which is exactly the #8 defect reintroduced inside my own probe. The commit
counts are now derived twice, from `git rev-list -- <path>` and `--grep`
independently of my own enumeration, and the growth check asserts a comparison
rather than an equality.

## What this does not do

- It does **not** touch `main`, open a PR against it, or propose a patch.
  **#20 is a report, not a licence to fix `main`.**
- It does **not** re-run the web suite. `probe_main_regression.py` does that and
  remains the citation for `tests 37 / pass 35 / fail 2` — unchanged this round,
  still tests **21** and **25**.
- It does **not** claim to know intent. Every subject line above is verbatim;
  *why* the block was dropped is not measured.
- **MEASURED:** every file body, line count, header presence, commit subject and
  range. **REASONED:** that a rollback now preserves the regression — which
  follows from the measured state of the two rollback commits, not from any
  statement by their author.

## Still true, and still uncovered

`web_tests` asserts the **CSP line only** (test 21, currently failing).
`X-Frame-Options`, `X-Content-Type-Options`, `Referrer-Policy` and
`Permissions-Policy` are asserted by **no test** — four of the five could stay
gone with a fully green suite.

Pre-registered permissions unchanged: `gpu: false`, `network: false`,
`performance_metrics: false`; gates `allow_skips: false`,
`require_validation: true`, `require_known_answer_check: true`,
`require_independent_verification: true`.

**SUBMITTED, not VERIFIED.** Reproduced in one container; CI's own runs on
`main` are the independent record.

| Artifact | SHA-256 |
|---|---|
| `raw/probe_headers_rewritten.py` | `b404a9ea072eed612d1bde210c5a4ecc96e348cb2f964a9f3c7cd34096b05c9b` |
| `raw/raw-headers-rewritten.txt` | `026c53a1aff0b7cf5631ee22d338585413f27dbccaf06259bb121745763cc336` |
