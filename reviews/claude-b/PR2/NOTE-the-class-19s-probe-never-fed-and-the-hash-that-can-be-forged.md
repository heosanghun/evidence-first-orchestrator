# The class #19's probe never fed — and a signed record bound to an event that does not exist

Reproduce with `raw/probe_implicit_exceptions_input_class.py`; raw output in
`raw/raw-implicit-exceptions-input-class.txt`. **32 checks, 0 unexpected.**
A **finding**, reported on **#19** rather than filed as a new issue — same key,
same missing guard.

**Scope, stated first:** 1 probe re-classified, 10 of its checks, 5 feeders, 5
projection classes, 3 un-fed, 2 of them covered, 1 driven end to end, 1 known
answer.

## The last of item 53's seven

`NOTE-issue19-is-the-only-one.md` concluded that **#19 is the sole instance of
its class**, because `repair_projections` drops exactly one key. That
measurement stands. The word that was wrong is **class**: it named a class of
**repair**, not a class of **input**.

Its ten checks have five feeders, and only one of them can be affected by
editing a file:

| feeder | checks |
|---|---|
| source text of `cli.py` | 1 |
| a hardcoded set of exception types | 1 |
| the `workspace.py` AST | 2 |
| **a live task projection** | **5** |
| a live workspace config | 1 |

The feeder split is a hand classification; what is **machine-checked** is that
the subject probe **never writes a projection file** (`writes: []`) and only
`unlink()`s one to reach the repair path. So it cannot have fed any *edited*
class, whatever my hand classification says.

| class of projection | fed? |
|---|---|
| normal — what the workspace wrote | fed |
| repair-dropped — a key absent after `repair_projections` | fed |
| **hand-absent** — a key removed by editing the file | **un-fed** |
| **wrong-valued** — a key present, holding anything at all | **un-fed** |
| **non-object** — valid JSON that is not an object | **un-fed** |

## Two of the three un-fed classes are covered

Measured, not assumed — both driven through a real `proxy_submit`:

| class | result |
|---|---|
| projection is a JSON list | `ConfigurationError: Expected a JSON object in …` — `read_json` refuses it before `validate_task` can index it |
| any **other** key altered | `IntegrityError: Task C1 projection differs from the signed ledger` |

Two of three predictions came back **negative**, and they are reported as
negatives. That is the useful half of an input-class round.

## The third is not covered

Driven end to end against a live workspace with a local git delivery repo:

| projection | outcome |
|---|---|
| control | **ACCEPTED**, `state: submitted` |
| `last_event_hash` **deleted** | `KeyError: 'last_event_hash'` — **#19, reproduced** |
| `last_event_hash` = `"f"*64` | **ACCEPTED** |
| `last_event_hash` = `12345` | **ACCEPTED** |
| `last_event_hash` = `null` | **ACCEPTED** |

The known answer is #19's own traceback, and the driver reproduces it — which
is what makes the four rows beside it worth reading.

> **Absent crashes. Present-and-arbitrary is accepted.**

## Why: one key, four exclusions, one read

Derived from the AST, not cited. `key != "last_event_hash"` appears at
`workspace.py:470` (`get_task`), `:495` (`list_tasks`), `:517` (the projection
writer's own comparison) and `:1511` (the audit path). **No comparison in the
package covers it** — which is the blindness #19's title already names.

It is **read** into a record at exactly one site, `workspace.py:1182`:

```python
"grant_event_hash": task_for_validation["last_event_hash"],
```

## What the forged value becomes

On the control, that field lands in **one** signed ledger event —
`task.proxy_submitted`, at `/payload/task/result/transport/grant_event_hash` —
and it **equals the hash of the `task.proxy_authorized` event**. Binding the
submission to its authorization is precisely its purpose.

With the projection forged, the **same signed event carries `"f"*64`**, a hash
that **matches no event in the ledger** (`matches: 0`). And:

```
doctor healthy: True
ledger  valid: True, signed: True
projection mismatches: []
```

So the second consequence of the blindness in #19 is not a crash. It is a
**signed record bound to an event that does not exist**, with every integrity
check in the product reporting clean.

## What this does not establish

- It does **not** retract `NOTE-issue19-is-the-only-one.md`. Its measurement
  holds for the classes it fed: repair drops exactly one key, and no second key
  sits in #19's position.
- It does **not** file a new issue. Same key, same missing guard, and #19's
  title already says *`audit_projections` is blind to it*. A second consequence
  of one blindness belongs on that issue.
- It does **not** claim a human reading the bundle could not spot it. It claims
  `doctor`, `ledger verify` and the projection comparison all report clean,
  which is measured.
- It does **not** measure the direct (non-proxy) submit path, which reads no
  `last_event_hash` — the AST census found **one** read site.
- Writing to `tasks/C1.json` is the tamper. That the file is editable with
  `doctor` clean was measured in item 66; what is new is that **one key in it is
  exempt from every comparison**, and that the exempt key is the one that ends
  up in a signed record.
- No network beyond a local git repo with an unreachable remote URL, no GPU.
  Six workspaces under `tempfile`, removed before the results print. The
  anchor's working tree is untouched, and it does **not** touch `main` or
  another agent's branch.
- **MEASURED:** the ten checks' feeders, the five classes, all five driven end
  to end, the exclusion and read sites, the control's binding to the
  authorization event, the forged value in the signed event, `doctor`'s
  verdict. **REASONED:** nothing.

Pre-registered permissions unchanged: `gpu: false`, `network: false`,
`performance_metrics: false`; gates `allow_skips: false`,
`require_validation: true`, `require_known_answer_check: true`,
`require_independent_verification: true`.

**SUBMITTED, not VERIFIED.** Re-running my own evidence is a re-run, not
independent confirmation.

| Artifact | SHA-256 |
|---|---|
| `raw/probe_implicit_exceptions_input_class.py` | `fd3ac1c1617849139c506f096482a648b573e7800ff69d9a9b122f3160cc1c07` |
| `raw/raw-implicit-exceptions-input-class.txt` | `251cedbd07c821f2e4f678ed1a238010dee430fc82aff91347a4adb626d83170` |
