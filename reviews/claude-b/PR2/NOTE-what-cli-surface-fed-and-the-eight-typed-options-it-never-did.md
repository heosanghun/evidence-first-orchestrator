# What "`cli.py` is clean" fed — and the eight typed options it never did

Reproduce with `raw/probe_cli_typed_options.py`; raw output in
`raw/raw-cli-typed-options.txt`. **17 checks, 0 unexpected.** A **map with a
near miss recorded** — no issue filed, and `NOTE-cli-surface-holds.md`'s verdict
is **not retracted**, only narrowed.

**Scope, stated first:** 1 note, 25 checks, 8 typed options, 13 driven inputs.

## The twenty-five, classified one at a time

| class | count |
|---|---|
| a well-formed CLI invocation — the controls | **10** |
| a **tampered** task projection (the audit/repair section) | 5 |
| an **authorization violation** with well-formed string arguments | 4 |
| a **static census** of the parser, driving nothing | 2 |
| a value malformed but still a **string** (`--id UPPER`) | 2 |
| a path that is not a workspace | 2 |
| | **25** |

Asserted **exhaustive** — a label I failed to classify fails the run.

**Every argument in all twenty-five is a string, because argparse hands
strings.** So item 47's question — *"did it feed a non-string?"* — cannot be
asked of this surface in the same words. The equivalent is: **which arguments
are typed?**

## Eight are, and none of the twenty-five drives one

Derived from the parser, not typed into the probe:

```
    task claim         --lease-seconds          int
    task proxy-authorize --duration-seconds     int
    worker once        --timeout-seconds        int
    worker loop        --poll-seconds           float
    worker loop        --timeout-seconds        int
    worker loop        --max-tasks              int
    worker loop        --idle-timeout-seconds   float
    serve              --port                   int
```

## Driven — and the un-fed class answers three different ways

| input | outcome |
|---|---|
| `--lease-seconds 600` | **accepted**, `duration_seconds=600` — control |
| `--lease-seconds abc` | **argparse `SystemExit(2)`** — never reaches EFO |
| `--lease-seconds -5` | **`ConfigurationError`** — *"Lease duration must be at least 10 seconds"* |
| `--lease-seconds 0` | **accepted**, and `duration_seconds` becomes **1800** |
| `--lease-seconds 999999999` | **accepted** — that is issue **#7**'s missing ceiling |

All **8** typed options reject a non-numeric value at parse time, so argparse is
a real first line for this class.

## The zero is the new fact

```python
    workspace.py:876   duration = lease_seconds or int(
                           self.config["defaults"]["lease_seconds"])
```

An explicit `0` is **falsy** and therefore indistinguishable from *"not
supplied"*. The floor at `model.py:139` never sees it, and the operator silently
gets the workspace default — **1800** — instead of what they asked for.

**Recorded, not filed.** The input is the operator's own argument rather than a
tampered document, and 1800 is the workspace's own default rather than a
weakening — the standard items 38, 45, 47, 53 and 54 all applied.

It is also **not issue #7**. #7 is the missing **ceiling**; this is the **floor
being skipped from below**, a different line and a different mechanism.

## A driver bug of mine, caught by a control

The first version claimed five different lease values against **one** task. The
task is `claimed` after the first drive, so every later value returned *"Task T1
is claimed, not pending"* — the state gate fired before the lease value was ever
examined, and all three answers looked identical. **Three drives agreeing
exactly is the tell.** Fixed by creating a fresh pending task per value; the
parse-level drives were added precisely because no workspace state can mask a
coercion.

## What this does not do

- It does **not** retract *"`cli.py` is clean"*. All 25 checks still pass.
- It does **not** file an issue, and nothing was accepted that weakens a gate.
- It drives **one** of the eight typed options to the domain. The other seven
  are driven only at **parse** level, because five of them start a worker loop
  or a server. Stated, not implied.
- It does **not** adjudicate the other five notes item 53 named. **Five
  remain.**
- No network. The workspace is a `tempfile` directory, removed before the
  results print. It does **not** touch `main`, the anchor's working tree, or
  another agent's branch.
- **MEASURED:** the 25-label classification and its exhaustiveness, the eight
  typed options derived from the parser, all five domain drives, all eight parse
  drives, the resulting durations, both source lines. **REASONED:** nothing.

Pre-registered permissions unchanged: `gpu: false`, `network: false`,
`performance_metrics: false`; gates `allow_skips: false`,
`require_validation: true`, `require_known_answer_check: true`,
`require_independent_verification: true`.

**SUBMITTED, not VERIFIED.** Re-running my own evidence is a re-run, not
independent confirmation.

| Artifact | SHA-256 |
|---|---|
| `raw/probe_cli_typed_options.py` | `48fdd046afe1af4ca995dde6f6ef12af32b3684b2bfe3c9588d85e1e645a147d` |
| `raw/raw-cli-typed-options.txt` | `7b5b9bbd3e758d5a9c330ee12952073dbab53979e47d26c1bb432bb364928ede` |
