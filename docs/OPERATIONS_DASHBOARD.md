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

Displayed progress is an **EFO workflow-phase indicator** derived from task
states. It is not model accuracy, training completion, or a scientific
performance result.

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
8. Redeploy the latest `main` commit after changing bindings.

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

If the server does not keep user services alive after logout, the administrator
must enable user lingering for the `shoon` account or schedule the same
one-shot command with the site's approved scheduler.

## Collector permissions

The service executes only observational operations:

- `nvidia-smi --query-gpu` and `--query-compute-apps`;
- `docker ps`, `docker top`, `docker inspect`, and `docker logs --tail`;
- EFO `status` and `agent list`;
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
