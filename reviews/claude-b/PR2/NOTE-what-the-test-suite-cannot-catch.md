# `tests/` read at last: 93 tests, 318 assertions, and **10 of the 16 issues cannot be expressed in it by name**

Reproduce with `raw/probe_test_suite_map.py`; raw output in
`raw/raw-test-suite-map.txt`. **16 checks, 0 unexpected.** No issue filed — a
suite that does not test a defect is not itself a defect.

Queue item 31. The documents are exhausted; `tests/` was the last untouched
surface. This review has invoked the suite through CI many times and never read
it.

**The output is a map, not a score.** Nothing here found a test that asserts
something false.

## Inventory

| Module | Tests | Assertions |
|---|---|---|
| `test_monitor_collector.py` | 27 | 150 |
| `test_proxy_submission.py` | 17 | 37 |
| `test_independence.py` | 13 | 23 |
| `test_workspace.py` | 12 | 30 |
| `test_evidence.py` | 10 | 12 |
| `test_proxy_status.py` | 9 | 51 |
| `test_doctor.py` | 2 | 6 |
| `test_adapter.py`, `test_concurrency.py`, `test_ledger.py` | 1 each | 2 / 5 / 2 |
| **total** | **93** | **318** |

Plus three Node files: `chat.test.mjs`, `local-health.test.mjs`,
`snapshot.test.mjs`.

> **Correction, 2026-08-03.** The standing check-in text has carried *"33 test
> methods"* for several rounds. That figure comes from this branch's **old base
> `dad3f4c4`**, which was missing four whole test modules — the branch-base
> defect already recorded in `SYNTHESIS.md`, resurfacing as a number rather
> than as a diff. The count at `main` is **93**.

## Which issues the suite could catch, measured by name

An issue's defect token either appears somewhere in a test source or it does
not. **Absence is decisive** — a token no test contains cannot be asserted by
one. Presence is only a lead, so the two that matter are read directly in the
next section.

| Issue | Defect site | Token | In the suite? |
|---|---|---|---|
| #3 | `independence.py::resolve_identity_registry` | `alias_of` | 3 files |
| #4 | `provenance.py::validate_git_provenance` | `no-replace-objects` | **absent** |
| #5 | `provenance.py::validate_git_provenance` | `refs/remotes` | **absent** |
| #6 | collector portfolio | `stale` | **absent** |
| #7 | `model.py::lease_expiry` | lease ceiling | **absent** |
| #8 | `evidence.py::validate_submission` | `[FILL]` | 2 files |
| #9 | `ledger.py::Ledger.verify` | `truncat` | **absent** |
| #10 | `archive.py::archive_evidence_bundle` | *(the function name)* | 1 file |
| #11 | `adapter.py::run_once` | `events.jsonl` | 1 file |
| #12 | `doctor.py::_scan_secrets` | `AWS_SECRET` | **absent** |
| #13 | `functions/api/chat.js` | `instructions` | `chat.test.mjs` |
| #14 | `functions/api/snapshot.js` | `FORBIDDEN_KEYS` | **absent** |
| #15 | `model.py::validate_task` | `allow_skips` | **absent** |
| #17 | `doctor.py::audit_legacy_workspace` | `write_test` | **absent** |
| #18 | `archive.py::archive_evidence_bundle` | `max_evidence_bytes` | **absent** |
| #19 | `workspace.py::Workspace.repair_projections` | `last_event_hash` | 1 file |

**Ten of sixteen are absent.** Every function named in that table is checked to
exist in its module and the run fails otherwise — **and it did fail**, on four
names I had written from memory: `verify_git_provenance` (it is
`validate_`), `run_agent_command` (it is `run_once`), and `repair_projections`
attributed to `doctor.py` when it is a `Workspace` method. A typo there would
have turned a covered issue into an uncovered one silently, which is why the
check exists.

## What the suite stubs out

**21 mock targets.** Eighteen are `monitor.collector.*` — `run_command`,
`query_gpus`, `read_meminfo`, `shutil.disk_usage`. The collector shells out to
`nvidia-smi` and reads `/proc`, so stubbing those is what makes it testable at
all; the consequence is only that those 27 tests measure the collector's
*logic* and never its interaction with a real machine.

The other **three are in the EFO package proper, and all three sit in one
test** — the suite's only end-to-end proxy submission,
`test_proxy_status.py:252-260`:

```
evidence_orchestrator.workspace.validate_submission
evidence_orchestrator.workspace.validate_git_provenance
evidence_orchestrator.workspace.archive_evidence_bundle
```

Evidence validation, Git provenance verification, and evidence archiving — the
three components carrying issues **#4, #5, #8, #10 and #18**. The test measures
that `proxy_submit` *orchestrates* them, which it does. It cannot measure what
they do.

## The two blind spots worth naming, read rather than grepped

### `repair_projections` has exactly one test, and #19 sits under it

`test_workspace.py:178`, `test_projection_loss_is_detected_and_repairable`.
One assertion before the repair — that `audit_projections` **detects** the loss,
a property the suite gets right — and two after:

```
        self.assertEqual(result["repaired"], ["T1"])
        self.assertEqual(self.workspace.get_task("T1")["state"], "pending")
```

The rebuild happened, and `state` is right. #19 is a *different key* going
missing from that same rebuild, so **this test passes with the defect present.**

### The suite's only mention of `last_event_hash` is an exclusion

`test_proxy_status.py:86`:

```
                if key != "last_event_hash"
```

which is the same exclusion the code makes at `workspace.py:1511`:

```
            key: value for key, value in disk_task.items() if key != "last_event_hash"
```

Both exclusions are **correct**: a projection carries the key and a ledger
snapshot does not, so comparing them requires dropping it. What neither does is
assert the key is *still there* after a rebuild — and that gap is #19.

**The suite encodes the same blindness as the code it tests.** That is the
general shape worth taking away, and it is why "the tests pass" and "the
property holds" came apart here.

## Scope

Static analysis of `tests/*.py` and `web_tests/*.mjs` at `main` `5694ab45`
(precondition verified: `HEAD` matches, `git status --porcelain` empty).
**Nothing was executed** — `pytest` is absent from this container and the
shipped runner is `python -m unittest`; every pass/fail count this review has
quoted is CI's, bound to a job id.

A harness bug worth disclosing because it would have inverted the headline: a
first pass used `grep -rl` over `tests/`, which matched compiled bytecode in
`tests/__pycache__` and reported `archive_evidence_bundle` and
`validate_git_provenance` as *present* in two files each. Both are absent from
the sources. The census now globs `tests/*.py`. A second version of the mock
census matched any line naming the package and counted an **import** as a mock;
it is now read from the AST as a `patch` call with a string first argument, and
that changed the answer from 3 to 21. Sixth and seventh filter bugs of this
review.

Not examined:

- the three Node test files are searched for tokens but **not read**. #13 and
  #14 live in `functions/api/*.js`, and adjudicating `chat.test.mjs` and
  `snapshot.test.mjs` line by line is a separate pass.
- **MEASURED:** the inventory, the mock targets, the token map, and both
  section-D readings. **REASONED:** that a token's absence implies the class is
  unasserted.

Pre-registered permissions unchanged: `gpu: false`, `network: false`,
`performance_metrics: false`; gates `allow_skips: false`,
`require_validation: true`, `require_known_answer_check: true`,
`require_independent_verification: true`.

**SUBMITTED, not VERIFIED.**

| Artifact | SHA-256 |
|---|---|
| `raw/probe_test_suite_map.py` | `9355a3a20d3039d4b19455a29d4959232d5576af301d2afd611ec693ec08f5d4` |
| `raw/raw-test-suite-map.txt` | `4358742ee48b3eb6cbb2eca5b91101cd99c12b4759db2af8746bb5ca677beb7d` |
