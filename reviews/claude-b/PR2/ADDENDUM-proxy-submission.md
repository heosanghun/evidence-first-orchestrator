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
