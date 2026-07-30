# Automated Agent Delivery

This guide removes the human operator from per-task prompt relay. The operator
performs one-time installation and authentication; after that, EFO delivers
role-bound tasks directly to each configured agent process.

## What automation requires

EFO can invoke an agent only when the provider exposes a CLI, API, or file
polling interface. It cannot wake a closed proprietary chat window. Interactive
chat agents therefore remain manual until they are replaced or accompanied by
an authenticated non-interactive runtime.

For Claude Code, use the official non-interactive `--print` (`-p`) mode. Install
and authenticate it using Anthropic's documentation:

- <https://docs.anthropic.com/en/docs/claude-code/getting-started>
- <https://docs.anthropic.com/en/docs/claude-code/cli-usage>

Do not store an API key, OAuth token, password, or SSH credential in an EFO
agent command. Agent commands are signed into the ledger.

## Bind the workspace before authentication

Before installing, authenticating, or starting a consumer, capture one
read-only identity packet:

```bash
efo workspace fingerprint /home/shoon/efo_ws
```

When reviewing an uninstalled checkout, bind the command to that exact source:

```bash
PYTHONPATH=/path/to/evidence-first-orchestrator/src \
  python3 -m evidence_orchestrator workspace fingerprint /home/shoon/efo_ws
```

Compare `hostname`, `user`, `runtime.efo_version`, `runtime.package_path`,
`workspace.workspace_id`, the canonical root path, ledger SHA-256 and head,
agent IDs, and task IDs with the approved baseline. Stop on any unexplained
difference. A valid signature proves one ledger is internally intact; it does
not prove that the operator opened the intended ledger.

Run provider authentication only in an operator-controlled terminal. Do not
wrap `claude auth login` in a script that captures stdout, and do not retain its
ephemeral authorization URL, state, or returned code in chat, an EFO report,
the ledger, or shell history. Open the URL in the operator's browser and enter
any returned code directly into the same live terminal process. If the URL was
logged, shared, or its waiting process ended, cancel that attempt and generate
a new one. Retain only the non-secret result of `claude auth status`.

## Identity is part of every prompt

The adapter renders the signed agent profile and current orchestrator profile
into every task prompt. The prompt explicitly says that the process:

- is only the registered task actor;
- cannot act or sign as the orchestrator or another worker;
- cannot treat submission as verification; and
- cannot independently finalize its own output.

This prevents a `claude-a` implementation worker from silently becoming
`antigravity`, even when both runtimes use the same model family.

## Configure Claude A and Claude B

Run these commands only as the current signed orchestrator. The two identities
may use the same installed Claude Code executable, but they keep separate task,
report, run, controller, and authorization records.

```bash
efo agent delivery /home/shoon/efo_ws \
  --actor codex \
  --id claude-a \
  --mode command \
  --prompt-stdin \
  --command-json '[
    "claude",
    "-p",
    "Execute the complete EFO task supplied on stdin. Obey its signed identity, permissions, write roots, gates, report path, and evidence path.",
    "--output-format",
    "text",
    "--max-turns",
    "80"
  ]'

efo agent delivery /home/shoon/efo_ws \
  --actor codex \
  --id claude-b \
  --mode command \
  --prompt-stdin \
  --command-json '[
    "claude",
    "-p",
    "Execute the complete EFO task supplied on stdin. Obey its signed identity, permissions, write roots, gates, report path, and evidence path.",
    "--output-format",
    "text",
    "--max-turns",
    "80"
  ]'
```

`--prompt-stdin` keeps the task body out of the process argument list. EFO sends
the generated prompt to the child process through standard input.

Do not use `--dangerously-skip-permissions`. Configure the provider's allowed
tools conservatively and use a separate OS account, container, or worktree for
hard filesystem isolation. EFO detects unauthorized writes inside its broker
workspace, but it cannot prevent a provider CLI from bypassing EFO and writing
elsewhere on the host.

## Run persistent consumers

Start one consumer for each identity:

```bash
efo worker loop /home/shoon/efo_ws \
  --agent claude-a \
  --poll-seconds 5

efo worker loop /home/shoon/efo_ws \
  --agent claude-b \
  --poll-seconds 5
```

Run the loops under a user service or another supervised process manager. Do
not launch them with an untracked shell background command. The service manager
should restart a failed loop, while EFO leases and recovery rules handle tasks
that were interrupted.

Once the consumers are running, the flow is:

1. the orchestrator creates a role-specific task;
2. the matching consumer atomically claims it;
3. EFO renders a self-contained, identity-bound prompt;
4. the provider CLI performs the task and writes the required report/evidence;
5. EFO submits the result; and
6. a separately authorized verifier reproduces and decides it.

No per-task copying or pasting by the user is required.

## Safe rollout

1. Verify the candidate EFO executable against a copy of the workspace.
2. Install and authenticate the provider CLI once.
3. Register `claude-a` and `claude-b` as distinct signed profiles.
4. Configure command delivery while neither agent owns an active task.
5. Run one read-only synthetic task per worker.
6. Confirm actor, controller, report path, and ledger events.
7. Start persistent consumers.
8. Transfer orchestrator authority only through the signed handoff command.

Keep Antigravity as a distinct agent. Never configure Claude A's command as the
Antigravity identity merely because the actual Antigravity consumer is idle.
