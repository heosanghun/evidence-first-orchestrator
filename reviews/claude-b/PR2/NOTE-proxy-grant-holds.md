# The proxy grant at `main` `5694ab45` holds — no issue filed

Reproduce with `raw/probe_proxy_grant.py`; raw output in
`raw/raw-proxy-grant.txt`. **27 checks, 0 unexpected.** Section A is the
positive control — an honest end-to-end proxy submission, with a real Git
delivery repository — and every rejection is asserted on its *message*, by
substring.

This is a clean result. Nothing here is filed as an issue. It is recorded
because a component that survives a deliberate attempt to break it is a
measurement, and because two of the findings below narrow the exposure claimed
in issues already open.

## The positive control

| Probe | Observed |
|---|---|
| honest proxy submission | `state='submitted'`, `attempt=1` |
| authorship is the offline author | `actor='claude' method='proxy'` |
| transport recorded separately | `actor='antigravity'` |
| the grant is consumed | `consumed_at=True consumed_by='antigravity'` |
| doctor afterwards | `healthy=True` |

## Every grant gate fires, with the right message

| Probe | Observed |
|---|---|
| submit with no grant | `AuthorizationError: Task C1 has no proxy authorization` |
| a wrong token | `AuthorizationError: Proxy authorization token is invalid` |
| an author who is not the task owner | `Proxy author 'other' is not task owner 'claude'` |
| the transport submitting as itself | `An author must use the normal claim/start/submit path` |
| a second authorization while one is live | `TransitionError: Task already has an active proxy authorization` |
| a transport that is not the orchestrator | `Proxy transport must be the workspace orchestrator` |
| a report outside the transport's report directory | `Proxy report must be under the transport actor's report directory: …` |
| a provenance commit that does not exist | `Git provenance command failed (rev-parse --verify 000…^{commit}): fatal: Needed a single revision` |
| a real commit the grant does not name | `Git provenance commit differs from the proxy authorization` |
| **replay** — the same token twice | `Proxy authorization does not match this submission: next_attempt` |
| a token minted in a *different* workspace, both holding a live grant | `Proxy authorization token is invalid` |

Two of these are better than I expected going in.

**Replay is caught by the attempt binding, not by the state check.** I expected
`requires a pending task`. The grant carries `next_attempt`, `_require_proxy_grant`
compares it against `task["attempt"] + 1`, and a consumed grant therefore stops
matching *before* the state machine is consulted. That is the stronger of the
two orderings: it holds even if a task is somehow returned to `pending`.

**The cross-workspace test needed a live grant on both sides to mean anything.**
My first version authorized only in workspace A and read `has no proxy
authorization` from B — which proves nothing, since B had no grant to compare
against. Corrected so both workspaces hold a live grant for `C1`; A's token is
then refused on the token hash.

### One guard is unreachable, and that is fine

`workspace.py:745` refuses a grant whose task the transport owns. It cannot
fire: the transport must be the orchestrator, and an orchestrator cannot own a
task at all —

```
create_task(owner="antigravity") -> ConfigurationError: Task owner 'antigravity' is not a worker
```

Defence in depth, same shape as `archive.py`'s destination-collision guard.

## Provenance binds every claim-bearing file, not just artifacts

My first fixture bound only the artifact and was refused:

```
EvidenceError: Git provenance does not bind every claim-bearing evidence file:
  .../reports/antigravity/C1.raw.txt
```

Raw output has to be in the commit too. That is the doctrine enforced rather
than described, and it is worth stating because raw output is exactly the thing
a dishonest submission would prefer to leave unbound.

## The proxy path is stricter than the normal path on retention

This narrows issue #10. On the normal `submit` path an artifact larger than
`max_evidence_bytes` is accepted and left external (`retained: false`). On the
proxy path the same artifact never reaches archival at all:

```
EvidenceError: Git source blob exceeds the proxy verification limit:
  deliverables/C1.artifact.txt (52428801 > 52428800)
```

So a proxy bundle is always complete — measured `'external': 0` — and #10's
"an over-limit artifact can be deleted afterwards" observation applies only to
the normal submission path. The archived bundle is labelled `proxy-worker`,
filed under the grant's `next_attempt`, and carries the force-retained
provenance manifest beside the report, manifest, artifact and raw output.

## Issue #10 does extend here, and that is not a new finding

Rewriting the archived provenance manifest after the fact:

```
recorded sha = 3a6b15e3eb991786...
on-disk sha  = 9321954e9bf6900c...
ledger.verify() -> {'valid': True, 'events': 10, 'signed': True}
doctor          -> healthy=True
```

Same gap, same code path, already filed as #10. Recorded here as confirmation
that the proxy bundle is not separately covered; no second issue.

## `transport_independence` is computed and never read — deliberately not filed

`workspace.py:1184` evaluates author-versus-transport independence on every
proxy submission. Every mention of the name in the source tree, enumerated by
the probe rather than by reading:

```
workspace.py:1184        evidence["transport_independence"] = evaluate_independence(
workspace.py:1301                transport_independence = evaluate_independence(
workspace.py:1305                verification["transport_overlap"] = not transport_independence[
workspace.py:1308                verification["transport_independence"] = transport_independence
```

The three lines in `verify` are a *different* comparison — transport versus
verifier — and that one is surfaced as `transport_overlap`. The value computed
at 1184 is stored on the task and consulted by nothing. Measured: an offline
author attested into the orchestrator's own control principal and model family
submits successfully, with the record saying so —

```
state='submitted'
independent=False  reasons=['same_control_principal', 'same_model_family']
```

I am not filing this. `docs/ARCHITECTURE.md:131-136` argues that transport
overlap is acceptable because *"transport does not establish authorship and all
source bytes are commit-bound"*, and the property that actually matters —
author versus **verifier** — is enforced, and raises
(`workspace.py:1321-1325`). A dead field is worth a sentence to whoever owns
the file; it is not a defect, and filing it would be filing something the
project's own reasoning already answers.

The commit-bound half of that argument is weakened by issues #4 and #5, which
are open and say so. This note does not restate them.

## Harness bugs, caught before any conclusion

Five, all mine, only the corrected run reported. The preset already registers
`claude`, so the fixture attests rather than adds. Provenance must bind the raw
output, not only the artifact. `0`×40 as a commit is refused earlier, by
`rev-parse`, than the grant comparison I was aiming at. Replay is refused on
`next_attempt`, not on task state. And the cross-workspace test was meaningless
until both workspaces held a live grant.

## Scope

`authorize_proxy_submission`, `_require_proxy_grant`, `proxy_submit`, and the
archival call at `workspace.py:1220`. Not examined: `provenance.py` internals
beyond what issues #4 and #5 already cover, and concurrent proxy submissions
against one grant (the probe is single-threaded, and the second check happens
inside `_task_lock`).

Pre-registered permissions unchanged: `gpu: false`, `network: false`,
`performance_metrics: false`; gates `allow_skips: false`,
`require_validation: true`, `require_known_answer_check: true`,
`require_independent_verification: true`.

**SUBMITTED, not VERIFIED.**

| Artifact | SHA-256 |
|---|---|
| `raw/probe_proxy_grant.py` | `4e9d2a56baa0201bc009a2a20fa31b80aa1947780d3b8eeb130d597b15a89824` |
| `raw/raw-proxy-grant.txt` | `52cd79510bd1bc84cbabac7c96788eaef57a2bb52db195fc4eec8cc65e0e524c` |
