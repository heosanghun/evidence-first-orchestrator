# Two implementations of agent identity at `main` `5694ab45` — they diverge on 8 of 12 shapes, always in the safe direction; no issue filed

Reproduce with `raw/probe_identity_two_impls.py`; raw output in
`raw/raw-identity-two-impls.txt`. **7 checks, 0 unexpected**, plus a 12-row
head-to-head table.

`independence.py::resolve_identity_registry` decides who is independent of whom
for the verification gate. `monitor/collector.py::_resolve_signed_identity_registry`
decides the same thing again, separately, for the dashboard. Two
implementations of one security-relevant idea is the shape that drifts quietly,
so this runs both over one corpus.

## Positive control

On a real workspace with an attested worker and an alias of it, both resolve
identically:

```
claude        agree: True   anthropic/anthropic-claude chain=[]
claude-alias  agree: True   anthropic/anthropic-claude chain=['claude']
collector groups the alias with its root: ['claude', 'claude-alias']
```

## Head to head

| Shape | `independence.py` | `collector.py` |
|---|---|---|
| an honest non-alias | `openai/openai-codex chain=[]` | same |
| an honest alias | `openai/openai-codex chain=['root']` | same |
| **an alias whose declared chain is wrong** | repaired → `chain=['mid', 'root']` | **rejected** |
| **an alias declaring a different principal from its target** | repaired → `openai/openai-codex` | **rejected** |
| **a non-alias carrying a non-empty `alias_chain`** | kept → `chain=['ghost']` | **rejected** |
| **an identity with an extra key** | accepted | **rejected** |
| **`schema_version: 2`** | accepted | **rejected** |
| **an alias cycle** | **raises** `ConfigurationError` | rejected |
| **a self-alias** | **raises** `ConfigurationError` | rejected |
| an alias to an agent that does not exist | `none` | rejected |
| **`agent_id` inside its own `alias_chain`** | repaired → `chain=['root']` | **rejected** |
| no identity at all | `none` | rejected |

**8 disagreements, and the collector is stricter in every one.**

## Why none of them is a defect

The important row is the fourth. An alias that *declares* a different principal
from its target does not get to keep the lie — `independence.py` rebuilds the
identity from the target (`independence.py:161-168`), so the declared
`anthropic/anthropic-claude` becomes the target's `openai/openai-codex`. The
repair runs toward the truth, not away from it.

The same holds for the other repairs. A wrong declared chain is replaced with
the real one. A self-reference inside `alias_chain` is dropped. A bogus chain
on a non-alias is kept as declared — which can only manufacture false
`shared_alias_lineage` matches, i.e. make two agents look *less* independent.
Every divergence where `independence.py` is more permissive about the
*declaration* still produces a verdict that is equal or more conservative about
*independence*, which is the property that matters.

The extra-key and `schema_version: 2` rows are the weakest of the eight:
`independence.py` reads the fields it wants and ignores the rest, so a future
schema would be silently consumed under old semantics. Worth a line to whoever
owns the file; not a finding today, since `build_identity` is the only writer
and it emits exactly version 1.

Two rows are worth naming for a different reason. A cycle or self-alias makes
`independence.py` **raise**, which would abort `audit_independence` entirely
rather than report — fail-closed but noisy. Neither is reachable through the
API (`add_agent` and `attest_agent_identity` both refuse a cycle, and agent
records are ledger-bound), so this is recorded, not filed.

## The gate the collector has and the core does not

```
collector, ledger_valid=False  -> registry = {}
independence.py                -> no such parameter; resolves anyway
```

Not a defect either way. `audit_independence` calls `self.ledger.verify()`
immediately before `resolve_identity_registry` (`workspace.py:1488`), so the
core relies on its caller. The collector cannot — it reads the ledger through
the CLI, so it carries the check itself and fails safe by making everything
unattributed.

## `task_actor_ids` is stricter than the audit, deliberately

Attribution compares the identity snapshot frozen at verification time against
the *currently* resolved registry, by exact dict equality:

| Probe | Observed |
|---|---|
| a verification whose snapshot matches the registry | `{'claude'}` |
| one whose snapshot no longer matches | `claude present: False` |

So the dashboard drops an actor whose identity has been re-attested since the
verification it is being credited for — precisely the mutation issue #3 is
about, where `audit_verification_events` instead trusts the frozen snapshot and
reports clean. The two components disagree about the same event. For
*attribution*, the strict reading is the safe one, and I am not proposing the
collector change; the divergence is recorded because it shows the strict check
is already written, in this repository, by the same authors.

## Why this is worth writing down at all

Nothing here is broken. What is worth recording is that one idea has two
implementations whose rules already differ on two thirds of the shapes tested,
and that the stricter one lives in the component with the *lower* security
stake. A future edit to either will not be checked against the other by
anything in the test suite — there is no test that runs both over one corpus,
which is why this probe exists.

## Scope

`_resolve_signed_identity_registry`, `resolve_signed_identity_groups`,
`task_actor_ids`, and `resolve_identity_registry` / `build_identity`. Not
examined: `collect_project_portfolios`' use of the groups beyond issue #6, and
`_policy_agents` beyond what the #3 comment already measured.

Pre-registered permissions unchanged: `gpu: false`, `network: false`,
`performance_metrics: false`; gates `allow_skips: false`,
`require_validation: true`, `require_known_answer_check: true`,
`require_independent_verification: true`.

**SUBMITTED, not VERIFIED.**

| Artifact | SHA-256 |
|---|---|
| `raw/probe_identity_two_impls.py` | `268e9073f0186ea916099535a335493d7e2fde59998819efbf103575ece417a0` |
| `raw/raw-identity-two-impls.txt` | `8c800ca119e9a40d8e97aeb4798b19df2dfb47ba31eb5cc15815ccf2a4606490` |
