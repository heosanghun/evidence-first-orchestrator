# 487 is too many to adjudicate — one more hop leaves 2, and both are guarded

Reproduce with `raw/probe_parameter_subset.py`; raw output in
`raw/raw-parameter-subset.txt`. **13 checks, 0 unexpected.** A **negative
result** — zero findings, no issue filed.

## The number first, as the item required

`NOTE-963-attribute-accesses-scoped-to-24-and-a-near-miss.md` narrowed 963
attribute accesses to the **24** whose base is bound from a dict field, and
named its own exclusion: a base arriving via a **parameter** or a **return** is
invisible to that filter. Queue item 41 asked whether the parameter subset is
adjudicable, and said to **say the number first and stop if it is too large**.

**The number is 487.**

```
    1132  attribute accesses on a bare name inside a function
     487  whose base is a PARAMETER of that function     <- item 41's population
       2  whose base is a parameter that RECEIVES d[...] or d.get(...)
       0  findings
```

487 is not adjudicable by hand, and the item's literal question is answered
**no**. Had the next step found nothing, saying the number and stopping is
where this would have ended.

## One more hop

The step that made `963 → 24` work was not type inference — it was one concrete
propagation. The same step here: which of those 487 parameters actually
**receives** a dict-field value at a call site?

**Two**, and they are the same base in the same function:

```
    provenance.py:76  branch.strip  in validate_git_source_claim()
    provenance.py:78  branch.strip  in validate_git_source_claim()
```

tainted by `provenance.py:165`, which passes `payload.get("branch")`.

## Adjudicated: both guarded

```python
    if not isinstance(branch, str) or not branch.strip():
```

`branch` genuinely can be `None` or a non-string — the call site proves it. And
the `or` **short-circuits**: a non-string is refused with `ConfigurationError`
before `.strip()` is ever reached. Line 78 runs only after the guard passed.

Zero findings. Item 38's near miss has no sibling in this population, and a
negative result is worth publishing.

## A filter bug in the middle — the fifteenth

The first run returned **8** sites, six of them `self.agents_dir`,
`self.ledger`, `self.tasks_dir` and friends. Those are not parameters receiving
documents; they are instance attributes.

The cause: for a **bound** call `obj.method(x)`, `self` is supplied by the
*receiver*, so the first written argument maps to `positional[1]`. Indexing a
parameter list that still contained `self` marked `self` itself as tainted.

Caught by **reading the output** rather than trusting the count — 8 → 2 after
the correction. The check that lists every site is now compared against a
counter incremented *by the printing loop*, so a truncated listing fails the
run; writing `len(sites)` on both sides would be the #8 defect, and one of those
slipped into `probe_headers_rewritten.py` two rounds ago.

## What this does not cover, with counts

- **One hop only.** A parameter receiving a bare *name* that is itself
  dict-bound is hop two and is not followed. `workspace.py:730` calls the very
  same `validate_git_source_claim(remote_url, branch)` with bare names, so this
  analysis does not reach it.
- **In-module call sites only.** **91** dict-field arguments go to a callee
  defined in another module and are not propagated.
- **`self` is excluded by design.** **244** accesses are attributes of the
  instance, whose values come from `__init__` rather than from a document.
- **It does not clear the other 485.** They are excluded because no in-module
  call site passes them a dict field — a statement about *this analysis*, not
  about their safety.
- **MEASURED:** every count, both sites, the guard line, the tainting call site.
  **REASONED:** nothing — the guard is read from the source, not inferred.

Pre-registered permissions unchanged: `gpu: false`, `network: false`,
`performance_metrics: false`; gates `allow_skips: false`,
`require_validation: true`, `require_known_answer_check: true`,
`require_independent_verification: true`.

**SUBMITTED, not VERIFIED.**

| Artifact | SHA-256 |
|---|---|
| `raw/probe_parameter_subset.py` | `240c02d1fb5e5b8b2a535b791691e80fe74f8d7a3addaaea4c9b87efa2f1498f` |
| `raw/raw-parameter-subset.txt` | `b7580742b1c7fbbea0c1e0a2a4ddc13250dae4c91c2bb1824dcb1733f58cbe92` |
