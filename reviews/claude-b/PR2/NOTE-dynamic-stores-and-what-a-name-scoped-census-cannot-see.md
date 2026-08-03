# The 9 excluded stores: two chains, not none — and the census refuted my own draft of this note

Reproduce with `raw/probe_dynamic_stores.py`; raw output in
`raw/raw-dynamic-stores.txt`. **14 checks, 0 unexpected.** No issue filed —
every chain here is guarded.

`NOTE-the-144-was-my-own-misleading-number.md` split the 144 dynamic-key
subscripts into 128 annotations, 9 stores and 7 runtime reads, excluded the
stores because `d[k] = v` *creates* its key, and named the leftover question:

> A store into a dict that a **later** read depends on is a different question,
> not asked here.

This asks it. The queue said to *"say plainly if the answer is none"*. **It is
not none.** Two chains exist.

## The census

**10 dynamic-key stores** across the package — the 9 in the thirteen modules
item 29 counted, plus `workspace.py:264`, which it counted separately.

Every stored-into dict is then adjudicated by how the module reads it back, and
the run fails on anything uncovered:

| Dict | How it is read back |
|---|---|
| `adapter.py::snapshot` | built and **returned**; never subscripted here |
| `ledger.py::tasks` | built and **returned** by `projected_tasks` |
| `provenance.py::files` | built and **returned**; see the correction below |
| `independence.py::declarations` | `.get()` ×2, iterated once |
| `independence.py::resolved` | **subscript-read at `:148` and `:177`** |
| `independence.py::submissions` | `.get()` once |
| `workspace.py::signed` | `.get()` once, `set()` once |

## A correction the probe forced on me, mid-write

I wrote this note expecting **two** dicts read back by dynamic subscript and
**five** stores feeding them, counting `provenance.py::files` because I knew it
becomes `expected_files` and is read at `:295`.

**The census said one and three, and the census was right.** Under the name
`files` that dict is stored into and returned — nothing more. The caller
rebinds the return value:

```
    expected_files = _evidence_file_map(evidence)
```

**A census keyed on a variable name measures a scope, not a value.** A rename
across a return defeats it completely.

That bounds this probe, and more usefully it bounds **every name-scoped census
in this review**: where a value crosses a function boundary, the chain has to be
*read*, and the result is then reasoned from reading rather than measured. It is
the eighth time a filter of mine was the limiting factor, and the first time the
limitation was in the *technique* rather than in a list I typed wrong.

## Chain 1 — `independence.py::resolved`, visible to the census

Stores at `:155`, `:162`, `:176` → reads at `:148`, `:177`. Item 29 classified
both reads as *own keyspace*; this traces why. Every key written is `agent_id`,
the same parameter the reads use; `:148` is guarded by `if agent_id in
resolved`, and `:177` reads the key assigned one line above. **Nothing new** —
the chain confirms the earlier classification rather than changing it.

## Chain 2 — `provenance.py`, and both sides are worker-supplied

Not visible to the census. Established by reading.

```
        files[Path(artifact["path"]).resolve()] = artifact["sha256"]
```

```
        files[Path(raw_output["path"]).resolve()] = raw_output["sha256"]
```

```
        if submitted_sha != expected_files[submitted]:
```

Item 29 established that **the key** comes from parsed input — `submitted` is
`(provenance.parent / record["submitted_path"]).resolve()`. What the store side
adds is that **the keyspace comes from parsed input too**: `_evidence_file_map`
keys the dict by the `artifact` and `raw_output` paths declared in the
**evidence manifest**, and `:295` indexes it with a path declared in the
**provenance document**.

Two worker-supplied documents on either side of one dict lookup.

**It is still safe.** `provenance.py:241` rejects any `submitted` not in the
map, in the same loop iteration, and item 29 proved the map is never mutated
after `:218`. But *"both sides are attacker-controlled and the only thing
between them is a membership test 54 lines up"* is a sharper statement of that
structure than item 29 could make on its own.

## A near miss: where `.get()` is load-bearing

`adapter.py:86-89`, in `_unauthorized_changes`:

```
    changed = {
        path
        for path in set(before) | set(after)
        if before.get(path) != after.get(path)
    }
```

The comprehension iterates the **union** of both keyspaces, so a subscript here
would raise `KeyError` on any file **added or deleted** during the run — which
is the normal case the function exists to detect. The `.get` is doing real work.

Worth naming because it is the shape that would have been a finding had it been
written the other way, and because a store census reporting only *"no reads"*
would have walked straight past it.

## Scope

Static analysis of all fourteen package modules at `main` `5694ab45`
(precondition verified: `HEAD` matches, `git status --porcelain` empty).
Nothing was executed.

Not covered:

- **Cross-module flow is read, not traced.** `ledger.projected_tasks()` is
  resolved through item 29's measurement that `workspace.py` has zero runtime
  dynamic-key reads — a cross-reference, not a new proof.
- Whether a crafted evidence manifest plus a crafted provenance document can
  reach `:295` with a key the map lacks. That is **behavioural**; it would need
  `validate_git_provenance` driven end to end against a real repository, and
  `network: false` forbids the fetch that would make it realistic.
- Constant-key stores, and stores through an attribute (`self.x[k] = v`) — the
  census keys on a bare `Name`, and there are none of the latter among these
  ten.
- **MEASURED:** the census, every access tally, chain 1, the near miss.
  **REASONED FROM READING:** chain 2. **REASONED:** that
  `.get()`/membership/iteration cannot raise `KeyError`, which is language
  semantics rather than a measurement.

Pre-registered permissions unchanged: `gpu: false`, `network: false`,
`performance_metrics: false`; gates `allow_skips: false`,
`require_validation: true`, `require_known_answer_check: true`,
`require_independent_verification: true`.

**SUBMITTED, not VERIFIED.**

| Artifact | SHA-256 |
|---|---|
| `raw/probe_dynamic_stores.py` | `83c3fd540e3bee8144f797d77d997677ca564fbe9f2a10f8ca8b15f84629da83` |
| `raw/raw-dynamic-stores.txt` | `318144b437179e9390a54f510f84a02e5f1f2adbb67f18e0f720fefe647b7011` |
