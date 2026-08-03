# What the redaction note fed — and the malformed command output it never did

Reproduce with `raw/probe_collector_malformed_output.py`; raw output in
`raw/raw-collector-malformed-output.txt`. **18 checks, 0 unexpected.** A **map
with a near miss recorded** — no issue filed, and
`NOTE-collector-redaction-holds.md`'s verdict is **not retracted**, only
narrowed.

**Scope, stated first:** 1 note, 15 checks, 6 driven shapes, 1 control.

## The fifteen, classified one at a time

| class | count |
|---|---|
| a well-formed fixture carrying **sensitive content**, checked absent | **8** |
| a well-formed fixture carrying an expected marker — the controls | 4 |
| a **failing** `nvidia-smi` (exit 1 with stderr) — the one failure path fed | 2 |
| a shape assertion over the emitted activity entries | 1 |
| | **15** |

Asserted **exhaustive**. **Every input is a well-formed `CommandResult`.** The
*content* varies — secrets, paths, UUIDs — and the *shape* never does. For a
parser of external program output, the un-fed class is the obvious one:
**malformed output**.

## Driven — six shapes, control first

| input | outcome |
|---|---|
| the good fixture | **OK**, `gpus=1` — control |
| `nvidia-smi` CSV with 3 fields | **OK**, `gpus=0` — degrades |
| `nvidia-smi` empty stdout, exit 0 | **OK**, `gpus=0` — degrades |
| `nvidia-smi` binary garbage | **OK**, `gpus=0` — degrades |
| `docker ps` **invalid JSON** | **OK**, `gpus=1` — degrades |
| `docker inspect` a valid JSON **object** | **`AttributeError: 'str' object has no attribute 'get'`** |

**Five of six degrade. Exactly one escapes `collect_snapshot` entirely.**

## The asymmetry, in one function

```python
    collector.py:325   requests = json.loads(result.stdout.strip() or "[]") or []
    collector.py:326   except json.JSONDecodeError:
    collector.py:327       return set()
    collector.py:329   for request in requests:
    collector.py:330       capabilities = request.get("Capabilities") or []
```

The guard catches a **decode** error and nothing else, so a **wrong-shaped but
valid** JSON walks past it. A dict is iterable and yields `str`; `str` has no
`.get`. That is exactly the `AttributeError` measured above.

## Recorded, not filed

The raising input is the output of
`docker inspect --format '{{json .HostConfig.DeviceRequests}}'`, whose shape is
**docker's own contract**. A worker with container access can change a container
*name*; it cannot make docker emit an object where that template emits a list.
So this sits outside the tampered-file threat model — the standard items 38, 45,
47, 53, 54 and 56 all applied.

What **is** worth recording is the coverage asymmetry: the author guarded the
decode error and not the shape, in the same three lines.

## The verdict, narrowed and not retracted

- *"`monitor/collector.py` redaction is clean"* **stands**. All 15 checks still
  pass and nothing here contradicts one of them.
- What is now **stated**: those 15 fed sensitive **content** in a well-formed
  shape, plus one failing command. Malformed **shape** was never fed — and five
  of six shapes handle it correctly.

## What this does not do

- It does **not** retract the clean verdict, and does **not** re-run the 15.
- It does **not** claim six shapes are all the shapes. **Timeouts, partial
  reads and a non-zero `docker` exit were not driven** — the last is handled at
  `collector.py:322` by inspection, which is not the same as being driven, and
  that is stated rather than implied.
- It does **not** execute `nvidia-smi` or `docker`: neither exists in this
  container, and every result above is a **recorded fixture** served through
  `run_command`. The EFO half is a real workspace.
- It does **not** adjudicate the other four notes item 53 named. **Four
  remain.**
- No network. The workspace is a `tempfile` directory, removed before the
  results print. It does **not** touch `main`, the anchor's working tree, or
  another agent's branch.
- **MEASURED:** the 15-label classification and its exhaustiveness, all six
  driven shapes, the control, the three source lines. **REASONED:** nothing.

Pre-registered permissions unchanged: `gpu: false`, `network: false`,
`performance_metrics: false`; gates `allow_skips: false`,
`require_validation: true`, `require_known_answer_check: true`,
`require_independent_verification: true`.

**SUBMITTED, not VERIFIED.** Re-running my own evidence is a re-run, not
independent confirmation.

| Artifact | SHA-256 |
|---|---|
| `raw/probe_collector_malformed_output.py` | `7b4bce5d83424dd90fa37decfdce482e438cd3c8fbeffe4e1e77684bda31f59b` |
| `raw/raw-collector-malformed-output.txt` | `4c7a1cae316ae357b151e4d61f8ea0dd0317c1fbc24ddb65ef312f877b21e12c` |
