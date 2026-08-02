# The ledger chain at `main` `5694ab45` — every documented claim holds; truncation is the one shape it does not cover

Reproduce with `raw/probe_ledger_chain.py`; raw output in
`raw/raw-ledger-chain.txt`. **12 checks pass, 1 flags.**

The hash chain is textbook-correct: `sequence`, `previous_hash`, `event_hash`
over `canonical_json` of the core fields, HMAC over that hash, both compared with
`hmac.compare_digest`, and the whole chain re-verified on every append before a
new event is written.

## The documented claims hold

`docs/ARCHITECTURE.md:160` and its neighbours were tested as written:

| Documented claim | Observed |
|---|---|
| **positive control** — untouched ledger | `{'valid': True, 'events': 8, 'signed': True}`, doctor `healthy=True` |
| "Ledger line is edited → hash or HMAC verification fails" | `IntegrityError: Ledger event hash mismatch at event 3` |
| a forged signature over an intact hash | `IntegrityError: Ledger signature mismatch at event 3` |
| two events reordered | `IntegrityError: Ledger sequence mismatch at event 3` |
| an event duplicated in place | `IntegrityError: Ledger sequence mismatch at event 4` |
| "Task JSON is lost → ledger retains complete snapshot" | `IntegrityError: T1: projection missing` |

**Not probed as a defect, because the documentation already says it:**
`README.md:422` and `SECURITY.md:38` state that the local HMAC key only protects
against parties who cannot read it, and that it is not a substitute for an
external transparency log. Re-signing a forged chain with the local key is
therefore an acknowledged limitation, not a finding, and I did not report it as
one. The same goes for `README.md:430` on a dishonest orchestrator misdeclaring
an identity — issue #3 is narrower than that disclaimer, and says so.

## The gap: a truncated ledger verifies clean

Truncation is not an edit, and there is no row for it in that table.

Dropping the last event and leaving the projections alone **is** caught — though
not by the chain:

| Step | Observed |
|---|---|
| `ledger.verify()` after dropping the tail | **accepted** — `{'valid': True, 'events': 7}` |
| `get_task("T1")` | `IntegrityError: Task T1 projection differs from the signed ledger` |
| `doctor` | `healthy=False` |

That is the projection cross-check doing the work, and it works. But it is the
only thing standing there, and it is defeated by rolling the projection back to
the snapshot the truncated chain still contains:

| Step | Observed |
|---|---|
| `ledger.verify()` | **accepted** — `{'valid': True, 'events': 7, 'signed': True}` |
| `get_task("T1")` | **accepted**, `state=pending` |
| `doctor` | **`healthy=True`** |

The `task.claimed` event is gone from history, every check reports clean, and
**none of this needs the signing key** — which is what distinguishes it from the
limitation the documentation does disclaim. The chain proves that the events it
still holds are authentic and in order. It does not prove that they are all of
them.

### Why the obvious fix does not work, and what would

`last_event_hash` looks like the anchor: it is written onto every projection
(`workspace.py:529`). It is excluded from every comparison that reads one
(`workspace.py:470`, `495`, `517`, `1511`). But re-checking it would not close
this — the rolled-back projection carries a hash that is still in the truncated
chain, so it stays consistent.

Closing it needs a count or head recorded where the ledger writer is not the
only party who has to update it: persist `{"events": N, "head": H}` after each
append and compare on verify, which catches accidental truncation and any writer
with partial access; or the external anchor `README.md:424` already recommends,
which is the only thing that closes it against a writer with full workspace
access.

## Severity, plainly

This needs filesystem write access to the workspace, and `SECURITY.md:34` already
says application-level ownership does not stop a process editing files directly.
So the exposure is adjacent to a stated limitation. What is not stated anywhere,
and is the reason this is worth a line in the threat table, is that after
truncation **`ledger verify` and `doctor` both report clean** — an operator
reading that table would reasonably expect the hash chain to cover a missing
tail, and it does not.

I am reporting this as a documentation-and-hardening gap, not as a new
vulnerability class.

## Harness bugs, caught before any conclusion

Two, both mine, only the corrected run reported: `doctor` exports
`audit_workspace`, not `diagnose`, and it takes a workspace **root path**, not a
`Workspace` object.

## Scope

`ledger.py` and the projection cross-checks in `workspace.py`. `archive.py` was
not probed — what archival does to the chain is still open.

Pre-registered permissions unchanged: `gpu: false`, `network: false`,
`performance_metrics: false`; gates `allow_skips: false`,
`require_validation: true`, `require_known_answer_check: true`,
`require_independent_verification: true`.

**SUBMITTED, not VERIFIED.**

| Artifact | SHA-256 |
|---|---|
| `raw/probe_ledger_chain.py` | `21b1e55da06820549bc0ecfebe74776c336cc02d5537e129b465466150dfb34e` |
| `raw/raw-ledger-chain.txt` | `84bff205eabf75bbd821b3dcca3f833be912e08cf6c3ae09506f30d7235f9c96` |
