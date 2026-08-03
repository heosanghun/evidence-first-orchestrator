# Claude B review of EFO `main` `5694ab45` — the map

One document for whoever picks this up next. Every claim below is measured and
bound to a probe and a raw output on this branch; nothing here is new evidence.

**1271 passing checks across 66 instrumented raw outputs** (as of `HEAD`
2026-08-03). `raw/` holds 159 files: **68 probe scripts, 83 raw outputs, 8
provenance-attack scripts** that predate the `[ok]` convention. Each is SHA-256
bound in the write-up that cites it. **These numbers are now machine-checked**:
`raw/probe_inventory_selfcheck.py` recounts `raw/` and **fails the run** if this
paragraph disagrees with it. The counts exclude that probe's **own** output,
which is the report of the run doing the counting — a self-reference with no
fixpoint, stated rather than hidden — the same guard the citation and quote counts got.
It also checks the headline `N checks, M unexpected` of all **60** write-ups
against the raw output each one names; nothing verified those until 2026-08-03.

Twelve `UNEXPECTED` lines survive, in five files —
`raw-evidence-gates.txt` (5), `raw-lifecycle-gates.txt` (3),
`raw-alias-lineage.txt` (2), `raw-attack-prov5-main.txt` (1),
`raw-ledger-chain.txt` (1). All are **findings** recorded under the older
counting convention, not harness failures; see the caveat at the end of this
document.

> **Correction, 2026-08-03.** This read *"Thirteen … `raw-attack-prov5-main.txt`
> (2)"* until the tally was fixed to count markers **by position** rather than
> by substring. That file has one finding and one *legend line* explaining the
> marker, and `text.count()` could not tell them apart. Both the total and the
> per-file list are now parsed out of this paragraph and compared against the
> measurement, so neither side is pinned —
> `NOTE-two-attack-scripts-ran-against-the-stale-base.md` has the detail.

> **Correction, 2026-08-03.** This paragraph previously read *"460 passing
> checks across 20 instrumented probes … 26 probe scripts and 65 raw outputs"*.
> All four numbers were stale, and the 65 does not reconcile with any state of
> `raw/` I can reconstruct (32 + 65 exceeds the 87 files present). They are now
> recounted with the rule stated: `[ok]` lines across `raw-*.txt`, and file
> counts by prefix. This is the same defect as the two below — a count copied
> into prose and never re-derived.

> **`main` has moved and keeps moving, from 2026-08-03 06:19Z.** This review
> stays anchored at `5694ab45`; every write-up and every SHA-256 below is bound
> to it and `/tmp/efo-prov` was deliberately not re-pointed. `origin/main` has
> been **red on every push since `b78c63d`** — a UI rewrite deleted the whole
> security-header block and the transport-badge rendering, and the header block
> has since been deleted **twice**, an explicit rollback having restored it in
> between. Its SHA is not recorded here because it changes every few minutes;
> the probe resolves it live and prints the head it measured.
> That is issue **#20** and
> `ADDENDUM-main-is-red-and-a-push-run-is-not-a-pr-run.md`, the only document
> here that reads a ref other than the anchor. It names both.

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
| `proxy_submit` + grant | clean — **scope narrowed**: the 27 checks fed `duration_seconds` twice (`300`, `10`), both at or above the floor; the un-fed class gives **`0` silently becoming the 1800s default** (a second instance of item 56's shape, at `workspace.py:735`), **`10**9` accepted — #7's missing ceiling on a second surface**, a **float** accepted against an `int` annotation, and a string raising a raw `TypeError`. The 10-second floor is **present** on this path — inside `lease_expiry`, called at both 771 and 889 | `NOTE-proxy-grant-holds.md`, `NOTE-what-the-proxy-grant-fed-and-the-duration-it-never-did.md` |
| `provenance.py` byte-exactness | clean — 9 mutations, all refused; **scope narrowed**: the 20 checks fed 11 byte mutations and 3 membership errors and **never a malformed record**, and driving that gap gives 7 refusals, 7 `EFOError`s, 0 accepted; unreachability holds **under the declared threat model** (item 57) | `NOTE-byte-exactness-holds.md`, `NOTE-what-byte-exactness-fed-and-the-malformed-record-it-never-did.md` |
| `monitor/collector.py` (redaction) | clean — **scope narrowed**: the 15 checks fed sensitive CONTENT in a well-formed shape and **never a malformed one**; of 6 driven shapes **5 degrade** and `docker inspect` returning a JSON object raises `AttributeError` past a guard that catches only `JSONDecodeError` | `NOTE-collector-redaction-holds.md`, `NOTE-what-collector-redaction-fed-and-the-malformed-output-it-never-did.md` |
| `functions/api/local-health.js` | clean — **the strongest shape measured** | `ADDENDUM-chat-refusal-and-grounding.md` |
| `public/assets/app.js` | clean | `NOTE-dashboard-escaping-holds.md` |
| `ledger.projected_tasks` | clean — **scope narrowed**: all 6 payloads the 17 checks fed were **dicts**, and the un-fed class is `payload` present but not a dict; 5 of 5 such shapes raise a raw `AttributeError` at `ledger.py:161`, where the `{}` default covers only an ABSENT payload. `Ledger.read` **does** carry the line-level guard the collector lacked (4 non-object lines refused, an object accepted). Reachable only with the signing key — a crash, not a bypass | `NOTE-projected-tasks-holds.md`, `NOTE-what-projected-tasks-fed-and-the-payload-it-never-did.md` |
| collector identity registry | clean, but diverges | `NOTE-two-identity-implementations.md` |
| `util.py`, `lock.py` | clean — **scope narrowed**: all 46 checks rested on my probe, and none fed a non-string; 17 driven inputs raise raw Python exceptions, 0 `EFOError` | `NOTE-util-and-lock-hold.md`, `NOTE-what-util-is-clean-rested-on-and-the-input-it-never-fed.md` |
| `cli.py` | clean — **scope narrowed**: all 25 checks fed strings (argparse hands strings) and **none of the 8 typed options**; driving those gives argparse rejection at parse time, the floor on `-5`, and `--lease-seconds 0` silently becoming the 1800s default | `NOTE-cli-surface-holds.md`, `NOTE-what-cli-surface-fed-and-the-eight-typed-options-it-never-did.md` |
| `dashboard.py`, `errors.py` | clean, **one claim corrected** | `NOTE-dashboard-and-errors-hold.md` — its `escapes: []` is disproved by #19 |
| alias / `alias_chain` machinery | clean | `NOTE-alias-lineage-holds.md` |
| `workspace.py` implicit exceptions | clean — #19 is the only instance | `NOTE-issue19-is-the-only-one.md` |
| the rest of the package, implicit exceptions | clean — 78 reads, 3 guarded indexes | `NOTE-implicit-exceptions-package-wide.md` |
| dynamic-key subscripts, whole package | clean — 7 runtime reads, 1 keyed by parsed input; a **published count of mine corrected** | `NOTE-the-144-was-my-own-misleading-number.md` |
| `SECURITY.md` / `CONTRIBUTING.md` claims | clean — ignore rules, no `shell=True`, report containment | `NOTE-remaining-docs-adjudicated.md` |
| `tests/` — 93 tests, 318 assertions | map, not a verdict — **10 of 16 issues cannot be expressed in it by name** | `NOTE-what-the-test-suite-cannot-catch.md` |
| `web_tests/` — 37 tests, 120 assertions | map — each of #13/#14 has a test that feeds the guard **only the input it already handles** | `NOTE-the-node-tests-exercise-only-the-covered-input.md` |
| dynamic-key **stores**, whole package | clean — 2 chains, both guarded; one invisible to a name-scoped census | `NOTE-dynamic-stores-and-what-a-name-scoped-census-cannot-see.md` |
| this review's own counts | machine-checked — inventory, 60 headline claims, citations, quotes | `NOTE-every-count-this-review-states-about-itself.md` |
| attribute accesses reachable from a document | clean — 963 scoped to **24**; a near miss driven and **not** filed, **under the threat model `SECURITY.md:38` declares** | `NOTE-963-attribute-accesses-scoped-to-24-and-a-near-miss.md` |
| `monitor/collector.py` coverage | map — 27 tests, **no test ages an input**; #6 has no vocabulary to be tested by | `NOTE-the-collector-suite-never-ages-an-input.md` |
| the 8 provenance-attack scripts | map — all self-document; **2 ran against an unpinned tree that was the stale base**, superseded by the `_main` re-runs | `NOTE-two-attack-scripts-ran-against-the-stale-base.md` |
| `public/_headers` at live `main` | map — the file is **maintained**; two commits that name it left the security block out, and a second rollback preserved the regression | `NOTE-the-headers-file-is-maintained-without-the-block.md` |
| #4 / #5 / #8 / #18 vs the Python suite | map — the components are driven unpatched; **3 of the 4 properties have no vocabulary at all**, the 4th's guard is fed only integers | `NOTE-four-issues-whose-property-the-suite-has-no-words-for.md` |
| attribute bases arriving via a PARAMETER | clean — 487 too many to adjudicate, one hop leaves **2**, both guarded by a short-circuiting `isinstance` | `NOTE-487-is-too-many-and-the-two-that-survive-are-guarded.md` |
| `raw-attack4.txt`, the orphan output | **partly reproducible — my earlier `unreproducible` was too strong.** No `attack4` script ever existed and `REPORT.md`'s provenance sentence is false, both unchanged; but `git show 7a9553b:…whl` restores the wheel **byte-exact** and **W1/W2 have been re-run** | `NOTE-raw-attack4-is-unreproducible-and-my-manifest-was-wrong.md`, `NOTE-the-wheel-was-never-lost-git-had-it-all-along.md` |
| the package vs the Python suite | map — **7 of 15 modules are never named by any test**, and #4/#5/#10/#15/#18 all live there; `errors.py` is the counter-example, `ledger.py` the near miss | `NOTE-seven-of-fifteen-modules-the-suite-never-names.md` |
| cross-module dict-field propagation | clean — 91 scoped to **22**, 16 accesses, one **driven** raise in `model.lease_expired`; the ledger projection guard blocks the API path **against an adversary who cannot read `.efo/ledger.key`** (item 57), so a near miss **not** filed | `NOTE-91-to-22-to-one-raise-that-the-ledger-guard-blocks.md` |
| hop-three closure | clean — closure **terminates** at 25 triples; `_validate_remote_url` is the only function found that raises a `ConfigurationError` on a non-string, and the one unguarded validator is a string **by construction** | `NOTE-hop-three-closes-and-the-one-unguarded-validator-is-unreachable.md` |
| `REPORT.md`'s own evidence | map — both named refs EXIST; 3 of 6 cited outputs have no producer, but **two were re-run here** (70/70 and 77/77, OK, exit 0) and only `raw-attack4.txt` is unreproducible | `NOTE-two-of-REPORTs-outputs-were-re-run-not-merely-catalogued.md` |
| the class-2b pattern | **census: 7 of 7 tests cannot fail on their issue** | `NOTE-class-2b-is-a-census-now-seven-of-seven.md` |
| this review's own censuses | bounded — **24 of 30 measured, 6 reasoned from reading** | `NOTE-which-of-my-censuses-measured-and-which-read.md` |
| my own 21 sound-verdict rows, censused cheaply | **lead, not a verdict — the cheap proxy is refuted** by item 47's hand measurement; 4 of 19 locatable probes are static censuses, 15 drive a component, and the 7 whose component carries an open issue are named for hand adjudication | `NOTE-the-cheap-way-to-census-my-clean-verdicts-is-refuted.md` |
| the `isinstance` guard, package-wide | map — **a positive pattern, measured**: 24 of 147 functions type-check at 66 sites, and only **11** guard an ARGUMENT; the other 43 guard data the function itself read. 35 of the 37 raising sites raise an `EFOError` | `NOTE-66-guards-and-only-eleven-of-them-guard-an-argument.md` |
| `raw-attack4.txt` W3, replayed | **replays — 6 of 6 steps**, exit codes and the rejection string identical; the driver never existed and was reconstructed, and a first reconstruction was caught wrong by the ledger event count (5, not 7). 7 of the 10 sections remain un-run; all are offline | `NOTE-w3-replays-and-the-driver-had-to-be-rebuilt.md` |
| the 4 modules with **no** `isinstance` | map — **the absence is real in one, reachable in none** (reachability measured **under the declared threat model** — item 57): `archive.py` gives 8 raw Python exceptions on 8 malformed manifests but all 3 call sites pass a validator's return; `doctor.py`'s 23 unguarded subscripts sit behind the ledger guard (5 tampered documents, 0 escaped); `lock.py` and `dashboard.py` read no document field at all | `NOTE-four-modules-with-no-guard-real-in-one-reachable-in-none.md` |
| `raw-attack4.txt` W4, and the ref it needs | map — **`transfer_orchestrator` is absent at the anchor and `7a9553b` is NOT an ancestor**, so W4/W5/W6/W6b drive a divergent line; replayed against `7a9553b` and **both tracebacks are the original driver's** (wrong path, wrong key on the CLI wrapper). The config/ledger divergence is real and by design | `NOTE-w4-needs-a-ref-the-anchor-never-took.md` |
| the ledger signature's SCOPE | map — **the precondition under items 45, 53 and 54**: a naive tamper is caught, but the same edit with the ledger payload updated and the chain **re-signed** audits `healthy: true` with `valid/signed: true`. The key is `.efo/ledger.key` inside the workspace. `SECURITY.md:38` states this limit verbatim, so it is **documented and driven in both directions**, not a defect | `NOTE-a-tamper-that-resigns-is-healthy-and-the-document-says-so.md` |
| which LINE produced each raw output | map — **a negative result, and its first answer was WRONG**: the token test places **27 of 77** on the anchor's line, **5** on the divergent one and leaves **45 undecidable**, and it has a **proven false negative** — `raw-attack4.txt`, which item 55 showed is mixed, carries no marker. **Not one** of `REPORT.md`'s 6 is on the anchor's line. As published this row read *35 / 1 / 41, four of six placed*; a bare `"independence"` substring reversed four — corrected by item 61 | `NOTE-which-line-produced-which-output-and-why-the-test-is-one-way.md`, `NOTE-the-suite-size-decided-it-and-a-substring-reversed-four.md` |
| `reports/`, `submissions/`, `archive/` | map — **the measured width of #10**: the 6 comparison messages name only Agent, Task and Workspace, and **6 of 6 tampers go unnoticed** — including deleting the whole archived bundle and rewriting `archive/T1.json`. All **7** archived files' sha256 are in signed ledger events; nothing recomputes them | `NOTE-reports-submissions-and-archive-are-compared-against-nothing.md` |
| the **suite size** as a provenance marker | map — **a correction of my own work**: no test count is shared between the two lines across all **20** reachable commits, so `Ran 77 tests` places `raw-recheck-cef5623.txt` on **`cef5623`** — the one commit anywhere with a 77-test suite, and no ancestor of the anchor. All three suites run (93 / 77 / 70). `REPORT.md:437` names `4aa47ca6` as its own subject, the known answer item 58 failed | `NOTE-the-suite-size-decided-it-and-a-substring-reversed-four.md` |
| every workspace directory, tampered | map — **the width of #10, whole-tree**: all **9** top-level directories enumerated and the classification asserted exhaustive both ways; the 3 never driven (`shared/`, `ledger/`, `.efo/`) take **8 tampers, 8 unnoticed** — including deleting `shared/` outright. And the control the line lacked: replacing `.efo/ledger.key` **is caught** (`Ledger signature mismatch at event 1`), deleting it caught differently — the driver is not blind | `NOTE-every-directory-tampered-and-the-one-that-is-caught.md` |
| what ELSE places an output | map — **a mostly-negative result**: the named classes cover **6 of 47** open outputs, so all of them are subsumed by one derivation — the distinctive **string literals** each line contains, differenced over full ancestry. The raw difference **contradicted item 61 on 5 outputs** (`proxy_submit` is a literal on one line and an *identifier* on the other); corrected to **0 contradictions, 19 agreements**, it places 12 and leaves **35 of 79 unplaceable by any class measured** | `NOTE-what-else-places-an-output-and-the-filter-the-ground-truth-caught.md` |
| `public/` at **`origin/main`**, not the anchor | **1 issue** | #20 every security header deleted from `_headers`, transport badge gone from `app.js`; main red for 9 pushes |

Twenty components were probed and found sound (one with a claim since corrected — see #19).

> **Made self-checking, 2026-08-03.** This number, the class-2b count below and
> the section heading beneath it were each stale when measured — the first by
> one, the second by five, the third by two. `probe_inventory_selfcheck.py` §E
> now derives all three from this document's own tables and **fails the run**
> when the prose disagrees. Every number in this review is now either
> machine-checked or carries a date.

**Every Markdown document in the repository has now been read end to end and
every falsifiable sentence adjudicated** — `README.md`, `docs/ARCHITECTURE.md`,
`docs/PROXY_SUBMISSION.md`, `docs/MIGRATION.md`, `SECURITY.md`,
`CONTRIBUTING.md` and `docs/OPERATIONS_DASHBOARD.md`. That is half the value of this
pass: it says where *not* to look next.

---

## Six classes that repeat

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

### 2b. Tests that encode the decision the issue objects to

Seven instances, and they are the reason "CI is green" and "the property
holds" come apart. Two are the sharpest — a test that *encodes* the decision:

| Where | What the test does |
|---|---|
| `test_proxy_status.py:86` (#19) | **excludes** `last_event_hash` from the comparison — the same exclusion `workspace.py:1511` makes |
| `chat.test.mjs` (#13) | **asserts** snapshot text lands in the model `instructions` block — the placement the issue objects to |

Neither test is wrong on its own terms. What both mean is that the suite cannot
be the thing that notices.

**This is now a census, not an observation.** Of the 16 issues, 10 have a defect
token in no test source at all; the other 6 — plus #14, whose test lives in
`web_tests/` — were each read to see what input their test feeds. **Seven of
seven cannot fail on the defect**
(`NOTE-class-2b-is-a-census-now-seven-of-seven.md`):

| Issue | Its test |
|---|---|
| #3 | re-attestation tested three times, never on a verifier |
| #8 | known-answer values and `[FILL]` both tested, never crossed |
| #10 | the archiver is **mocked out** in its only appearance |
| #11 | token match in an unrelated file |
| #13 | Korean-only input; the second finding is **asserted** |
| #14 | feeds `password`, a key the set contains |
| #19 | the repair test asserts `state`, not the dropped key |

A statement about coverage **shape**, not test quality: every one of these tests
asserts something true.

**A second shape, found 2026-08-03.** #6 is not in that table because it has no
test at all — and the reason is sharper than "absent". `monitor/collector.py:900`
decides that a `pending` task with an active `external_phase` counts as active
by **pure set membership, with no timestamp in the branch**. The words `stale`,
`freshness`, `age`, `elapsed` and `expired` appear **nowhere** in the collector's
27 tests, and the suite's single `time.time` stub pins the clock to a constant
inside a signature test. So there is no vocabulary for the property, and nothing
for a test to be about (`NOTE-the-collector-suite-never-ages-an-input.md`).

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

`NOTE-citation-audit-of-this-review.md` audits all **255 live citations across
72 documents**; every one now resolves at `main`. Three did not:

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
lenient. 325 inline spans remain undecidable by position and are named as a
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

**A limit of the technique, not of a list — found 2026-08-03.** Tracing those
stores forward, the census reported that `provenance.py::files` is never read
back, contradicting a claim I was mid-way through writing. The census was
right: the dict is **renamed across a return** (`expected_files =
_evidence_file_map(evidence)`), and a census keyed on a variable *name* measures
a **scope**, not a **value**. Every name-scoped census in this review carries
that bound; where a value crosses a function boundary the chain has to be read,
and the result is reasoned from reading rather than measured.
`NOTE-dynamic-stores-and-what-a-name-scoped-census-cannot-see.md` says which of
its own results fall on each side.

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

> **Correction, 2026-08-03.** Diagnosing the `test_concurrency` divergence I
> wrote that the `push` and `pull_request` jobs were *"same commit, OS,
> Python"*. The **commit** claim is wrong as a general statement: a push run
> checks out the branch head, a pull_request run checks out
> `refs/pull/N/merge` — the branch **merged into `main`**. They share a head
> SHA and not a tree. The concurrency conclusion survives (`barrier.wait()`
> outside the `try` is independent of the base), but the argument did not, and
> the same shortcut would have made me call issue #20's failure a flake.

`c16df6d` merges `origin/main` in. The branch is now `main` plus
`reviews/claude-b/` alone — 17,011 insertions, **zero deletions**, nothing
outside `reviews/`.

**The findings are unaffected**: every probe runs against a separate checkout
verified at `git rev-parse HEAD == 5694ab45` with an empty `git status`, and
that verification is now a standing precondition of the review rather than an
assumption. What *was* affected is PR #16's CI — every green run before
`c16df6d` exercised stale source, so none of them is evidence about `main`. The
first honest run is `30776534613`, all 11 checks green.

**A second consequence, found 2026-08-03.** `attack2.sh` and `attack3.sh`
declare `REPO=/workspace/evidence-first-orchestrator` — the branch's own working
tree, unpinned — and were committed 2026-07-30, four days before `c16df6d`. They
therefore ran against `dad3f4c4`'s 193-line `provenance.py`, not main's 341-line
rewrite. Both were re-run against pinned refs (`attack_prov_main.sh`,
`attack_prov5_main.py`), which is what the issues cite, but the branch never
said the originals were superseded. Recorded in
`NOTE-two-attack-scripts-ran-against-the-stale-base.md`, which also notes that
`raw-attack4.txt` has no script in `raw/`.

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
