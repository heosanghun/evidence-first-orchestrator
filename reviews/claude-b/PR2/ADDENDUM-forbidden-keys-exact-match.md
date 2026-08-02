# `snapshot.js` at `main` `5694ab45` — the ingest gate is strict where it validates, and `FORBIDDEN_KEYS` is the third guard keyed on a naming convention this codebase does not use

Reproduce with `raw/probe_snapshot_ingest.mjs` (Node v22.22.2); raw output in
`raw/raw-snapshot-ingest.txt`. **36 checks, 0 unexpected.** The handlers run as
real exported functions with real `Request`/`Response` and a KV double.

`README.md:359-361` describes the *published artifact*:

> Public snapshots omit passwords, secrets, environment variables, command
> lines, PIDs, GPU UUIDs, ledger signatures, hashes, and event payloads.

`NOTE-collector-redaction-holds.md` measured that the collector does not
**produce** those. This measures whether the endpoint would **accept** them —
and `onRequestGet` serves whatever was accepted, byte for byte.

## What holds, and it is a lot

| Probe | Observed |
|---|---|
| **positive control** — an honest snapshot | `200 ok=true`, stored, served back by GET with `"mode":"live"` |
| unsigned | `401 invalid_signature` |
| signed with the wrong secret | `401 invalid_signature` |
| correctly signed, an hour old | `401 invalid_timestamp` |
| correctly signed, an hour in the future | `401 invalid_timestamp` |
| an extra field on a task projection | `400 task has unexpected or missing fields` |
| an extra field on an agent projection | `400 agent has unexpected or missing fields` |
| a missing field on a task projection | `400 task has unexpected or missing fields` |

`constantTimeEqual` is correct, including the cases its cyclic index invites —
`("abc","abcabc")`, `("a","aa")`, `("ab","abab")` all `false`, because the
length XOR seeds `difference` before the loop.

Two things deserve more than a table row.

**The projection validation is stricter than it had to be.** My own fixture was
rejected with `task canonical projection is inconsistent`, because I wrote
`progress_percent: 45` on a `running` task and `CANONICAL_TASK_PROGRESS` says
`running` is 55. The endpoint refuses to publish a progress number that does not
follow from the state it is paired with. That is the doctrine of this repository
enforced at the last hop before a number becomes public, and it is the right
place for it.

**Forbidden keys are caught at any depth**, with the path reported:

```
$.gpus[0].uuid          $.system.token       $.system.nested.secret
$.alerts[0].pid         $.source.command     $.system.cmdline
```

## The finding: exact-name matching, and no value inspection

`hasForbiddenKey` compares `key.toLowerCase()` against a set of twelve bare
words (`snapshot.js:6-19`). Anything compound passes. Measured, each accepted
with `200 ok=true`:

| Key | Verdict |
|---|---|
| `system.api_key` | **accepted** |
| `system.access_token` | **accepted** |
| `gpus[0].gpu_uuid` | **accepted** |
| `gpus[0].process_id` | **accepted** |
| `system.command_line` | **accepted** |
| `system.ssh_key` | **accepted** |
| `system.environment_variables` | **accepted** |

The list already contains `cmdline` and `command`. It does not contain
`command_line` — the third spelling, and the one `docker inspect` and most
Python code would produce. `uuid` is listed; `gpu_uuid`, which is the exact key
`monitor/collector.py:255` builds in `query_compute_apps`, is not.

And values are never examined at all:

```
system.note = "AKIA1234567890EXAMPLE /home/operator/.ssh/id_ed25519 python train.py"
  -> 200 ok=true
  -> and GET serves it: AKIA1234567890EXAMPLE present: true
```

### Which containers are shape-checked, and which are not

`tasks`, `agents`, `projects` and `activity` get exact key sets and
cross-consistency checks. Everything else relies on `FORBIDDEN_KEYS` alone —
measured by accepting each of these:

```
system replaced with an arbitrary object   -> 200 ok=true
an arbitrary extra field on a GPU entry    -> 200 ok=true
an arbitrary alert object                  -> 200 ok=true
```

So `system`, extra keys on `gpus[]`, `alerts[]`, `history[]`, `workspace` and
`source` are free-form, and the only thing standing between them and the public
GET response is a twelve-word exact-match list.

## Why this is worth filing rather than shrugging at

The honest counter-argument first: publishing requires `EFO_INGEST_SECRET`, so
this is not an anonymous-attacker path, and the collector that holds the secret
was measured clean. Nothing here demonstrates a live leak.

What makes it worth a line anyway is that it is the **third independent
instance of one bug class** in this codebase, and the three compose:

| Where | Guard | Misses |
|---|---|---|
| `doctor.py` `_scan_secrets` (issue #12) | `\b(secret\|token\|api[_-]?key)\b` | `AWS_SECRET_ACCESS_KEY`, `GITHUB_TOKEN` — `_` is a word character |
| `monitor/collector.py` `sanitize_label` (`NOTE-collector-redaction-holds.md`) | character allow-list | strips `=` from `--api-key=sk-ant-0123`, leaving the value readable but no longer matching the scanner's pattern |
| `snapshot.js` `FORBIDDEN_KEYS` (here) | exact key name | `api_key`, `gpu_uuid`, `command_line`, `ssh_key` |

Each guard is keyed on a naming convention, and the convention each assumes is
not the snake_case-compound one the codebase itself writes — `gpu_uuid`,
`process_id`, `max_evidence_bytes`, `raw_output_path`, `last_event_hash`. Three
layers that were each meant to be the backstop for the others all have the same
blind spot, so they do not compose into defence in depth.

### Suggested fix

Match a forbidden word as a token inside the key, not as the whole key:

```js
const FORBIDDEN_PATTERN =
  /(?:^|[^a-z0-9])(password|passwd|secret|token|environment|env|command|cmdline|pid|uuid|ssh|authorization|credential|key)(?:$|[^a-z0-9])/;
```

That catches all seven rows above while still admitting `key_count` style names
if the word list is kept tight. Pair it with exact key sets for `system` and
`gpus[]` — the collector already emits a fixed shape for both, so an allow-list
costs nothing and would make `FORBIDDEN_KEYS` a backstop rather than the only
line, exactly as `local-health.js` already does (see
`ADDENDUM-chat-refusal-and-grounding.md`, where every hostile payload is
refused by an exact key set).

## Scope

`functions/api/snapshot.js`: `onRequestPost`, `onRequestGet`,
`validateSnapshot`, `validateTaskProjection`, `validateAgentProjection`,
`hasForbiddenKey`, `constantTimeEqual`, `hmacHex`. Not examined:
`normalizeLegacyAgentProjections`' legacy path, `validateProjectProjection`
beyond a smoke test, and `public/assets/app.js`.

Pre-registered permissions unchanged: `gpu: false`, `network: false`,
`performance_metrics: false`; gates `allow_skips: false`,
`require_validation: true`, `require_known_answer_check: true`,
`require_independent_verification: true`. No network call was made — the KV is
a double and no request left the process.

## Harness bug, caught before any conclusion

One, mine, and the positive control caught it: my base fixture set
`progress_percent: 45` on a `running` task, which the endpoint correctly
refuses. Every "accepted" row below section A would have been meaningless while
the baseline itself was rejected. Fixed to 55 and only the corrected run is
reported.

**SUBMITTED, not VERIFIED.**

| Artifact | SHA-256 |
|---|---|
| `raw/probe_snapshot_ingest.mjs` | `87a7dfccbb2bb64c511a5c8af07144039c10bcc851578ea07df77dab2820b541` |
| `raw/raw-snapshot-ingest.txt` | `77d00517857b414cafd4d5e4bd6d039e7b31c709e9534b57d27f012f3dca73a1` |
