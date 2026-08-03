# `reports/`, `submissions/` and `archive/` are compared against nothing — six for six

Reproduce with `raw/probe_archive_tree_uncompared.py`; raw output in
`raw/raw-archive-tree-uncompared.txt`. **14 checks, 0 unexpected.** A **map** —
**no issue filed**, nothing retracted.

**Scope, stated first:** 7 workspaces, a full lifecycle each, 4 directories, 6
tampers, 1 control, 7 recorded hashes.

## What item 57 left open

That round measured the covered set — config, agent records, task projections —
and found `runs/` uncovered. It could **not** enumerate `reports/`,
`submissions/` or `archive/`, because a fresh workspace does not create them,
and it said so.

This builds a workspace far enough to have all three: init → two identity
attestations → create → claim → start → **submit** with a real evidence bundle
→ **verify** with a second bundle → **archive**. The task reaches `archived` and
the untouched workspace audits **healthy** — the control.

## The six comparison messages name only three things

Derived from `workspace.py`, not typed:

```
    Agent {agent_id} registration differs from the signed ledger
    Agent {agent_id!r} registration differs from the signed ledger
    Task {task['id']} projection differs from the signed ledger
    Task {task_id} projection differs from the signed ledger
    Workspace configuration differs from the signed ledger
    {task_id}: no ledger event
```

**Not one names `reports/`, `submissions/` or `archive/`.** Driven rather than
read off:

| tamper | outcome |
|---|---|
| the untouched workspace | **healthy** — control |
| edit `archive/T1.json` (flip the state to `pending`) | **healthy — unnoticed** |
| edit an **archived artifact** | **healthy — unnoticed** |
| delete an **archived artifact** | **healthy — unnoticed** |
| edit `submissions/.../bundle.json` | **healthy — unnoticed** |
| **delete the whole `submissions/T1`** | **healthy — unnoticed** |
| edit a report under `reports/claude/` | **healthy — unnoticed** |

**Six for six.**

## And the data to catch every one is already signed

```
    archived evidence files                              7
    sha256 values recorded in SIGNED ledger events       7
    archived files whose hash IS in the ledger           7
```

Nothing recomputes them.

## What this is — and what it is not

- It is the **measured width of issue #10**, not a new issue. #10 says
  `archive.py` retention has no verifier. What this adds is that the gap is not
  only retention: an archived bundle can be **edited or deleted wholesale**, and
  the archived task record **rewritten**, with `doctor` still reporting
  `healthy: true`.
- **Not filed.** It quantifies an open issue of mine rather than opening
  another.
- Every *"unnoticed"* here is measured **under the threat model
  `SECURITY.md:38` declares** — item 57 showed that a **re-signed** tamper of
  the *covered* files is healthy too. The difference is that these six need
  **no key at all**.
- It does **not** claim the covered set is wrong: config, agents and tasks
  **are** compared, and item 57 drove that.

## What this does not do

- It does **not** enumerate `shared/`. That directory exists after `init` and
  was **not driven** — stated, not implied.
- It does **not** test the CLI `ledger audit-projections` path separately;
  `doctor.audit_workspace` calls `audit_projections` and is the surface an
  operator is told to run.
- It does **not** propose a fix, and does **not** retract or narrow #10.
- No network. Seven workspaces, all `tempfile` directories, removed before the
  results print. The anchor's working tree is untouched, and it does **not**
  touch `main` or another agent's branch.
- **MEASURED:** the six comparison messages, the lifecycle reaching `archived`,
  the three directories, all seven archived files and their ledger-recorded
  hashes, all six tampers, the control. **REASONED:** nothing.

> **A filter slip of mine, caught by the run.** `.strip("{}")` left the trailing
> `}:` on `{task_id}:` — stripping a **set of characters** is not stripping a
> **suffix**. Corrected to the measured token before the run reported here.

Pre-registered permissions unchanged: `gpu: false`, `network: false`,
`performance_metrics: false`; gates `allow_skips: false`,
`require_validation: true`, `require_known_answer_check: true`,
`require_independent_verification: true`.

**SUBMITTED, not VERIFIED.** Re-running my own evidence is a re-run, not
independent confirmation.

| Artifact | SHA-256 |
|---|---|
| `raw/probe_archive_tree_uncompared.py` | `c65ba360f35cff9eb45c9333ed86931f2ac5b28c832e11f965ea6e0e5d336816` |
| `raw/raw-archive-tree-uncompared.txt` | `22e8813514441aaeec38f626dd0042b0d55ac8df685b8aa43a044e4eae6b2ce6` |
