# Operations Dashboard

The web dashboard is a sanitized operations view for Evidence First
Orchestrator and the System 1.5 GPU server. It is designed for desktop and
mobile browsers and updates every 15 seconds from a snapshot collected every
120 seconds.

## Trust boundary

The browser never connects to SSH. The data path is:

```text
SSH server read-only collector
  -> HMAC-signed HTTPS POST
  -> Cloudflare Pages Function
  -> Cloudflare KV latest snapshot
  -> browser GET /api/snapshot
```

The function rejects a snapshot containing a key named `password`, `secret`,
`token`, `environment`, `env`, `command`, `cmdline`, `pid`, `uuid`, `ssh`, or
`authorization`, including nested values. The collector uses process IDs and
GPU UUIDs only for local correlation and removes them before serialization.

The hourly activity view is a bounded projection of the signed EFO ledger. It
keeps at most 300 recent events and exposes only:

- event sequence and timestamp;
- a configured display alias for the actor;
- the state-transition action and display category;
- task ID and title.

It never exports the ledger payload, description, previous/event hash,
signature, lease data, report paths, evidence paths, or signing key. The
dashboard groups this projection into one-hour buckets for selectable 24-hour,
72-hour, and 7-day views.

Displayed progress is an **EFO workflow-phase indicator** derived from task
states. It is not model accuracy, training completion, or a scientific
performance result.

The optional `project_portfolios` collector configuration freezes each
project's denominator as an explicit list of EFO task IDs. A configured task
that does not exist yet remains at zero percent and is not silently removed.
This lets the top portfolio show CTS and System 1.5 without implying that a
verified preparatory task equals a successful model result. The public
projection contains only sanitized labels, state counts, workflow progress,
and GPU indexes with an actually active mapped workload.

The Pages content security policy intentionally rejects inline styles. All
percentage fills use native `<progress>` elements styled by the external
stylesheet; resource rings use SVG attributes; hourly bars use SVG geometry.
Do not add `unsafe-inline` to make a visual fill work.

## Read-only operations chat

The bottom of the dashboard contains a Korean-language Codex operations
assistant. It is deliberately not a command channel and is not connected to a
private Codex desktop conversation. Every answer is grounded in the latest
sanitized snapshot stored in `EFO_MONITOR_KV`.

The chat has two explicit modes:

- **Live snapshot** is always available. It deterministically reports project
  workflow progress, agent assignments, blocked tasks, next milestones, and
  active GPU mappings without using a model API.
- **OpenAI + live snapshot** is optional. It sends a bounded sanitized
  projection to the OpenAI Responses API for more flexible conversation. If
  that request fails, the endpoint returns the deterministic snapshot answer
  instead.

The optional model path is disabled unless all three controls are present:

```text
OPENAI_API_KEY      encrypted Pages secret
EFO_CHAT_ENABLED    exact value "true"
EFO_VIEW_TOKEN      dashboard access protection enabled
```

This prevents a public, unprotected dashboard from becoming an unbounded paid
model endpoint. `EFO_CHAT_MODEL` can override the cost-sensitive default
`gpt-5.6-luna`. The browser keeps at most 20 messages in session storage and
sends at most eight prior messages. The server accepts a 1,500-character
question, never stores the conversation, sets `store=false` on model requests,
and sends a privacy-preserving safety identifier.

The model receives no SSH credentials, secrets, process IDs, commands, full
ledger payloads, or mutation tools. Requests to start, stop, delete, deploy, or
change work are answered as read-only requests and are not executed.

## Local Windows workstation load

The optional local collector uses built-in PowerShell and CIM only. It reports
an alias, aggregate CPU and memory use, C: drive pressure, uptime, and a process
count. It never reports the Windows username, hostname, process names, command
lines, file paths, open documents, or application contents.

The displayed "operational fatigue" value is a reproducible composite:

```text
35% CPU use
40% memory use
15% disk pressure, scaled from 0 at 70% full to 100 at 100% full
10% uptime pressure, scaled from 0 at 24 hours to 100 at seven days
```

The endpoint applies a 70/30 exponential smoothing step only when consecutive
samples belong to the same recent boot session. A reboot resets smoothing.
The labels are low (<40), moderate (40-69.9), high (70-84.9), and critical
(>=85). This is an operations signal, not a medical stress score, hardware
health test, or lifespan estimate. Disk and memory percentages remain visible
beside the composite so the user can inspect the cause.

Create a separate secret from the SSH collector secret:

```powershell
$root = "$env:LOCALAPPDATA\EFO Monitor"
New-Item -ItemType Directory -Force $root
Copy-Item monitor\local-windows.config.example.json "$root\config.json"
# Put the same 32+ character random value used for the encrypted
# EFO_LOCAL_INGEST_SECRET variable in "$root\ingest-secret".
```

Verify a local sample without sending it:

```powershell
.\monitor\collect_local_windows.ps1 `
  -Config "$env:LOCALAPPDATA\EFO Monitor\config.json" `
  -Stdout -NoSubmit
```

After inspecting the output, run one signed submission and install the
two-minute per-user scheduled task:

```powershell
.\monitor\collect_local_windows.ps1 `
  -Config "$env:LOCALAPPDATA\EFO Monitor\config.json"
.\monitor\install_local_windows_task.ps1 `
  -RepositoryRoot (Get-Location).Path `
  -Config "$env:LOCALAPPDATA\EFO Monitor\config.json"
```

## Agent-card projection

Agent cards are a derived convenience view; the complete task table remains
the canonical operational history. The collector assigns a task to a card
only when the signed ledger is valid and either:

- the task actor exactly matches the configured EFO agent ID; or
- signed identity snapshots establish the same `control_principal` and
  `model_family`, with a valid `alias_of` and `alias_chain`.

Unknown, unattested, cyclic, self-referential, or inconsistent aliases are not
merged. Signed verification activity can make a task relevant to a verifier's
card without changing the task owner.

Selection is deterministic. Live canonical work and transport observations
take priority over terminal history. Within the same class, the newest signed
timestamp wins and task ID resolves an exact tie. This prevents an old blocked
probe from making an agent look currently blocked after newer work, while the
old row remains visible in the complete task table.

Each non-idle card binds its title, workflow progress, next action, status
source, badge, and timestamp to a task ID in the same public snapshot. The
Pages Function rejects missing tasks, mismatched values, extra card fields,
and hidden state on an idle card. Transport badges describe an orchestrator
observation; they never rewrite the canonical task state.

Collector versions `1.0` and `1.1` did not bind cards to task IDs. During a
rolling release, the Pages Function accepts their exact seven-field card
shape but normalizes each card to a safe waiting/offline projection with no
current task, zero workflow progress, and `status_source=none`. It marks the
stored source as `agent_projection_compat=legacy_idle`. Extra legacy fields
and legacy-shaped cards claiming to be collector `1.2` still fail closed.
Once collector `1.2` uploads, full task-bound cards replace the compatibility
projection.

## Cloudflare Pages

The repository's `wrangler.toml` is the source of truth for the Pages project
name, compatibility date, and `public/` output directory. For the
Git-connected Pages project:

1. Set the production branch to `main`.
2. Leave the build command empty.
3. Confirm the detected build output directory is `public`.
4. Create a KV namespace for the latest monitor snapshot.
5. Add the Pages Functions KV binding `EFO_MONITOR_KV`.
6. Add an encrypted variable named `EFO_INGEST_SECRET`.
7. Optionally add `EFO_VIEW_TOKEN` to require a dashboard access key.
8. To enable model-backed chat, add encrypted `OPENAI_API_KEY`, set
   `EFO_CHAT_ENABLED=true`, and optionally set `EFO_CHAT_MODEL`.
9. To collect the local workstation, add encrypted
   `EFO_LOCAL_INGEST_SECRET` with the same value stored only in the local
   protected secret file.
10. Redeploy the latest `main` commit after changing bindings.

`EFO_INGEST_SECRET` should be at least 32 random bytes. Keep exactly the same
value in the protected SSH server secret file. Do not commit either secret.

The configuration can be checked without revealing a secret:

```bash
curl https://evidence-first-orchestrator.pages.dev/api/snapshot?health=1
```

The response reports only whether storage, ingestion, a snapshot, and optional
viewer protection are configured.

## SSH collector

The collector requires Python 3.10+ and standard server tools only. It installs
no Python package and does not need root.

```bash
git clone https://github.com/heosanghun/evidence-first-orchestrator.git \
  "$HOME/evidence-first-orchestrator"
cd "$HOME/evidence-first-orchestrator"

install -d -m 700 "$HOME/.config/efo-monitor"
install -m 600 monitor/config.example.json \
  "$HOME/.config/efo-monitor/config.json"
install -m 600 /dev/null "$HOME/.config/efo-monitor/ingest-secret"
```

Place the same random value used for the Cloudflare encrypted variable in
`~/.config/efo-monitor/ingest-secret`, then edit `config.json` to match the EFO
workspace and public project aliases.

Project portfolio definitions are explicit and describe workflow gates, not
accuracy:

```json
{
  "project_portfolios": [
    {
      "id": "cts",
      "name": "CTS",
      "objective": "Validate the latent operator through preregistered gates.",
      "phase": "Operator validity",
      "next_milestone": "Decode-quality gate",
      "task_ids": ["C1", "P1b-2", "P1b-9", "CTS-R1", "CTS-R2"]
    },
    {
      "id": "system-1-5",
      "name": "System 1.5",
      "objective": "Rebuild and validate Thought-Slot DEQ.",
      "phase": "Thought-Slot audit",
      "next_milestone": "T>1 pilot",
      "task_ids": ["A-G1", "S15-TS-AUDIT", "S15-TS-OPERATOR", "S15-TS-PILOT"]
    }
  ]
}
```

Run one local, non-submitting check first:

```bash
python3 -m monitor.collector \
  --config "$HOME/.config/efo-monitor/config.json" \
  --stdout --no-submit
```

Inspect the JSON and confirm that it contains no sensitive fields. Then run one
signed submission:

```bash
python3 -m monitor.collector \
  --config "$HOME/.config/efo-monitor/config.json"
```

Finally enable the two-minute user timer:

```bash
bash monitor/install_user_service.sh "$HOME/evidence-first-orchestrator"
systemctl --user list-timers efo-monitor.timer
journalctl --user -u efo-monitor.service --no-pager -n 30
```

Check whether user services remain alive after logout:

```bash
loginctl show-user "$USER" -p Linger --value
```

If the result is `no`, either ask the administrator to enable lingering or use
the included user-cron installer. It adds one marker-delimited, idempotent
entry, uses `flock` to prevent overlapping runs, and performs an immediate
signed submission:

```bash
bash monitor/install_cron_service.sh "$HOME/evidence-first-orchestrator"
tail -n 20 "$HOME/.local/state/efo-monitor/collector.log"
```

## Collector permissions

The service executes only observational operations:

- `nvidia-smi --query-gpu` and `--query-compute-apps`;
- `docker ps`, `docker top`, `docker inspect`, and `docker logs --tail`;
- EFO `status` and `agent list`;
- a sanitized projection of `ledger/events.jsonl`;
- reads from `/proc`, plus disk usage;
- one HTTPS POST to the configured Pages Function.

It contains no Docker lifecycle command and no training command. Project
aliases are evaluated locally so public data can use stable, human-readable
names instead of raw container details.

## Local verification

```bash
python -m unittest tests.test_monitor_collector -v
npm run test:web
```

The web page falls back to `public/data/demo.json` only when the API is not
available. The top status and footer clearly label that state as `DEMO`.
