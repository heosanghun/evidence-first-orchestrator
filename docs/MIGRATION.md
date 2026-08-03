# Migration Guide

This guide moves an existing Markdown inbox protocol to EFO without interrupting
active work.

## Phase 0: freeze credentials

Before copying or publishing the shared workspace:

1. remove plaintext passwords, API keys, and access tokens;
2. rotate any credential that was stored in a shared Markdown file;
3. pass credentials through environment variables, an SSH agent, or an OS
   secret store;
4. do not copy credential-bearing environment documents into Git.

Run the read-only audit:

```bash
efo legacy audit "E:\\path\\to\\legacy-workspace"
```

## Phase 1: dual-run without changing active files

Create the broker next to, not inside, the active workspace:

```bash
efo init "E:\\agent-broker" \
  --name "Research collaboration" \
  --control-principal antigravity-control \
  --model-family antigravity-runtime \
  --preset antigravity-codex-claude
```

Keep the existing Markdown inboxes read-only from EFO's perspective. Add new
tasks to the broker while agents finish already claimed legacy work.

Do not automatically translate historical `DONE` lines to `VERIFIED`. Import
them as provenance notes or leave them in the legacy archive until independently
rechecked.

## Phase 2: verify agent access

Run the optional write check from inside each agent's own execution context:

```bash
efo legacy audit "E:\\path\\to\\legacy-workspace" \
  --agent codex \
  --write-test
```

The check writes and removes one temporary file only in
`reports/<agent>/`.

For a remote server, record a read-only identity probe as task evidence. A
typical probe includes:

- hostname;
- repository commit;
- artifact directory sample;
- accelerator index and UUID inventory.

Use SSH keys or an agent. Do not place passwords in commands, prompts, reports,
or EFO configuration.

Before accepting new work, attest every legacy agent's controller and model
family. Aliases inherit the identity of their root:

```bash
efo agent attest "E:\\agent-broker" \
  --actor antigravity \
  --id codex \
  --control-principal codex-control \
  --model-family openai-codex

efo agent attest "E:\\agent-broker" \
  --actor antigravity \
  --id codex-helper \
  --alias-of codex
```

Audit prior verification events separately. The optional policy is read-only
and does not authorize future work:

```bash
efo ledger audit-independence "E:\\agent-broker" \
  --identity-policy legacy-identities.json
```

## Phase 3: move task control

The orchestrator remains the only task creator. Register at least one verifier
with a different control principal and model family from each worker it reviews:

```bash
efo agent add "E:\\agent-broker" \
  --actor antigravity \
  --id claude-verifier \
  --role verifier \
  --control-principal claude-b-control \
  --model-family anthropic-claude
```

Then create the task:

```bash
efo task add "E:\\agent-broker" \
  --actor antigravity \
  --id NEW-1 \
  --owner codex \
  --title "First brokered task" \
  --description-file task.md
```

Workers use manual claim/start/submit commands, or command adapters if their
installed CLI supports non-interactive execution.

Workers that can publish Git but cannot connect to the workspace must not have
their commands replayed with a forged `--actor`. Use a one-time proxy grant and
the explicit transport path instead:

```bash
efo task proxy-authorize "E:\\agent-broker" \
  --actor antigravity \
  --id C1 \
  --transport-actor antigravity \
  --remote-url https://github.com/example/project.git \
  --branch claude/C1 \
  --commit FULL_COMMIT_OBJECT_ID

efo task proxy-submit "E:\\agent-broker" \
  --actor antigravity \
  --author claude \
  --id C1 \
  --proxy-token ONE_TIME_TOKEN \
  --report "E:\\agent-broker\\reports\\antigravity\\C1.md" \
  --evidence "E:\\agent-broker\\reports\\antigravity\\C1.evidence.json" \
  --provenance "E:\\agent-broker\\reports\\antigravity\\C1.provenance.json" \
  --source-repository "E:\\deliveries\\C1"
```

The transport envelope belongs under the transport actor's report directory.
Its claim-bearing files must be byte-identical to raw Git blobs. Do not copy
them through a text-mode tool. See
[Transparent Proxy Submission](PROXY_SUBMISSION.md).

Keep `shared/FACTS.md` as a human-readable source during the transition. Once
stable, store each proposed fact as a task claim with its evidence; update the
human document only after the task reaches `VERIFIED`.

## Phase 4: retire shared multi-writer logs

Stop appending to the legacy `logs/EVENTS.md`. The signed EFO ledger becomes the
machine source of truth. Export a human-readable activity summary when needed
instead of letting multiple processes append to one Markdown file.

## Recommended ownership

| Actor | Broker actions | Project writes |
|---|---|---|
| Antigravity | create, recover, requeue, attest identities, archive | shared facts and task definitions |
| Codex | claim, start, heartbeat, block, submit | Codex-owned implementation and reports |
| Claude Code | claim, start, heartbeat, block, submit | Claude-owned implementation and reports |
| Independent verifier | reproduce, accept, or reject | verifier-owned reports only |

The two workers should never be assigned overlapping write roots. A dependent
task should name the earlier task as a prerequisite instead of editing the same
files concurrently.
