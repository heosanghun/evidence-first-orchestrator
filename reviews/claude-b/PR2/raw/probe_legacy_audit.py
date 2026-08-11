#!/usr/bin/env python3
"""EFO `efo legacy audit` at main (5694ab45), driven against a real Markdown tree.

`NOTE-cli-surface-holds.md` adjudicated this subcommand read-only FROM THE
PARSER. That is a claim about the command table, not about the code, and
`docs/MIGRATION.md` documents a mode that deliberately writes. This probe
builds the legacy workspace MIGRATION.md describes and drives the real
`audit_legacy_workspace` and the real `cli.main` against it.

MIGRATION.md's testable claims, with the paragraph each sits in:

  Phase 0 (:16-20)  "Run the read-only audit: efo legacy audit <path>"
  Phase 2 (:43-52)  "Run the optional write check from inside each agent's own
                     execution context ... The check writes and removes one
                     temporary file only in `reports/<agent>/`."

Section C enumerates every shape of `--agent` and FAILS the run on any shape
this probe has not adjudicated.

    python3 probe_legacy_audit.py
"""

from __future__ import annotations

import io
import json
import shutil
import sys
import tempfile
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

sys.path.insert(0, "/tmp/efo-prov/src")
from evidence_orchestrator import errors  # noqa: E402
from evidence_orchestrator.cli import main as cli_main  # noqa: E402
from evidence_orchestrator.doctor import (  # noqa: E402
    LEGACY_REQUIRED,
    audit_legacy_workspace,
    audit_workspace,
)
from evidence_orchestrator.workspace import Workspace  # noqa: E402

FAIL = 0
ROOT = Path(tempfile.mkdtemp(prefix="efo-legacy-")).resolve()
LEGACY = ROOT / "legacy-workspace"
DOCS = Path("/tmp/efo-prov/docs/MIGRATION.md").read_text(encoding="utf-8")


def check(name: str, expected: str, observed: str) -> None:
    global FAIL
    ok = expected in observed
    if not ok:
        FAIL += 1
    print(f"  [{'ok' if ok else '!! UNEXPECTED !!'}] {name}")
    print(f"        expected: {expected}")
    print(f"        observed: {observed}")


def tree() -> dict[str, tuple[int, int]]:
    """Every path under ROOT with its size and mtime - the write oracle."""
    return {
        str(path.relative_to(ROOT)): (
            path.stat().st_size if path.is_file() else -1,
            path.stat().st_mtime_ns,
        )
        for path in sorted(ROOT.rglob("*"))
    }


def run_cli(*argv: str) -> tuple[int, str]:
    out, err = io.StringIO(), io.StringIO()
    try:
        with redirect_stdout(out), redirect_stderr(err):
            code = cli_main(list(argv))
    except SystemExit as exc:
        code = int(exc.code or 0)
    return code, out.getvalue() or err.getvalue()


def build_legacy() -> None:
    """Exactly the tree doctor.LEGACY_REQUIRED names, plus report dirs."""
    for relative in LEGACY_REQUIRED:
        path = LEGACY / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(f"# {relative}\n\nlegacy content\n", encoding="utf-8")
    (LEGACY / "logs" / "EVENTS.md").write_text(
        "[2026-08-01 09:00] antigravity NOTE T1 opened the inbox\n"
        "[2026-08-01 10:00] codex START T1 begin work\n"
        "[2026-08-01 12:00] codex DONE T1 finished\n",
        encoding="utf-8",
    )
    for agent in ("codex", "claude"):
        (LEGACY / "reports" / agent).mkdir(parents=True, exist_ok=True)


# ---------------------------------------------------------------- A
print("########## A. POSITIVE CONTROL - a real legacy tree, driven by the CLI ##########")
build_legacy()
check("MIGRATION.md documents the read-only audit (Phase 0, :16-20)",
      'efo legacy audit "E:\\\\path\\\\to\\\\legacy-workspace"',
      next(line.strip() for line in DOCS.splitlines()
           if line.strip().startswith("efo legacy audit") and "--agent" not in line))
code, out = run_cli("legacy", "audit", str(LEGACY))
check("the CLI accepts it", "exit 0", f"exit {code}")
report = json.loads(out)
check("  and calls the tree compatible", "compatible: True",
      f"compatible: {report['compatible']}")
check("  having found all seven required files", "missing: []",
      "missing: " + str([c["path"] for c in report["checks"]
                         if not (c["exists"] and c["readable"])]))
check("  and no malformed events", "malformed: 0",
      f"malformed: {len(report['malformed_events'])}")
print("  The positive control is LIVE: an incompatible tree must be refused,")
print("  or 'compatible' proves nothing. Deleting one required file:")
hidden = LEGACY / "shared" / "FACTS.md"
hidden.rename(hidden.with_suffix(".md.bak"))
control = audit_legacy_workspace(LEGACY)
check("  one missing file flips the verdict", "compatible: False",
      f"compatible: {control['compatible']}")
hidden.with_suffix(".md.bak").rename(hidden)

# ---------------------------------------------------------------- B
print("\n########## B. Phase 0's claim: the audit is READ-ONLY ##########")
before = tree()
audit_legacy_workspace(LEGACY)
run_cli("legacy", "audit", str(LEGACY))
after = tree()
check("no path created, removed, or modified by two audits",
      "delta: {'added': [], 'removed': [], 'changed': []}",
      "delta: " + str({
          "added": sorted(set(after) - set(before)),
          "removed": sorted(set(before) - set(after)),
          "changed": sorted(k for k in set(before) & set(after)
                            if before[k] != after[k]),
      }))
print("  Phase 0's read-only claim HOLDS for the default mode.")

# ---------------------------------------------------------------- C
print("\n########## C. Phase 2's claim: writes 'only in reports/<agent>/' ##########")
claim = next(line.strip() for line in DOCS.splitlines()
             if "temporary file only in" in line)
print(f"  MIGRATION.md:51-52 -> {claim!r}")
print("             ... continuing: '`reports/<agent>/`.'")
print("  `audit_legacy_workspace` builds that directory as")
print("      report_dir = root_path / 'reports' / agent_id")
print("  and gates it on `report_dir.is_dir()`. That is an EXISTENCE check,")
print("  not a CONTAINMENT check, and agent_id is never validated - the CLI")
print("  takes --agent as a free string and `validate_agent_id` is not called.")

OUTSIDE = ROOT / "outside"
OUTSIDE.mkdir(exist_ok=True)
REPORTS = (LEGACY / "reports").resolve()

def classify(written: Path, shape: str) -> str:
    """Two INDEPENDENT properties, which my first draft wrongly conflated.

    'inside the reports subtree' and 'is the directory this --agent named'
    are not the same question: reports/codex/../claude is inside the subtree
    and is somebody else's directory.
    """
    if not (written.is_relative_to(REPORTS) and written != REPORTS):
        return "ESCAPES"
    if written == (REPORTS / shape):
        return "OWN"
    return "OTHER-AGENT"


# shape -> (what happens, expected classification)
ADJUDICATED = {
    "codex": ("writes to reports/codex", "OWN"),
    "claude": ("writes to reports/claude", "OWN"),
    "": ("refused - agent_id is required for a legacy write test", "REFUSED"),
    "nope": ("refused - report directory does not exist", "REFUSED"),
    "reports": ("refused - reports/reports does not exist", "REFUSED"),
    "..": ("leaves the reports subtree - the legacy root itself", "ESCAPES"),
    "../..": ("leaves the workspace - two levels up", "ESCAPES"),
    ".": ("reports/ itself, above any agent", "ESCAPES"),
    str(OUTSIDE): ("an unrelated absolute path", "ESCAPES"),
    "codex/../claude": (
        "inside the subtree, but ANOTHER agent's directory", "OTHER-AGENT"),
}

results: dict[str, tuple[str, str]] = {}
for shape in ADJUDICATED:
    snapshot = tree()
    try:
        outcome = audit_legacy_workspace(LEGACY, agent_id=shape, write_test=True)
        written = Path(outcome["write_test"]["path"]).resolve()
        results[shape] = (f"wrote to {written}", classify(written, shape))
    except errors.ConfigurationError as exc:
        results[shape] = (f"refused ({exc})", "REFUSED")
    residue = sorted(set(tree()) - set(snapshot))
    if residue:
        results[shape] = (results[shape][0] + f" LEAVING {residue}",
                          results[shape][1])

uncovered = [shape for shape in results if shape not in ADJUDICATED]
for shape in ADJUDICATED:
    note, expected_class = ADJUDICATED[shape]
    observed, actual_class = results[shape]
    if expected_class != actual_class:
        FAIL += 1
    marker = "  " if expected_class == actual_class else "!!"
    print(f"  {marker}--agent {shape!r:30} {actual_class}")
    print(f"        {note}")
    print(f"        observed: {observed[:110]}")
check("every --agent shape is adjudicated", "uncovered: []",
      f"uncovered: {uncovered}")


def label(shape: str) -> str:
    return "<abs>" if shape.startswith(str(ROOT)) else shape


check("shapes that leave the reports subtree entirely",
      "['.', '..', '../..', '<abs>']",
      str(sorted(label(s) for s, (_, kind) in results.items()
                 if kind == "ESCAPES")))
check("  and shapes that land in a DIFFERENT agent's directory",
      "['codex/../claude']",
      str(sorted(label(s) for s, (_, kind) in results.items()
                 if kind == "OTHER-AGENT")))
print("  The documented sentence says 'only in `reports/<agent>/`'. Four")
print("  shapes leave that subtree altogether - three of them leave the")
print("  workspace - and a fifth stays inside it while writing into a")
print("  different agent's directory than the one named on the command line.")
print("  Phase 2 says to run this 'from inside each agent's own execution")
print("  context', so who owns the target directory is the point of the check.")
print("  The temporary file IS removed in every case: the 'writes and removes'")
print("  half of the claim holds. This is about WHERE, not about residue.")

print("\n  The reported path hides it. `write_test.path` is stored unresolved:")
outcome = audit_legacy_workspace(LEGACY, agent_id="../..", write_test=True)
check("  the JSON an operator reads still contains 'reports'",
      "reports", outcome["write_test"]["path"])
check("  while the directory actually written to is the legacy root's parent",
      str(ROOT), str(Path(outcome["write_test"]["path"]).resolve()))
print("  So a --write-test run that escaped two levels reports a path string")
print("  containing `/reports/`, and `writable: true`, and exit 0.")

# ---------------------------------------------------------------- D
print("\n########## D. does the legacy verdict reach `doctor`'s healthy flag? ##########")
broker = ROOT / "broker"
workspace = Workspace.initialize(broker, name="broker", orchestrator="antigravity",
                                 preset="antigravity-codex-claude")
workspace.attest_agent_identity(actor="antigravity", agent_id="claude",
                                control_principal="anthropic",
                                model_family="anthropic-claude")
plain = audit_workspace(broker)
check("the broker alone is healthy", "healthy: True", f"healthy: {plain['healthy']}")

(LEGACY / "logs" / "EVENTS.md").write_text(
    "[2026-08-01 10:00] codex START T1 begin work\n"
    "[2026-08-01 99:99] codex DONE\n",
    encoding="utf-8",
)
(LEGACY / "shared" / "ENV.md").write_text(
    "api_key: sk-live-000111222333\n", encoding="utf-8")
merged = audit_workspace(broker, legacy_root=LEGACY)
check("the legacy tree is now broken", "compatible: False",
      f"compatible: {merged['legacy']['compatible']}")
check("  and carries a plaintext secret", "secret findings: 1",
      f"secret findings: {len(merged['legacy']['secret_findings'])}")
check("  yet the top-level verdict is unchanged", "healthy: True",
      f"healthy: {merged['healthy']}")
code, _ = run_cli("doctor", str(broker), "--legacy-root", str(LEGACY))
check("  and the CLI exits 0", "exit 0", f"exit {code}")
print("  `healthy` is computed before `legacy` is attached and never consults")
print("  it (doctor.py:203-211 vs :213-219). NOT FILED: nothing claims it does")
print("  - README.md describes `doctor` as a broker check and `--legacy-root`")
print("  as an add-on. Recorded because one payload with one `healthy: true`")
print("  and a `legacy.compatible: false` beside it invites the wrong read.")

# ---------------------------------------------------------------- E
print("\n########## E. what the legacy secret scan does not see ##########")
(LEGACY / "shared" / "ENV.md").write_text(
    "AWS_SECRET_ACCESS_KEY=wJalrXUtnFEMIexampleKEY\n"
    "GITHUB_TOKEN=ghp_0123456789abcdef\n"
    "api_key: sk-live-000111222333\n",
    encoding="utf-8",
)
(LEGACY / "shared" / "CREDENTIALS.md").write_text(
    "password: hunter2\n", encoding="utf-8")
(LEGACY / "reports" / "codex" / "run.md").write_text(
    "token: ghs_secretvalue\n", encoding="utf-8")
scan = audit_legacy_workspace(LEGACY)
found = sorted((f["key"], Path(f["path"]).name) for f in scan["secret_findings"])
check("only the bare-word key is caught", "[('api_key', 'ENV.md')]", str(found))
print("  Two misses, and they are DIFFERENT KINDS:")
print("   1. AWS_SECRET_ACCESS_KEY / GITHUB_TOKEN sit in a scanned file and are")
print("      missed by the regex - SECRET_RE's \\b treats '_' as a word")
print("      character. This is the SAME `_scan_secrets` and the SAME defect")
print("      already filed as issue #12; recorded here, not filed again,")
print("      because it is one fix surface reached by a second caller.")
print("   2. shared/CREDENTIALS.md and reports/codex/run.md are never opened at")
print("      all - the scan iterates LEGACY_REQUIRED, seven fixed paths.")
check("  the scan covers exactly the seven required files", "7",
      str(len(LEGACY_REQUIRED)))
print("  MIGRATION.md Phase 0 (:8-14) asks the operator to remove plaintext")
print("  credentials and then says 'Run the read-only audit'. It does not")
print("  claim the audit proves step 1 was done, so #2 is a MAP, not a finding.")
print("  Worth an operator knowing anyway: a clean `secret_findings: []` means")
print("  'nothing matched in seven files', not 'this tree carries no secrets'.")

shutil.rmtree(ROOT, ignore_errors=True)
print(f"\n########## {FAIL} unexpected result(s) ##########")
print("Pre-registered permissions unchanged: gpu/network/performance_metrics")
print("all false. No network call was made and no measured performance claim")
print("appears above.")
print("SUBMITTED, not VERIFIED.")
