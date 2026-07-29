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

## Phase 3: move task control

The orchestrator becomes the only creator and verifier:

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
| Antigravity | create, recover, requeue, verify, archive | shared facts and task definitions |
| Codex | claim, start, heartbeat, block, submit | Codex-owned implementation and reports |
| Claude Code | claim, start, heartbeat, block, submit | Claude-owned implementation and reports |

The two workers should never be assigned overlapping write roots. A dependent
task should name the earlier task as a prerequisite instead of editing the same
files concurrently.
