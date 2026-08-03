# Every directory a workspace has, tampered — and the one tamper that *is* caught

Reproduce with `raw/probe_every_directory_tampered.py`; raw output in
`raw/raw-every-directory-tampered.txt`. **18 checks, 0 unexpected.** A **map**
that widens an open issue — **no issue filed**, nothing retracted.

**Scope, stated first:** 9 directories enumerated, 3 coverage classes asserted
exhaustive, 8 new tampers, 2 positive controls, 1 caught.

## What item 60 left open, and why it was a real gap

That round said plainly that it did **not** enumerate `shared/` — the
directory exists after `init` and no tamper touched it. Driven rather than
repeated:

```
    shared/ exists after INIT alone   True
    and it is EMPTY                   []
```

So it is not an artefact of any particular lifecycle. It ships with every
workspace and nothing had ever been written against it.

## The population, enumerated rather than named

```
    ['.efo', 'agents', 'archive', 'ledger', 'reports',
     'runs', 'shared', 'submissions', 'tasks']
```

**Nine** top-level directories, read off the filesystem. The classification is
asserted **exhaustive in both directions** — no directory is unclassified, and
no class names a directory that does not exist:

| class | directories |
|---|---|
| driven by **item 57** | `agents/`, `tasks/`, `runs/` *(+ `.efo/workspace.json` as config)* |
| driven by **item 60** | `reports/`, `submissions/`, `archive/` |
| **never driven** | `shared/`, `ledger/`, `.efo/` |

## The eight new tampers

| tamper | outcome |
|---|---|
| add a file under `shared/` | **healthy — unnoticed** |
| add a subtree under `shared/` | **healthy — unnoticed** |
| **delete `shared/` entirely** | **healthy — unnoticed** |
| add a stray file under `ledger/` | **healthy — unnoticed** |
| add a stray file under `.efo/` | **healthy — unnoticed** |
| add a stray lock under `.efo/locks/` | **healthy — unnoticed** |
| **delete the shipped `runs/.gitignore`** | **healthy — unnoticed** |
| **delete `.efo/.gitignore`** | **healthy — unnoticed** |

**Eight for eight**, three of them deletions rather than plants. The
complement is asserted too — **0 caught** — because a count of "unnoticed"
alone would read the same if the audit had crashed, since this probe reports a
raise as *caught*.

## And a tamper that *is* caught

Every round in this line has reported *unnoticed*, which is a fair reason to
ask whether the driver detects anything at all. `.efo/ledger.key` lives
**inside** the workspace (item 57), so replacing it must break every
signature:

| tamper | outcome |
|---|---|
| **replace** `.efo/ledger.key` | **CAUGHT** — `Ledger signature mismatch at event 1` |
| **delete** `.efo/ledger.key` | **CAUGHT** — `Ledger signing key is missing: …` |

Two **distinct** failure messages, asserted distinct so this is not one
control counted twice. **The driver is not blind.** What the eight above show
is the *scope* of what the signature covers — not a failure to look.

## What this is — and what it is not

- It is the **measured width of issue #10**, widened from the three
  directories item 60 named to the **whole tree**. **Not filed** — quantifying
  an open issue is not opening another.
- It does **not** claim the covered set is wrong. Config, agents and tasks
  **are** compared (item 57), and the section above confirms the signature
  path still bites.
- Every *unnoticed* is measured **under the threat model `SECURITY.md:38`
  declares**. A tamper needing the key is a different measurement — and the
  two controls are exactly the ones that need it.

## What this does not do

- It does **not** enumerate **files** exhaustively — only directories, plus
  the four shipped files the tampers name. A file this round did not touch is
  **unchecked**, not shown safe.
  > **Closed 2026-08-03 by item 66.** All **27** shipped files are now
  > enumerated and collapsed to **17 kinds**, every kind driven: **5 caught,
  > 12 unnoticed**. The four `reports/<agent>/` kinds — including the
  > **evidence manifest** and the artifact and raw output whose `sha256` it
  > carries — had been reached by no round.
  > `NOTE-every-file-tampered-and-the-four-reports-kinds.md`.
- It does **not** propose a fix, and does **not** retract or narrow #10.
- Workspaces are keyed by **index**, not by the tamper's first word — items 57
  and 60 both hit collisions when two drives derived the same directory name.
- No network, no GPU. Twelve `tempfile` workspaces, removed before the results
  print. The anchor's working tree is untouched, and it does **not** touch
  `main` or another agent's branch.
- **MEASURED:** the directory enumeration, the exhaustiveness of the
  classification in both directions, `shared/` after a bare `init`, all eight
  tampers and their complement, both key tampers and their distinctness, the
  lifecycle control. **REASONED:** nothing.

Pre-registered permissions unchanged: `gpu: false`, `network: false`,
`performance_metrics: false`; gates `allow_skips: false`,
`require_validation: true`, `require_known_answer_check: true`,
`require_independent_verification: true`.

**SUBMITTED, not VERIFIED.** Re-running my own evidence is a re-run, not
independent confirmation.

| Artifact | SHA-256 |
|---|---|
| `raw/probe_every_directory_tampered.py` | `bd2198c514960ec450082477f52aad1c524ab4021f23eaf7a1bdffcd408e83d3` |
| `raw/raw-every-directory-tampered.txt` | `12d3688950452502a3d5009576f175310542e838c1d347f52488d681878a1b42` |
