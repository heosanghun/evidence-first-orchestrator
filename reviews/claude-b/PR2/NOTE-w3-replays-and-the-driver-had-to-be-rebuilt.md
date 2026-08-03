# W3 replays — six steps, and the driver had to be rebuilt from the output

Reproduce with `raw/probe_w3_replay.py`; raw output in `raw/raw-w3-replay.txt`.
**21 checks, 0 unexpected.** A **replay**, not a new finding — no issue filed,
nothing retracted.

## Scope, stated first — because the item asked for that before anything else

`raw-attack4.txt` carries **ten** section headers. Item 49 re-ran three (W1, W2,
W2b), leaving **seven**: W3–W8 plus a W6b rerun, about **24 commands** driving a
live v0.1-against-v2 shared workspace — init, task add, a signed orchestrator
handoff, and both clients reading each other's state.

**Every one of those commands is a local filesystem call. No network, no server,
no build.** EFO is a file-backed orchestrator and its own suite runs offline; the
v0.1 client is `py3-none-any` and runs from `PYTHONPATH`.

Twenty-four is more than one round, so this does **W3 alone** — six steps.

## The driver is gone, and that is the interesting part

Item 43 established that **no `attack4` script ever existed** — `git log --all
--diff-filter=D` finds nothing. So the command sequence is not recoverable and
had to be **reconstructed from the output**. The reconstruction is not assumed
correct; it is checked against two things a wrong sequence would not produce:

```
    the ledger event count   7
    the rejection string     "Agent 'antigravity' registration differs
                              from the signed ledger"
```

**The first reconstruction was wrong, and the event count said so.** `v2 init
--preset antigravity-codex-claude` followed by `v2 task add` gives **5 events**
and v0.1 `status` exiting **0** — no rejection at all. The missing step is
`agent attest`, which writes the identity block v0.1 cannot read. With two
attestations the count is 7 and the rejection appears.

That is the whole property W3 is about, and it was invisible until the number
disagreed.

## W3, replayed

| step | committed | fresh run |
|---|---|---|
| v2 `init` | `exit=0` | **0** |
| v2 `task add` | `exit=0` | **0** |
| v0.1 `status` | `exit=2`, *"Agent 'antigravity' registration differs from the signed ledger"* | **2**, same string |
| v0.1 `ledger verify` | `exit=0`, `events 7, signed true, valid true` | **0**, 7 / true / true |
| v0.1 `doctor` | `exit=0`, same error, `healthy: false` | **0**, same error, false |
| v0.1 `task show C1` | `exit=0` | **0** |

Six for six. **The shape W3 recorded is real and reproduces**: the v0.1 client
refuses the *agent record* while accepting the *ledger* and the *task* that v2
wrote. It fails closed on identity, not on the chain — and `ledger verify` exits
0 while `status` exits 2 in the same workspace.

Every expectation above is **parsed out of the committed `raw-attack4.txt`**;
every observation comes from a fresh run in a `tempfile` directory. Neither side
is typed in twice.

## What does not reproduce, and must not

The ledger **head** differs — `f888c7f2…` committed against `7f5469c2…` fresh.
The chain is HMAC-signed with a per-workspace key and every event carries a
timestamp, so a byte-equal head would mean the run had *not* been redone. What
must match are the properties: count, `signed`, `valid`, the exit codes, the
error string. Those do.

Also not reproduced and **not attempted**: W8's thirteen-key agent record. That
listing was taken *after* the W4 handoff, so it carries `governance_epoch` and
`active`; the record at W3 time has ten keys. Reading it as a W3 expectation
would be reading the wrong section.

## A count of mine, corrected in place

`NOTE-the-wheel-was-never-lost-git-had-it-all-along.md` said item 49 covered
*"2 of the 8 sections"*. The file has **ten** headers and the note covered
**three** — its one-byte-difference table and its six byte-identical security
modules **are W2b**, which I had not counted as a section. Corrected there with
a dated banner. This probe now **parses** the header list and **derives** the
remaining seven rather than naming them, so the next added section cannot slip
past.

## What this does not do

- It does **not** run W4–W8. Their blocker is gone and their scope is stated
  above; they remain **un-run** and are not claimed otherwise.
- It does **not** claim P2-1 or P2-2 are re-verified.
- It does **not** recover the original driver — that script never existed. The
  sequence here is a reconstruction matching the recorded event count and error
  string; a different sequence reaching the same state is **not excluded**.
- It does **not** file an issue and retracts nothing.
- No network, no server, no pip, no build. The workspace is a
  `tempfile.TemporaryDirectory()`, removed before the comparison section prints.
  It does **not** touch `main`, the anchor's working tree, or another agent's
  branch.
- **MEASURED:** the ten parsed section headers, all four parsed expectations,
  all four v2 setup exits, all six W3 outcomes, the head mismatch.
  **REASONED:** nothing.

Pre-registered permissions unchanged: `gpu: false`, `network: false`,
`performance_metrics: false`; gates `allow_skips: false`,
`require_validation: true`, `require_known_answer_check: true`,
`require_independent_verification: true`.

**SUBMITTED, not VERIFIED.** Re-running my own evidence is a re-run, not
independent confirmation.

| Artifact | SHA-256 |
|---|---|
| `raw/probe_w3_replay.py` | `f9461d131e8edd655d1903e0cc1e8e54e853659fe9146a36b7f9d7820ce600d6` |
| `raw/raw-w3-replay.txt` | `6ca52d4e6f637dcffdafde664ada87caccb4f916f5278d779b4aecf5df2dbe10` |
