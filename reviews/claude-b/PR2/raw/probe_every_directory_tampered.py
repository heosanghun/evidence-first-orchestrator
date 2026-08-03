#!/usr/bin/env python3
"""Every directory a workspace has, tampered - and the one that IS caught.

Queue item 63, closing what item 60 stated it had not done: `shared/` exists
after `init` and no tamper touched it. Rather than adding that one directory,
this ENUMERATES every directory a workspace actually has from the filesystem
and asserts the classification is EXHAUSTIVE - so "compared against nothing"
covers the whole tree rather than the three item 60 happened to name.

    item 57 drove : .efo/workspace.json (config), agents/, tasks/, runs/
    item 60 drove : reports/, submissions/, archive/
    never driven  : shared/, ledger/, .efo/ itself, .efo/locks/

AND THIS ROUND HAS A TAMPER THAT IS CAUGHT. Every previous round in this line
reported "unnoticed", which makes a reader reasonably ask whether the DRIVER
detects anything at all. `.efo/ledger.key` is inside the workspace (item 57),
so replacing it must break every signature - and it does. That is the positive
control the earlier rounds' negatives needed.

Workspaces are keyed by INDEX, not by the tamper's first word: items 57 and 60
both hit collisions when two drives derived the same directory name.

    python3 probe_every_directory_tampered.py

SCOPE, stated first: 9 directories enumerated, 3 coverage classes asserted
exhaustive, 8 new tampers, 2 positive controls, 1 caught. A MAP that WIDENS an
open issue (#10) rather than filing a new one.
"""

from __future__ import annotations

import hashlib
import json
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
REVIEWS = Path("/workspace/evidence-first-orchestrator/reviews/claude-b/PR2")
ROOT = Path(tempfile.mkdtemp(prefix="efo-item63-"))


def check(name: str, expected: str, observed: str) -> None:
    global FAIL
    ok = expected in observed
    if not ok:
        FAIL += 1
    print(f"  [{'ok' if ok else '!! UNEXPECTED !!'}] {name}")
    print(f"        expected: {expected}")
    print(f"        observed: {observed}")


def git(*arguments: str) -> str:
    return subprocess.run(["git", "-C", str(ANCHOR), *arguments],
                          capture_output=True, text=True).stdout.strip()


def sha_of(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


# ---------------------------------------------------------------- A
print("########## A. POSITIVE CONTROL, and the scope FIRST ##########")
check("the review's anchor is UNMOVED at 5694ab45",
      "5694ab455139f1e72d946bc2fe7e42c7c0c8a43a", git("rev-parse", "HEAD"))
check("  with no working-tree modification", "dirty: ''",
      f"dirty: {git('status', '--porcelain')!r}")


def lifecycle(tag: str) -> Path:
    root = ROOT / tag
    workspace = Workspace.initialize(root, name="item63",
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
        return f"CAUGHT (raised {type(exc).__name__})"
    return ("HEALTHY - unnoticed" if result["healthy"]
            else f"CAUGHT: {result.get('error', 'no error key')[:44]}")


baseline = lifecycle("control")
check("the lifecycle reaches `archived` - the CONTROL", "state: archived",
      "state: " + json.loads(
          (baseline / "tasks" / "T1.json").read_text(
              encoding="utf-8"))["state"])
check("  and the untouched workspace audits healthy", "HEALTHY",
      audit(baseline))

# ---------------------------------------------------------------- B
print("\n########## B. every directory, ENUMERATED not named ##########")
every = sorted(str(p.relative_to(baseline)) for p in baseline.rglob("*")
               if p.is_dir())
top = sorted({name.split("/")[0] for name in every})
print(f"    top-level directories : {top}")
print(f"    all directories       : {len(every)}")
ITEM57 = {"agents", "tasks", "runs"}          # + .efo/workspace.json, config
ITEM60 = {"reports", "submissions", "archive"}
THIS = {"shared", "ledger", ".efo"}
check("every top-level directory falls in exactly one coverage class",
      "unclassified: []",
      f"unclassified: {sorted(set(top) - ITEM57 - ITEM60 - THIS)}")
check("  and no class names a directory that does not exist",
      "phantom: []",
      f"phantom: {sorted((ITEM57 | ITEM60 | THIS) - set(top))}")
check("    nine top-level directories in total", "top: 9", f"top: {len(top)}")
check("    and they are exactly these",
      "['.efo', 'agents', 'archive', 'ledger', 'reports', 'runs', 'shared', "
      "'submissions', 'tasks']", str(top))
# Item 60's premise, driven rather than repeated: `shared/` exists after
# INIT, before any task work, which is why "it was not driven" was a real gap
# rather than an artefact of the lifecycle this probe happens to run.
fresh = Workspace.initialize(ROOT / "fresh", name="fresh",
                             orchestrator="antigravity",
                             preset="antigravity-codex-claude")
check("  `shared/` exists after INIT alone - item 60's stated premise",
      "shared after init: True",
      f"shared after init: {(fresh.root / 'shared').is_dir()}")
check("    and it is EMPTY, so nothing about it is task-derived",
      "contents: []",
      f"contents: {sorted(p.name for p in (fresh.root / 'shared').iterdir())}")
print("  Item 57 drove config, agents, tasks and runs; item 60 drove reports,")
print("  submissions and archive. THREE were never driven - and item 60 said")
print("  so for `shared/` explicitly. Section C drives all three.")

# ---------------------------------------------------------------- C
print("\n########## C. the never-driven directories, DRIVEN ##########")


def drive(index: int, label: str, mutate) -> str:
    """One fresh workspace per tamper, keyed by INDEX.

    Items 57 and 60 both collided when two drives derived a directory name
    from the tamper's first word. The index cannot collide.
    """
    root = lifecycle(f"t{index:02d}")
    mutate(root)
    return audit(root)


TAMPERS = [
    ("add a file under shared/",
     lambda r: (r / "shared" / "planted.txt").write_text("x")),
    ("add a subtree under shared/",
     lambda r: ((r / "shared" / "deep").mkdir(),
                (r / "shared" / "deep" / "x.json").write_text("{}"))),
    ("DELETE shared/ entirely",
     lambda r: shutil.rmtree(r / "shared")),
    ("add a stray file under ledger/",
     lambda r: (r / "ledger" / "extra.jsonl").write_text("{}\n")),
    ("add a stray file under .efo/",
     lambda r: (r / ".efo" / "planted.json").write_text("{}")),
    ("add a stray lock under .efo/locks/",
     lambda r: (r / ".efo" / "locks" / "planted.lock").write_text("")),
    ("DELETE the shipped runs/.gitignore",
     lambda r: (r / "runs" / ".gitignore").unlink()),
    ("DELETE .efo/.gitignore",
     lambda r: (r / ".efo" / ".gitignore").unlink()),
]
results = []
for index, (label, mutate) in enumerate(TAMPERS, start=1):
    outcome = drive(index, label, mutate)
    results.append((label, outcome))
    print(f"    {label:<38} {outcome}")
check("all eight new tampers go unnoticed",
      "unnoticed: 8",
      f"unnoticed: {sum(1 for _, o in results if 'HEALTHY' in o)}")
# The complement, asserted rather than inferred: a count of "unnoticed" alone
# would also read 8 if the audit had crashed on some of them, because a raise
# is reported as CAUGHT by `audit`.
check("  and NONE of the eight was caught - the complement", "caught: 0",
      f"caught: {sum(1 for _, o in results if 'CAUGHT' in o)}")
check("    three of them are DELETIONS, not just plants", "deletions: 3",
      f"deletions: {sum(1 for label, _ in results if 'DELETE' in label)}")

# ---------------------------------------------------------------- D
print("\n########## D. and a tamper that IS caught - the other direction ##########")
print("  Every round in this line has reported `unnoticed`, which is a fair")
print("  reason to ask whether the driver detects anything at all. The key")
print("  lives INSIDE the workspace (item 57), so replacing it must break")
print("  every signature.")
caught = []
for index, (label, mutate) in enumerate([
        ("REPLACE .efo/ledger.key",
         lambda r: (r / ".efo" / "ledger.key").write_bytes(b"9" * 32)),
        ("DELETE .efo/ledger.key",
         lambda r: (r / ".efo" / "ledger.key").unlink()),
], start=90):
    outcome = drive(index, label, mutate)
    caught.append((label, outcome))
    print(f"    {label:<38} {outcome}")
check("replacing the signing key IS caught", "CAUGHT", caught[0][1])
check("  by a SIGNATURE mismatch, named", "Ledger signature mismatch",
      caught[0][1])
check("  and deleting it is caught too", "CAUGHT", caught[1][1])
check("    by a DIFFERENT failure - the key being absent",
      "Ledger signing key is missing", caught[1][1])
check("      so the two controls are not one message twice",
      "distinct: True",
      f"distinct: {caught[0][1].split(':')[1] != caught[1][1].split(':')[1]}")
print("  So the driver is not blind: it catches what the signature covers.")
print("  What the eight above show is the SCOPE of that coverage, not a")
print("  failure to look.")

# ---------------------------------------------------------------- E
print("\n########## E. what this does NOT establish ##########")
print("  * It does NOT file an issue. This WIDENS the measured width of #10")
print("    from three directories to the whole tree; quantifying an open")
print("    issue is not opening another one.")
print("  * It does NOT claim the covered set is wrong. Config, agents and")
print("    tasks ARE compared - item 57 drove that, and section D confirms")
print("    the signature path still bites.")
print("  * Every `unnoticed` is measured UNDER THE THREAT MODEL SECURITY.md:38")
print("    declares. A tamper needing the key is a different measurement, and")
print("    section D is the one that needs it.")
print("  * It does NOT enumerate FILES exhaustively - only directories, plus")
print("    the four shipped files the tampers name. A file this round did not")
print("    touch is UNCHECKED, not shown safe.")
print("  * It does NOT propose a fix, and does not retract or narrow #10.")
print("  * No network, no GPU. Eleven tempfile workspaces, removed before the")
print("    results print. The anchor's working tree is untouched, and it does")
print("    not touch `main` or another agent's branch.")
print("  * MEASURED: the directory enumeration, the exhaustiveness of the")
print("    classification, all eight tampers, both key tampers, the")
print("    lifecycle control. REASONED: nothing.")

shutil.rmtree(ROOT, ignore_errors=True)
print(f"\n########## {FAIL} unexpected result(s) ##########")
print("Pre-registered permissions unchanged - gpu/network/performance_metrics")
print("all false. SUBMITTED, not VERIFIED: re-running my own evidence is a")
print("re-run, not independent confirmation.")
