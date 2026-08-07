# W4 needs a ref the anchor never took — and both its tracebacks are the driver's

Reproduce with `raw/probe_w4_replay.py`; raw output in `raw/raw-w4-replay.txt`.
**21 checks, 0 unexpected.** A **map about a ref this review is not anchored
to** — no issue filed, nothing retracted.

**Scope, stated first:** 2 refs, **1 of the 7** remaining sections, 5 driven
commands.

## The correction, first

Item 52 replayed W3 six-for-six at the anchor and wrote that W4–W8's *"blocker
is gone"*. **For W4, W5, W6 and W6b that is wrong**, and the reason is not a
missing client:

```
    transfer_orchestrator     7 occurrences across 3 files at 7a9553b
                              (cli.py, workspace.py, test_meta_orchestration.py)
                              0 files at 5694ab45 — not src, not tests, not docs

    git merge-base --is-ancestor 7a9553b 5694ab45   →  NO
```

**`7a9553b` is not an ancestor of the anchor.** The anchor's `workspace.py` line
begins at `f827f29`; `7a9553b` is a separate branch. Corrected in that note with
a dated banner.

So `raw-attack4.txt` **mixes two lines of history**: W1/W2/W2b compare the v0.1
wheel against `git archive f827f29` — the anchor's ancestor — while W4, W5, W6
and W6b drive a v2 that only exists on the other line. W3 reproduced at the
anchor because its property (the v0.1 client refusing an attested agent record)
is common to both.

The anchor's ledger action list is **derived from its own source**, not typed
here, and holds no orchestrator transfer:

```
    agent.added  agent.identity_attested  task.archived  task.blocked
    task.claimed  task.created  task.heartbeat  task.lease_expired
    task.proxy_authorized  task.proxy_status_reported  task.proxy_submitted
    task.rejected  task.requeued  task.started  task.submitted  task.verified
    workspace.initialized
```

## W4 replayed — against `7a9553b`, named rather than assumed

| | committed | fresh run at `7a9553b` |
|---|---|---|
| `workspace transfer-orchestrator` | `exit=0` | **0** |
| payload keys | `event_hash`, `from`, `to`, `reason` | **same four** |
| from → to | `antigravity → codex` | **antigravity → codex** |
| `event_hash` | `58f129a9…` | **differs — and must** |

The hash is signed and timestamped; a byte-equal one would mean the run had not
been redone.

## Both tracebacks are the original driver's

| | result |
|---|---|
| driver's path `ws4/workspace.json` | **`FileNotFoundError`** — reproduces exactly |
| correct path `.efo/workspace.json` | **`antigravity`** |
| driver's key `status_json['orchestrator']` | **`KeyError: 'orchestrator'`** — reproduces exactly |
| correct key `['status']['orchestrator']` | **`codex`** |

The CLI's `status` output has keys `['status', 'tasks']`, so indexing
`orchestrator` on the **wrapper** raises. **W6b is the same question asked
correctly**, and it answers. Neither traceback is EFO's.

> **An expectation of mine, corrected to the measurement.** I first predicted
> that `Workspace(...).status()['orchestrator']` would raise the `KeyError`. It
> does not — the Python API returns a flat dict and gives `codex` directly. The
> `KeyError` comes from the **CLI's JSON**, which is a different shape. Measured
> before it was written down.

## The config/ledger divergence is real, and by design

```python
    def orchestrator(self) -> str:
        orchestrator = str(self.config["orchestrator"])
        if not self.ledger.path.exists():
            return orchestrator
        for event in self.ledger.read():
            if event.get("action") != "workspace.orchestrator_transferred":
                continue
            target = event.get("payload", {}).get("to")
            if isinstance(target, str):
                orchestrator = target
        return orchestrator
```

At `7a9553b` the property **seeds from the config and then replays the transfer
events**. So *"config file orchestrator: antigravity"* and *"effective
orchestrator: codex"* are both correct at once — the config is a seed, the
ledger is the authority. W6/W6b measured a real divergence, and it is the
intended one.

**This says nothing about the anchor**, where no such event exists and
`orchestrator` is the config value alone.

## What this does not do

- It does **not** run W5, W6, W6b, W7 or W8. Four of the six remaining sections
  need `7a9553b`, which is now checked out at `/tmp/efo-7a9553b` and named.
- It does **not** review `7a9553b`. That commit is **not** this review's
  subject; nothing here is a verdict about its code.
- It does **not** claim to know which v2 produced `raw-attack4.txt` — only that
  the API W4 uses exists on `7a9553b`'s line and not the anchor's.
- It does **not** file an issue and retracts no finding. It **does** correct
  item 52's *"their blocker is gone"*, in place and dated.
- No network, no server. Both checkouts are local (`git clone --shared`), and
  the workspace is a `tempfile` directory removed before the results print. It
  does **not** touch `main`, the anchor's working tree, or another agent's
  branch.
- **MEASURED:** both file censuses, the ancestry, the anchor's action list, the
  committed payload, all five driven commands, both tracebacks and both
  corrections, the property body. **REASONED:** nothing.

Pre-registered permissions unchanged: `gpu: false`, `network: false`,
`performance_metrics: false`; gates `allow_skips: false`,
`require_validation: true`, `require_known_answer_check: true`,
`require_independent_verification: true`.

**SUBMITTED, not VERIFIED.** Re-running my own evidence is a re-run, not
independent confirmation.

| Artifact | SHA-256 |
|---|---|
| `raw/probe_w4_replay.py` | `8bb143dce90ef45040dceb4b9f658c92a77523cab856eefe2f6cff7b827e0c71` |
| `raw/raw-w4-replay.txt` | `53d2097ee23bf76a9114bf8c1d4f0ae2a41db60a2385eaba4435217581f77e54` |
