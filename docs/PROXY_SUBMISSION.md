# Transparent Proxy Submission

Some workers can deliver a Git commit but cannot connect to the EFO workspace.
EFO records that situation without pretending that the worker ran a local CLI
command.

## Trust Model

The workspace orchestrator is the policy root. Only that actor may issue a
proxy grant or transport a proxy submission. This prevents ordinary workers
from naming another agent as the author. It does not make a malicious
orchestrator cryptographically honest. EFO's ledger has one workspace HMAC key,
so actor identity remains a signed policy declaration rather than a
hardware-backed provider identity.

The task owner is always the declared author. The CLI cannot choose an
unrelated registered agent. A proxy grant binds one future attempt to:

- the workspace ID;
- task ID and next attempt number;
- task owner;
- transport actor;
- Git remote URL, branch, and full commit object ID;
- an expiration time; and
- a one-time bearer token whose SHA-256, not plaintext, is signed into the
  ledger.

The grant prevents accidental cross-task, cross-workspace, cross-transport, and
replay use. The trusted orchestrator could still make a false author
designation, just as it could create a false task assignment. That residual
authority is explicit rather than hidden behind a forged worker command.

## Signed Event Shape

`task.proxy_authorized` records the source constraint before ingestion.
`task.proxy_submitted` then records the real transport actor as the ledger
event actor. The task result keeps the identities separate:

```json
{
  "authorship": {
    "actor": "claude",
    "identity": {"control_principal": "...", "model_family": "..."},
    "method": "proxy"
  },
  "transport": {
    "actor": "antigravity",
    "identity": {"control_principal": "...", "model_family": "..."},
    "grant_event_hash": "..."
  },
  "provenance": {
    "kind": "git",
    "remote_url": "https://example.invalid/repository.git",
    "branch": "claude/C1",
    "commit": "full-object-id",
    "byte_exact": true
  }
}
```

The transport actor creates the six-section report and evidence envelope under
its own report directory. Claim-bearing artifacts and raw validation outputs
must be exact Git blobs from the author's commit.

## Git Verification

Proxy submission never fetches from the network. The operator supplies an
already available local Git repository. EFO verifies:

1. the configured remote URL exactly matches the preregistered grant;
2. the full commit object exists;
3. the commit is reachable from the declared local or remote-tracking branch;
4. every claim-bearing artifact and raw output is listed once;
5. every listed source is a safe repository-relative POSIX path;
6. `git cat-file blob` bytes have the same SHA-256 as the submitted bytes; and
7. every evidence file is under the transport actor's report directory.

The blob comparison intentionally happens before any checkout conversion.
LF-to-CRLF conversion, BOM insertion, encoding conversion, or any other byte
mutation is a hard failure even when rendered text looks identical. Embedded
credentials in HTTP remote URLs are rejected so the signed ledger and archived
provenance cannot become a credential store.

## Verification Policy

Independent verification is evaluated against the declared author, not the
transport actor. A transport actor may also verify only when its signed control
principal and model family are independent of the author. EFO records
`transport_overlap=true` when the transport actor, one of its aliases, or
another identity that is non-independent under the signed identity policy
performs verification. Reviewers can therefore apply a stricter local policy
without an alias bypass.

This choice avoids a three-model deadlock for byte-exact relays: transport is
not authorship, the source bytes are commit-bound, and the verifier still must
provide a separate manifest and rerun the checks. Deployments that require a
third independent actor can reject any verification with transport overlap.

## CLI Workflow

```bash
efo task proxy-authorize WORKSPACE \
  --actor antigravity \
  --id C1 \
  --transport-actor antigravity \
  --remote-url https://github.com/example/project.git \
  --branch claude/C1 \
  --commit FULL_COMMIT_OBJECT_ID \
  --duration-seconds 1800

efo task proxy-submit WORKSPACE \
  --actor antigravity \
  --author claude \
  --id C1 \
  --proxy-token ONE_TIME_TOKEN \
  --report reports/antigravity/C1.md \
  --evidence reports/antigravity/C1.evidence.json \
  --provenance reports/antigravity/C1.provenance.json \
  --source-repository /path/to/local/repository
```

The proxy path accepts only a pending task. It moves directly to submitted
without fabricating claim, start, heartbeat, or worker lease events.

## Rejected Alternatives

| Alternative | Reason rejected |
|---|---|
| Call normal submit with `--actor claude` | Forges the ledger event actor and a worker lease |
| Add an arbitrary `--author` flag to normal submit | Creates a general impersonation backdoor |
| Trust Git author or committer metadata | Those strings are self-declared and forgeable |
| Trust a checked-out file hash | Checkout filters and line-ending conversion can change bytes |
| Fetch a branch during submission | Violates offline operation and makes evidence depend on mutable network state |
| Treat transport as author | Erases the distinction this feature exists to preserve |

## Backward Compatibility

Direct `task submit` and evidence schema version 1 are unchanged. The new event
still includes `payload.task`, so older ledgers that project the latest task
snapshot can read the submitted state and later verify or reject it. Unknown
result fields are ignored by existing task validation.

Older independence-audit code does not recognize `task.proxy_submitted` as the
submission event and can therefore lose the immutable author snapshot during a
retrospective audit. Upgrade before auditing proxy submissions. No Git
provenance is imposed retroactively on historical direct submissions.
