# `efo legacy audit --write-test` writes outside `reports/<agent>/`, and reports a path that says otherwise

Reproduce with `raw/probe_legacy_audit.py`; raw output in
`raw/raw-legacy-audit.txt`. **19 checks, 0 unexpected.** Filed as issue #17.

`NOTE-cli-surface-holds.md` adjudicated `legacy audit` read-only **from the
parser**, which is a claim about the command table and not about the code.
`docs/MIGRATION.md` documents a mode that deliberately writes. This is that
mode, driven against a real Markdown tree built from `doctor.LEGACY_REQUIRED`.

## The documented claim

`docs/MIGRATION.md:43-52`, Phase 2:

> Run the optional write check from inside each agent's own execution context:
> ```bash
> efo legacy audit "E:\path\to\legacy-workspace" --agent codex --write-test
> ```
> **The check writes and removes one temporary file only in `reports/<agent>/`.**

Three assertions: it writes, it removes, and it does so *only* in
`reports/<agent>/`. The first two hold. The third does not.

## What the code does

`doctor.py:109-113`:

```python
report_dir = root_path / "reports" / agent_id
if not report_dir.is_dir():
    raise ConfigurationError(...)
```

`agent_id` is interpolated straight into a path and is never validated —
`validate_agent_id` is not called on this path, and the CLI takes `--agent` as
a free string. The guard is an **existence** check, not a **containment**
check, so it refuses a directory that does not exist and accepts any directory
that does.

## Every shape of `--agent`, enumerated

The probe **fails the run on any shape the map does not cover**.
`uncovered: []`.

| `--agent` | Result |
|---|---|
| `codex`, `claude` | writes to `reports/<that agent>` — as documented |
| `""` | refused — *agent_id is required for a legacy write test* |
| `nope`, `reports` | refused — *report directory does not exist* |
| `..` | **escapes** — writes to the legacy root itself |
| `../..` | **escapes** — writes two levels above the legacy root |
| `.` | **escapes** — writes to `reports/` itself, above any agent |
| `/abs/path` | **escapes** — writes to an unrelated absolute path |
| `codex/../claude` | **another agent's directory** — resolves to `reports/claude` |

Four shapes leave the `reports/` subtree, three of them leaving the workspace
entirely. A fifth stays inside it and writes into a *different* agent's
directory than the one named on the command line — which matters because Phase
2 says to run this *"from inside each agent's own execution context"*. Who owns
the target directory is the whole point of the check.

The temporary file **is** removed in every case, including the escapes. This is
about *where*, not about residue.

## The report hides it

`write_test["path"]` is stored unresolved (`doctor.py:121`). With
`--agent ../..`:

```
"write_test": {"tested": true, "writable": true,
               "path": ".../legacy-workspace/reports/../.."}
```

The string contains `/reports/`. The directory actually written to is the
legacy root's parent. The command exits 0 and reports `writable: true`.

So an operator who runs the documented Phase 2 check, or a script that greps
the JSON for `reports/`, sees a compliant-looking result for a run that wrote
outside the workspace.

## Why it can bite, and the caller path

`efo legacy audit <path> --agent <x> --write-test` reaches it directly, and so
does `efo doctor <broker> --legacy-root <path> --legacy-agent <x>
--legacy-write-test` (`doctor.py:215-219`). Both are documented operator
commands run during a migration, when the legacy tree is still the live
workspace. The write is one small temp file that is then unlinked, so the
damage ceiling is low — but the *guarantee* the documentation offers, that the
check cannot touch anything outside one agent's report directory, does not
hold, and the reported path actively obscures that.

The fix is the one already used elsewhere in this codebase: resolve, then check
containment. `util.is_relative_to` exists for exactly this and is measured
correct in `NOTE-util-and-lock-hold.md` — it gets `reports/wombat` vs
`reports/w` right and fails closed on a symlink pointing outside. Calling
`validate_agent_id` first would also refuse `..`, `.` and `/abs` outright.

## Two things measured and NOT filed

**Phase 0's read-only claim holds.** `MIGRATION.md:16-20` offers
`efo legacy audit <path>` with no flags. Two full audits, one through
`audit_legacy_workspace` and one through the real CLI, produced
`{'added': [], 'removed': [], 'changed': []}` against a size-and-mtime
snapshot of the whole tree.

**`doctor`'s `healthy` ignores the legacy verdict.** With a broken legacy tree
(`compatible: false`, one plaintext secret) attached via `--legacy-root`, the
top-level result stays `healthy: true` and the CLI exits 0. `healthy` is
computed at `doctor.py:203-211`, before `legacy` is attached at `:213-219`, and
never consults it. Not filed — `README.md` describes `doctor` as a broker check
and `--legacy-root` as an add-on, so nothing claims otherwise. Recorded because
one payload carrying `healthy: true` next to `legacy.compatible: false` invites
the wrong read.

## The secret scan, and a second caller for issue #12

Planting four credentials in the legacy tree, only one is found:

| Planted | Where | Seen |
|---|---|---|
| `api_key: sk-live-…` | `shared/ENV.md` | **yes** |
| `AWS_SECRET_ACCESS_KEY=…` | `shared/ENV.md` | no |
| `GITHUB_TOKEN=…` | `shared/ENV.md` | no |
| `password: hunter2` | `shared/CREDENTIALS.md` | no |
| `token: ghs_…` | `reports/codex/run.md` | no |

Two different kinds of miss. The first two sit in a **scanned** file and are
missed by `SECRET_RE`'s `\b`, which treats `_` as a word character — the same
`_scan_secrets` and the same defect already filed as **issue #12**. Recorded
here rather than filed again: one fix surface, reached by a second caller.

The last two are never opened at all. The scan iterates `LEGACY_REQUIRED`,
seven fixed paths. That is a **map, not a finding** — `MIGRATION.md:8-14` asks
the operator to remove plaintext credentials and *then* says "Run the read-only
audit"; it never claims the audit proves step 1 was done. Worth an operator
knowing anyway: `secret_findings: []` means *nothing matched in seven files*,
not *this tree carries no secrets*.

## Harness bug, disclosed

My first classification treated *"inside the `reports/` subtree"* and *"is the
directory this `--agent` named"* as one property, and so scored
`codex/../claude` as a failure of containment. It is not — `reports/claude` is
inside the subtree. The two are independent questions and the probe now
classifies each shape as `OWN` / `OTHER-AGENT` / `ESCAPES` / `REFUSED`. My
expectation was wrong, not the code; only the corrected run is reported.

## Scope

`audit_legacy_workspace` in default and `--write-test` modes, driven through
both the Python API and the real `cli.main`, against a legacy tree built from
`LEGACY_REQUIRED`; the `--agent` shape census; the read-only property measured
by whole-tree snapshot; the interaction with `doctor --legacy-root`. Not
examined: `EVENT_RE`'s handling of lines that do not begin with a date (they
are skipped rather than flagged, which `doctor.py`'s own risk list already
concedes — *"no atomic multi-writer lock or tamper signature"*), and Windows
path semantics, since `E:\...` cannot be exercised here.

Pre-registered permissions unchanged: `gpu: false`, `network: false`,
`performance_metrics: false`; gates `allow_skips: false`,
`require_validation: true`, `require_known_answer_check: true`,
`require_independent_verification: true`.

**SUBMITTED, not VERIFIED.**

| Artifact | SHA-256 |
|---|---|
| `raw/probe_legacy_audit.py` | `76639539a5e99eda454180e3be770260721b76da30134d25f23e5ff17a94860c` |
| `raw/raw-legacy-audit.txt` | `6d26c85d92f7044d0d654d9d8631c3faa03164eec3e2c146ea54751f4417a493` |
