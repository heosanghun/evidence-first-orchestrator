# Security Policy

## Reporting

Please report a suspected vulnerability through a private GitHub security
advisory when the repository supports it. Do not include live credentials,
private research data, or unpublished model artifacts in an issue.

## Security properties

- External commands are launched with an argument list and `shell=False`.
- Task lease tokens are stored only as SHA-256 digests.
- Proxy grant tokens are one-time, task-bound, and stored only as SHA-256
  digests.
- Offline Git evidence is compared against raw blob bytes without checkout
  conversion or network fetches.
- The event ledger is hash-chained and HMAC-signed with a local key.
- The dashboard is read-only and binds to loopback by default.
- Cloudflare snapshot and local-health ingestion use independent HMAC secrets;
  replay windows, bounded payloads, strict schemas, and constant-time signature
  checks are enforced before data is stored.
- Local Windows telemetry is aggregate-only: no hostname, user name, process
  name, command line, environment variable, or file path is accepted.
- The operations assistant receives a bounded, sanitized snapshot and exposes
  no mutation tools. Infrastructure-control requests are refused.
- Optional model-backed chat is disabled unless both the explicit enable flag
  and viewer authentication are configured; deterministic snapshot answers
  remain available without an API key.
- Worker reports and manifests must remain inside their owned report directory.
- Task permissions default to no GPU, no network, and no performance metrics.

## Limitations

Application-level ownership does not stop a process that directly edits files
outside EFO. Use containers, OS accounts, ACLs, and read-only mounts when
workers are not equally trusted.

The local ledger signing key protects against edits by parties that cannot read
the key. If every worker uses the same OS account, use an external append-only
store or a key held only by the orchestrator for stronger guarantees.

The orchestrator is the proxy-submission policy root. A signed proxy event
proves what that orchestrator declared and transported; it does not
cryptographically prove that a remote model authored the commit. Stronger
deployments should require provider attestations or per-agent public-key
signatures in addition to EFO's Git provenance checks.

## Credential handling

Never commit:

- `.efo/ledger.key`;
- SSH passwords or private keys;
- API tokens;
- cloud credentials;
- dashboard ingestion or viewer secrets;
- model API keys;
- private benchmark data;
- raw model checkpoints.

New workspaces create nested ignore rules for `.efo/ledger.key`, lock files, and
`runs/`. Keep those rules in place when embedding a workspace in another Git
repository.

Use environment variables, an SSH agent, or an OS credential store. Rotate a
credential immediately if it has appeared in a shared prompt, report, log, or
repository.
