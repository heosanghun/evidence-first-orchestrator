# The alias machinery holds at `main` `5694ab45` — no finding

I listed `alias_of` / `alias_chain` / `shared_alias_lineage` as unexamined in
issues #3, #4 and #5. It has now been examined. **Nothing here is a defect**, so
no issue was filed and nothing was commented anywhere; this note exists only so
the boundary is closed and nobody spends the hour again.

Reproduce with `raw/probe_alias_lineage.py`; raw output in
`raw/raw-alias-lineage.txt`.

## The guards fire

Each is stated expected/observed so a pass cannot be confused with a gate that
never ran.

| Guard | Observed |
|---|---|
| self-alias | rejected — `Agent cannot alias itself` |
| `alias_of` together with an explicit principal/family | rejected — `Alias identity inherits control principal and model family` |
| alias inherits the target's identity | `control_principal=openai model_family=openai-codex alias_chain=['t']` |
| cycle `t → x` while `x → t` | rejected — `Agent identity alias chain contains a cycle` |
| reparenting an already-attested alias | rejected — `An attested alias lineage cannot be removed or reparented` |

And the lineage comparison fires in both shapes that matter:

| Pair | Observed |
|---|---|
| a target versus its own alias | `independent=False`, reasons include `shared_alias_lineage` |
| two aliases of the same target | `independent=False`, reasons include `shared_alias_lineage` |

## The one asymmetry, and why it is not a finding

`evaluate_independence` (`independence.py:99-106`) builds each side's lineage as
`set(alias_chain) ∪ {actor}`. It never reads `alias_of`. Constructed directly,
two identities that both declare `alias_of="t"` with empty chains are reported
**`independent=True`, `reasons=[]`** — measured.

That state is not reachable through any supported write path. `_prepare_identity`
(`workspace.py:355-395`) always derives the chain from the target
(`alias_chain = [target_id, *target_identity["alias_chain"]]`) and both
`add_agent` and `attest_agent_identity` go through it. The probe tries it:
`add_agent(alias_of="t")` produces `alias_chain=['t']`, not an empty one.

So the asymmetry is defence-in-depth, not a bypass. Worth closing if the file is
touched anyway — `alias_of` could join the lineage union in one line — but it
does not justify a change on its own, and I am not proposing one.

The probe prints this as `!! UNEXPECTED !!` because its stated hypothesis was
"reachable = YES"; the hypothesis was **falsified**, which is the good outcome.

## Harness bug, caught before any conclusion

The first run reported 8 unexpected results. Six were mine: `check()` compared
expected and observed for exact string equality, so a guard that rejected *with
an explanatory message* did not match the bare string `rejected`. The comparison
is now a substring match and only the corrected run is reported. The two
remaining flags are the C section above, and neither is a defect.

## Scope

Only the alias machinery. Still unexamined on `main`: transport-attested
progress, proxy-status and monitor-collector code, and the `workspace.py`
lifecycle gates beyond the identity path. The open defects remain issues #3
(forged verifier independence), #4 (`git replace` forges byte-exactness) and #5
(never-pushed commit accepted when the tracking ref is absent).

Pre-registered permissions unchanged: `gpu: false`, `network: false`,
`performance_metrics: false`; gates `allow_skips: false`,
`require_validation: true`, `require_known_answer_check: true`,
`require_independent_verification: true`.

**SUBMITTED, not VERIFIED.**

| Artifact | SHA-256 |
|---|---|
| `raw/probe_alias_lineage.py` | `e9cd5a7a7f0df845d423b5f1fc5dccff2c7476373661172eaec3b8c818e94fb4` |
| `raw/raw-alias-lineage.txt` | `0182d4fc6e950d38758a17c7da265b0eb334ddff2c110bec7245a27963fd499b` |
