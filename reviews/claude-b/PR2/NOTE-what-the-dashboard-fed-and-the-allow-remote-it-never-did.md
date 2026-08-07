# What the dashboard checks fed — and the `allow_remote` class they never did

Reproduce with `raw/probe_dashboard_allow_remote_class.py`; raw output in
`raw/raw-dashboard-allow-remote-class.txt`. **19 checks, 0 unexpected.** A
**narrowed scope** on a clean verdict — the verdict is **not retracted** and
**no issue is filed**.

**Scope, stated first:** 28 published checks classified, 3 typed parameters, 1
un-fed class, 10 driven values, 3 controls, 1 reachability measurement.

## The question item 47 asks of every clean note

`NOTE-dashboard-and-errors-hold.md` drove the bind guard with **fourteen host
spellings** and found it a **strict allow-list**. That result stands. But
`dashboard.serve` has **three** typed keyword parameters:

```python
host: str = "127.0.0.1"    port: int = 8765    allow_remote: bool = False
```

Classified from the published probe's own source: `host` takes the fourteen
strings, **`port` is always `0`**, and `allow_remote` reaches `serve()` only
through a helper whose signature is `bind_verdict(host: str, allow_remote:
bool = False)` — so only real booleans ever arrive.

**The un-fed class is a non-bool `allow_remote`.**

## The guard is a truthiness test, quoted from the file

`dashboard.py:218`:

```python
if host not in {"127.0.0.1", "::1", "localhost"} and not allow_remote:
```

**Strict on the host, loose on the flag — in one expression.** The host side is
exact set membership; the flag side is `not allow_remote`, which asks about
truthiness, not type.

## Driven

| `allow_remote` | outcome |
|---|---|
| `"no"` | **past the guard** |
| `"false"` | **past the guard** |
| `"0"` | **past the guard** |
| `1` | **past the guard** |
| `["x"]` | **past the guard** |
| `0` | refused by the bind guard |
| `""` | refused |
| `[]` | refused |
| `None` | refused |
| `0.0` | refused |

**Five of ten bypass the documented refusal**, and the three sharpest are the
**strings a reader would take to mean false** — `"no"`, `"false"`, `"0"`. Each
one turns the remote-binding guard off.

> **No socket is bound anywhere in this probe.** `serve()` is pointed at a path
> that is *not* a workspace, so `Workspace(root)` raises immediately **after**
> the guard — which error comes back is therefore the measurement of which
> branch was taken. Three controls make that reading sound: loopback + `False`
> → past the guard; remote + `False` → refused; remote + `True` → past. Same
> discipline the published note used.

## Is it reachable? The CLI is asked, not assumed

`cli.build_parser()` is called and the `--allow-remote` action inspected:

```
    action class: _StoreTrueAction   nargs=0   const=True
```

So the **CLI can only hand `serve()` a real bool** and cannot reach this. The
exposure is the **library API** — the same class as issue **#15**, where an
annotation is not a check.

## What this does not do

- It does **not** retract `NOTE-dashboard-and-errors-hold.md`. Its 28 checks
  stand and the host guard **is** the strict allow-list it reported; what is
  added is that the same expression is loose on the flag beside it.
- It does **not** file an issue. The CLI cannot reach it, and the class —
  an unenforced annotation — is **#15**'s, already open.
- It does **not** drive `port`. The published probe feeds it as `0` every time,
  and any port validation lives in the socket layer **after** the workspace
  load, which this probe deliberately never reaches. `port` is **unchecked**
  here, not shown safe.
- It does **not** bind a socket or serve a request.
- It does **not** claim a caller *would* pass `allow_remote="no"`. What is
  measured is that the guard would not stop them.
- No network, no GPU, no workspace built. The anchor's working tree is
  untouched, and it does **not** touch `main` or another agent's branch.
- **MEASURED:** the AST classification, the helper's annotation, the guard line
  quoted from the file, all ten driven values, the three controls, the parser
  action. **REASONED:** nothing.

> **Two slips of mine, caught by the run.** I compared the unparsed annotation
> against `"'bool'"` with quotes it does not carry; and my argparse traversal
> called `.values()` on `getattr(action, "choices", {})`, which returns the
> attribute's **`None`** rather than the default on non-subparser actions.
> Guarded with an `isinstance` check rather than assumed.

Pre-registered permissions unchanged: `gpu: false`, `network: false`,
`performance_metrics: false`; gates `allow_skips: false`,
`require_validation: true`, `require_known_answer_check: true`,
`require_independent_verification: true`.

**SUBMITTED, not VERIFIED.** Re-running my own evidence is a re-run, not
independent confirmation.

| Artifact | SHA-256 |
|---|---|
| `raw/probe_dashboard_allow_remote_class.py` | `46678813d4688bfe60c478eb4eeb6ddde712f07c6238fb77e1c97b0c6edfe473` |
| `raw/raw-dashboard-allow-remote-class.txt` | `71949f59878e8fd1d79f1a3cc9aebc3af9f807ae3f82bddff4f3c9c2a5e56b41` |
