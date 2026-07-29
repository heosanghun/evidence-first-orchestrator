# Security Policy

## Reporting

Please report a suspected vulnerability through a private GitHub security
advisory when the repository supports it. Do not include live credentials,
private research data, or unpublished model artifacts in an issue.

## Security properties

- External commands are launched with an argument list and `shell=False`.
- Task lease tokens are stored only as SHA-256 digests.
- The event ledger is hash-chained and HMAC-signed with a local key.
- The dashboard is read-only and binds to loopback by default.
- Worker reports and manifests must remain inside their owned report directory.
- Task permissions default to no GPU, no network, and no performance metrics.

## Limitations

Application-level ownership does not stop a process that directly edits files
outside EFO. Use containers, OS accounts, ACLs, and read-only mounts when
workers are not equally trusted.

The local ledger signing key protects against edits by parties that cannot read
the key. If every worker uses the same OS account, use an external append-only
store or a key held only by the orchestrator for stronger guarantees.

## Credential handling

Never commit:

- `.efo/ledger.key`;
- SSH passwords or private keys;
- API tokens;
- cloud credentials;
- private benchmark data;
- raw model checkpoints.

New workspaces create nested ignore rules for `.efo/ledger.key`, lock files, and
`runs/`. Keep those rules in place when embedding a workspace in another Git
repository.

Use environment variables, an SSH agent, or an OS credential store. Rotate a
credential immediately if it has appeared in a shared prompt, report, log, or
repository.
