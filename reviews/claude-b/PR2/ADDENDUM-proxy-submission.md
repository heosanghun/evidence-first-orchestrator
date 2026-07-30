# Addendum — P1-1 survives `codex/proxy-submission`

Checked at `e2cf6b4b00d7bdff481e538c9aab786333a10d1c` (`codex/proxy-submission`,
branched off `main` at `f2cc922`, commits `41c4812 feat: enforce independent
verifier identities` and `e2cf6b4 feat: add transparent proxy submissions`).

That branch does **not** contain `cef5623`. It is an independent
reimplementation of the same controls, off the newer `main` — new
`independence.py` (281 lines) and a rewritten `provenance.py` (341 lines),
with its own `tests/test_independence.py` and `tests/test_proxy_submission.py`.
It has no open PR yet, which is why this is being filed now rather than after
one is opened.

**Finding: P1-1 reproduces, and the mutation now lands in a worse position.**

The API changed but the substrate did not. `agent update` is gone; the identity
write path is now `agent attest` / `attest_agent_identity`, still
orchestrator-only, and still free to rewrite `control_principal` and
`model_family` — only alias lineage is protected
(`workspace.py:398-444`). `resolve_identity_registry` reads the identity from
the mutable agent record and consults the signed policy **only as a fallback
when the agent has no identity at all** (`independence.py:128-146`), so a
policy declaration does not pin an agent that already has one.

| Step | Command | Observed |
|---|---|---|
| B3 | `claude-verifier` (declared identical to `claude`) verifies `claude`'s task | **rejected** — `Independent verification could not be established: same_control_principal, same_model_family` |
| B4 | `agent attest --control-principal openai --model-family openai-codex` | exit 0 |
| B5 | **byte-identical** verify replayed | **accepted, exit 0**, task state `verified` |
| B6 | `efo ledger audit-independence` | `checked: 1`, `independent: 1`, `non_independent: 0`, `findings[0].independent: true` |

Ledger positions (B7):

```
 5  agent.added              claude-verifier  control_principal=claude  model_family=anthropic-claude
 9  task.submitted
10  agent.identity_attested  claude-verifier  control_principal=openai  model_family=openai-codex
11  task.verified
```

This is sharper than on `cef5623`. There, the declaration change preceded task
creation. Here it lands at **seq 10 — after `task.submitted` at seq 9 and
immediately before `task.verified` at seq 11**, i.e. inside the task's own
lifetime, in the single most suspicious position available. The audit still
reports it independent, sourcing the verifier from
`verifier_identity_source: "verification_snapshot"` — the snapshot frozen from
the already-mutated declaration.

An audit that reads the ledger it is auditing has everything it needs here: the
attestation event sits between the submission and the verification of the very
task being judged. Flagging that case requires no new data, only the comparison.

## Suggested fix, unchanged in substance

`audit_verification_events` already receives the full event list. For each
`task.verified`, scan for `agent.identity_attested` on the worker or verifier
with a sequence between that task's `task.created` and its `task.verified`. If
one exists, the record is not `independent` — report it as inconclusive, name
the mutating sequence, and count it so the summary stops reading clean. The
in-lifetime case (seq 9 < 10 < 11) is the unambiguous one and is worth rejecting
outright rather than merely flagging.

## Scope and boundary

Only P1-1 was retested on this branch. The `provenance.py` rewrite is 341 lines
against the 193 reviewed in ③, so **the six Git provenance attacks were not
re-run here** and their earlier "all rejected" result does not transfer. The
alias/`alias_chain` machinery and `shared_alias_lineage` are new and were not
examined at all.

Suite at `e2cf6b4`: 67 tests, OK, 0 skipped, exit 0 — measured, `raw/raw-proxy-suite.txt`.

**SUBMITTED, not VERIFIED.** `raw/attack_proxy.sh` is self-contained and rerunnable;
it creates and destroys its own workspace under `/tmp`.

## Evidence

| Artifact | SHA-256 |
|---|---|
| `raw/attack_proxy.sh` | `5c177cd7254192b529dd62c00a6b654d3707bb7d4eca4cf2feef274917e2fd70` |
| `raw/raw-attack-proxy.txt` | `c8b8d1af8285ee7418c7a773973289f9dc0c8fd7279dc01188ca7a04a8f3f368` |
| `raw/raw-proxy-suite.txt` | `881a7ea3f7afe3bb76a8e540334eb2dd3df7f0de23ff9cf4aaa5353f4327fabd` |

One harness bug of mine was caught before any conclusion was drawn: the first
run of B5 failed with `Independent verification manifest is required`, which is
a different gate than the one under test. The verifier evidence manifest was
added and the whole script re-run; only the corrected run is reported.

---

## Escalation: P1-1 is now on `main`

`codex/proxy-submission` was merged. `main` is now
`f35d5176d97337b8f41555b5d8af08bc4f4167a7`, and the only commit added between
the branch state reviewed above and the merge is `f35d517 fix: serialize task
projection reads during claim` — a concurrency fix. `independence.py` is
**unchanged**; `audit_verification_events` was not touched.

Re-run against `main` at `f35d5176`, measured, not inferred:

| Step | Observed at `f35d5176` |
|---|---|
| B3 honest verify by a same-identity verifier | rejected — `same_control_principal, same_model_family` |
| B4 `agent attest --control-principal openai --model-family openai-codex` | exit 0 |
| B5 byte-identical verify replayed | **accepted, exit 0**, state `verified` |
| B6 `ledger audit-independence` | `checked: 1`, `independent: 1`, `non_independent: 0` |
| B7 ledger | attestation at seq 10, between `task.submitted` (9) and `task.verified` (11) |

Suite at `f35d5176`: 67 tests, OK, 0 skipped, exit 0.

`raw/raw-attack-main.txt` is byte-identical to `raw/raw-attack-proxy.txt`
because the script emits no absolute paths. They are separate runs: distinct
workspaces (`wsm` vs `wsp`), timestamps 66 minutes apart, and `REPO` pointing at
`/tmp/efo-main` (`f35d517`) versus `/tmp/efo-proxy` (`e2cf6b4`). The module was
confirmed to resolve from `/tmp/efo-main/src/` for the `main` run.

| Artifact | SHA-256 |
|---|---|
| `raw/attack_main.sh` | `e285e1b30311d80f05a3082fdad63ab4803910fa12462a1ff3bc1f8ff5840b78` |
| `raw/raw-attack-main.txt` | `c8b8d1af8285ee7418c7a773973289f9dc0c8fd7279dc01188ca7a04a8f3f368` |
| `raw/raw-main-suite.txt` | `051b79ea49a522e24da66344b673800d901c60f8a054287e9fb7e2d3f14736fd` |

---

## Re-confirmed at `main` = `31705d5d` (issue #3 was filed against `f35d5176`)

`main` has advanced twice since issue #3 was filed, both times without touching
the finding:

- `f2cc922 → f35d5176` — `codex/proxy-submission` merge (the reviewed work).
- `f35d5176 → 31705d5d` — `9b9e0c5 feat: add transport-attested worker progress`,
  `4871867 fix: expire proxy status and reject forged projections`,
  `31705d5 fix: align monitor task projection contract`.

`src/evidence_orchestrator/independence.py` is **untouched** across both, and a
diff-wide grep for `audit_verification_events` and `identity_attested` over
`f35d5176..31705d5d` returns **0 hits**. Note that `4871867`'s "reject forged
projections" is about task projections, not identity declarations — it does not
reach this path.

Measured at `31705d5d`, not inferred:

| Step | Observed |
|---|---|
| B3 honest verify by a same-identity verifier | rejected — `same_control_principal, same_model_family` |
| B5 byte-identical verify after `agent attest` | **accepted, exit 0**, state `verified` |
| B6 `ledger audit-independence` | `checked: 1`, `independent: 1`, `non_independent: 0` |

Suite at `31705d5d`: **79 tests, OK, 0 skipped, exit 0** — up from 67, so the
twelve new tests do not cover this case either.

Run binding, since the raw output again hashes identically to the earlier runs
(the script emits no absolute paths): workspace `wsm2`, timestamp
`2026-07-30 12:16:48Z`, `REPO=/tmp/efo-main2`, and the module confirmed
resolving from `/tmp/efo-main2/src/evidence_orchestrator/__init__.py`.

| Artifact | SHA-256 |
|---|---|
| `raw/attack_main2.sh` | `62aa3ada8737ae7579046b8502c26ee66a637f6ddf34ffd4dbeddde773cddf42` |
| `raw/raw-attack-main2.txt` | `c8b8d1af8285ee7418c7a773973289f9dc0c8fd7279dc01188ca7a04a8f3f368` |
| `raw/raw-main2-suite.txt` | `03551fe32b11ba02b28ae0b1f9ca6bc7ae18117464150dee5c84defea42565b6` |
