# 24 of the 30 were measured, 6 were read — the name-scoped bound, made specific

Reproduce with `raw/probe_census_bounds.py`; raw output in
`raw/raw-census-bounds.txt`. **7 checks, 0 unexpected.** No issue filed — this
bounds **my own earlier write-up** and finds nothing new in EFO.

`NOTE-dynamic-stores-and-what-a-name-scoped-census-cannot-see.md` found the
limit the hard way — `provenance.py`'s `files` becomes `expected_files` across a
return and the chain vanished — and named the consequence without measuring it:

> That bounds **every name-scoped census in this review.**

Queue item 35 is that measurement.

## The population

The largest such census is the constant-key adjudication in
`NOTE-implicit-exceptions-package-wide.md`: **30 `(module, base)` pairs**, each
carrying a sentence about where the value *comes from* — *"a task projection"*,
*"the dict `workspace.claim` RETURNS"*. Those are claims about a **value**. The
census only ever saw a **name**.

| How the base is bound | Count | Can the census see the origin? |
|---|---|---|
| assigned from a call | 12 | yes — the call is in the same scope |
| loop / comprehension target | 10 | yes — the iterable is in the same scope |
| built in place | 2 | yes — the literal is right there |
| **parameter** | **6** | **no** |

**24 measured, 6 read.**

## The six, and what the caller actually passes

A parameter is the whole problem: the census reads the name the *callee* chose,
and the caller may bind that value to anything.

| Site | Caller passes | |
|---|---|---|
| `render_task_prompt(task)` | `task` | same name |
| `evaluate_independence(worker)` | `worker_identity` | **different** |
| `evaluate_independence(verifier)` | `verifier_identity` | **different** |
| `validate_task(task)` | `record` | **different** |
| `archive_evidence_bundle(manifest)` | `evidence['manifest']` | **different** |
| `archive_evidence_bundle(report)` | `evidence['report']` | **different** |

**Five of six.** I guessed three before measuring, on the assumption that most
callers reuse the parameter name; the AST says five. Only
`render_task_prompt(task=task)` reuses it, and that is luck rather than a
property — nothing stops a future caller renaming it, and the census would not
notice.

Two of the five do not pass a variable at all. `archive_evidence_bundle` is
called with `evidence['manifest']` — a **subscript**. The census adjudicated
`manifest` as *"the caller passes `{path, sha256}`; workspace builds it"*, which
is correct and was reached by reading `workspace.py`, not by anything the census
could see.

**All six adjudications stand.** What changes is that the note presented 30
results uniformly when 24 were measured and 6 were read.

## Every census in the review, with its bound

| Write-up | Census | Bound |
|---|---|---|
| `NOTE-implicit-exceptions-package-wide.md` | constant-key subscript reads | **6 of 30 reasoned from reading** — banner added |
| `NOTE-the-144-was-my-own-misleading-number.md` | dynamic-key reads | classified by key **provenance**, not base name; the parsed-input case was traced by reading and says so. Unaffected |
| `NOTE-dynamic-stores-and-what-a-name-scoped-census-cannot-see.md` | dynamic-key stores | where the limit was found; already separates measured from read |
| `NOTE-issue19-is-the-only-one.md` | `workspace.py` subscript reads | one module, and `workspace.py` has **zero** runtime dynamic-key reads — a rename cannot hide a constant key |
| `NOTE-what-the-test-suite-cannot-catch.md` | `tests/` token map | keys on tokens in test sources, and every issue's token is checked to exist in its module |
| `NOTE-the-node-tests-exercise-only-the-covered-input.md` | `web_tests/` | **executed** — the guards are driven, not named. Immune |

Exactly one published result needed a stated bound. It has one now.

## Two filter bugs of mine, both caught by checks in this probe

- `binding_of` handled `ast.Assign` and not `ast.AnnAssign`, so
  `doctor.py::result` — declared `result: dict[str, Any] = {...}` — fell out of
  the census and the count came back **29 of 30**. The exhaustiveness check
  caught it. **Tenth** hand-rolled filter in this review to be the bug.
- The caller comparison first asked `name not in window` against the raw text of
  the call. `worker` is a substring of `worker_identity`, so it reported **zero**
  differences — it would have silently erased the finding. Now parsed from the
  AST, matching keyword arguments by name and positional ones by index against
  the callee signature. **Eleventh.**

## Scope

Static analysis at `main` `5694ab45` (precondition verified: `HEAD` matches,
`git status --porcelain` empty). Nothing executed.

Not established:

- This does **not** re-adjudicate the six. Their reasons were reached by reading
  the callers and remain correct.
- `binding_of` takes the **first** function in which a name resolves, which is
  why the table names the function alongside the module.
- Call sites are read at **one** caller each. A second caller could bind yet
  another name; that would strengthen the point, so it is not chased.
- **MEASURED:** the classification of all 30, and the caller-side expression at
  six call sites. **REASONED:** that a parameter's origin is invisible to a
  name-scoped census — which is what a parameter means.

Pre-registered permissions unchanged: `gpu: false`, `network: false`,
`performance_metrics: false`; gates `allow_skips: false`,
`require_validation: true`, `require_known_answer_check: true`,
`require_independent_verification: true`.

**SUBMITTED, not VERIFIED.**

| Artifact | SHA-256 |
|---|---|
| `raw/probe_census_bounds.py` | `b2555a7e8cb9cae36c10813ca075ab701b358ec8dc1b62744327269187eff37c` |
| `raw/raw-census-bounds.txt` | `684f7cbe61a7f0a8b1a81fffe74db1c0d7201d2fd9ed42117b044da0d46b186e` |
