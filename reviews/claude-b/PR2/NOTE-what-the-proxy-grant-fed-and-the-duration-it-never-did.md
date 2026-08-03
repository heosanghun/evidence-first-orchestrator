# What the proxy-grant checks fed — and the duration class they never did

Reproduce with `raw/probe_proxy_grant_duration_class.py`; raw output in
`raw/raw-proxy-grant-duration-class.txt`. **22 checks, 0 unexpected.** A
**narrowed scope** on a clean verdict — the verdict is **not retracted** and
**no issue is filed**.

**Scope, stated first:** 27 published checks classified, 1 un-fed class, 1
wrong hypothesis of mine recorded, 6 durations driven, 2 known answers, 2 open
issues quantified.

## The question item 47 asks of every clean note

`NOTE-proxy-grant-holds.md` drove every authorization gate and none moved the
verdict. **What input class did its 27 checks feed?**

`authorize_proxy_submission` takes one typed option — `duration_seconds: int |
None`. Classified from the published probe's **own source by AST**, it is fed
exactly twice: **`300`** and **`10`**. Both ints, both at or above the
10-second floor.

> **A parse of `ast.keyword` alone reported "fed: 1".** The option is supplied
> in **two syntactic forms** — once as a keyword argument, once as a dict entry
> in the probe's own default-kwargs mapping. Undercounting the population is
> how this was caught; both forms are parsed now.

So the un-fed class is a duration **outside `[10, 300]`**: zero, negative,
enormous, or not an int at all.

## A hypothesis of mine, and why it is wrong

`workspace.py:735-736` derives the duration with no validation beside it:

```python
duration = duration_seconds or int(
    self.config["defaults"]["lease_seconds"]
)
```

I expected the 10-second floor to be **missing** on this path — an asymmetry
with the lease path. **It is not.** The floor lives *inside* `lease_expiry`:

```python
if seconds < 10:
    raise ConfigurationError("Lease duration must be at least 10 seconds")
```

and `lease_expiry(duration, now)` is called at **line 771** (the grant) and
**line 889** (the lease) — the same expression, both paths. *Asking what a
guard actually covers before concluding it does not cover a path* is the rule;
here the answer is that it does. Recorded rather than quietly dropped.

## The un-fed class, driven

| `duration_seconds` | result |
|---|---|
| *absent* | **1800s** — the configured default |
| **`0`** | **1800s** — falsy, silently replaced |
| `5` | `ConfigurationError: Lease duration must be at least 10 seconds` |
| `-5` | `ConfigurationError` — same message |
| `True` | `ConfigurationError` — truthy, and `True < 10` |
| **`10.5`** (a float) | **accepted**, 10s — the annotation says `int` |
| **`"300"`** (a string) | **`TypeError: '<' not supported between instances of 'str' and 'int'`** — raw, not an `EFOError` |
| **`10**9`** | **accepted**, 1 000 000 000s — **no ceiling** |

**A caller asking for no window gets the longest one.** `0` and *absent* are
byte-identical in outcome, asserted identical.

## What that is, in terms of issues already open

- The **falsy zero** is a **second instance** of the shape item 56 measured at
  `workspace.py:876` for `--lease-seconds`. Same expression, different method.
  Not a new issue — the same defect on another surface.
- The **absent ceiling** is issue **#7**'s claim (*"the floor is enforced, the
  ceiling does not exist"*) on a **second surface**. **Quantifying** an open
  issue, not filing another.
- The **float** and the **`TypeError`** are **#15**'s class — an annotation is
  not a check. #15 already says `permissions`/`gates` are never type-checked;
  this is the same class on a third field, recorded here rather than appended
  there.

## What this does not do

- It does **not** retract `NOTE-proxy-grant-holds.md`. Its 27 checks stand;
  what is added is the input class they did not feed.
- It does **not** file an issue. Every finding maps onto #7, #15 or item 56.
- It does **not** drive `proxy_submit` itself, only the **grant**. The delivery
  path needs a real git repository and the published probe already exercises it
  end to end.
- It does **not** claim the floor is missing here — the section above measured
  the opposite of what I expected and says so.
- Workspaces are keyed by **index**: a grant is one-per-task, so a shared
  workspace would make the second drive fail on *state* rather than on input —
  the collision items 57 and 60 both hit.
- No network, no GPU. Nine `tempfile` workspaces, removed before the results
  print. The anchor's working tree is untouched, and it does **not** touch
  `main` or another agent's branch.
- **MEASURED:** the AST classification in both syntactic forms, both quoted
  source regions and both `lease_expiry` call sites, the default and zero
  spans, all six driven durations, the control. **REASONED:** nothing.

Pre-registered permissions unchanged: `gpu: false`, `network: false`,
`performance_metrics: false`; gates `allow_skips: false`,
`require_validation: true`, `require_known_answer_check: true`,
`require_independent_verification: true`.

**SUBMITTED, not VERIFIED.** Re-running my own evidence is a re-run, not
independent confirmation.

| Artifact | SHA-256 |
|---|---|
| `raw/probe_proxy_grant_duration_class.py` | `4a892d4f529dd9c441fe29fafcda5795b6c0552fdcf840d708495c8c2e5c1ded` |
| `raw/raw-proxy-grant-duration-class.txt` | `b8b9be18593267c28230a169d1226ced33b8cacb1280758197d995554ec7ec8f` |
