# `cli.py` at `main` `5694ab45` — the CLI weakens nothing, and exactly one mutating command leaves no signed record; no issue filed

Reproduce with `raw/probe_cli_surface.py`; raw output in
`raw/raw-cli-surface.txt`. **25 checks, 0 unexpected.** The CLI is driven
through its real `main()` against a real workspace.

Two questions worth asking of a command line: can it reach anything the Python
API gates, and does any command write to the workspace without leaving a ledger
event.

## Positive control

`init` → `agent add` → `task add` → `status`, all exit 0, task emitted as JSON
with `state: pending` and
`{'gpu': False, 'network': False, 'performance_metrics': False}`. Reading did
not append: `events: 4 -> 4`.

## Every subcommand, enumerated from the parser

All **30** are listed in the raw output with an adjudication, and the probe
**fails the run on any subcommand the map does not cover**, so a new command
cannot ship unexamined. `uncovered: []`, `stale: []`.

Twenty of them mutate, and nineteen of those append a named event —
`task.created`, `task.claimed`, `task.started`, `task.heartbeat`,
`task.blocked`, `task.submitted`, `task.proxy_authorized`,
`task.external_status_reported`, `task.proxy_submitted`, `task.verified` /
`task.rejected`, `task.requeued`, `task.archived`, `agent.added`,
`agent.identity_attested`, `workspace.initialized`, plus the two `worker`
commands via the adapter and `recover`'s per-lease blocks.

## The exception: `ledger repair-projections`

```
audit-projections notices the edit -> exit 2, "T1: projection differs from ledger"
repair-projections                 -> exit 0
   it rewrote the projection          changed: True
   and appended NOTHING to the ledger events: 4 -> 4
```

It is the **only mutating command with no signed record of itself**. Issue #12
is about what it does to a *truncated* chain — it rebuilds the projection from
the tampered ledger and reports `healthy=True`. This is the narrower and
separate fact: even in the honest case, where an operator repairs a genuinely
corrupted projection file, the repair leaves no event. An auditor reading the
ledger afterwards sees the projection agreeing with history and no indication
that it was ever made to agree.

Recorded here rather than filed as its own issue: it is the same command and
the same fix surface as #12, and #12's suggested change (refuse to repair when
the ledger cannot prove its own completeness) is where a `projection.repaired`
event would naturally be added at the same time.

## The CLI weakens no API gate

| Probe | Observed |
|---|---|
| a worker passing `--actor claude` to `task add` | exit 2, `Only orchestrator 'antigravity' may perform this action` |
| the orchestrator claiming a worker's task | exit 2 |
| `--id UPPER` for an agent | exit 2, `Agent id must start with a lower-case letter …` |
| a `path` that is not a workspace | exit 2, `Not an Evidence First Orchestrator workspace: …` |

`--actor` is a claim, not an authentication — but that is the documented model
(`README.md:430`, and issue #3 is the narrower case), and the CLI applies
exactly the same `_require_orchestrator` and `validate_agent_id` the Python API
does. Nothing here is looser.

### `evidence check` validates arbitrary paths, by design

> **CORRECTED 2026-08-03.** The paragraph below originally cited
> `README.md:590` for the phrase *"Validate a submission bundle"*. That
> citation was wrong: `README.md` has 452 lines, and the phrase appears in no
> Markdown file in the repository. It is **`cli.py:590`**, an argparse `help=`
> string. The line number was right and the file was wrong, which is why it
> read as plausible. It matters for the argument — I leaned on it as
> *documented intent*, and a `help=` string is a weaker basis than README
> prose. The conclusion is unchanged, because it never rested on the quote: it
> rests on the measurement that the command appends nothing.

`Workspace.submit` requires the report and manifest to live under
`reports/<actor>/`. `efo evidence check` does not — it takes any two paths:

```
--report <a file outside the workspace>
  -> exit 2, "Report is missing required numbered sections: 1, 2, 3, 4, 5, 6"
  -> having appended nothing: events: 4
```

It failed on the **content**, never reaching an ownership question, and wrote
nothing. `cli.py:590` registers this subcommand with
`help="Validate a submission bundle"`, which is what it does: a dry run for an
author checking their own bundle before submitting it. The looser path check is a convenience, not a bypass, because
nothing it does is recorded.

## Harness bugs, caught before any conclusion

Six, all mine, only the corrected run reported: `task add` and `task claim` take
`--id`, not `--task-id`; `efo init` opens the ledger with **two** events, not
one (the workspace and its orchestrator); and four expectation strings named
`exit 1` where the CLI returns `exit 2`, plus one case difference (`Report`, not
`report`). Every one was a correct refusal mislabelled by me.

## Scope

`cli.py`'s parser and all 30 subcommands, `main()`'s error handling, and the
mutation/ledger census. Not examined: `dashboard.py` behind `efo serve` (no
socket was bound), `errors.py`, and the `legacy audit` path against a real
Markdown workspace.

Pre-registered permissions unchanged: `gpu: false`, `network: false`,
`performance_metrics: false`; gates `allow_skips: false`,
`require_validation: true`, `require_known_answer_check: true`,
`require_independent_verification: true`.

**SUBMITTED, not VERIFIED.**

| Artifact | SHA-256 |
|---|---|
| `raw/probe_cli_surface.py` | `cd332a4f2ecb05aa0e7bea2819b4d8c8b09fdb900f70aa9f14153f04287d285a` |
| `raw/raw-cli-surface.txt` | `c9a98d65477d8c5f463b0489dc8f27d43c91fda04fb4eb4325d120f360b61f49` |
