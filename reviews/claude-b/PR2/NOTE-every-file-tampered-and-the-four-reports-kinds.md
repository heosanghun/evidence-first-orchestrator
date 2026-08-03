# Every file a workspace ships, tampered — and the four `reports/` kinds nothing reached

Reproduce with `raw/probe_every_file_tampered.py`; raw output in
`raw/raw-every-file-tampered.txt`. **17 checks, 0 unexpected.** A **map** that
widens an open issue — **no issue filed**, nothing retracted.

**Scope, stated first:** 27 files, 17 kinds, 17 edit tampers, 2 positive
controls, 1 exhaustiveness assertion.

## What item 63 left open

That round enumerated **directories** and said plainly it did **not** enumerate
files. This does.

A full lifecycle to `archived` ships **27 files**, which collapse to **17
kinds** once the task id, the agent name and the content hashes are normalised
away. The kind rule is a **judgement stated in the source** — directory role
plus extension — and what is *asserted* is that every one of the 27 maps to
exactly one kind.

Every kind is then driven with an edit. This does **not cite** what items 57,
60 and 63 covered — it **re-derives all of it** in one run and adds what none
of them reached.

## All seventeen

| kind | outcome |
|---|---|
| `.efo/ledger.key` | **CAUGHT** — `Ledger signature mismatch at event 1` |
| `.efo/workspace.json` | **CAUGHT** — `Workspace configuration differs from the…` |
| `agents/*.json` | **CAUGHT** — `Agent 'antigravity' registration differs…` |
| `ledger/events.jsonl` | **CAUGHT** — `Malformed ledger JSON at line 13` |
| `tasks/*.json` | **CAUGHT** — `T1: projection differs from ledger` |
| `.efo/.gitignore` | healthy — unnoticed |
| `archive/*.json` | healthy — unnoticed |
| **`reports/<agent>/*.evidence.json`** | **healthy — unnoticed** |
| **`reports/<agent>/*.artifact.txt`** | **healthy — unnoticed** |
| **`reports/<agent>/*.raw.txt`** | **healthy — unnoticed** |
| **`reports/<agent>/*.md`** | **healthy — unnoticed** |
| `runs/.gitignore` | healthy — unnoticed |
| `submissions/.../bundle.json` | healthy — unnoticed |
| `submissions/.../files/*.evidence.json` | healthy — unnoticed |
| `submissions/.../files/*.artifact.txt` | healthy — unnoticed |
| `submissions/.../files/*.raw.txt` | healthy — unnoticed |
| `submissions/.../files/*.md` | healthy — unnoticed |

**5 caught, 12 unnoticed**, and the two classes are asserted to account for
every kind.

> I predicted **four** caught. There are **five** — I overlooked that
> `ledger/events.jsonl` is itself a kind. Corrected to the measurement, and the
> next section asks what that catch is actually *about*.

## Three distinct guards, not one

The ledger catch above is on **shape**: appending a line to a JSONL leaves
invalid JSON. That is not the same guard as one firing on a forged *value*, so
it was asked separately — a **valid-JSON** edit to a ledger record:

```
    a VALID-JSON edit to a ledger line    CAUGHT: Ledger event hash mismatch at event 12
```

> I expected the **signature** to fire. It is the **hash chain** — a **third**
> distinct message, checked before the signature is reached, and asserted
> distinct from it. Corrected to the measurement.

So the ledger is defended in depth: malformed shape, broken chain, bad
signature — three separate messages, all measured here.

## The four `reports/` kinds

```
    reports/<agent>/*.artifact.txt     healthy - unnoticed
    reports/<agent>/*.evidence.json    healthy - unnoticed
    reports/<agent>/*.md               healthy - unnoticed
    reports/<agent>/*.raw.txt          healthy - unnoticed
```

Item 60 drove **a report** under `reports/`. It did **not** drive the
**evidence manifest**, nor the artifact and raw output whose `sha256` that
manifest carries, **while they sit in the author's own directory** — only their
copies under `submissions/`. Those hashes are checked at **submit** time;
nothing re-checks them afterwards.

## The control, so a sheet of negatives means something

```
    replace .efo/ledger.key    CAUGHT: Ledger signature mismatch at event 1
```

Item 63's control, re-run here. **The driver is not blind** — the twelve
negatives measure the *scope* of what is compared, not a failure to look.

## What this does not do

- It does **not** file an issue. This widens the measured width of **#10** from
  directories to files; quantifying an open issue is not opening another.
- It does **not** claim the covered set is wrong. Five kinds **are** compared,
  by three distinct guards.
- Every *unnoticed* is measured **under the threat model `SECURITY.md:38`
  declares**.
- It drives an **edit** of each kind, not a **delete**. Item 63 drove three
  deletions at directory level; a per-kind deletion sweep is **unchecked**
  here, not shown safe.
- No network, no GPU. Twenty `tempfile` workspaces, removed before the results
  print. The anchor's working tree is untouched, and it does **not** touch
  `main` or another agent's branch.
- **MEASURED:** the file enumeration, the kind collapse and its completeness,
  all 17 edits, the valid-JSON ledger edit, the four `reports/` kinds, the key
  control, the lifecycle control. **REASONED:** nothing.

Pre-registered permissions unchanged: `gpu: false`, `network: false`,
`performance_metrics: false`; gates `allow_skips: false`,
`require_validation: true`, `require_known_answer_check: true`,
`require_independent_verification: true`.

**SUBMITTED, not VERIFIED.** Re-running my own evidence is a re-run, not
independent confirmation.

| Artifact | SHA-256 |
|---|---|
| `raw/probe_every_file_tampered.py` | `36b43bbe89444cf1c0dc4b8299b84d9fb33e0e5d0aaf95931b039acd99612233` |
| `raw/raw-every-file-tampered.txt` | `11b705357558fffd7ffbb84e9eab6b07e85d58d2d49772c9ef385a55ca1fb1bf` |
