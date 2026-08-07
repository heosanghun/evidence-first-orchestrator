#!/usr/bin/env python3
"""reports/, submissions/ and archive/ are compared against NOTHING - six for six.

Queue item 60, from item 57. That round measured the covered set for the config,
the agent records and the task projections, and found `runs/` uncovered. It
could not enumerate `reports/`, `submissions/` or `archive/` because a FRESH
workspace does not create them, and it said so.

This builds a workspace far enough to have all three - init, two identity
attestations, create, claim, start, submit with a real evidence bundle, verify
with a second bundle, archive - and then tampers with each directory.

    control - untouched                HEALTHY
    edit archive/T1.json               HEALTHY - unnoticed
    edit an ARCHIVED artifact          HEALTHY - unnoticed
    delete an ARCHIVED artifact        HEALTHY - unnoticed
    edit submissions bundle.json       HEALTHY - unnoticed
    delete the whole submissions/T1    HEALTHY - unnoticed
    edit a report under reports/       HEALTHY - unnoticed

SIX FOR SIX. And the data to catch every one of them is already in the ledger:
the seven archived files carry seven sha256 values, and ALL SEVEN are recorded
in signed events. Nothing recomputes them.

That is the measured WIDTH of issue #10 ("retention has no verifier"), not a
new issue: same component, same root cause, and #10 already says the archive
has no verifier. What this adds is that the gap is not only retention - an
archived bundle can be EDITED or DELETED wholesale and `doctor` still reports
`healthy: true`.

NOT FILED. It quantifies an open issue of mine rather than opening another, and
- per item 57 - every "unnoticed" here is measured under the threat model
`SECURITY.md:38` declares.

    python3 probe_archive_tree_uncompared.py

SCOPE, stated first: 7 workspaces, a full lifecycle each, 4 directories,
6 tampers, 1 control, 7 recorded hashes. A MAP. No issue filed.
"""

from __future__ import annotations

import hashlib
import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, "/tmp/efo-prov/src")
from evidence_orchestrator import doctor  # noqa: E402
from evidence_orchestrator.workspace import Workspace  # noqa: E402

FAIL = 0
ANCHOR = Path("/tmp/efo-prov")
SRC = ANCHOR / "src" / "evidence_orchestrator"
ROOT = Path(tempfile.mkdtemp(prefix="efo-item60-")).resolve()


def check(name: str, expected: str, observed: str) -> None:
    global FAIL
    ok = expected in observed
    if not ok:
        FAIL += 1
    print(f"  [{'ok' if ok else '!! UNEXPECTED !!'}] {name}")
    print(f"        expected: {expected}")
    print(f"        observed: {observed}")


def sha_of(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


# ---------------------------------------------------------------- A
print("########## A. POSITIVE CONTROL, and the scope FIRST ##########")
check("the review's anchor is UNMOVED at 5694ab45",
      "5694ab455139f1e72d946bc2fe7e42c7c0c8a43a",
      subprocess.run(["git", "-C", str(ANCHOR), "rev-parse", "HEAD"],
                     capture_output=True, text=True).stdout.strip())
check("  with no working-tree modification", "dirty: ''",
      f"dirty: {subprocess.run(['git', '-C', str(ANCHOR), 'status', '--porcelain'], capture_output=True, text=True).stdout.strip()!r}")

# The comparison messages are DERIVED from workspace.py, not typed: item 57
# measured six, and if a seventh appeared this check would fail rather than
# quietly measure the wrong covered set.
comparisons = sorted(set(re.findall(
    r'"([^"]*(?:differs from the signed ledger|no ledger event)[^"]*)"',
    (SRC / "workspace.py").read_text(encoding="utf-8"))))
# `.strip("{}")` left the trailing `}:` on `{task_id}:` - stripping a SET of
# characters is not stripping a suffix. Corrected to the measured token.
covered_nouns = sorted({message.split()[0].strip("{}:") for message in comparisons})
for message in comparisons:
    print(f"    workspace.py  {message}")
check("  comparison messages the package declares", "messages: 6",
      f"messages: {len(comparisons)}")
check("    and every one names an Agent, a Task or the Workspace config",
      "nouns: ['Agent', 'Task', 'Workspace', 'task_id']",
      f"nouns: {covered_nouns}")
print("  Not one of them names reports/, submissions/ or archive/. Section C")
print("  drives that rather than reading it off.")


# ---------------------------------------------------------------- B
print("\n########## B. a workspace driven to `archived` ##########")


def lifecycle(tag: str) -> Path:
    root = ROOT / tag
    workspace = Workspace.initialize(root, name="item60",
                                     orchestrator="antigravity",
                                     preset="antigravity-codex-claude")
    for agent in ("antigravity", "claude"):
        workspace.attest_agent_identity(
            actor="antigravity", agent_id=agent,
            control_principal="principal-" + agent,
            model_family="family-" + agent)
    workspace.create_task(actor="antigravity", task_id="T1", title="t",
                          description="d", owner="claude")
    claim = workspace.claim(actor="claude", task_id="T1")
    token = claim["lease_token"]
    workspace.start(actor="claude", task_id="T1", lease_token=token)

    def bundle(agent: str, suffix: str) -> tuple[Path, Path]:
        home = workspace.reports_dir / agent
        home.mkdir(parents=True, exist_ok=True)
        report = home / f"T1{suffix}.md"
        report.write_text("\n".join(
            f"## {n}. Section {n}\n\ncontent{suffix}\n" for n in range(1, 7))
            + "\n", encoding="utf-8")
        artifact = home / f"T1{suffix}.artifact.txt"
        artifact.write_bytes(f"measured{suffix}\n".encode())
        raw = home / f"T1{suffix}.raw.txt"
        raw.write_bytes(f"1 passed{suffix}\n".encode())
        manifest = home / f"T1{suffix}.evidence.json"
        manifest.write_text(json.dumps({
            "schema_version": 1,
            "artifacts": [{"path": str(artifact), "sha256": sha_of(artifact)}],
            "validations": [{"command": "pytest -q", "exit_code": 0,
                             "passed": 1, "failed": 0, "skipped": 0,
                             "skip_reasons": [],
                             "raw_output_path": str(raw),
                             "raw_output_sha256": sha_of(raw)}],
            "known_answer_checks": [{"name": "two plus two", "expected": 4,
                                     "observed": 4, "passed": True}],
            "claims": [{"name": "functional behavior", "kind": "functional",
                        "measured": True, "value": "pass",
                        "evidence": [str(artifact)]}],
        }, indent=2), encoding="utf-8")
        return report, manifest

    report, manifest = bundle("claude", "")
    workspace.submit(actor="claude", task_id="T1", lease_token=token,
                     report_path=report, manifest_path=manifest)
    _, verification = bundle("antigravity", "-v")
    workspace.verify(actor="antigravity", task_id="T1", decision="accept",
                     note="ok", verification_manifest=verification)
    workspace.archive(actor="antigravity", task_id="T1")
    return root


def audit(root: Path) -> str:
    try:
        result = doctor.audit_workspace(root)
    except Exception as exc:  # noqa: BLE001 - a raise is still "caught"
        return f"caught (raised {type(exc).__name__})"
    return ("HEALTHY - unnoticed" if result["healthy"]
            else f"caught: {result.get('error', 'no error key')[:46]}")


baseline = lifecycle("control")
directories = sorted(p.name for p in baseline.iterdir() if p.is_dir())
print(f"    directories after archive: {directories}")
check("the lifecycle reaches `archived`", "state: archived",
      "state: " + json.loads(
          (baseline / "tasks" / "T1.json").read_text(encoding="utf-8"))["state"])
check("  and all three directories now exist",
      "present: ['archive', 'reports', 'submissions']",
      "present: " + str(sorted({"archive", "reports", "submissions"}
                               & set(directories))))
check("    the untouched workspace audits healthy - CONTROL",
      "HEALTHY", audit(baseline))

archived = sorted(baseline.glob("submissions/T1/**/files/*"))
recorded: set[str] = set()


def walk(value) -> None:
    if isinstance(value, dict):
        for key, item in value.items():
            if key in ("sha256", "raw_output_sha256") and isinstance(item, str):
                recorded.add(item)
            walk(item)
    elif isinstance(value, list):
        for item in value:
            walk(item)


walk([json.loads(line) for line
      in (baseline / "ledger" / "events.jsonl").read_text(
          encoding="utf-8").splitlines() if line.strip()])
on_disk = {sha_of(path) for path in archived}
check("  archived evidence files", "files: 7", f"files: {len(archived)}")
check("    sha256 values recorded in SIGNED ledger events",
      "recorded: 7", f"recorded: {len(recorded)}")
check("      every archived file's hash IS in the ledger", "matched: 7",
      f"matched: {len(on_disk & recorded)}")
print("  So the data to detect any tamper below already exists, signed.")

# ---------------------------------------------------------------- C
print("\n########## C. DRIVEN - six tampers, one per fresh workspace ##########")


def files_of(root: Path) -> list:
    return sorted(root.glob("submissions/T1/**/files/*"))


TAMPERS = [
    ("edit archive/T1.json", lambda root: (root / "archive" / "T1.json")
     .write_text(json.dumps({**json.loads(
         (root / "archive" / "T1.json").read_text(encoding="utf-8")),
         "state": "pending"}, indent=2), encoding="utf-8")),
    ("edit an ARCHIVED artifact",
     lambda root: files_of(root)[0].write_bytes(b"tampered\n")),
    ("delete an ARCHIVED artifact", lambda root: files_of(root)[0].unlink()),
    ("edit submissions bundle.json",
     lambda root: next(root.glob("submissions/T1/**/bundle.json"))
     .write_text("{}", encoding="utf-8")),
    ("delete the whole submissions/T1",
     lambda root: shutil.rmtree(root / "submissions" / "T1")),
    ("edit a report under reports/",
     lambda root: (root / "reports" / "claude" / "T1.md")
     .write_text("# rewritten\n", encoding="utf-8")),
]
outcomes: dict[str, str] = {}
try:
    # A fresh workspace per tamper, keyed by INDEX: item 57's three `config:`
    # drives collided because the directory came from the tag's first word.
    for index, (label, mutate) in enumerate(TAMPERS):
        root = lifecycle(f"tamper-{index}")
        mutate(root)
        outcomes[label] = audit(root)
finally:
    pass

for label, outcome in outcomes.items():
    print(f"    {label:<34}{outcome}")
check("six tampers driven", "driven: 6", f"driven: {len(outcomes)}")
check("  NONE of them is caught", "caught: []",
      f"caught: {[k for k, v in outcomes.items() if not v.startswith('HEALTHY')]}")
check("    including deleting the entire archived bundle",
      "HEALTHY - unnoticed", outcomes["delete the whole submissions/T1"])
check("      and rewriting the archived task record",
      "HEALTHY - unnoticed", outcomes["edit archive/T1.json"])

shutil.rmtree(ROOT, ignore_errors=True)

# ---------------------------------------------------------------- D
print("\n########## D. what this is, and what it is NOT ##########")
print("  * It is the measured WIDTH of issue #10, not a new issue. #10 says")
print("    `archive.py` retention has no verifier; this adds that the gap is")
print("    not only retention - an archived bundle can be EDITED or DELETED")
print("    wholesale, and the archived task record REWRITTEN, with `doctor`")
print("    still reporting healthy: true.")
print("  * NOT FILED. It quantifies an open issue of mine rather than opening")
print("    another one.")
print("  * Every `unnoticed` here is measured UNDER THE THREAT MODEL")
print("    SECURITY.md:38 declares - item 57 showed a re-signed tamper of the")
print("    COVERED files is healthy too. The difference is that these six")
print("    need no key at all.")
print("  * It does NOT claim the covered set is wrong: config, agents and")
print("    tasks are compared, and item 57 drove that.")

print("\n########## E. what this does NOT do ##########")
print("  * It does not enumerate `shared/`. That directory exists after init")
print("    and was not driven - stated, not implied.")
print("  * It does not test the CLI `ledger audit-projections` path")
print("    separately; `doctor.audit_workspace` calls audit_projections and")
print("    is the surface an operator is told to run.")
print("  * It does not propose a fix, and does not retract #10 or narrow it.")
print("  * No network. Seven workspaces, all tempfile directories, removed")
print("    above. The anchor's working tree is untouched.")
print("  * MEASURED: the six comparison messages, the lifecycle reaching")
print("    archived, the three directories, all seven archived files and")
print("    their ledger-recorded hashes, all six tampers, the control.")
print("    REASONED: nothing.")

print(f"\n########## {FAIL} unexpected result(s) ##########")
print("Seven full lifecycles driven against temporary workspaces. Anchor")
print("untouched, no `main` write, no issue filed. Pre-registered permissions")
print("unchanged - gpu/network/performance_metrics all false.")
print("SUBMITTED, not VERIFIED.")
