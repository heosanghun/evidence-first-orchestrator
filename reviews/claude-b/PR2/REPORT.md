# Claude B — independent verification of EFO Draft PR #2

> **Review target, added 2026-08-03.** This document reviews
> **`codex/meta-orchestration-v2`**, not `main`. It never said so, and that
> omission made its citations look fabricated: `workspace.py:2366` is out of
> range on `main` (1562 lines) and on this branch's former base `dad3f4c4`
> (920 lines), and `docs/META_ORCHESTRATION_V2.md` exists on neither. Both
> resolve on `codex/meta-orchestration-v2`, where `workspace.py` is 2528 lines
> and that document exists. **The citations were correct for their subject all
> along** — what was missing was the subject. Found by
> `raw/probe_citation_audit.py`; nothing in this document's substance changed.

- Repository under review: `heosanghun/evidence-first-orchestrator`
- Branch / commit: `codex/meta-orchestration-v2` @ `4aa47ca602d36c22cbaf2ce63fa442ee398c317e`
- Working tree during the review: clean (`git status --porcelain` empty)
- Reviewer role: Claude B (verifier), independent of the PR author (Codex)
- Date: 2026-07-30
- Status: **SUBMITTED — not VERIFIED.** These are my own measurements on this
  container. They become VERIFIED only when a third party reproduces them.

**Verdict: do not approve as-is.** One P1 finding bypasses the PR's headline
control, and the audit command built to catch it reports the workspace clean.

### Re-verified at the current PR head `cef5623`

The branch moved after this review was written. Everything below was measured at
`4aa47ca`; I re-ran the load-bearing checks against the new head
`cef56234a873fefddd51f8cfedb737705a6f0d9a` before delivering, rather than
assuming the findings still hold.

Three commits landed in between — `7b651fe` identity-bound automatic agent
delivery, `b83c648` workspace fingerprint binding, `cef5623` source-bound module
entrypoint — touching `adapter.py`, `cli.py`, `job_runner.py`, a new
`fingerprint.py`, and `workspace.py` in the agent add/update region only.
`identity.py` is **unchanged**, and neither `audit_independence` nor
`transfer_orchestrator` was modified.

| Check | at `4aa47ca` | at `cef5623` |
|---|---|---|
| Full suite | 70 tests, OK, 0 skipped, exit 0 | **77 tests, OK, 0 skipped, exit 0** |
| P1-1 critical-tier independence forgery | reproduces | **reproduces identically** — A2 rejected, A4 accepted after one `agent update`, `verify` exit 0, audit `independent` / `action_required: 0`, unchanged after revert |
| P2-1 stale config orchestrator | reproduces | **reproduces** — config `antigravity`, effective `codex` |
| P2-2 v0.1 client on a v2 workspace | fails closed pre-handoff | **unchanged** — `Agent 'antigravity' registration differs from the signed ledger` |

The seven new tests all pass and the suite still has zero skips. **No finding in
this report is addressed by the three new commits.** The scope note in §6 still
applies, and now also covers the new automated-delivery, fingerprint, and
entrypoint code, which this review did not examine.

Raw output: `raw/raw-attack2-cef5623.txt`, `raw/raw-recheck-cef5623.txt`.

### Executable reproducer for P1-1

`test_p1_1.py` in this directory pins the finding as a stdlib `unittest`.
Deliberately **not** placed under `tests/`, so it cannot turn the suite red;
move it there once `audit_independence` is fixed.

```
PYTHONPATH=src python3 -m unittest reviews.claude-b.PR2.test_p1_1 -v
Ran 3 tests   FAILED (failures=2)   exit=1
```

| Test | at `cef5623` | Meaning |
|---|---|---|
| `test_the_bypass_itself_reproduces` | **ok** | harness control — the bypass is real and the fixture is sound |
| `test_audit_flags_independence_that_rested_on_a_mutated_declaration` | **FAIL** — `'independent' == 'independent'` | P1-1 proper |
| `test_reverting_the_declaration_does_not_launder_the_record` | **FAIL** — `0 not greater than or equal to 1` | same root cause, frozen-profile path |

The two failures are the finding, not a broken test: they assert the behaviour
`META_ORCHESTRATION_V2.md:69-70` already promises. Raw output:
`raw-p1-1-regression.txt`.

> No PR-side action was taken: no approval, no merge, no comment, no server
> deploy, no orchestrator handover. Per the assignment, none of the PR's own
> test results or Codex's internal review were reused as evidence — every
> number below comes from a command I ran on this container.

---

## 1. What I set out to do

Five sub-tasks, as assigned:

| # | Sub-task | Pre-registered scope |
|---|---|---|
| ① | Re-run the full suite on Linux with zero skips | Do not reuse the PR's test output |
| ② | Attack `actor` / `controller` / `model_family` independence | Bypass, then check detectability |
| ③ | Reproduce wrong Git remote, local-only commit, replace-ref, partial file submission, CRLF tampering | Each must be rejected |
| ④ | v0.1 workspace compatibility + post-handover fail-closed for old clients | Both directions |
| ⑤ | Report P0 / P1 / P2; approve only if clean | Approve only if nothing found |

Pre-registered permissions and gates (unchanged throughout, never relaxed
mid-task): `gpu: false`, `network: false`, `performance_metrics: false`;
`allow_skips: false`, `require_validation: true`,
`require_known_answer_check: true`, `require_independent_verification: true`.

Explicit prohibitions honoured: no server deployment, no merge, no orchestrator
handover, no reuse of the PR's own evidence.

## 2. What I actually did

| Step | Action | Raw output |
|---|---|---|
| ① | `PYTHONPATH=src python3 -m unittest discover -s tests -t . -v` on `4aa47ca` | `raw/raw-full-final.txt` |
| ② | Scripted 4-agent workspace; honest critical task → forge one declared field → replay → full lifecycle to `task.verified` → `efo audit independence` → revert → re-audit → `ledger verify` / `doctor` | `raw/raw-attack2.txt` (script: `raw/attack2.sh`) |
| ② | Probes: worker mutating a verifier's identity; worker mutating its own; `--no-independent-verification` on a critical task; self-verify | in-line, §3 |
| ③ | Real `origin.git` + work clone, honest positive control, then six provenance attacks | `raw/raw-attack3.txt` (script: `raw/attack3.sh`) |
| ④ | v0.1 wheel provenance (hash + source diff vs `f827f29`), v0.1 → v2 workspace, signed handoff, post-handover behaviour of both clients, v2 → v0.1 workspace | `raw/raw-attack4.txt` |

Two harness bugs of mine were caught and fixed before any conclusion was drawn:
`attack2.sh` initially failed at argparse (missing `--description`) and exported
`WS` after the heredoc that needed it. The first run's "expected nonzero" at
step A2 was argparse exit 2, not the independence gate. Both were corrected and
the whole script re-run; only the corrected run is reported.

## 3. How I verified — commands, exit codes, real counts

### ① Full suite, Linux, zero skips

```
$ cd /workspace/evidence-first-orchestrator && git rev-parse HEAD
4aa47ca602d36c22cbaf2ce63fa442ee398c317e
$ PYTHONPATH=src python3 -m unittest discover -s tests -t . -v
Ran 70 tests in 9.140s
OK
exit=0
```

**70 run, 70 passed, 0 failed, 0 skipped, exit 0.** Grep for `skipped` in the
raw output returns 0 lines. Reproduced independently; the PR's own reported
result was not consulted.

### ② Independence attack

| Step | Command | Observed |
|---|---|---|
| A2 | critical task, owner `claude-a`, verifier `claude-b`, dims `actor+controller+model_family` | **rejected** — `No allowed verifier is independent from the task owner under the declared dimensions`, exit 2 |
| A3 | `agent update --actor antigravity --id claude-b --model-family gpt` | exit 0 |
| A4 | **byte-identical** `task add` replayed | **accepted**, exit 0 |
| A5 | claim → start → submit (`claude-a`) → attest → verify (`claude-b`) | all exit 0; `task.verified` at ledger seq 13 |
| A6 | `efo audit independence` | `status: "independent"`, `action_required: 0`, `non_independent: 0`, `inconclusive: 0` |
| A7 | revert `model_family` to `claude-code`, re-audit | **unchanged** — still `independent`, still `action_required: 0` |
| A8 | `ledger verify` / `doctor` | `valid: true` / `healthy: true`, exit 0 |
| A9 | ledger contents | seq 6 `agent.added` (`claude-code`), seq 7 `agent.updated` (`gpt`), seq 13 `task.verified`, seq 14 `agent.updated` (`claude-code`) |

The declared identities the preset ships (A1, measured):

```
claude-a {"controller_id":"claude-a","id":"claude-a","model_family":"claude-code","provider":"anthropic","role":"worker"}
claude-b {"controller_id":"claude-b","id":"claude-b","model_family":"claude-code","provider":"anthropic","role":"verifier"}
```

Bounding probes (error text is the evidence; the printed exit code belongs to
`tail`, not to `efo`):

| Probe | Result |
|---|---|
| worker `claude-a` mutates `claude-b`'s identity | `error: Only orchestrator 'antigravity' may perform this action` |
| worker `claude-b` mutates its own identity | `error: Only orchestrator 'antigravity' may perform this action` |
| critical task with `--no-independent-verification` | `error: critical risk tasks require validation, known-answer, zero-skip, and independent-verification gates` |
| critical task, verifier = owner (`claude-a`) | `error: Allowed verifier 'claude-a' lacks verifier authority` |

So the bypass is **orchestrator-privileged only**. The gate opt-out and the
naive self-verify path are both closed.

### ③ Git provenance attacks

Positive control first, so that a rejection is not mistaken for a broken
harness:

| Case | Command intent | Observed |
|---|---|---|
| **G-BASE** | honest proxy delivery | **accepted**, exit 0, state `submitted` — harness is valid |
| G1 | `origin` repointed at `evil.git` | rejected: `Git remote URL mismatch: expected .../origin.git, observed .../evil.git` |
| G2 | commit exists locally, never pushed | rejected: `Remote ref 'refs/heads/main' advertises 53f6fc2…, not 772fe44…` |
| G3 | `git replace` swaps the honest commit's content | rejected: `Delivered artifact bytes differ from the Git blob for a.txt` |
| G4 | bind 1 of 2 pre-registered repo paths | rejected: `Proxy delivery must bind exactly the preregistered repository paths` |
| G4b | bind `a.txt` twice to fake the count | rejected: same message (duplicate detection works) |
| G5 | CRLF-tamper the delivered bytes **and re-stamp the manifest SHA** so only the blob check can catch it | rejected: `Delivered artifact bytes differ from the Git blob for a.txt` |
| G8 | `url.<evil>.insteadOf <good>` rewrite | rejected: `Git remote URL mismatch` — `git remote get-url` returns the *post-rewrite* URL, so the check and the transport agree; this is **not** a bypass |

G3 is worth spelling out. With the replacement ref active, plain git lies:

```
$ git -C work cat-file blob 53f6fc2:a.txt          -> alpha-evil
$ git -C work --no-replace-objects cat-file blob 53f6fc2:a.txt -> alpha
```

`provenance.py:47` passes `--no-replace-objects` on every invocation, so EFO
reads the real blob. This is correct and deliberate.

**All six attack vectors rejected. No P0/P1 in ③.**

### ④ v0.1 compatibility and post-handover behaviour

Wheel provenance, checked myself rather than taken from the fixture README:

```
sha256(tests/fixtures/evidence_first_orchestrator-0.1.0-py3-none-any.whl)
  = 18ed72c3f2ddf38a9a18d435032095cfbc074b2e21b9397d96e4a76b103b2354   (matches README)
```

Diffing the wheel's 14 modules against `git archive f827f29`:

| Module group | Result |
|---|---|
| `workspace.py`, `ledger.py`, `cli.py`, `evidence.py`, `adapter.py`, `doctor.py` | **byte-identical** (SHA-256 equal) |
| `__init__`, `__main__`, `archive`, `dashboard`, `errors`, `lock`, `model`, `util` | differ by **exactly one trailing newline**; equal after `rstrip()` |

Behaviour matrix (measured):

| Client | Workspace | Command | Result |
|---|---|---|---|
| v0.1 | v2, **pre**-handoff | `status` | `error: Agent 'antigravity' registration differs from the signed ledger`, exit 2 |
| v0.1 | v2, pre-handoff | `doctor` | `"healthy": false` |
| v0.1 | v2, pre-handoff | `ledger verify` | `valid: true`, exit 0 |
| v0.1 | v2, pre-handoff | `task show C1` | exit 0 |
| v2 | v2 | `workspace transfer-orchestrator --to codex` | exit 0, event `58f129a9…` |
| v0.1 | v2, **post**-handoff | `task add --actor antigravity` (deposed) | rejected, exit 2 |
| v0.1 | v2, post-handoff | `task add --actor codex` (new) | rejected, exit 2 |
| **v2** | v2, post-handoff | `task add --actor antigravity` (deposed) | rejected: `Only orchestrator 'codex' may perform this action` |
| **v2** | v2, post-handoff | `task add --actor codex` (new) | accepted, exit 0 |
| v2 | v0.1-created | `status` / `doctor` | exit 0 / `"healthy": true` |
| both | v2, post-handoff | `ledger verify` | identical head `773b616e…`, `valid: true` |

Authority resolution after the handoff:

```
config file orchestrator : antigravity
effective orchestrator   : codex
```

## 4. Known-answer comparison

| Check | Expected | Observed | Match |
|---|---|---|---|
| Suite result on Linux | 0 skips, 0 failures | 70 passed, 0 failed, 0 skipped, exit 0 | yes |
| Honest critical task w/ same-family verifier | rejected | rejected | yes |
| Same task after one declared-field change | *should still be rejected* | **accepted, exit 0** | **no** |
| `efo audit independence` on the forged history | flags it | `independent`, `action_required: 0` | **no** |
| Wheel SHA-256 vs README | `18ed72c3…2354` | `18ed72c3…2354` | yes |
| Wheel code vs `git archive f827f29` | identical | identical except 1 trailing `\n` in 8/14 files | partial |
| Honest proxy delivery | accepted | accepted, exit 0 | yes |
| G1–G5, G8 | each rejected | each rejected | yes |
| Deposed orchestrator post-handoff (v2) | rejected | rejected | yes |
| Old client post-handoff | fails closed | fails closed | yes |
| v2 reading a v0.1 workspace | works | `healthy: true`, exit 0 | yes |
| `.efo/workspace.json` after handoff | *undeclared* | still `antigravity` | see P2-1 |

## 5. Findings

### P1-1 — A one-command identity edit forges critical-tier independence, and `audit independence` calls the result clean

*measured.* `raw/raw-attack2.txt`, steps A2 / A4 / A6 / A7.

A `critical` task with three-dimension independence is correctly refused when
the author and verifier share a `model_family`. A single
`efo agent update --model-family gpt` makes the byte-identical `task add`
succeed, and the task then runs all the way to `task.verified` with
`claude-b` verifying `claude-a`.

The bypass itself is a known consequence of declarative identity, and
`docs/META_ORCHESTRATION_V2.md:69-72` says so. What is *not* covered by that
caveat is the second half of the same paragraph:

> "EFO can prove that the signed declaration did not change silently; it cannot
> prove that an operator told the truth about the underlying model."

Operationally the first clause does not hold. The mutation **is** recorded — at
ledger seq 7, six events before the verification at seq 13 — but no shipped
command surfaces the relationship. `efo audit independence`, the one command
whose purpose is retrospective independence review, returns
`status: "independent"`, `action_required: 0`. `ledger verify` returns
`valid: true`; `doctor` returns `healthy: true`. Reverting the declaration
afterwards changes nothing, because `audit_independence` prefers the
`frozen_verification` profile (`workspace.py:2366`) — so the forgery is opaque
both during and after.

An auditor who runs the audit gets an affirmative all-clear. That is worse than
no audit, and it is why I am scoring this P1 rather than P2.

Bounding: orchestrator-only. A worker cannot mutate any identity, cannot
self-verify, and cannot opt out of the critical-tier gates (all four probes in
§3). So this is an insider-orchestrator capability — which is precisely the
party the independence control exists to constrain in a four-agent setup where
Antigravity both assigns work and could route verification.

Suggested fix, cheap and local to `audit_independence`:

1. Freeze the ledger *sequence number* of the agent-profile version used, into
   the verification snapshot alongside the profile itself.
2. In the audit, for each `task.verified` record, scan `agent.added` /
   `agent.updated` events for the author and verifier. If any
   independence-relevant field changed between workspace init and that task's
   `task.created`, downgrade the record to `inconclusive` with a reason naming
   the mutating sequence — e.g. `"claude-b.model_family changed at seq 7 before
   this task was created"`.
3. Count those toward `action_required`, so the summary stops reading clean.

This keeps identity declarative, as designed, while making the declaration's
*history* load-bearing — which is what the documentation already promises.

### P2-1 — `workspace transfer-orchestrator` never updates the on-disk config

*measured.* `raw/raw-attack4.txt`, W6 / W6b.

After a signed handoff to `codex`, `.efo/workspace.json` still carries
`"orchestrator": "antigravity"`. Authority is derived by replaying the ledger
(`workspace.py:254-264`), and v2 uses the derived value everywhere it matters —
the deposed orchestrator is correctly refused, the new one accepted. So v2 is
internally sound.

The risk is any reader that trusts the config file. Today that is safe only
because v0.1 fails closed for an *unrelated* reason (P2-2). The protection is
incidental, not designed. Suggest either writing the derived orchestrator back
on transfer, or adding an explicit marker (e.g.
`"orchestrator_authority": "ledger"`) so a stale reader can tell the field is
not authoritative.

### P2-2 — v0.1 forward readability is narrower than the fixture README states

*measured.* `raw/raw-attack4.txt`, W3.

`tests/fixtures/README.md` says the compatibility tests "verify both forward
readability and the v0.1 client's fail-closed behavior after a signed v0.2
orchestrator handoff."

Measured: a v0.1 client cannot run `status` or `doctor` against a v2 workspace
**before any handoff at all** — v2 agent records carry `identity` and
`governance_epoch`, which v0.1's projection does not reproduce, so it raises
`Agent 'antigravity' registration differs from the signed ledger`. Forward
readability is real but limited to `ledger verify` and `task show`.

The consequence is that the post-handover fail-closed property, while true, is
vacuous: v0.1 was already closed. There is no test that would catch a future
change which restores v0.1 `status` and thereby reopens the handover question.
Suggest stating the actual scope in the README and adding a test that asserts
fail-closed *for a reason tied to the handoff*, not to record shape.

### P2-3 — the v0.1 wheel is not byte-reproducible from `f827f29`

*measured.* `raw/raw-attack4.txt`, W2 / W2b.

Eight of fourteen modules carry one extra trailing newline versus
`git archive f827f29`; content is equal after `rstrip()`, and all six
security-relevant modules are byte-identical. Nothing is wrong with the
fixture — but the README's provenance claim is verifiable only up to trailing
whitespace. Suggest recording the exact build command, or wording the claim as
content-identical.

### P2-4 — `core.autocrlf=true` makes an honest delivery fail with a tampering-shaped error

*measured.* `raw/raw-attack3.txt`, G6.

With `core.autocrlf=true`, a clean checkout produces `alpha\r\n` in the working
tree while the blob holds `alpha\n`, so an honest proxy submission is rejected
with the same message as the G5 tampering attempt. This is fail-closed and
therefore not a security defect, but a Windows-configured worker repo will hit
it, and the message points at tampering rather than at line-ending
normalisation. Suggest naming `core.autocrlf` / `.gitattributes` as a probable
cause in the error text.

### Confirmed working — no finding

*measured.* 70/70 tests, zero skips, Linux, exit 0 (①). All six Git provenance
vectors rejected with a passing positive control (③). `--no-replace-objects`
defeats replace-ref. Duplicate repo-path binding detected. `insteadOf` rewriting
is not a bypass. Worker-side identity mutation, gate opt-out, and self-verify
all blocked. v2 reads v0.1 workspaces cleanly. Both clients agree on the ledger
head hash after a handoff.

### Claims register

| # | Claim | Status |
|---|---|---|
| 1 | 70 tests pass, 0 skipped, exit 0, on `4aa47ca`, Linux | measured |
| 2 | Critical-tier 3-dimension independence rejects a same-family verifier | measured |
| 3 | One `agent update` flips that rejection to acceptance | measured |
| 4 | The forged task reaches `task.verified` | measured |
| 5 | `audit independence` reports `independent` / `action_required: 0` | measured |
| 6 | Reverting the declaration does not change the audit verdict | measured |
| 7 | Identity mutation is orchestrator-only | measured |
| 8 | G1–G5, G8 all rejected; G-BASE accepted | measured |
| 9 | Wheel SHA matches README; 6 core modules byte-identical to `f827f29` | measured |
| 10 | v0.1 fails closed on a v2 workspace both pre- and post-handoff | measured |
| 11 | Deposed orchestrator rejected by v2; new one accepted | measured |
| 12 | Config file orchestrator stale after handoff | measured |
| 13 | Whether any *other* EFO deployment relies on the stale config field | `[FILL]` — not measured, no other deployment available here |
| 14 | Behaviour under real network remotes (HTTPS/SSH) rather than local bare repos | `[FILL]` — `network: false` was pre-registered and not relaxed |
| 15 | Windows/macOS behaviour | `[FILL]` — Linux container only |
| 16 | Concurrency and lease behaviour under real multi-process load | `[FILL]` — not in scope for this review |

## 6. What I did not do, and could not verify

- **No PR action.** No approval, no merge, no review comment, no label. The
  verdict is *do not approve as-is*; posting it to the PR is outside the
  repository scope granted to this session and was not performed.
- **No server deploy, no orchestrator handover** — both explicitly prohibited.
  The handover in ④ was performed only inside a throwaway `/tmp` workspace.
- **No network remotes.** ③ used local bare repositories over `file://`.
  Authentication failures, redirect handling, and TOCTOU against a real remote
  between `ls-remote` and `cat-file` are unmeasured (`[FILL]`). The TOCTOU
  window is inherent to the design, not introduced by this PR.
- **No GPU, no performance measurement.** `gpu: false` and
  `performance_metrics: false` held throughout. This container has no GPU and no
  `torch`/`pytest`, so any timing or throughput claim would be unmeasurable.
  None is made.
- **Linux only.** P2-4 predicts a Windows failure from the mechanism; I did not
  run it on Windows.
- **I did not audit the full 6,207-line diff.** The review was scoped to the
  five assigned sub-tasks. Areas not examined include the adapter's Linux
  double-fork tracking, the GPU/repo resource-lock implementation, the dashboard
  changes, and `job_runner.py`.
- **SUBMITTED, not VERIFIED.** Every number above is my own measurement. I did
  not verify my own work; a third party reproducing `raw/attack2.sh` and
  `raw/attack3.sh` against `4aa47ca` is what would make this VERIFIED.

## Evidence manifest

All paths relative to this directory. Reproduce with
`sha256sum raw/*` from `reviews/efo-pr2-claude-b/`.

| Artifact | SHA-256 |
|---|---|
| `raw/raw-full-final.txt` | `3eb0af1acdc663cd9f4cff45ecd85a902009f3debdf7f7e69bc4b44a7b47e4fe` |
| `raw/raw-attack2.txt` | `bf77550793a94eecbf3cfd8bb8bbf4b8d0ca3a3bbc37afbdb957d50c8fb917df` |
| `raw/raw-attack3.txt` | `add26d91dd393693e2e59495d684962ac984bf985601207ad3743ad90eb45674` |
| `raw/raw-attack4.txt` | `20ef3693887c816a8329dd436ebee03ba4a959e2ac8ae3e7bea5567894ffd450` |
| `raw/attack2.sh` | `5204097f2b40588b6ae215e52d6e38fbdfe95e2593e95d0239b4f5cb4a745f67` |
| `raw/attack3.sh` | `4385fc9648480cb3ecd50b9b6a8d7bcb73ff854755e897f2427b977133d89547` |
| `raw/raw-attack2-cef5623.txt` | `2d82415ef4005a3273546bb1f2a46b58e801a949434523256b47b06fe3742dfc` |
| `raw/raw-recheck-cef5623.txt` | `3f5acae762e6460eb858ff32c8df6d39879aea9ed6c35f387ff40e7d5c502b81` |
| `raw/attack2_cef.sh` | `b46504a1393b0de30ac2b3d33fec43bbf9776bd587be489cea88b5f20e99c318` |
| `test_p1_1.py` | `3c9f3329ec84588de7bc5c658ca48435bbc59fce2d68a48bf241b9e25738d958` |
| `raw-p1-1-regression.txt` | `54487c46d7be2aed1b89b4d5a45484450f768a032aa9f22667eeadf843b21f1b` |

Subject under review: `heosanghun/evidence-first-orchestrator` @
`4aa47ca602d36c22cbaf2ce63fa442ee398c317e`, working tree clean.

`raw/attack2.sh` and `raw/attack3.sh` are self-contained and rerunnable; they
create and destroy their own workspaces under `/tmp` and touch nothing in either
repository. `raw-attack4.txt` was produced by the inline command blocks quoted
in §3 ④.
