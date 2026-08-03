# Every issue that has a test, and what input the test feeds — seven of seven cannot fail on the defect

Reproduce with `raw/probe_class2b_census.py`; raw output in
`raw/raw-class2b-census.txt`. **12 checks, 0 unexpected.** No issue filed — all
seven are already open, and a suite that does not test a defect is not itself a
defect.

Queue item 36. Three instances of one pattern were already on the record — #13's
Korean-only gate, #13's asserted grounding placement, #14's `password`. This
turns the observation into a census.

`NOTE-what-the-test-suite-cannot-catch.md` measured that **10 of 16 issues have
a defect token in no test source**, so those cannot be asserted by name. The
population left was the six that do. #13 and #19 were already adjudicated; this
reads the other four.

## The census

| Issue | What its test does |
|---|---|
| #3 | re-attestation **is** tested, three times — never on a verifier |
| #8 | both paths tested, **never crossed** |
| #10 | the component is **mocked out** in its only appearance |
| #11 | token match, unrelated file |
| #13 | Korean-only input; and the second finding is **asserted** by the test |
| #14 | feeds `password`, a key the set contains |
| #19 | the one repair test asserts `state`, not the dropped key |

**Seven of seven.** Four reasons: the test feeds a covered input, the test
asserts the behaviour the issue objects to, the component is mocked out, or the
token match was spurious.

This is a statement about **coverage shape**, not test quality. Every one of
these tests asserts something true.

## #3 — the two guarded shapes are tested; the third is not

Three `attest_agent_identity` call sites, and **none re-attests an agent whose
declared role is `verifier`**:

```
    test_independence.py:161  attests 'antigravity'   role: declared elsewhere
    test_independence.py:193  attests 'alias-one'     role: worker
    test_independence.py:243  attests 'codex'         role: declared elsewhere
```

Both re-attestation tests **refuse**, and both are about a different guard:

- `test_attested_alias_lineage_cannot_be_removed` — re-attesting an agent that
  carries an alias lineage.
- `test_submission_snapshot_prevents_identity_laundering` — re-attesting the
  **worker** *after* submit; the submission snapshot preserves authorship.

#3 re-attests the **verifier**, *before* verifying, on an agent with no alias
lineage — the one combination the suite never builds. Both existing tests pass
with #3 present.

## #8 — two paths, tested separately, never crossed

The suite's known-answer fixtures compare **real values**:

```
    helpers.py:87 expected=4 observed=4 if known_answer_passed else 5
```

and, inside a generated worker script, `"expected": "known-output"` /
`"observed": "known-output"`.

The one test that asserts on `[FILL]` is `test_unmeasured_claim_requires_fill`,
which sets a **claim's** `value` to `0.7` and asserts validation **refuses** it —
the opposite direction, on a different field.

So the suite tests known-answer checks with real values (passing and failing)
and tests `[FILL]` on claims, and never crosses the two. **#8 lives exactly in
the cross:** `expected == observed == "[FILL]"` on a known-answer check.

## #10 and #11 — token matches that do not survive reading

**#10.** The suite mentions `archive_evidence_bundle` exactly **once**, and that
mention is a `patch()` target at `test_proxy_status.py:260` — the archiver is
**replaced with a stub** returning `{'retained': 0, 'external': 0}`. There is no
test of the archiver at all.

**#11.** The two mentions of `events.jsonl` are in `test_monitor_collector.py`,
building a ledger path for the **collector**. That file imports nothing from
`adapter`. #11 is about the command adapter's grant to a child process — a
different component entirely.

Both were flagged as *present* by the token map, which is exactly why that map
called presence **a lead** and absence **decisive**.

## A blind spot in this probe, stated

The known-answer census matches **dict literals** carrying both `expected` and
`observed`, and found **one**. The second fixture is source code inside a
`textwrap.dedent` string — `test_adapter.py` writes a worker *program* — and is
invisible to it. That one is checked by text instead.

**A census over syntax cannot see a fixture that is a program.** Same family as
the rename-across-a-return bound in
`NOTE-which-of-my-censuses-measured-and-which-read.md`.

## Scope

Static analysis of `tests/*.py` at `main` `5694ab45` (precondition verified:
`HEAD` matches, `git status --porcelain` empty; `origin/main` has moved and is
red — see `ADDENDUM-main-is-red-and-a-push-run-is-not-a-pr-run.md`). Nothing
executed.

Not established:

- It does not run the suite. CI does that; every count this review quotes is
  CI's, bound to a job id.
- The role of two re-attested agents is reported as *"declared elsewhere"*
  rather than guessed — they are declared in a shared fixture. Neither is a
  verifier, which was established by **reading** those two tests.
- **MEASURED:** every count and call site above. **REASONED:** that a test
  exercising only a guarded shape cannot fail on an unguarded one — which for
  #3 rests on reading the two tests, and is labelled as such.

Pre-registered permissions unchanged: `gpu: false`, `network: false`,
`performance_metrics: false`; gates `allow_skips: false`,
`require_validation: true`, `require_known_answer_check: true`,
`require_independent_verification: true`.

**SUBMITTED, not VERIFIED.**

| Artifact | SHA-256 |
|---|---|
| `raw/probe_class2b_census.py` | `090a6b13e999d5e7e2debbf76996230a3957fbd6d34da10ac6f4752e4c475866` |
| `raw/raw-class2b-census.txt` | `8d4368b7767cdf771cb77a763a2e3a764d4d73645df7b231fafba8f49023fcd3` |
