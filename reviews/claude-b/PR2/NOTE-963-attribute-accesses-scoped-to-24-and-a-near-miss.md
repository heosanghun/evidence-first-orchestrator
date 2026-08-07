# 963 attribute accesses scoped to 24 — and a near miss that is **not** issue #21

Reproduce with `raw/probe_attribute_subset.py`; raw output in
`raw/raw-attribute-subset.txt`. **8 checks, 0 unexpected.** **No issue filed**,
and the reason is the point of this note.

Queue item 38. `NOTE-implicit-exceptions-package-wide.md` named **963 attribute
accesses** as not statically enumerable without type inference. That stands.
The item asked whether the subset a **parsed document** can reach is small
enough to adjudicate — and to *say the number first and stop if it is still too
many.*

```
    963 total  →  24 on a name bound from a dict field
```

24 is adjudicable, so this did not stop.

## Where the 24 are

| Module | Count |
|---|---|
| `independence.py` | 21 |
| `adapter.py`, `evidence.py` | 3 between them |

They cluster almost entirely in the retrospective audit, which is the one place
that walks **historical ledger events** rather than a validated projection.

## The shape worth naming

```
    d.get("k", {}).get("j")
```

The `{}` default applies only when the key is **absent**. If the key is
**present and holds `None` or a string**, the second `.get` raises
`AttributeError` — which `cli.main` does not catch, so it escapes as a
traceback. That is **#19's shape exactly**.

**14 such sites package-wide**, and they are not confined to one module:

```
    independence.py:197  agents.get(agent_id, {}).get('identity')
    independence.py:211  event.get('payload', {}).get('task')
    independence.py:217  task.get('result', {}).get('authorship', {})
    ledger.py:161        event.get('payload', {}).get('task')
    provenance.py:118    evidence.get('manifest', {}).get('artifacts', [])
    workspace.py:1296    task.get('result', {}).get('transport')
    workspace.py:1311    task.get('result', {}).get('authorship', {})
    workspace.py:1346    task.get('result', {}).get('manifest', {}).get('sha256')
```

`workspace.py:1296-1346` is the **proxy verification path**.

## Driven, not argued

```
    synthetic event, result = "not-a-dict"   ->  AttributeError: 'str' object has no attribute 'get'
    positive control, result = {}            ->  no exception
```

So the function *is* fragile to the shape, and the positive control shows the
harness is not simply broken.

## Why this is not a finding

The question that decides it is whether a **real ledger** can contain such an
event. What I could establish:

- `model.validate_task` constrains `id`, `owner`, `state`, `title`, `revision`,
  `prerequisites`, `permissions` and `gates`. It does **not** constrain `result`
  at all.
- **But** the audit reaches `:217` only for `task.submitted` /
  `task.proxy_submitted` events, and `workspace.submit` writes
  `result=evidence` — a dict it builds itself.
- `requeue` **does** set `result=None` (`workspace.py:1411`), but a requeued
  event carries action `task.requeued`, which the audit skips at both of its
  action filters before reaching any `.get` chain.

**I could not construct a public-API sequence that puts a non-dict `result`
into a `task.submitted` payload.** So the honest verdict is: *reachable from a
crafted or tampered ledger; not shown reachable through the API.*

**No issue is filed on that basis.** The hypothesis going in was that this
would be **#21**. It is not, on the evidence I have, and writing that down is
the deliverable — a near miss recorded is worth more than a finding asserted.

## Scope

Static analysis at `main` `5694ab45` (precondition verified: `HEAD` matches,
`git status --porcelain` empty), plus two driven calls to
`audit_verification_events` against literals built in the probe. No network, no
GPU, no performance measurement.

Not established:

- This does **not** clear the other **939** attribute accesses. They are
  excluded because their base is not bound from a dict field — a **syntactic**
  filter. A value reaching a name by another route, a parameter or a return, is
  invisible to it: the bound recorded in
  `NOTE-which-of-my-censuses-measured-and-which-read.md`.
- It does **not** prove the ledger cannot hold a malformed payload. It proves I
  could not produce one through the API in this container. An attacker who can
  write *and re-sign* the ledger is a different threat model, partly covered by
  #9 and #12.
- **MEASURED:** 963, 24, the module split, the 14 chained sites, both driven
  outcomes. **REASONED:** that the action filters block the requeue route —
  read from the source, not driven end to end.

Pre-registered permissions unchanged: `gpu: false`, `network: false`,
`performance_metrics: false`; gates `allow_skips: false`,
`require_validation: true`, `require_known_answer_check: true`,
`require_independent_verification: true`.

**SUBMITTED, not VERIFIED.**

| Artifact | SHA-256 |
|---|---|
| `raw/probe_attribute_subset.py` | `ffd7bbf3872439bfd89eb6df9c2a1655661f213cce090c8f1c9a72ae464c26b0` |
| `raw/raw-attribute-subset.txt` | `047da498431c00a0db14bfabe0b13970c8b664709d395c0975f27ccbc6af5601` |
