# A tamper that re-signs is healthy — and `SECURITY.md` says so in as many words

Reproduce with `raw/probe_ledger_signature_scope.py`; raw output in
`raw/raw-ledger-signature-scope.txt`. **20 checks, 0 unexpected.** A **map that
names a precondition** — no issue filed, nothing retracted.

**Scope, stated first:** 7 signed fields, 1 key, 6 comparison messages, 7 driven
tampers, 2 controls.

## The question three of my own notes rested on

Items 45, 53 and 54 each concluded a gap was **unreachable** because the ledger
signature or the projection comparison fires first. None asked **what the
signature covers**, or whether *"the guard blocks the path"* is a property or an
artifact of the tampers chosen.

**It is an artifact** — and the boundary is exactly where the document says it
is.

## What the signature covers

Derived from `ledger.py`'s own tuple, not typed into the probe:

```
    sequence, timestamp, actor, action, task_id, payload, previous_hash
```

SHA-256 over canonical JSON, then HMAC-SHA256 with a key from
`os.urandom(32)` — stored **inside the workspace it protects**, at
`.efo/ledger.key`, mode `0600`.

Six comparison messages exist in `workspace.py`, covering the **config**, the
**agent** records and the **task** projections. Driven:

| tamper | outcome |
|---|---|
| `config.name` | caught — *"Workspace configuration differs from the signed ledger"* |
| `config.orchestrator` | caught — same |
| `config.defaults.lease_seconds` | caught — same |
| a stray file under `tasks/` | caught — *"ZZ: no ledger event"* |
| a stray file under `runs/` | **unnoticed** — scratch space, not covered |

## The answer: re-sign, and it is healthy

| | outcome |
|---|---|
| a naive projection edit | **caught** — *"projection differs from ledger"* (control) |
| the same edit, ledger payload updated, whole chain **re-signed** | **`healthy: true`** |
| …and `ledger verify` on it | **`valid: true`, `signed: true`** |
| …and the task title now reads | **`"tampered"`** |

Anyone who can write `tasks/C1.json` can also **read `.efo/ledger.key`** — same
filesystem, same account. Recomputing the chain is a dozen lines. Every tamper
items 45, 53 and 54 drove left the signature stale; that is what the guard
catches.

## …and the document already says exactly this

`SECURITY.md` states, verbatim and asserted by the probe:

> *"The local ledger signing key protects against edits by parties that cannot
> read the key. If every worker uses the same OS account, use an external
> append-only store or a key held only by the orchestrator for stronger
> guarantees."*

and

> *"Application-level ownership does not stop a process that directly edits
> files outside EFO."*

So this is a **documented limit, driven in both directions and holding**:
cannot read the key → caught; can read the key → passes. **Not a defect.** It
is the same shape as `functions/api/local-health.js`, the strongest this review
has measured — a document that says what the code does, checked rather than
believed.

## What it means for three of my own notes

| item | conclusion | the precondition it never stated |
|---|---|---|
| **45** | `model.lease_expired`'s raise is blocked by the projection guard | holds only against an adversary who cannot read `.efo/ledger.key` |
| **53** | `provenance.py`'s `files`-list guards are never fed a malformed record | same |
| **54** | `doctor.py`'s 23 unguarded subscripts all sit behind the guard | same |

Each is correct **as measured**. Each holds **only** under the threat model
`SECURITY.md` declares. None of the three said so, and the difference between
*"unreachable"* and *"unreachable under the declared threat model"* is the whole
point of this round. Stated here and carried into SYNTHESIS rather than left
implicit.

## Two driver bugs of mine, both caught by the run

- I expected **2** comparison messages, from the two I had already seen in items
  45 and 54. `workspace.py` declares **6**. Corrected to the measurement.
- The five simple tampers derived their directory name from the tag's first
  word, so the three `config:` drives **collided** and the second hit
  *"Workspace already initialized"*. Caught by the exception; fixed with an
  index.

## What this does not do

- It does **not** file an issue. `SECURITY.md` states the limit, and the drive
  **confirms** the document rather than contradicting it.
- It does **not** retract items 45, 53 or 54 — it names the precondition each
  relied on without stating.
- It does **not** claim the covered set is complete beyond what was driven:
  config, agents and tasks are compared; `runs/` is not. `reports/`,
  `submissions/` and `archive/` are **not enumerated** — a fresh workspace does
  not create them. Stated, not implied.
- It does **not** attempt a tamper *without* the key; that case is already the
  naive control here and the whole of items 45 and 54.
- No network. Every workspace is a `tempfile` directory, removed before the
  document section prints. It does **not** touch `main`, the anchor's working
  tree, or another agent's branch.
- **MEASURED:** the seven covered fields derived from `ledger.py`, the key
  location and mode, all six comparison messages, all five simple tampers, both
  controls, the re-signed tamper and its `verify`, three `SECURITY.md`
  sentences. **REASONED:** nothing.

Pre-registered permissions unchanged: `gpu: false`, `network: false`,
`performance_metrics: false`; gates `allow_skips: false`,
`require_validation: true`, `require_known_answer_check: true`,
`require_independent_verification: true`.

**SUBMITTED, not VERIFIED.** Re-running my own evidence is a re-run, not
independent confirmation.

| Artifact | SHA-256 |
|---|---|
| `raw/probe_ledger_signature_scope.py` | `bf2777c49e979b7cf495fe0d936bdf6a29760e4cffdd3c06e59dd136b2a74f37` |
| `raw/raw-ledger-signature-scope.txt` | `974e59c1b195313a088331bca54b242f00d33d08fdceefad64dc5909e806ecb2` |
