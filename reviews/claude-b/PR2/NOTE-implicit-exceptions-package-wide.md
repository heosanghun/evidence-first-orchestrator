# The implicit-exception census, package-wide — no second #19, and the boundary of what static analysis can say

> **Correction, 2026-08-03.** The last row of the coverage table below said
> *"dynamic-key subscripts, `x[variable]` — **unmeasured** — 144 sites"*. The
> count of 144 reproduces exactly, but it is **misleading**: 128 of those sites
> are type annotations (`dict[str, Any]`) and 9 are stores (`d[k] = v`, which
> cannot raise `KeyError`). The runtime read population is **7**, and all seven
> are now adjudicated in `NOTE-the-144-was-my-own-misleading-number.md` —
> exactly one is keyed by parsed input. The row is amended below rather than
> deleted, so the error stays visible.

Reproduce with `raw/probe_implicit_exceptions_all_modules.py`; raw output in
`raw/raw-implicit-all-modules.txt`. **9 checks, 0 unexpected.** No issue filed.

`NOTE-issue19-is-the-only-one.md` proved #19 is the only instance of its class
**in `workspace.py`'s subscript reads**, and named two gaps in its own scope:
the other modules, and exception shapes other than a dict index. This closes
the first, closes half the second, and says plainly why the rest cannot be
closed statically.

## Coverage, checked rather than asserted

Thirteen modules — the whole package except `workspace.py`, which is covered by
the earlier note. The probe compares its own module list against the package
directory and fails on anything silently unlisted.

**My first draft of that list missed `errors.py`.** The check caught it. That
is the third time in this review that a hand-written filter was the bug —
after the `raise`-statement census that could not see a dict index (#19), and
the variable-name filter that missed `task_for_validation`. The list-versus-
directory check is now cheap and permanent.

## Integer indexes — the `IndexError` shape

**Three sites in the entire package outside `workspace.py`**, all in
`provenance.py`, all reading `fields = metadata.split()` from a `git ls-tree`
line:

```
provenance.py:283  fields[1]
provenance.py:284  fields[0]
provenance.py:314  fields[0]
```

They are safe by **short-circuit ordering**, which the probe checks from the
AST rather than assuming. The operands of the `or` chain, in order:

```
['not separator', 'tree_path != source_path', 'len(fields) != 3',
 "fields[1] != 'blob'", "fields[0] not in {'100644', '100755'}"]
```

`len(fields) != 3` precedes both indexes. `:314` reads `fields[0]` again but is
reachable only after that chain did *not* raise, so the guard has already held.

**Measured:** the ordering. **Not measured:** a malformed `git ls-tree` line
driven end to end, which would need a crafted repository.

## String keys — 78 reads, 30 base objects, all adjudicated

> **Bound added 2026-08-03.** This section adjudicates each base by the name it
> carries **inside one function**, and each reason is a claim about where the
> VALUE comes from. A name-scoped census cannot see that. Measured in
> `NOTE-which-of-my-censuses-measured-and-which-read.md`: **24 of the 30 bases
> are bound in the same scope** — 12 from a call, 10 loop targets, 2 built in
> place — and their adjudication is measured. The other **6 are PARAMETERS**,
> where five of six callers bind a different name (`worker_identity`,
> `verifier_identity`, `record`, `evidence['manifest']`, `evidence['report']`).
> Those six reasons were reached by READING the callers and remain correct;
> this section presented all 30 uniformly and should not have.

Every `(module, base)` pair carries the reason a missing key cannot reach it,
and the run fails on anything uncovered. `uncovered: []`, `stale: []`.

The reasons fall into four kinds: task projections and agent records returned
by the workspace API; dicts a validator **returns** rather than accepts
(`evidence`, `provenance`, `independence`); dicts the module itself just built
(`claim`, `submitted`, `result`, `check`); and schema-validated manifest
entries.

**The structural point:** not one of these bases is a projection that any
*repair* path rebuilds. That is exactly what made #19 reachable —
`repair_projections` writes a task file with a key missing, and `workspace.py`
reads that key. No module outside `workspace.py` consumes a rebuilt projection,
so the #19 shape has no second home.

## What this does not cover

Stated rather than implied, because a census reporting only its successes reads
as complete when it is not:

| Shape | Status |
|---|---|
| constant-key subscript reads, whole package | **measured** — all adjudicated |
| `IndexError` from integer indexes | **measured** — 3 sites, all guarded |
| `AttributeError`, `TypeError`, `ZeroDivisionError`, `StopIteration` | **unmeasured** |
| dynamic-key subscripts, `x[variable]` | ~~**unmeasured** — 144 sites~~ → **measured**: 7 runtime reads, all adjudicated (see the correction banner) |

`AttributeError` and `TypeError` are **not statically enumerable here**. `x.foo`
is unsafe only if `x` can be `None` or another type, and deciding that needs
type inference this probe does not have. For scale: **963 attribute accesses**
across these modules. **Scoped 2026-08-03**: of those 963, **24**
are read on a name bound from a dict field — the subset a parsed document can
control — and all 24 are adjudicated in
`NOTE-963-attribute-accesses-scoped-to-24-and-a-near-miss.md`. The remaining 939
stay unmeasured for the reason given here. Enumerating them without adjudication would be the
appearance of coverage, not coverage — so they are named as a gap instead.

So the honest claim after this round is: *every constant-key subscript read in
the package is adjudicated, the three integer indexes are guarded by
short-circuit ordering, and no module outside `workspace.py` reads from a
repair-rebuilt projection.* It is **not**: *no implicit exception can escape
the CLI.*

## Scope

Static analysis of thirteen modules at `main` `5694ab45` (precondition
verified: `HEAD` matches, `git status --porcelain` empty), plus one AST
ordering check. **Nothing was executed against a live workspace in this probe**
— the behavioural half of this question was measured in
`NOTE-issue19-is-the-only-one.md` and `ADDENDUM-architecture-claims-and-repair-drops-a-field.md`.

Pre-registered permissions unchanged: `gpu: false`, `network: false`,
`performance_metrics: false`; gates `allow_skips: false`,
`require_validation: true`, `require_known_answer_check: true`,
`require_independent_verification: true`.

**SUBMITTED, not VERIFIED.**

| Artifact | SHA-256 |
|---|---|
| `raw/probe_implicit_exceptions_all_modules.py` | `0d4e4b2a19562e4275c491036298a3883c5732facbe9ba151255dc2f467bcb13` |
| `raw/raw-implicit-all-modules.txt` | `7bc8089fb48e84ff32918a80ce1fce493fa772212bd043f34e3f3898dd68a654` |
