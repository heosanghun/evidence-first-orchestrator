# The collector's redaction claim at `main` `5694ab45` holds — no issue filed

Reproduce with `raw/probe_collector_redaction.py`; raw output in
`raw/raw-collector-redaction.txt`. **15 checks, 0 unexpected.**

`README.md:359-363` makes a specific, testable promise about the SSH collector,
and that list is the standard applied here:

> Public snapshots omit passwords, secrets, environment variables, command
> lines, PIDs, GPU UUIDs, ledger signatures, hashes, and event payloads.
> Activity history contains only event time, sequence, actor alias, transition
> label, task ID, and task title.

Method: a unique marker planted in exactly one input, the whole snapshot
serialized, and the blob searched for it. `nvidia-smi` and `docker` are absent
from this container, so their output is served from recorded fixtures through
`run_command` — **the real binaries were not executed**. The EFO half runs the
real CLI against a real workspace.

## The positive control, which is what makes the clean scan mean anything

An earlier run of this probe reported every marker absent while
`tasks=0 activity=0` — the collector had read nothing, because the child
process could not import the package. A scan that finds no leak in an empty
snapshot proves nothing. Corrected, and the reported run is the live one:

```
gpus=1  tasks=1  activity=8  alerts=0
```

| Marker that must appear | Observed |
|---|---|
| the GPU name | present |
| the task title | present |
| the container name, as a project label | present |
| the ledger event stream, as activity | present |

## Every item on the omission list holds

| Planted in | Marker | In the snapshot |
|---|---|---|
| `nvidia-smi --query-gpu` uuid field | `GPU-MARKERUUID…` | **absent** |
| `--query-compute-apps` pid + `docker top` | `918273645` | **absent** |
| `docker ps` `Command`, `inspect` `Config.Cmd`, `docker logs` | `MARKERCMDLINE` | **absent** |
| a task description | `MARKERDESC` | **absent** |
| the credential value inside that description | `AKIA1234567890EXAMPLE` | **absent** |
| an absolute path inside a real `blocked_reason` | `MARKERBLOCKED` | **absent** |
| the first ledger event's `signature` | (real value) | **absent** |
| the first ledger event's `event_hash` | (real value) | **absent** |

The design earns this rather than getting it by luck. `_uuid` is prefixed so
`strip_internal_fields` removes it; compute-app PIDs are used only for
correlation inside `map_projects_to_gpus` and never returned; `query_containers`
reads only `ID`, `Names` and `Status` out of `docker ps --format {{json .}}`
even though the full record is available; `task_to_view` and `collect_activity`
whitelist fields rather than blacklisting them, so `description`,
`blocked_reason` and `result` never had a path out.

That last point is worth stating plainly: the adapter writes absolute paths into
`blocked_reason` (`Evidence gate rejected output: Report does not exist: /abs/…`),
and a blacklist would very likely have missed it. The whitelist did not.

## Activity history carries three fields the sentence does not name

```
documented: event time, sequence, actor alias, transition label, task ID, task title
emitted:    ['action', 'actor', 'actor_name', 'at', 'category', 'label',
             'sequence', 'task_id', 'title']
```

`action` (`task.created`), `category` (`system`) and `actor` alongside
`actor_name` are the extras. None is free text — `action` and `category` come
from a fixed table, and `actor` is an agent id like `antigravity`. Recorded for
accuracy, not filed: the sentence reads as a description of the sensitivity
class, and none of the three carries anything a reader would object to.

One entry, verbatim:

```json
{"sequence": 1, "at": "2026-08-02T06:14:16Z", "actor": "antigravity",
 "actor_name": "antigravity", "action": "workspace.initialized",
 "label": "워크스페이스 생성", "category": "system",
 "task_id": null, "title": null}
```

## The one channel where the guarantee depends on an external program

`query_gpus` (`collector.py:200-209`) and `collect_efo` (`1038-1048`) put raw
subprocess stderr into a public alert. Measured with a failing `nvidia-smi`:

```json
{"severity": "critical", "title": "GPU 상태 수집 실패",
 "message": "MARKERSTDERR /home/operator/.config/efo/ingest-secret",
 "at": "..."}
```

The path survives intact, because `sanitize_label` is a character filter, not a
redactor — `/`, `.`, `_`, `:`, `@` and `-` are all inside its allow-set:

```
'/home/operator/.ssh/id_ed25519'        -> '/home/operator/.ssh/id_ed25519'
'python train.py --api-key=sk-ant-0123' -> 'python train.py --api-keysk-ant-0123'
'token=abc; rm -rf /'                   -> 'tokenabc rm -rf /'
'user@host:/srv/data'                   -> 'user@host:/srv/data'
'$(whoami)`id`'                         -> 'whoamiid'
```

**I am not filing this**, and the reason matters: file paths are not on the
collector's omission list, and I planted a *path to* a secret, not a secret.
Nothing here demonstrates a documented promise being broken. What it does show
is that this is the only place in the collector where arbitrary external text
becomes public, and the promise there rests on what `nvidia-smi` or the
configured `efo_command` happens to write to stderr rather than on anything the
collector controls.

If whoever owns the file wants to close it, the cheap version is to publish a
fixed message plus the return code and keep the stderr locally.

### One interaction worth flagging to the same owner

`'--api-key=sk-ant-0123'` becomes `'--api-keysk-ant-0123'`. The `=` is
stripped and the credential survives. That is precisely the shape that
`doctor._scan_secrets` (issue #12) cannot match — its pattern needs a
`[:=|]` or whitespace after the keyword. So text that passes through
`sanitize_label` becomes *less* detectable by the project's own secret scanner
while remaining just as readable to a person. Neither behaviour is wrong on its
own; together they point the wrong way.

## Hostname — measured, deliberately not scored

`collect_system` emits `sanitize_label(socket.gethostname(), "gpu-server")`,
and `source.host` falls back to it when `display_host` is unset
(`collector.py:1277-1280`):

```
system.hostname = 'vm'
source.host     = 'vm'
```

`README.md:369` says *"Local collection sends no hostname, process names,
command lines, or file paths"* — but that sentence sits inside the Windows-PC
panel paragraph, alongside the operational load index, and the collector's own
list at 359-361 does not name hostname. My first reading treated it as a
collector claim and would have filed a false finding. Reading the paragraph it
belongs to is what stopped that. Recorded as an observation against no claim.

## Harness bugs, caught before any conclusion

Three, all mine, only the corrected run reported. Attesting the orchestrator's
own identity made the CLI refuse the workspace on reload
(`Agent antigravity registration differs from the signed ledger`), which is a
separate question and not one this probe is asking. The child process needed
`PYTHONPATH`, without which every EFO read returned empty — the false-clean run
described above. And the first version passed the entire serialized snapshot as
the `observed` string, making the output unreadable.

## Scope

`collect_snapshot` and everything it reaches: `query_gpus`,
`query_compute_apps`, `query_containers`, `container_progress`,
`map_projects_to_gpus`, `collect_system`, `collect_efo`, `task_to_view`,
`collect_activity`, `build_alerts`, `strip_internal_fields`, `sanitize_label`.
Not examined: `submit_snapshot`'s transport, `collect_project_portfolios`
beyond what issue #6 already covers, `functions/api/chat.js` and
`local-health.js` (queued), and the real `nvidia-smi`/`docker` binaries, which
this container does not have.

Pre-registered permissions unchanged: `gpu: false`, `network: false`,
`performance_metrics: false`; gates `allow_skips: false`,
`require_validation: true`, `require_known_answer_check: true`,
`require_independent_verification: true`. **No GPU was used or measured** — the
GPU inputs above are recorded fixtures, and every number in them is fixture
text, not a measurement.

**SUBMITTED, not VERIFIED.**

| Artifact | SHA-256 |
|---|---|
| `raw/probe_collector_redaction.py` | `be26ea006ec98a20e131ae0b6224b7b1ff637ee1f68729694d173074c20a80a8` |
| `raw/raw-collector-redaction.txt` | `bc9c4b7f57a218787fed0d56596a0d219414fa7171e4c34816076e388098f0f5` |
