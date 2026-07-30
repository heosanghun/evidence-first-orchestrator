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
  --preset meta-4-agent
```

Keep the existing Markdown inboxes read-only from EFO's perspective. Add new
tasks to the broker while agents finish already claimed legacy work.

Do not automatically translate historical `DONE` lines to `VERIFIED`. Import
them as provenance notes or leave them in the legacy archive until independently
rechecked.

Proxy delivery is fail-closed for legacy tasks because their expected remote,
ref, and complete source path set were not frozen at creation. Create a new,
dedicated delivery task with `--allow-proxy-delivery`,
`--proxy-remote-name`, `--proxy-remote-url`, a full `refs/heads/...`
`--proxy-ref`, and every `--proxy-repo-path`; do not retrofit those values into
an old task projection. The orchestrator must be able to authenticate to the
remote because proxy submission checks its advertised branch head online.

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

## Phase 3: declare identities and move task control

Register controller, provider, model family, capabilities, and concurrency
before relying on cross-agent verification. Different names alone are not an
independence boundary. Existing registrations can be amended through signed
`agent update` events.

The orchestrator remains the only task creator. Independent verifier agents can
attest and finalize work when the task policy allows them:

```bash
efo task add "E:\\agent-broker" \
  --actor antigravity \
  --id NEW-1 \
  --owner codex \
  --title "First brokered task" \
  --description-file task.md \
  --resource-lock repo:project
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

If the meta-orchestrator changes, use a signed handoff after testing the new
EFO executable against a copy of the workspace:

```bash
efo workspace transfer-orchestrator "E:\\agent-broker" \
  --actor antigravity \
  --to codex \
  --reason "Approved meta-orchestrator handoff"
```

Never edit `workspace.json` to change authority.

After upgrading, run `efo audit independence`. The audit walks historical
verification events, including attempts later invalidated and requeued.
Event-time identities that cannot be established remain `inconclusive` and
make `doctor` unhealthy until the attempt is explicitly reviewed or
quarantined.

The repository retains the exact v0.1.0 wheel as a compatibility fixture. The
v0.2 test suite creates a workspace with that wheel, opens and transitions it
with v0.2, then confirms that the preserved v0.1 client fails closed after a
signed orchestrator handoff.

## Recommended ownership

| Actor | Broker actions | Project writes |
|---|---|---|
| Codex meta-agent | create, recover, requeue, cross-model verify, archive | task graph and Codex-owned work |
| Claude A | claim, start, heartbeat, block, submit | implementation |
| Claude B | attest, adversarial review, regression tests | verifier-owned reports and tests |
| Antigravity | experiment operations, provenance, proxy delivery | shared facts and experiment records |

Workers should never be assigned overlapping write roots or resource locks. A
dependent task should name the earlier task as a prerequisite instead of
editing the same files concurrently. See
[Meta-Orchestration v2](META_ORCHESTRATION_V2.md) for the full four-agent
profile.
