# `SECURITY.md`, `CONTRIBUTING.md`, `OPERATIONS_DASHBOARD.md` — the last unread documents; three claims probed, all hold

Reproduce with `raw/probe_remaining_docs.py`; raw output in
`raw/raw-remaining-docs.txt`. **13 checks, 0 unexpected.** No issue filed.

These were the last three documents no pass had read end to end. With them
adjudicated, **every Markdown document in the repository has now been read
straight through and every falsifiable sentence mapped to a measurement or a
reason it needs none.**

| Disposition | Count |
|---|---|
| probed here for the first time | 3 |
| already covered by an existing write-up | 13 |
| stated limitations, operator advice, or contributor process | 5 |

## The three probed

### `SECURITY.md:61-63` — nested ignore rules

> New workspaces create nested ignore rules for `.efo/ledger.key`, lock files,
> and `runs/`.

Holds, and all three named things are covered. A fresh workspace writes exactly
two ignore files:

```
.efo/.gitignore    ledger.key
                   locks/
runs/.gitignore    *
                   !.gitignore
```

The `runs/` rule is the strict form — ignore everything, re-include only the
rule itself — so a file added under `runs/` later is ignored without anyone
updating a pattern.

**Not measured:** whether git honours them when the workspace is embedded in a
parent repository. That needs a real parent repo, and the sentence's own next
line is the caveat (*"Keep those rules in place when embedding a workspace in
another Git repository"*).

### `SECURITY.md:11` and `CONTRIBUTING.md:18` — no `shell=True`

Holds. **One** `shell=` keyword exists across `src/` and `monitor/`:

```
src/evidence_orchestrator/adapter.py:180  shell=False
```

Counted from the **AST**, not by grepping the string, so `shell = True` with
spaces, or a variable passed as the value, would still have been seen. A
subprocess call with no `shell` keyword defaults to `False`, which is why a
count of one explicit use is not itself a concern.

### `SECURITY.md:29` — reports stay in their owned directory

> Worker reports and manifests must remain inside their owned report directory.

Holds, driven behaviourally. Both refusals name the rule:

| Submitted report | Result |
|---|---|
| outside the workspace entirely | `Report must be under the actor's report directory` |
| another agent's report directory | same refusal |

The guard is `is_relative_to` at `workspace.py:1017` and `:1021` — the helper
`NOTE-util-and-lock-hold.md` measured as correct, distinguishing
`reports/wombat` from `reports/w` and failing **closed** on a symlink pointing
outside. Two further call sites enforce the same rule for the transport
envelope (`:1118`, `:1123`) and the verifier (`:1335`);
`NOTE-proxy-grant-holds.md` covers the transport pair.

This is the third document to state a containment promise, after
`MIGRATION.md:43-52` and `README.md:404-406` — but note it is a **different**
containment: worker reports, which hold, versus the legacy write test, which
does not (issue #17). Same shape of promise, different code path, opposite
verdict. Worth keeping distinct.

## What `OPERATIONS_DASHBOARD.md` yielded

Nothing new, and that is stated plainly rather than dressed up as a thorough
pass. It is 319 lines that are mostly deployment instructions — wrangler
config, SSH setup, systemd units. Its behavioural claims restate the collector
and chat properties already measured in `NOTE-collector-redaction-holds.md`,
issue #13 and issue #14.

## What is not a code property

Five entries are adjudicated as *not falsifiable against the code*, and the
distinction matters:

- `SECURITY.md:34-46` — three stated limitations (application-level ownership
  does not stop a process editing files directly; the local key protects only
  against parties who cannot read it; the orchestrator is the proxy policy
  root and a signed event does not prove a remote model authored a commit).
  Honest, and correctly outside the scope of a measurement.
- `SECURITY.md:50-59` — the never-commit list is advice to an operator.
- `CONTRIBUTING.md:14-21` and `:24-31` — contributor norms and PR process. One
  of them, *"keep external command execution free of `shell=True`"*, **is** also
  a property of the shipped code, and that half is section B.

## Scope

Every falsifiable sentence in `SECURITY.md` (67 lines), `CONTRIBUTING.md` (31)
and `docs/OPERATIONS_DASHBOARD.md` (319) at `main` `5694ab45` (precondition
verified: `HEAD` matches, `git status --porcelain` empty).

Not examined: git's actual behaviour on the nested ignore rules inside a parent
repository, and the dashboard deployment instructions as instructions — no
wrangler deploy or SSH collector install was attempted, and `network: false`
forbids it.

Pre-registered permissions unchanged: `gpu: false`, `network: false`,
`performance_metrics: false`; gates `allow_skips: false`,
`require_validation: true`, `require_known_answer_check: true`,
`require_independent_verification: true`.

**SUBMITTED, not VERIFIED.**

| Artifact | SHA-256 |
|---|---|
| `raw/probe_remaining_docs.py` | `89a56d42e2c40654c0894c93e086c38540588bdd0d0314eca37df64364a77b8f` |
| `raw/raw-remaining-docs.txt` | `5ff3f0416109d37b18a9826c3d773868f8ed98927785ec004263be1f988a51a0` |
