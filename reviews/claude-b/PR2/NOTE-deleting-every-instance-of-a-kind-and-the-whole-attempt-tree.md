# Deleting *every* instance of a kind — and the whole attempt tree in one operation

Reproduce with `raw/probe_delete_every_instance_of_a_kind.py`; raw output in
`raw/raw-delete-every-instance-of-a-kind.txt`. **31 checks, 0 unexpected.**
A **map that widens the measured width of #10** a second time — no issue
filed, nothing retracted.

**Scope, stated first:** 27 files, 17 kinds, 9 multi-instance, 8 singleton, 26
deletion drives, 1 whole-subtree delete, 1 exhaustiveness assertion.

> **EXTENDED 2026-08-04 by item 75 — nothing here is retracted.** This round
> said plainly it does not delete across **tasks**. It has now been driven with
> three archived tasks: the split below moves to **12 multi / 5 singleton**,
> three kinds cross, and `tasks/*.json` — one of the four caught kinds — turns
> out to report a message that **enumerates** once there is more than one of it
> (`T1: …; T2: …; T3: …`), which one task could not show. **54 of 65 files**
> can then be removed with `doctor` healthy. See
> `NOTE-deleting-across-tasks-54-of-65-files-and-doctor-is-healthy.md`.

## What item 69 left open, in its own words

That round drove a delete of each of the 17 file kinds and said plainly:

> *It deletes ONE instance of each kind, not every instance. Deleting all three
> `agents/*.json` at once is UNCHECKED, not shown safe.*

This is that pass.

## The population splits itself

A full lifecycle to `archived` ships 27 files in 17 kinds. **Nine** kinds have
more than one instance; **eight** have exactly one — and for a singleton,
*delete one* and *delete all* are the same file set. That is measured from the
instance counts, not argued, and it makes the eight a **positive control**:
they must reproduce item 69's delete column.

They do. Four of the eight are caught — `.efo/ledger.key`,
`.efo/workspace.json`, `ledger/events.jsonl`, `tasks/*.json` — exactly item
69's four singletons.

## The nine, one instance versus all

| kind | instances | one deleted | all deleted |
|---|---|---|---|
| `agents/*.json` | 3 | **CAUGHT** | **CAUGHT** |
| `reports/<agent>/*.md` | 2 | healthy | healthy |
| `reports/<agent>/*.artifact.txt` | 2 | healthy | healthy |
| `reports/<agent>/*.evidence.json` | 2 | healthy | healthy |
| `reports/<agent>/*.raw.txt` | 2 | healthy | healthy |
| `submissions/.../bundle.json` | 2 | healthy | healthy |
| `submissions/.../files/*.artifact.txt` | 2 | healthy | healthy |
| `submissions/.../files/*.evidence.json` | 2 | healthy | healthy |
| `submissions/.../files/*.raw.txt` | 2 | healthy | healthy |

**Nothing moves — 0 of 9.** The verdict is the same and so is the message,
including for the one caught kind:

```
one agent record deleted : One or more signed agent projections are missing
all three deleted        : One or more signed agent projections are missing
```

Item 69 found that *the set holds while the message moves* between editing and
deleting. Between deleting one and deleting all, **neither** moves.

> So **eight** multi-instance kinds can be removed **entirely** — every report,
> every submitted copy, both bundles — with `doctor` reporting healthy.

## A truncation that would have hidden the answer

Item 69's audit helper cut the error message at **40 characters**. This round's
whole question is whether the message *moves*, and at 40 characters the agent
message reads `One or more signed agent projections are` — the word `missing`
falls off the end. The helper is un-truncated here, and the two messages are
compared in full. A truncation that hides exactly the difference under test is
not a display choice.

## The whole attempt tree, in one operation

Item 63 deleted **top-level** directories. `submissions/T1/attempt-001/` is a
sub-tree — the one holding the archived evidence itself, and the shape an
operator would actually reach for. It holds **9** files. Removing all of it in
one `rmtree`:

```
HEALTHY - unnoticed
task state: archived
```

The task still reports `archived` with none of its evidence on disk.

## What this does not establish

- It does **not** file an issue. Item 69 widened #10 from edits to deletes;
  this widens it from one instance to every instance. Quantifying an open issue
  is not opening another.
- It does **not** retract item 69. Its one-instance column is re-derived here
  for the eight singletons and agrees.
- The audit surface is `doctor.audit_workspace`, the same one items 63, 66 and
  69 used. A human listing the directory sees the files are gone; the product's
  own health check does not.
- It does **not** delete across **tasks** — one task, one attempt. A workspace
  with several archived tasks is **unchecked**, not shown safe.
- No network, no GPU. Twenty-eight `tempfile` workspaces, removed before the
  results print. The anchor's working tree is untouched, and it does **not**
  touch `main` or another agent's branch.
- **MEASURED:** the file enumeration, the kind collapse, the instance counts,
  all eight singleton deletes, all nine kinds both ways, the full messages, the
  whole-subtree delete, the lifecycle control. **REASONED:** nothing.

Pre-registered permissions unchanged: `gpu: false`, `network: false`,
`performance_metrics: false`; gates `allow_skips: false`,
`require_validation: true`, `require_known_answer_check: true`,
`require_independent_verification: true`.

**SUBMITTED, not VERIFIED.** Re-running my own evidence is a re-run, not
independent confirmation.

| Artifact | SHA-256 |
|---|---|
| `raw/probe_delete_every_instance_of_a_kind.py` | `6a93b688bc4ecd318fa245ac25670658e0df6edd6ff54c4c03ddd1cde9416f8b` |
| `raw/raw-delete-every-instance-of-a-kind.txt` | `9bee5208a29a52acfbafc25f3c5d1cbabb4e6884a47bcb3e683207e77e631e83` |
