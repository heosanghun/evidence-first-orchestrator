# Issue #3 re-run at `main` `5694ab45` — still reproduces; the alias machinery it left open is clean

Reproduce with `raw/probe_independence_audit.py`; raw output in
`raw/raw-independence-audit.txt`. **18 checks, 0 unexpected.**

Issue #3 was measured at `f35d5176`. `main` is now `5694ab45`, and #3's own
*Scope and boundary* section says the `alias_of` / `alias_chain` /
`shared_alias_lineage` machinery was new and unexamined at the time. This
closes those open items and re-runs the finding itself.

No new issue is filed — this is the same finding at a newer commit, and it
belongs as a comment on #3.

## Positive control

An honestly independent verifier is accepted, the audit reports it
independent, and both sides are sourced from the recorded snapshots:

```
verify              -> accepted (verified)
audit-independence  -> checked=1 independent=1 non_independent=0
                       worker=submission_snapshot verifier=verification_snapshot
```

## #3 still reproduces, verbatim

| Step | Observed at `5694ab45` |
|---|---|
| a verifier declared identical to the worker verifies | **rejected** — `Independent verification could not be established: same_control_principal, same_model_family` |
| `attest_agent_identity(claude-verifier, openai, openai-codex)` | accepted |
| the byte-identical verification, replayed | **accepted**, `verified` |
| `audit-independence` | `checked=1 independent=1 non_independent=0` |
| the verifier's identity source | `verification_snapshot` |

The mutating event still sits inside the task's own lifetime, which is what
made #3 worth filing:

```
  5  agent.identity_attested    antigravity
 10  task.submitted             claude
 11  agent.identity_attested    antigravity      <- the mutation
 12  task.verified              claude-verifier
```

`submitted < attested < verified` → **True**.

The reason is unchanged and now measured directly rather than argued: the audit
never looks at attestation events at all. Every event action the module
mentions, extracted from the source rather than read off:

```
if event.get("action") in {"task.submitted", "task.proxy_submitted"}:
if event.get("action") != "task.verified":
```

and `identity_attested` does not appear anywhere in `independence.py`.

So #3's suggested fix — for each `task.verified`, look for an
`agent.identity_attested` on the worker or verifier whose sequence falls inside
that task's lifetime — has not been applied, and nothing else was substituted
for it.

## #3's secondary claim also holds

#3 noted that `resolve_identity_registry` consults the signed policy *only* as a
fallback for agents with no identity, so a policy cannot pin an agent that
already has one. Measured both directions:

| Probe | Observed |
|---|---|
| a policy naming an agent that **already has** an identity | ignored — `control_principal=openai`, the mutated value |
| the audit run with that policy | still `checked=1 independent=1 non_independent=0` |
| a policy naming an agent with **no** identity | applied — `control_principal=mistral` |

An auditor who tries to pin the verifier through the policy gets the same clean
all-clear. The policy is still not a mitigation for this.

## The alias machinery #3 left unexamined is clean

This is new ground, and nothing is wrong with it:

| Probe | Observed |
|---|---|
| a verifier registered as `alias_of="claude"` (the worker) verifying | **rejected** — `same_control_principal, same_model_family, shared_alias_lineage` |
| a three-deep chain `leaf → mid → root` | resolves to the root's principal, `chain=['mid', 'root']` |
| an alias cycle `a → b → a` | `ConfigurationError: Identity policy alias cycle: a -> b -> a` |
| an alias pointing at an agent with no identity | resolves to `None`, so `evaluate_independence` refuses — conservative |

An alias cannot be used to launder a verifier past the check, and the lineage
reason is reported alongside the principal and family ones rather than instead
of them.

## One more thing the audit gets right

A `task.verified` with no matching `task.submitted` falls back to the task
owner's *current* identity — and **says so**:

```
worker_identity_source = signed_agent_identity   (not submission_snapshot)
```

The fallback is disclosed rather than silent, which is the right shape and the
opposite of the failure #3 is about.

## Scope

`audit_verification_events`, `resolve_identity_registry`, `build_identity`,
`identity_snapshot`, `evaluate_independence`, and the `verify` gate that
consumes them. Not examined: `_resolve_signed_identity_registry` in
`monitor/collector.py`, which is a separate implementation of the same idea.

Pre-registered permissions unchanged: `gpu: false`, `network: false`,
`performance_metrics: false`; gates `allow_skips: false`,
`require_validation: true`, `require_known_answer_check: true`,
`require_independent_verification: true`.

**SUBMITTED, not VERIFIED.**

| Artifact | SHA-256 |
|---|---|
| `raw/probe_independence_audit.py` | `d24ff5303811a197af0676eff03f2233133f7312cea0b83d527ed515e9fa29a1` |
| `raw/raw-independence-audit.txt` | `1c8004fe44e6356b2172a11edd3d14dccbd56be89bea8c3c90977d09ee459c30` |
