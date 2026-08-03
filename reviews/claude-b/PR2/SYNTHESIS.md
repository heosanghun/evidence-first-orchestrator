# Claude B review of EFO `main` `5694ab45` — the map

One document for whoever picks this up next. Every claim below is measured and
bound to a probe and a raw output on this branch; nothing here is new evidence.

**652 passing checks across 32 instrumented raw outputs** (as of `HEAD`
2026-08-03). `raw/` holds 89 files: **33 probe scripts, 48 raw outputs, 8
provenance-attack scripts** that predate the `[ok]` convention. Each is SHA-256
bound in the write-up that cites it. These four numbers are **not yet
machine-checked** — unlike the citation and quote counts below, nothing fails
when they drift. Recount with `ls raw/ | ...` and `grep -c '[ok]' raw/raw-*.txt`
rather than trusting them; making them self-checking is queued.

Thirteen `UNEXPECTED` lines survive, in five files —
`raw-evidence-gates.txt` (5), `raw-lifecycle-gates.txt` (3),
`raw-alias-lineage.txt` (2), `raw-attack-prov5-main.txt` (2),
`raw-ledger-chain.txt` (1). All are **findings** recorded under the older
counting convention, not harness failures; see the caveat at the end of this
document.

> **Correction, 2026-08-03.** This paragraph previously read *"460 passing
> checks across 20 instrumented probes … 26 probe scripts and 65 raw outputs"*.
> All four numbers were stale, and the 65 does not reconcile with any state of
> `raw/` I can reconstruct (32 + 65 exceeds the 87 files present). They are now
> recounted with the rule stated: `[ok]` lines across `raw-*.txt`, and file
> counts by prefix. This is the same defect as the two below — a count copied
> into prose and never re-derived.

**Nothing here is VERIFIED.** Every issue and note is a *submission*. No
third-party reply exists on any of issues #3–#15 as of this writing, and I have
never treated my own re-run as independent confirmation.

---

## Where each component stands

| Component | Verdict | Where |
|---|---|---|
| `provenance.py` | **2 issues** | #4 `git replace` forges byte-exact provenance; #5 a never-pushed commit passes |
| `independence.py` | **1 issue, still open at this commit** | #3, re-confirmed — `NOTE-issue3-still-reproduces-at-5694ab45.md` |
| `monitor/collector.py` (portfolio) | **1 issue** | #6 a month-old `ready` still reads active at 85% |
| `workspace.py` (lease) | **1 issue** | #7 the floor is enforced, the ceiling does not exist |
| `evidence.py` | **1 issue** | #8 a known-answer check can compare `[FILL]` with itself |
| `ledger.py` | **1 issue** | #9 a truncated chain verifies clean |
| `archive.py` | **1 issue** | #10 retention has no verifier |
| `adapter.py` | **1 issue** | #11 the child is granted `ledger/events.jsonl` |
| `doctor.py` | **1 issue (two findings)** | #12 repair launders a truncated chain; `\b` misses `AWS_SECRET_ACCESS_KEY` |
| `functions/api/chat.js` | **1 issue (two findings)** | #13 the refusal is Korean-gated; snapshot text lands in `instructions` |
| `functions/api/snapshot.js` | **1 issue** | #14 `FORBIDDEN_KEYS` matches whole key names |
| `model.py` | **1 issue** | #15 `permissions`/`gates` are never type-checked |
| `doctor.py` (legacy path) | **1 issue** | #17 `--write-test` writes outside `reports/<agent>/` and reports a path that hides it |
| `archive.py` / `provenance.py` limit | **1 issue** | #18 one config key is a copy threshold on one path and a hard ceiling on the other |
| `repair_projections` / `cli.py` | **1 issue** | #19 repair drops `last_event_hash`; a later proxy submit escapes the CLI as a `KeyError` traceback |
| `proxy_submit` + grant | clean | `NOTE-proxy-grant-holds.md` |
| `provenance.py` byte-exactness | clean — 9 mutations, all refused | `NOTE-byte-exactness-holds.md` |
| `monitor/collector.py` (redaction) | clean | `NOTE-collector-redaction-holds.md` |
| `functions/api/local-health.js` | clean — **the strongest shape measured** | `ADDENDUM-chat-refusal-and-grounding.md` |
| `public/assets/app.js` | clean | `NOTE-dashboard-escaping-holds.md` |
| `ledger.projected_tasks` | clean | `NOTE-projected-tasks-holds.md` |
| collector identity registry | clean, but diverges | `NOTE-two-identity-implementations.md` |
| `util.py`, `lock.py` | clean | `NOTE-util-and-lock-hold.md` |
| `cli.py` | clean | `NOTE-cli-surface-holds.md` |
| `dashboard.py`, `errors.py` | clean, **one claim corrected** | `NOTE-dashboard-and-errors-hold.md` — its `escapes: []` is disproved by #19 |
| alias / `alias_chain` machinery | clean | `NOTE-alias-lineage-holds.md` |
| `workspace.py` implicit exceptions | clean — #19 is the only instance | `NOTE-issue19-is-the-only-one.md` |
| the rest of the package, implicit exceptions | clean — 78 reads, 3 guarded indexes | `NOTE-implicit-exceptions-package-wide.md` |
| dynamic-key subscripts, whole package | clean — 7 runtime reads, 1 keyed by parsed input; a **published count of mine corrected** | `NOTE-the-144-was-my-own-misleading-number.md` |
| `SECURITY.md` / `CONTRIBUTING.md` claims | clean — ignore rules, no `shell=True`, report containment | `NOTE-remaining-docs-adjudicated.md` |
| `tests/` — 93 tests, 318 assertions | map, not a verdict — **10 of 16 issues cannot be expressed in it by name** | `NOTE-what-the-test-suite-cannot-catch.md` |

Fifteen components were probed and found sound (one with a claim since corrected — see #19).

**Every Markdown document in the repository has now been read end to end and
every falsifiable sentence adjudicated** — `README.md`, `docs/ARCHITECTURE.md`,
`docs/PROXY_SUBMISSION.md`, `docs/MIGRATION.md`, `SECURITY.md`,
`CONTRIBUTING.md` and `docs/OPERATIONS_DASHBOARD.md`. That is half the value of this
pass: it says where *not* to look next.

---

## Four classes that repeat

These are the reason to read this document rather than fifteen issues.

### 1. Guards keyed on a naming convention the codebase does not write

Three independent guards, each meant as a backstop for the others, share one
blind spot — none assumes the snake_case-compound convention the project itself
uses (`gpu_uuid`, `process_id`, `raw_output_path`, `max_evidence_bytes`).

| Where | Guard | Misses |
|---|---|---|
| `doctor._scan_secrets` (#12) | `\b(secret\|token\|api[_-]?key)\b` | `AWS_SECRET_ACCESS_KEY`, `GITHUB_TOKEN` — `_` is a word character |
| `collector.sanitize_label` (`NOTE-collector-redaction-holds.md`) | character allow-list | strips the `=` from `--api-key=sk-ant-0123`, leaving the value readable but no longer matching the scanner |
| `snapshot.js` `FORBIDDEN_KEYS` (#14) | exact key name | `api_key`, `gpu_uuid`, `command_line`, `ssh_key` |

They do not compose into defence in depth; they compose into one shared gap.
The cheap fix is the same in all three: match the keyword as a **token inside**
the name, not as the whole name or a `\b`-delimited word.

### 2. Repair and retention paths that leave no signed record

| Where | What happens |
|---|---|
| `repair_projections` (#12) | rebuilds the projection **from the tampered ledger**, reverts a real `task.claimed`, reports `repaired: ['T1']`, leaves `doctor healthy=True` |
| `repair_projections` again (#19) | silently drops `last_event_hash`; `audit_projections` excludes that key so nothing notices, and the next proxy submit dies with an uncaught `KeyError` |
| the same command via the CLI (`NOTE-cli-surface-holds.md`) | the only mutating subcommand of 30 that appends no event — even in the honest case |
| `archive.py` (#10) | the ledger holds every per-file sha256; no shipped code ever recomputes them. Tamper, replace `bundle.json`, or `rm -rf` the bundle — `ledger.verify`, `get_task`, `audit_projections` and `doctor` all stay clean |

The thread: the system is careful about recording *work* and careless about
recording *maintenance*. An auditor sees the effect and not the cause.

### 3. Two implementations of agent identity, already diverging

`independence.py::resolve_identity_registry` decides who is independent for the
verification gate. `collector.py::_resolve_signed_identity_registry` decides the
same thing again for the dashboard. Run over one corpus they **agree on 4 shapes
and differ on 8** — the collector stricter every time
(`NOTE-two-identity-implementations.md`).

Every divergence currently lands safe, which is why no issue was filed. What is
worth knowing is that the stricter implementation lives in the component with
the *lower* security stake, and **nothing in the test suite runs both over one
corpus**, so a future edit to either will not be checked against the other.

### 3b. One knob, two policies

`max_evidence_bytes` is read by `archive.py:128` as a *copy threshold* — over
the limit, keep the artifact external and still bind it, which is what
`README.md:391-394` documents — and by `provenance.py:263` as a *hard ceiling*
that refuses the submission (#18). Same number, opposite meanings, one lever,
and only one of the two written down. It rhymes with class 3: two
implementations of one idea that nothing runs over a shared corpus.

### 4. Type confusion that only ever opens gates

`permissions={"performance_metrics": "false"}` **allows** the measured
performance claim it appears to forbid; `gates={"allow_skips": "false"}` allows
the skip (#15). The `require_*` gates restrict when truthy, so the same
confusion fails **safe** there. Every flag moves the same way under a stray
string: toward permission. There is no spelling of the mistake that makes a
task stricter than intended.

---

## What is measured clean, and worth not re-probing

- **Evidence gates.** `exit_code != 0 or failed` in one condition; skip refused
  unless explicitly allowed *and* individually justified; `[FILL]` required
  exactly; measured claims bound to hashed artifacts. 17 gates hold (#8 covers
  the two that do not).
- **The lifecycle.** 13 gates hold; lease theft is properly closed —
  `_require_lease` checks owner *and* compares the token with
  `secrets.compare_digest`, and `heartbeat` cannot revive a lapsed lease.
- **The proxy grant.** Every gate fires, including replay — caught by the
  `next_attempt` binding *before* the state machine, which is the stronger
  ordering — and a token minted in another workspace.
- **`local-health.js`.** Enforces "no hostname, process names, command lines,
  or file paths" **server-side with an exact key set**, not by trusting the
  collector. Plus HMAC and a 300-second replay window. The right shape.
- **`app.js`.** All 89 `innerHTML` interpolations enumerated with `escapeHtml`
  stripped first; none carries free text. `escapeHtml` replaces `&` first,
  which is the ordering that resists entity smuggling.
- **The state machine.** `transition` agrees with `TRANSITIONS` on all 64 edges
  of the full 8×8 matrix.
- **`is_relative_to`.** Gets `reports/wombat` vs `reports/w` right and fails
  **closed** on a symlink pointing outside — which is why #11's snapshot blind
  spot does not extend to the ownership gate.
- **The dashboard bind guard.** A strict allow-list: `127.1`, `127.0.0.2`,
  `0177.0.0.1`, `[::1]` and `LOCALHOST` all reach loopback and are all refused.
- **Proxy byte-exactness.** Nine mutations refused, including the three that
  render identically — a trailing newline added, removed, and trailing
  whitespace. The comparison is over `git cat-file blob` bytes, never a
  checkout, so no smudge filter can launder anything.

---

## Three wrong citations in my own write-ups, found and fixed on 2026-08-03

`NOTE-citation-audit-of-this-review.md` audits all **170 live citations across
37 documents**; every one now resolves at `main`. Three did not:

- `README.md:590` [retracted] was really `cli.py:590` — right line, wrong file, in a file
  of 452 lines. I had cited an argparse `help=` string as documented intent.
- `README.md:336-337` was `:335-336` — off by one.
- `REPORT.md` reviews `codex/meta-orchestration-v2` (`workspace.py` = 2528
  lines) and never named it, so its correct citations looked invented against
  `main`.

Nothing in the workflow checked a citation before that probe existed. The nine
anchors the filed issues rest on were spot-checked and all hold, but that is
luck rather than process.

A follow-up pass (`NOTE-quote-accuracy.md`) then asked whether a citation that
resolves also *quotes* accurately. Of eleven unambiguous (citation, fenced
block) pairs, seven are verbatim and four are adjudicated non-quotes — but
**two blocks had been condensed renderings presented as source**, and are now
verbatim. The fix was to make the documents literal rather than the checker
lenient. 235 inline spans remain undecidable by position and are named as a
gap.

## A misleading number I published, corrected on 2026-08-03

`NOTE-implicit-exceptions-package-wide.md` named its own next gap as
*"dynamic-key subscripts, `x[variable]` — unmeasured — **144** sites"*. The
count reproduces exactly, and that is what makes it worse than an arithmetic
slip: **128 of the 144 are type annotations** (`dict[str, Any]`) and 9 are
stores, which create their key and cannot `KeyError`. The runtime read
population is **7**. A reader would have taken the uncovered surface to be
twenty times its real size.

All seven are now adjudicated by key provenance in
`NOTE-the-144-was-my-own-misleading-number.md`: **one** is keyed by parsed
input (`provenance.py:295`, guarded 54 lines earlier at `:241`), two index a
dict from its own keyspace, two are slices, two are local literals.
`workspace.py` has **zero** runtime dynamic-key reads.

That is the **fifth** hand-written filter in this review to be the bug — after
the `raise` census blind to a dict index (#19), the variable-name filter that
missed `task_for_validation`, the module list that missed `errors.py`, and the
quote-accuracy window built from a range's start only — and the **second** time
the bug was in a figure already on the record.

## Counts that drifted, caught and made self-checking on 2026-08-03

Pulling on the 144 exposed a wider version of the same problem: **numbers
copied into prose and never re-derived.** Three pairs disagreed with the raw
output committed beside them.

| Document | Stated | Raw output said |
|---|---|---|
| `NOTE-quote-accuracy.md` | "Eleven such pairs exist"; 194 inline spans | 12 pairs; 215 spans |
| `NOTE-citation-audit-of-this-review.md` | 141 citations / 34 documents | 152 / 35 |
| this document, header | 460 checks, 20 probes, 26 scripts, 65 outputs | 636 / 31 / 32 / 47 |

Every one was true when written. None was true when read, and *"Eleven"* sat
directly above a table of 7 + 5 that does not sum to eleven — an inconsistency
visible on the page for two rounds without being pulled.

The fix is not another refresh. `probe_citation_audit.py` section F and
`probe_quote_accuracy.py` section E now **read the prose and fail the run** when
a stated count disagrees with the count that run measured. A drifting number is
indistinguishable from an invented one, which is the failure this project
exists to prevent.

## A defect in this branch, found and fixed on 2026-08-03

Until `c16df6d`, this branch was based on `dad3f4c4`, an ancestor of `main`,
and was **behind main by 9,457 lines** — `workspace.py` −680, `provenance.py`
−341, and four whole test modules plus `web_tests/*`. Merging PR #16 would have
reverted `main`. The PR body called it "documentation only", which was true of
the commits and false of the branch.

It was caught by a line-number mismatch: a CI traceback cited
`tests/test_concurrency.py:49`, and `main` has that statement at `:54`.

`c16df6d` merges `origin/main` in. The branch is now `main` plus
`reviews/claude-b/` alone — 17,011 insertions, **zero deletions**, nothing
outside `reviews/`.

**The findings are unaffected**: every probe runs against a separate checkout
verified at `git rev-parse HEAD == 5694ab45` with an empty `git status`, and
that verification is now a standing precondition of the review rather than an
assumption. What *was* affected is PR #16's CI — every green run before
`c16df6d` exercised stale source, so none of them is evidence about `main`. The
first honest run is `30776534613`, all 11 checks green.

Related, measured while checking for further contamination of my own making:
`reviews/claude-b/PR2/test_p1_1.py` is named `test_*`, but neither test runner
collects it. CI runs `python -m unittest discover -s tests -t .` (start
directory `tests`) and `node --test` over three explicitly named files in
`web_tests/`. The green run on `c16df6d`, which contains both that file and
`main`'s full suite, is the measurement.

## Two caveats about this document's own numbers

**The counting convention changed mid-pass.** The early probes
(`raw-evidence-gates.txt` 17/5, `raw-lifecycle-gates.txt` 13/3,
`raw-ledger-chain.txt` 12/1, `raw-alias-lineage.txt` 9/2) marked a *finding* as
`UNEXPECTED`. Later probes record observed behaviour as the expectation and
carry the interpretation in the write-up, so they read `0 unexpected` even where
they found something. The flagged counts in the older files are findings, not
harness failures; each is explained in its own ADDENDUM.

**Harness bugs were common and are all disclosed.** Roughly two dozen across the
pass, every one caught before a conclusion, every corrected run the only one
reported. Three would have become false findings if I had stopped early:

- a non-greedy interpolation regex truncated a nested template and reported
  `alert.message` as unescaped — it is escaped;
- a `PYTHONPATH` omission made the collector read an empty workspace, so every
  redaction marker read "absent" from a snapshot that contained nothing;
- I expected `NaN != NaN` to make a task projection permanently unequal to its
  ledger snapshot. CPython's dict comparison checks identity before equality,
  so it does not.

Two premises of mine were wrong in the code's favour and are recorded as such:
the workspace config **is** bound to the signed ledger, and `cli.py` catches
four exception families rather than only `EFOError`.

---

## What was not examined

`tests/` beyond invoking the suite; `Ledger.append` and `FileLock` under real
concurrent load; the served dashboard HTML; any behaviour of the OpenAI model
behind `chat.js` (`network: false` — the request was constructed, never issued);
the real `nvidia-smi` and `docker` binaries (recorded fixtures only); and
Windows path semantics anywhere, since `E:\...` cannot be exercised here.

`docs/MIGRATION.md`'s legacy path **has since been examined** — see
`ADDENDUM-legacy-write-test-escapes-reports.md` and issue #17.

Pre-registered permissions were never relaxed at any point in this pass:
`gpu: false`, `network: false`, `performance_metrics: false`; gates
`allow_skips: false`, `require_validation: true`,
`require_known_answer_check: true`, `require_independent_verification: true`.

**SUBMITTED, not VERIFIED.**
