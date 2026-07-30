# EFO-5 Claude B Worker Submission

Worker: `claude-b`

Actual runtime: `Claude Code 2.1.220`, `claude-opus-5`

Base: `0828c0b6ff792da29317228679f7e962aec457ad`

Head: `5a7f7f60e4a30dbfd9c9da82e9dfee3eb959fcb4`

Transport: `antigravity`

## 1. Scope

Claude B implemented the preregistered EFO-5 hardening task in an isolated
clone. The committed diff changes exactly the three authorized paths:

- `monitor/collector.py`
- `tests/test_monitor_collector.py`
- `docs/OPERATIONS_DASHBOARD.md`

No API, UI, package, production configuration, dataset, benchmark, or GPU
path changed.

## 2. Implementation

The implementation adds one fail-closed actor helper used by verification and
external-status attribution. The helper requires a nonempty actor, a resolved
registered identity dict, and a claimed identity dict exactly equal to the
resolved identity. Missing snapshots can no longer pass through
`None == None`.

Profile `id` is now presentation-only. Attribution uses `efo_id` plus its
validated signed alias group.

Card selection is recency-first. Exact timestamp ties use the preregistered
class order `attention`, `live`, `terminal`, followed by task ID. Canonical
task rows, history, alerts, privacy projection, and the 11-field card contract
remain unchanged.

## 3. Validation

Raw verifier-captured worker logs against the clean committed state record:

```text
Python: 98 passed, 0 failed, 0 skipped
Node:   18 passed, 0 failed, 0 skipped
Static: Python compile, two Node syntax checks, Git diff check,
        exact write scope, clean worktree, and exact HEAD all passed
```

The Claude B worker session itself reported the same complete suite outcomes
and ended with `RESULT: READY`. Web-search and web-fetch usage were both zero.

## 4. Known Answers

The added synthetic tests cover all seven frozen answers:

1. unregistered verifier without identity does not assign a card;
2. external author without identity does not assign a card;
3. display-ID collision does not widen attribution;
4. newer blocked work outranks older live work;
5. newer live or verified work outranks older blocked work;
6. equal timestamps use class priority and task ID; and
7. every non-idle card names a retained task in the same snapshot.

Additional tests cover partial, extra, mutated, list, and string identity
claims and pin the exact card-state classifier.

## 5. Claims

This submission claims only deterministic software behavior and exact Git
provenance:

- secondary attribution requires a complete current signed identity;
- display labels do not confer task ownership;
- card recency is deterministic and symmetric for new blocks and recovery;
- the public card/task contracts are unchanged; and
- the exact three changed blobs are content-addressed.

Submission is not verification and does not authorize deployment.

## 6. Limitations

The worker and Claude A share the Anthropic model family, so Claude A cannot
serve as the formal independent verifier. Codex must reproduce the exact
commit and accept or reject it through EFO.

The Claude API was used only as worker control-plane transport. Project
execution used no network, web search, web fetch, GPU, production service,
dataset, benchmark, or performance measurement.
