# Meta-Orchestration v2

This profile coordinates one Codex meta-agent, two Claude Code workers, and
Antigravity without pretending that different agent names guarantee independent
judgment.

## 1. Team roles

| Agent | Primary strengths | Default work | Must not be sole verifier for |
|---|---|---|---|
| `codex` | decomposition, integration, cross-model reproduction, final decisions | task graph, assignment, independent reproduction, adjudication | its own implementation |
| `claude-a` | long-context implementation, broad cross-file changes, documentation | bounded implementation and repair tasks | Claude-family output |
| `claude-b` | adversarial review, edge cases, regression and attack tests | pre-merge review and negative testing | Claude-family output |
| `antigravity` | experiment operations, provenance, data and GPU scheduling | preregistration, runtime operations, artifact custody, FACTS updates | Claude-family output when it also uses Claude Code |

Claude A and Claude B are operationally separated but share a model family.
Their review is useful and required for high-risk changes, but it does not
satisfy a task that requires `model_family` independence. Codex supplies the
cross-model check for Claude-family work. Claude B supplies the cross-model
check for Codex-authored control-plane work.

## 2. Separation of duties

| Work author | Required pre-review | Independent verifier/finalizer |
|---|---|---|
| Claude A | Claude B | Codex |
| Claude B | Claude A when practical | Codex |
| Antigravity | Claude B for reproducibility | Codex |
| Codex | Claude B | Claude B or Claude A |

The finalizer must be independent from the work author under every dimension
preregistered by the task. For critical control-plane work, use:

```text
actor + controller + model_family
```

`required_attestations` means additional reviewers before the final decision.
The finalizer is not allowed to count its own attestation twice and must always
submit its own independent verification manifest. With only one cross-model
verifier available, set the attestation count to zero and let that verifier
provide the finalization evidence.

The task author and proxy submitter must be distinct identities. A proxy may
retain verification eligibility because artifact custody is not authorship,
but the Git commit and every delivered byte must be bound in the signed record.

## 3. Failure modes and controls

| Failure mode | EFO control |
|---|---|
| Two names controlled by one process | `controller_id` independence |
| Same-model blind spot | `model_family` independence |
| Verifier role has no authority | `task attest` and verifier-authorized `task verify` |
| Meta-agent approves its own code | finalizer independence check |
| Cloud worker cannot reach EFO | preregistered `task proxy-submit`, online remote-head proof, author and proxy recorded separately |
| CRLF or archive conversion changes code | byte comparison against `git cat-file blob` |
| Two tasks edit/use the same scarce object | `resource_locks` held through verification |
| One agent silently accumulates tasks | `max_concurrency` |
| Wrong agent receives a task | `required_capabilities` checked at creation and claim |
| Any-GPU allocation | GPU permission requires an explicit `gpu:<index>` lock |
| Results are inspected before preregistration | `outcome_data=false` by default |
| Old aliases remain callable | signed agent profile update with `active=false` |
| Revoked process keeps using a GPU | Windows Job Object or serialized Linux subreaper + adapter-only execution token; `revoking` retains locks until termination is acknowledged |
| Linux worker escapes its process group | subreaper tracks `setsid()`/double-fork descendants; unconfirmed cleanup disables further broker execution |
| Orchestrator identity changes by file edit | signed `workspace.orchestrator_transferred` event |
| Past approval disappears after requeue | ledger-history `audit independence` |

Identity metadata is declarative. EFO can prove that the signed declaration did
not change silently; it cannot prove that an operator told the truth about the
underlying model. For high-risk work, retain the provider run ID or external
session record as provenance evidence.

## 4. Routing algorithm

Codex applies these filters in order:

1. Prerequisites are `verified` or `archived`.
2. The owner is active and has every required capability.
3. The owner is below `max_concurrency`.
4. No claimed, running, revoking, or submitted task holds a requested resource
   lock.
5. Allowed write roots do not overlap with an active change unless the task
   explicitly shares a read-only resource.
6. The verifier is allowed and independent under the task policy.
7. The task reveals only the data permitted before unblinding.

Among eligible agents, prefer the specialist role in the table above. Do not
use speed as a reason to weaken an evidence gate.

## 5. Risk tiers

| Tier | Examples | EFO-enforced minimum | Operating procedure |
|---|---|---|---|
| `low` | prose cleanup, deterministic formatting | normal evidence gates | one functional check |
| `medium` | isolated module or utility | independent finalizer | one independent reproduction |
| `high` | shared loader, evaluator, statistical code | named strict three-dimension finalizer | separate peer-review task |
| `critical` | EFO, metric headline, checkpoint selection, GPU launch | named strict three-dimension finalizer, zero skips | peer-review prerequisite and raw evidence retention |

No task may claim measured performance unless
`permissions.performance_metrics=true`. Reading outcome-bearing data before a
protocol is locked requires `permissions.outcome_data=true`.

## 6. Bootstrap an existing workspace

For a new workspace, start with `--preset meta-4-agent`. The preset leaves
Antigravity's provider and model family unknown on purpose; the operator must
declare the actual runtime identity before strict verification.

The current orchestrator performs profile registration and the signed handoff.
No other actor should issue these commands under the orchestrator's name.

Per-task prompt relay by the user is not part of steady-state operation. After
the signed profiles are registered, configure each provider CLI as a command
consumer using [Automated Agent Delivery](AUTOMATED_DELIVERY.md). Claude A must
remain `claude-a`; an idle Antigravity process does not authorize Claude A to
use the `antigravity` actor, report directory, lease, or verification power.

```bash
efo agent update /home/shoon/efo_ws \
  --actor antigravity \
  --id antigravity \
  --controller-id antigravity \
  --provider anthropic \
  --model-family claude-code \
  --capability experiment-ops \
  --capability data-audit \
  --capability gpu-schedule \
  --capability proxy_submit \
  --capability verify

efo agent update /home/shoon/efo_ws \
  --actor antigravity \
  --id codex \
  --controller-id codex \
  --provider openai \
  --model-family codex \
  --capability code \
  --capability meta-orchestrate \
  --capability research \
  --capability verify

efo agent add /home/shoon/efo_ws \
  --actor antigravity \
  --id claude-a \
  --role worker \
  --controller-id claude-a \
  --provider anthropic \
  --model-family claude-code \
  --capability code \
  --capability implementation

efo agent add /home/shoon/efo_ws \
  --actor antigravity \
  --id claude-b \
  --role verifier \
  --controller-id claude-b \
  --provider anthropic \
  --model-family claude-code \
  --capability adversarial-review \
  --capability regression-test \
  --capability verify
```

After the profiles and v2 executable are independently checked:

```bash
efo workspace transfer-orchestrator /home/shoon/efo_ws \
  --actor antigravity \
  --to codex \
  --reason "User appointed Codex as meta-orchestrator."
```

Immediately verify:

```bash
efo ledger verify /home/shoon/efo_ws
efo doctor /home/shoon/efo_ws
efo audit independence /home/shoon/efo_ws
```

Do not rewrite `.efo/workspace.json` or any historical ledger line.

## 7. Initial staged assignments

### Stage 0: control-plane review

`Claude B` reviews the EFO v2 branch as a Codex-authored critical change.
Required checks:

- run the full unit test suite with zero skips;
- attempt same-actor, same-controller, and same-model approval bypasses;
- reproduce wrong-remote, local-only commit, partial-scope, and CRLF
  Git-delivery failures;
- confirm legacy task projections and ledger signatures remain readable;
- verify that a verifier can finalize Codex-authored work while Codex cannot
  self-finalize under strict dimensions.

`Antigravity` performs an operational-only review:

- test the upgrade in a copy of the workspace;
- verify all existing task and agent projections;
- recover or explicitly close the expired `DRYRUN`;
- register profiles and perform the signed handoff;
- do not independently certify Claude-family code as cross-model evidence.

### Stage 1: reconcile existing work

1. Create a dedicated C1 delivery task that preregisters remote name, URL,
   full branch ref, complete repository paths, and resource locks; then
   proxy-submit the exact remotely advertised commit/blobs.
2. Let Codex independently reproduce C1 and finalize it.
3. Independently verify the submitted P1b-3 preregistration before creating
   P1b-4.
4. Run the retrospective independence audit and quarantine any historical
   approval that fails the new policy with `task invalidate`. Do not rewrite
   the old event.

### Stage 2: resume project work

Only after Stage 1:

- Claude A takes implementation tasks with disjoint write roots.
- Claude B receives adversarial review tasks, not a duplicate implementation.
- Antigravity schedules experiments only after code and protocol gates pass.
- Codex keeps the task graph, performs cross-model verification, and records
  final decisions.

## 8. Communication packet

Every assignment must include:

1. objective and explicit non-objectives;
2. owner and allowed write roots;
3. prerequisites and immutable acceptance gates;
4. permissions, including GPU/network/outcome access;
5. required capabilities and resource locks;
6. expected report and evidence paths;
7. named allowed verifier(s) and independence dimensions;
8. stop conditions and escalation path.

Narrative status messages are advisory. The signed EFO state and retained
evidence bundle are authoritative.
