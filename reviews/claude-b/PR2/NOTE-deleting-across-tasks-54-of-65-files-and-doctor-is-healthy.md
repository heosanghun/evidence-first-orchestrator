# Deleting across tasks — 54 of 65 files removed, and `doctor` reports healthy

Reproduce with `raw/probe_delete_across_tasks.py`; raw output in
`raw/raw-delete-across-tasks.txt`. **22 checks, 0 unexpected.** A **map that
widens the measured width of #10** a third time — no issue filed, nothing
retracted.

**Scope, stated first:** 2 workspace shapes, 65 files, 17 kinds, the 3 kinds
that cross the split, 6 per-kind drives, 5 whole-tree drives, 1 exhaustiveness
assertion.

## What item 72 left open, in its own words

> *It does **not** delete across **tasks** — one task, one attempt. A workspace
> with several archived tasks is **unchecked**, not shown safe.*

Both workspace shapes are built **in this run** — one task and three — so the
comparison stands on this run rather than on item 72's table plus this one.

## The split moves, and that is the measurement

| | files | kinds | multi-instance | singleton |
|---|---|---|---|---|
| one task | 27 | 17 | **9** | **8** |
| three tasks | **65** | 17 | **12** | **5** |

Item 72's split is re-derived here and agrees exactly. **Three kinds cross** —
`archive/*.json`, `submissions/.../files/*.md`, `tasks/*.json` — and none
crosses back.

`tasks/*.json` is one of the **four kinds item 72 measured as caught**, and a
kind whose message *could not possibly* move while there was only one of it.

## At three tasks, that message moves — and enumerates

| deletion | verdict |
|---|---|
| one `tasks/*.json` | `CAUGHT: T2: projection missing` |
| all three | `CAUGHT: T1: projection missing; T2: projection missing; T3: projection missing` |

Item 72 measured `agents/*.json` reporting **identically** for one and for all
three. This kind does not. The difference is only visible once a kind has more
than one instance to lose — which is exactly why item 72 could not see it.

`archive/*.json` is **unnoticed** either way, one or all three.

## Whole trees, and the one file that is load-bearing

| deletion | files | verdict |
|---|---|---|
| one task's submission tree | 9 | **healthy** |
| all three submission trees | 27 | **healthy** |
| everything belonging to T2 | 19 | **caught** — `T2: projection missing` |
| the same, sparing `tasks/T2.json` | 18 | **healthy** |
| every task's evidence, sparing the 3 projections | **54 of 65** | **healthy** |

> Sparing **one file of nineteen** turns a caught deletion into an invisible
> one. Every archived bundle, every report, every submitted copy and every
> archive record — **54 of 65 files** — can be removed with the product's own
> health check reporting the workspace healthy.

What is load-bearing is the three task **projections**: 3 files, and no
evidence at all.

## What this does not establish

- It does **not** file an issue. Item 69 widened #10 from edits to deletes,
  item 72 from one instance to every instance, this from one task to a whole
  workspace. Quantifying an open issue is not opening another.
- It does **not** retract item 72. Its one-task split is re-derived here from a
  workspace built in this run and agrees.
- The audit surface is `doctor.audit_workspace`, as in items 63, 66, 69 and 72.
  A human listing the directory sees the files are gone.
- Three tasks, **one attempt each**. A task with several attempts is
  **unchecked**, not shown safe.
- The `T*` filename sweep in the last two drives is bounded by the count it
  prints — 54 of 65 — rather than by my description of it.
- No network, no GPU. Twelve `tempfile` workspaces, removed before the results
  print. The anchor's working tree is untouched, and it does **not** touch
  `main` or another agent's branch.
- **MEASURED:** both censuses, the crossing kinds in both directions, six
  per-kind drives, five whole-tree drives, every verdict and every full
  message. **REASONED:** nothing.

Pre-registered permissions unchanged: `gpu: false`, `network: false`,
`performance_metrics: false`; gates `allow_skips: false`,
`require_validation: true`, `require_known_answer_check: true`,
`require_independent_verification: true`.

**SUBMITTED, not VERIFIED.** Re-running my own evidence is a re-run, not
independent confirmation.

| Artifact | SHA-256 |
|---|---|
| `raw/probe_delete_across_tasks.py` | `e36ad047b8895959966cfbb2283480147053e7667cfc6bc94f95eefe5ee494a1` |
| `raw/raw-delete-across-tasks.txt` | `1d1fe05f8517ff30bd18907a72dd55aff6c8d4a51732047823dafa6c69202201` |
