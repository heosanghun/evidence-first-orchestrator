# `README.md` read end to end — every claim adjudicated, and issue #17 was understated

Reproduce with `raw/probe_readme_claims.py`; raw output in
`raw/raw-readme-claims.txt`. **15 checks, 0 unexpected.** No new issue filed;
one comment owed on #17.

`README.md` is the last long document, and the one an operator actually
follows, so a wrong sentence here costs the most. Every falsifiable sentence in
its 452 lines is now adjudicated, and the probe **fails on anything it has not
covered**.

| Disposition | Count |
|---|---|
| probed here for the first time | 4 |
| already covered by an existing ADDENDUM or NOTE | 24 |
| the thesis, or stated limitations | 2 |

## The anchors I inherited were mostly wrong

The queue listed four "known covered" anchors. Three did not survive contact:

| Inherited | Actual |
|---|---|
| `:336-337` bind guard | **`:335-336`** — off by one |
| `:590` `evidence check` | **does not exist** — README.md has 452 lines; it is `cli.py:590` |
| `:430` "the `--actor` trust model" | **not that** — `:430-432` is a stated limitation about identity declarations being policy inputs, not attestations |
| `:391-394` retention | correct |

Corrected in `NOTE-citation-audit-of-this-review.md`. Recorded again here
because an anchor list is the kind of thing that gets copied forward
unexamined, and three of these had been.

## Issue #17 understated its own scope

I filed #17 citing `docs/MIGRATION.md:43-52`. **`README.md:404-406` makes the
same promise:**

> The audit checks required files, event-line formatting, read access, and
> secret-like plaintext values. A write test is opt-in and **targets only the
> selected agent's report directory**.

So the containment guarantee is stated in the document an operator is most
likely to read, not only in the migration guide. The measured behaviour is
unchanged — `--agent ..`, `../..`, `.` and an absolute path all write outside
`reports/<agent>/`, and `codex/../claude` writes into a *different* agent's
directory. What changes is the blast radius of the documentation error: two
documents promise it, not one.

A comment on #17 naming the second source is owed. A new issue is not — same
defect, same fix surface.

## The three other claims probed here

**`:21` — "EFO has no runtime dependencies beyond Python 3.10 or newer."**
Holds. `pyproject.toml` declares `dependencies: []` and `requires-python:
>=3.10`, and an AST walk over every module in `src/` finds **no import outside
the standard library**. Checked both ways deliberately: a declared-empty list
and a stray import are two different lies, and only the second breaks an
install. Not covered by the sentence, and so not checked: the optional
dashboard under `monitor/` and `functions/`.

**`:433` — "It never stores SSH passwords or API tokens in task files."**
A task created with credentials in its title and description stores them
verbatim. That is **not** a contradiction, and it is recorded as a **map, not a
finding**: the sentence is about EFO's own behaviour — there is no credential
field in the task schema and nothing is read from the environment into a task —
not a filter on operator-supplied free text, and the README never says it is.
The neighbouring safeguard is real and fires: `efo doctor` flagged both planted
values. Its `\b` blind spot is issue #12.

**`:365-366` — the bundled sample is visibly identified as `DEMO`.**
Partial. The marker exists in the shipped assets. **Not measured:** that it is
*visible to a viewer*, or that it appears whenever the API is unconfigured —
that needs the page rendered against an unconfigured backend, and
`network: false` forbids fetching one. Counted as partial rather than as
covered.

## What this closes

With `README.md` done, every long document in the repository has now been read
straight through and adjudicated sentence by sentence: `ARCHITECTURE.md`
(5 probed, 28 covered, 3 limitations), `PROXY_SUBMISSION.md` and
`MIGRATION.md` (via the byte-exactness and legacy passes), and now `README.md`.
The claim census is no longer the gap.

## Scope

Every falsifiable sentence in `README.md` at `5694ab45` (precondition verified:
`HEAD` matches, `git status --porcelain` empty), the dependency claim by AST,
the task-file credential claim by driving a real workspace, and the `DEMO`
marker by presence in the shipped assets.

Not examined: the rendered dashboard page, and `docs/OPERATIONS_DASHBOARD.md`
and `CONTRIBUTING.md`, which `README.md` links but which no pass has read end
to end.

Pre-registered permissions unchanged: `gpu: false`, `network: false`,
`performance_metrics: false`; gates `allow_skips: false`,
`require_validation: true`, `require_known_answer_check: true`,
`require_independent_verification: true`.

**SUBMITTED, not VERIFIED.**

| Artifact | SHA-256 |
|---|---|
| `raw/probe_readme_claims.py` | `4f4a9553dec9933831ff3eb4d4335b073a8d2974b9350c15d930ff3dcdea7f0d` |
| `raw/raw-readme-claims.txt` | `65ebcdb1f95f9bd73ee21a692a4be9af9985251d9725c0d1c9cf002161b4ca19` |
