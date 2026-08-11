# The command adapter at `main` `5694ab45` — the ownership guard works; its allow-list hands the child the ledger

Reproduce with `raw/probe_adapter_sandbox.py`; raw output in
`raw/raw-adapter-sandbox.txt`. **31 checks, 0 unexpected.** Section A is the
positive control — an honest command agent must reach `submitted` before any
block below means anything — and every block is asserted on the *reason*
recorded in the ledger, by substring, so a different guard firing cannot be
mistaken for the one under test.

The child agent is a real subprocess launched through `run_once`, not a mock.

## The documented claim holds

`docs/ARCHITECTURE.md:161` — *"Agent writes another workspace area → Command
adapter reports and blocks"* — and `README.md:150` item 5, *"detects writes
outside the agent's workspace ownership"*:

| Probe | State | Reported |
|---|---|---|
| **positive control** — honest agent | `submitted` | doctor `healthy=True` |
| write into another agent's report directory | `blocked` | `['reports/other/planted.md']` |
| rewrite `shared/FACTS.md` | `blocked` | `['shared/FACTS.md']` |
| rewrite `.efo/workspace.json` | `blocked` | `['.efo/workspace.json']` |
| rewrite another agent's task projection | `blocked` | `['tasks/T2.json']` |
| exit code 3 | `blocked` | `Agent command exited with code 3` |
| overrun a 2 s timeout | `blocked` | `Agent command timed out after 2s` |
| write no report at all | `blocked` | `Evidence gate rejected output: Report does not exist: …` |
| declare a failing validation | `blocked` | `Evidence gate rejected output: validations[0] did not pass: exit_code=1, failed=2` |

Prefix matching is correct — no off-by-one either way, checked directly rather
than inferred:

```
reports/wombat/x.md    vs ['reports/w']     -> FLAGGED   (sibling sharing a name prefix)
reports/w/x.md         vs ['reports/w']     -> allowed
reports/w              vs ['reports/w']     -> allowed
tasks/T1.json          vs ['tasks/T1.json'] -> allowed
tasks/T10.json         vs ['tasks/T1.json'] -> FLAGGED   (longer sibling of a file grant)
```

`argv` is built by textual substitution (`adapter.py:55-62`) and run with
`shell=False` (`adapter.py:180`), so metacharacters in a path are not
interpreted.

## The finding: `ledger/events.jsonl` is on the allow-list

`adapter.py:147-156` builds the effective ownership set. Measured for a default
worker:

```
reports/w
runs/w
reports/w            <- duplicated; adapter.py:151-152 re-adds the agent default
runs/w               <- same
tasks/T1.json
ledger/events.jsonl
```

The last line is the signed event stream. So the child process may rewrite it,
and the component whose documented job is to report writes outside the agent's
ownership will not say a word.

Executed end to end, with the child doing exactly the truncation from issue #9
from *inside* the sandbox the adapter is supposed to be policing — drop the
tail event, roll `tasks/T1.json` back to the snapshot the truncated chain still
holds:

```
the child dropped ledger event 12 (task.started) and rolled tasks/T1.json back to match
```

| Question | Observed |
|---|---|
| does the adapter report an unauthorized change? | **`None`** |
| what does it say instead? | `Task T1 must be running before submission` |
| does the chain still verify? | **accepted** — `{'valid': True, 'events': 12, 'signed': True}` |
| does `doctor` notice? | **`healthy=True`** |
| is the erased event still in history? | `task.started present: False` → `['task.created', 'task.claimed', 'task.blocked']` |

A signed event was erased and the run was recorded as an ordinary transition
failure. Nothing anywhere attributes it to the ledger rewrite that caused it.

### Why the obvious fix does not work, and what would

Removing `ledger/events.jsonl` from the list would break the adapter. The
snapshot diff cannot attribute a write to a *process* — `adapter.py:193` has
the adapter itself heartbeating into the ledger while the child runs, and
`_commit_task` rewrites `tasks/<id>.json` on `start`. Both would be flagged as
unauthorized changes by the agent. The grant is structural: the sanctioned set
is precisely *the files the broker itself touches during the run*, and the
child inherits them.

What closes it is counting rather than allow-listing. The adapter knows exactly
what it wrote: one `task.started` event plus N heartbeats. Record the ledger
event count and head hash before launching the child, compare after, and treat
any surplus **or deficit** as a child write — a deficit is the truncation case
and is not otherwise reachable. The same applies to `tasks/<id>.json`: compare
against the projection `_commit_task` last returned rather than exempting the
path. That turns two blanket grants into two exact expectations.

## Structural blind spots, measured and reported as context

A before/after snapshot cannot see these, and `docs/ARCHITECTURE.md:163` already
says *"Agent bypasses the broker → Detectable in some cases, not preventable
without OS isolation"*, so none of them is filed as a defect:

| Probe | Observed |
|---|---|
| a file rewritten and restored within the run | `submitted`, `unauthorized_changes=None` |
| an empty directory created in `shared/` | not reported (`_workspace_snapshot` records files only); `exists=True` afterwards |
| a write through a symlink pointing outside the workspace | `submitted`, not reported, and the write landed outside |

The symlink case is the sharpest of the three, and it is worth one sentence in
the failure table even though it is covered by the OS-isolation caveat: the
link itself lives in `reports/w`, which the agent owns, so nothing about
creating it is anomalous.

Two further facts, measured, both consistent with what the documentation
already says: `_workspace_snapshot` skips `.efo/locks/` and nothing else, so
`.efo/ledger.key` sits inside the tree the child runs in — the local-key
limitation `SECURITY.md:38` states — and `adapter.py:158` passes
`{**os.environ, …}` straight to the child, which is how this probe's own mode
variable reached it. An untrusted agent CLI therefore inherits every credential
in the broker's environment. `docs/ARCHITECTURE.md:165-169` recommends a
container or separate OS account for exactly this, so it is recorded, not
filed.

## Severity, plainly

This does not defeat the evidence gates: the honest path still requires a
passing manifest, and a failing one is still refused. What it defeats is
*attribution*. Issue #9's severity note said the truncation attack "needs
filesystem write access to the workspace" — a command-mode agent has that by
design, and this measurement shows the write is sanctioned rather than merely
possible. That is the part worth correcting in #9's assessment.

## Scope

`adapter.py` in full — `run_once`, `_workspace_snapshot`,
`_unauthorized_changes`, `_expand_command`, `render_task_prompt`. Not examined:
`run_loop`'s idle and `max_tasks` accounting under real concurrency, and
`proxy_submit`'s archival path (`workspace.py:1220`), which is still queued.

Pre-registered permissions unchanged: `gpu: false`, `network: false`,
`performance_metrics: false`; gates `allow_skips: false`,
`require_validation: true`, `require_known_answer_check: true`,
`require_independent_verification: true`.

**SUBMITTED, not VERIFIED.**

| Artifact | SHA-256 |
|---|---|
| `raw/probe_adapter_sandbox.py` | `a3c4b4e0e353071ff55c348054fca3d9b57d36a1588a7490cd6849715549dace` |
| `raw/raw-adapter-sandbox.txt` | `9ceef5c47d3958a5ed11930af9899050ea78be8c9b642ea063b300a3e72520e4` |
