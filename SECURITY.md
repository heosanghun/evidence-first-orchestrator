# Security Policy

## Reporting

Please report a suspected vulnerability through a private GitHub security
advisory when the repository supports it. Do not include live credentials,
private research data, or unpublished model artifacts in an issue.

## Security properties

- External commands are launched with an argument list and `shell=False`.
- Task lease tokens are stored only as SHA-256 digests.
- Revocation retains resource locks until process termination is acknowledged
  or externally confirmed with a signed evidence note.
- Command adapters gate worker launch behind a Linux child subreaper plus
  process group, or a Windows Job Object, and bind release authority to a
  broker-held execution token.
- The event ledger is hash-chained and HMAC-signed with a local key.
- The dashboard is read-only and binds to loopback by default.
- Orchestrator-only commits recheck current authority inside the ledger lock.
- Worker reports and manifests must remain inside their owned report directory.
- Task permissions default to no GPU, no network, and no performance metrics.
- Proxy submissions require distinct author and proxy identities and compare
  a task-preregistered remote name, URL, advertised branch ref, and complete
  path set against exact Git blobs.
- Proxy submission performs a bounded `git ls-remote` lookup and rejects a
  commit that exists only in the local source clone.
- Strict tasks can reject matching actor, controller, or model-family profiles.
- Submission records freeze author identity before any later profile update.
- High and critical tasks enforce named three-dimension-independent finalizers.
- Every accepting finalizer supplies its own verification manifest, even when
  additional accepting attestations are required.
- Historical independence audit reads signed verification events, not only the
  current task projection.

## Limitations

Application-level ownership does not stop a process that directly edits files
outside EFO. Use containers, OS accounts, ACLs, and read-only mounts when
workers are not equally trusted.

The local ledger signing key protects against edits by parties that cannot read
the key. If every worker uses the same OS account, use an external append-only
store or a key held only by the orchestrator for stronger guarantees.

For manual or externally launched processes, EFO cannot itself prove that a
PID tree, container, or accelerator context has stopped. Such tasks remain in
`revoking` and retain locks until the orchestrator records an external
confirmation. Manual workers cannot self-confirm termination. The
orchestrator's confirmation is an auditable assertion, not hardware
attestation.

On Linux, command-adapter execution is serialized in each broker process. The
broker becomes a child subreaper and tracks descendants that escape their
inherited process group with `setsid()` or double-fork daemonization. A task is
blocked until that tracked set is empty; if termination cannot be confirmed,
the broker disables further command execution until restart. Non-Linux POSIX
command adapters fail closed because EFO cannot provide equivalent tracking.
Windows uses a non-breakaway Job Object. Use containers, delegated cgroups,
separate OS accounts, or a scheduler for adversarial code and accelerator
workloads; EFO's process controls are an operational containment layer, not a
complete kernel security boundary.

Agent identity profiles are signed declarations, not hardware attestations.
EFO detects undeclared, matching, or silently changed identity fields; it
cannot prove that a declared provider or model family is truthful. Retain
provider run IDs or external session attestations for critical work.

Git provenance proves that the configured remote advertised the exact branch
head at submission time and that delivered bytes match blobs in that commit.
This relies on Git transport authentication, DNS/TLS or SSH trust, and the
remote host's honesty; it does not prove that the repository or commit is
semantically trustworthy. Retain provider-side run or audit IDs for critical
deliveries and review the preregistered source before creating the task.

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
