# The eight attack scripts are not opaque — but two ran against an unpinned tree that was the stale base

Reproduce with `raw/probe_attack_provenance.py`; raw output in
`raw/raw-attack-provenance.txt`. **11 checks, 0 unexpected.** No issue filed —
this audits **my own evidence**, not EFO.

Queue item 40 asked whether `raw/`'s third category — the attack scripts that
predate the `[ok]` convention — should stay historical or be documented, and
said to **stop rather than invent a rationale** if a script's purpose could not
be reconstructed.

**The premise is wrong, and that is the first result.** The category is not
opaque: **all eight self-document in their first three lines.** Nothing had to
be reconstructed, and saying so is better than writing a rationale I would have
had to invent.

## What was never recorded

**Which ref each one ran against.**

| Script | `REPO` under test |
|---|---|
| `attack2.sh` | **`/workspace/evidence-first-orchestrator`** — the branch tree, unpinned |
| `attack3.sh` | **`/workspace/evidence-first-orchestrator`** — same |
| `attack2_cef.sh` | `/tmp/efo-cef5623` |
| `attack_main.sh` | `/tmp/efo-main` |
| `attack_main2.sh` | `/tmp/efo-main2` |
| `attack_proxy.sh` | `/tmp/efo-proxy` |
| `attack_prov_main.sh` | `/tmp/efo-prov` — main `5694ab45` |
| `attack_prov5_main.py` | `/tmp/efo-prov` |

Six name a pinned checkout. **Two point at the review branch's own working
tree.**

## And at that time the branch *was* the stale base

```
    attack2.sh   first committed  a820891  2026-07-30
    attack3.sh   first committed  a820891  2026-07-30
    branch-base merge             c16df6d  2026-08-03
```

Until `c16df6d` the branch was based on `dad3f4c4` — **behind main by 9,457
lines, `provenance.py` −341**, per `SYNTHESIS.md`.

`attack3.sh` is the **Git-provenance suite** — G1 wrong remote, G2 local-only
commit, G3 `replace-ref` swap, G4 partial submission. Its results therefore
describe a **193-line** `provenance.py`, not main's 341-line rewrite.

**That is exactly why `attack_prov_main.sh` and `attack_prov5_main.py` exist**:
they re-ran the same attacks against `/tmp/efo-prov` at main. The re-runs were
done and the issues cite them. What was **never written down** is that the two
originals are superseded — so a reader takes all eight as evidence about main.

Same defect as `REPORT.md` reviewing an unnamed ref, which
`NOTE-citation-audit-of-this-review.md` already recorded. This is its second
instance, in a different category of artifact.

## Two smaller gaps in the same category

- **Nine outputs, eight scripts.** `raw-attack4.txt` has no `attack4` script in
  `raw/`: one result on this branch cannot be reproduced from what the branch
  ships. Named rather than quietly dropped from the count.
  The nine excludes **this probe's own output**, which matches `raw-attack*.txt`
  and would have made the census grow by one the moment it was committed — the
  same no-fixpoint self-reference `probe_inventory_selfcheck.py` hit, one level
  down. Excluded **by name**, and the exclusion is itself asserted, so a second
  one cannot hide behind it.
- **`predate the [ok] convention` is exact for eight of nine.** None uses `[ok]`,
  but `raw-attack-prov5-main.txt` carries **one bare `!! UNEXPECTED !!`** without
  it — the failure marker alone, at the end of a status line. Slightly generous,
  now stated.

## The count of that marker was itself wrong, in two places

The line above first read **2 markers**, because the count was
`text.count("!! UNEXPECTED !!")`. The file has **one finding**
(`G2b  !! UNEXPECTED !!`) and **one legend line** — *"Any `'!! UNEXPECTED !!'`
above is a finding"* — and a substring count cannot tell them apart.

The same bug was live in `raw/probe_inventory_selfcheck.py`'s `tally()`, which
counts every raw output in the review. There it did two things at once:

- it counted this probe's **own 10 checks as 12**, because a check here is
  *named* after the token it searches for;
- it inflated the review-wide `UNEXPECTED` total from **12 to 13**.

Both are now counted **by position**: bracketed at the start of a line (the
`check()` convention) or bare at the end (the older attack scripts'). A marker
anywhere else on a line is prose.

**The first attempt at that fix was worse than the bug.** Using `endswith` for
*both* markers matched 163 ordinary sentences ending in the letters `ok` and
took the census from 740 to **922**. It was checked against a known answer
before it was believed. That is the thirteenth and fourteenth filter bug in
this review, and the second time one was caught inside the fix for another.

`SYNTHESIS.md`'s tally moves **13 → 12** as a result. No finding changes: the
one real `G2b` failure is still one real failure.

## What this does not do

- It does **not** re-run any attack. The scripts drive real git repositories and
  several need refs that no longer exist in this container. Re-running them is
  not possible here and is not claimed.
- It does **not** retract any finding. #3, #4 and #5 were each re-run against a
  **pinned** ref, and those re-runs are what the issues cite. The gap is
  bookkeeping on this branch, not a defect in the findings.
- **MEASURED:** every header, every declared `REPO`, both commit dates, the
  output inventory. **REASONED:** that `attack3`'s results describe the old
  `provenance.py` — which follows from the date and the declared path, not from
  re-reading the 193-line file.

Pre-registered permissions unchanged: `gpu: false`, `network: false`,
`performance_metrics: false`; gates `allow_skips: false`,
`require_validation: true`, `require_known_answer_check: true`,
`require_independent_verification: true`.

**SUBMITTED, not VERIFIED.**

| Artifact | SHA-256 |
|---|---|
| `raw/probe_attack_provenance.py` | `df39a0d0b232788afa1ef3936d8e8b729ef34057fe33b25de7cd32787608e863` |
| `raw/raw-attack-provenance.txt` | `c740eb5f7037dd3b5aec56222f527e533dfac1c907bcfba89d27a83a92eabdf4` |
