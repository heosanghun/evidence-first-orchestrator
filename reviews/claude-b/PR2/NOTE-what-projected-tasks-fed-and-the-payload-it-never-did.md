# What `projected_tasks` is clean *on* — and the payload shape it never fed

Reproduce with `raw/probe_projected_tasks_input_class.py`; raw output in
`raw/raw-projected-tasks-input-class.txt`. **25 checks, 0 unexpected.** A
**narrowed scope** on a clean verdict — the verdict is **not retracted** and
**no issue is filed**.

**Scope, stated first:** 17 published checks classified, 6 payload arguments,
1 guard driven both ways, 5 non-dict payloads, 4 falsy task ids, 2 signed
chains, 3 public entry points.

## The question item 47 asks of every clean note

`NOTE-projected-tasks-holds.md` fed the fold six malformed shapes and none of
them moved the verdict. **What input class did those checks actually feed?**

Classified from the published probe's **own source by AST**, not read off the
note:

```
    payload argument kinds : {'dict': 6}
    payload['task'] kinds  : {'dict': 2, 'str': 1, '<absent>': 1}
```

Every one of the six is a **dict**. All the variation is one level *down* —
inside the payload. So the un-fed class is **`payload` present but not a
dict**, and `ledger.py:161` is:

```python
snapshot = event.get("payload", {}).get("task")
```

The `{}` default covers payload being **absent**. It does nothing when payload
is present and of the wrong type.

## The guard that *does* exist — and this is the contrast

`ledger.py:64-65`, quoted from the file:

```python
if not isinstance(event, dict):
    raise IntegrityError(f"Ledger line {line_number} is not an object")
```

Driven **both ways**:

| line | result |
|---|---|
| `[1, 2, 3]` | **`IntegrityError`** |
| `"just a string"` | **`IntegrityError`** |
| `42` | **`IntegrityError`** |
| `null` | **`IntegrityError`** |
| `{"a": 1}` | **accepted** — the other direction |

This is precisely the guard `monitor/collector.py` **lacked** (item 59), where
valid JSON of the wrong shape walked past a handler catching only
`JSONDecodeError`. Here the package **does** check shape at the line level —
and then stops one field short.

## Driving the un-fed class

| `payload` is | result |
|---|---|
| a string | **`AttributeError: 'str' object has no attribute 'get'`** |
| a list | **`AttributeError`** |
| an integer | **`AttributeError`** |
| `null` | **`AttributeError`** |
| a boolean | **`AttributeError`** |
| *absent* | `{}` — the case the default was written for |

**Five for five**, and the exception is a **raw `AttributeError`**, not an
`EFOError`.

## A falsy `task_id` is not an absent one

| `task_id` | folded? |
|---|---|
| `null` | dropped |
| `""` | dropped |
| `0` | dropped |
| `false` | dropped |

The published probe fed only `null`. The other three reach the same outcome by
the same truthiness test, so this **narrows** the note's row rather than
contradicting it.

## Is the absence *reachable*?

Two different measurements. Signed with the workspace's **own** key:

```
    verify()            {'valid': True, 'events': 5, 'signed': True}
    projected_tasks()   AttributeError: 'str' object has no attribute 'get'
    list_tasks()        AttributeError
    get_task("T1")      ConfigurationError: Unknown task: T1
```

`get_task` **did not** raise it — and asking why is the useful part. No
`tasks/T1.json` existed, so an earlier existence check fired before the fold
was consulted. **That check covers a task that does not exist, not a payload of
the wrong type.** Driven with a task that *does* exist:

```
    tasks/T1.json exists          True          (control)
    get_task("T1") before tamper  id: 'T1'      (control)
    get_task("T1") after tamper   AttributeError
```

So **all three public paths crash** once the task exists; the earlier check
merely masked one of them.

## What this is — and what it is not

- The absence is **real** and reachable **only with the signing key** — the
  same precondition items 45/53/54/57 record, and the limit `SECURITY.md:38`
  declares. It is a **crash, not a bypass**: nothing is accepted that should be
  refused.
- **Not filed.** A holder of the ledger key can already rewrite the chain
  (#9). Quantifying an open precondition is not opening a new issue.
- **Not a new instance of #19.** #19 is a `KeyError` escaping the CLI on a
  repaired projection; this is an `AttributeError` inside the fold on a signed
  non-dict payload. Related shape, different path — recorded here rather than
  appended there.

## What this does not do

- It does **not** retract `NOTE-projected-tasks-holds.md`. Its 17 checks stand;
  what is added is the input class they did not feed.
- It does **not** measure `Ledger.append` under concurrency, nor
  `_verify_events` beyond what #9 already covers.
- No network, no GPU. Three tempfile workspaces, removed before the results
  print. The anchor's working tree is untouched, and it does **not** touch
  `main` or another agent's branch.
- **MEASURED:** the AST classification, both directions of the `read()` guard,
  five non-dict payloads, the absent case, four falsy task ids, two signed
  chains, three public entry points, both sub-case controls. **REASONED:**
  nothing.

> **Two expectations of mine failed and were corrected to the measurement.** I
> predicted **two** inner-task kinds (there are **three** — `dict`, `str`,
> `<absent>`), and I predicted `get_task` would raise `AttributeError` like the
> other two. It raises `ConfigurationError` instead, because of a check that
> fires earlier — which is why the second workspace exists. A third slip was
> caught by the run: the AST walk called `literal_eval` on every matching dict,
> and the signed-chain event at `probe_projected_tasks.py:201` contains
> `last["sequence"] + 1`, an `ast.Subscript` that cannot be evaluated. Fixed by
> evaluating the **payload value alone** and **counting** what cannot be
> evaluated instead of raising.

Pre-registered permissions unchanged: `gpu: false`, `network: false`,
`performance_metrics: false`; gates `allow_skips: false`,
`require_validation: true`, `require_known_answer_check: true`,
`require_independent_verification: true`.

**SUBMITTED, not VERIFIED.** Re-running my own evidence is a re-run, not
independent confirmation.

| Artifact | SHA-256 |
|---|---|
| `raw/probe_projected_tasks_input_class.py` | `a77db591f26bb9f9c004a187ee80d00ea7766003f03d53f774aabc86e87a3cc8` |
| `raw/raw-projected-tasks-input-class.txt` | `79c5fcbdc9176a196aa6e04f5bc001736ea595913ed9abaab7e9c5dcf14d6e2e` |
