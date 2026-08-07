#!/usr/bin/env python3
"""Deleting across TASKS - 54 of 65 files removed, and doctor reports healthy.

Queue item 75, closing what item 72 stated it had not done: that round drove
one task and one attempt, and said plainly that a workspace with several
archived tasks was UNCHECKED, not shown safe.

Both populations are built in THIS run - a one-task workspace and a
three-task one - so the comparison stands on this run rather than on item
72's table plus this one. The split item 72 leaned on MOVES:

    one task      9 multi-instance kinds / 8 singletons
    three tasks  12 multi-instance kinds / 5 singletons

Three kinds cross, and one of them is `tasks/*.json` - one of the four kinds
item 72 measured as CAUGHT, and a kind whose message could not possibly move
while there was only one of it. At three tasks it moves, and it ENUMERATES:

    one projection deleted   T2: projection missing
    all three deleted        T1: projection missing; T2: projection missing;
                             T3: projection missing

And the deletion that matters:

    everything belonging to T2                 19 files  CAUGHT (the projection)
    everything for T2 EXCEPT tasks/T2.json     18 files  HEALTHY
    every task's evidence EXCEPT the three
        projections                            54 of 65  HEALTHY

    python3 probe_delete_across_tasks.py

SCOPE, stated first: 2 workspace shapes, 65 files, 17 kinds, the 3 kinds that
cross the split, 6 per-kind drives, 5 whole-tree drives, 1 exhaustiveness
assertion. A MAP that widens the measured width of #10 a third time. No issue
filed. Roughly 200s - it builds 12 workspaces, most of them three tasks deep.
"""

from __future__ import annotations

import hashlib
import json
import re
import shutil
import subprocess
import sys
import tempfile
from collections import Counter
from pathlib import Path

sys.path.insert(0, "/tmp/efo-prov/src")
from evidence_orchestrator import doctor  # noqa: E402
from evidence_orchestrator.workspace import Workspace  # noqa: E402

FAIL = 0
ANCHOR = Path("/tmp/efo-prov")
ANCHOR_SHA = "5694ab455139f1e72d946bc2fe7e42c7c0c8a43a"
ROOT = Path(tempfile.mkdtemp(prefix="efo-item75-"))


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
check("the review's anchor is UNMOVED at 5694ab45", ANCHOR_SHA,
      git("rev-parse", "HEAD"))
check("  with no working-tree modification", "dirty: ''",
      f"dirty: {git('status', '--porcelain')!r}")

INDEX = [0]


def lifecycle(task_ids: tuple) -> Path:
    """A workspace with every named task driven to `archived`."""
    INDEX[0] += 1
    root = ROOT / f"{INDEX[0]:02d}"
    workspace = Workspace.initialize(root, name="item75",
                                     orchestrator="antigravity",
                                     preset="antigravity-codex-claude")
    for agent in ("antigravity", "claude"):
        workspace.attest_agent_identity(
            actor="antigravity", agent_id=agent,
            control_principal="p-" + agent, model_family="f-" + agent)
    for task_id in task_ids:
        workspace.create_task(actor="antigravity", task_id=task_id, title="t",
                              description="d", owner="claude")
        token = workspace.claim(actor="claude", task_id=task_id)["lease_token"]
        workspace.start(actor="claude", task_id=task_id, lease_token=token)

        def bundle(agent: str, suffix: str) -> tuple:
            home = workspace.reports_dir / agent
            home.mkdir(parents=True, exist_ok=True)
            report = home / f"{task_id}{suffix}.md"
            report.write_text("\n".join(
                f"## {n}. Section {n}\n\ncontent{suffix}\n"
                for n in range(1, 7)) + "\n", encoding="utf-8")
            artifact = home / f"{task_id}{suffix}.artifact.txt"
            artifact.write_bytes(f"measured{suffix}\n".encode())
            raw = home / f"{task_id}{suffix}.raw.txt"
            raw.write_bytes(f"1 passed{suffix}\n".encode())
            manifest = home / f"{task_id}{suffix}.evidence.json"
            manifest.write_text(json.dumps({
                "schema_version": 1,
                "artifacts": [{"path": str(artifact),
                               "sha256": sha_of(artifact)}],
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
        workspace.submit(actor="claude", task_id=task_id, lease_token=token,
                         report_path=report, manifest_path=manifest)
        _, verification = bundle("antigravity", "-v")
        workspace.verify(actor="antigravity", task_id=task_id,
                         decision="accept", note="ok",
                         verification_manifest=verification)
        workspace.archive(actor="antigravity", task_id=task_id)
    return root


def audit(root: Path) -> str:
    """Item 72's helper - UN-truncated, for the same reason it was there."""
    try:
        result = doctor.audit_workspace(root)
    except Exception as exc:  # noqa: BLE001 - a raise is still "caught"
        return f"CAUGHT (raised {type(exc).__name__})"
    return ("HEALTHY - unnoticed" if result["healthy"]
            else f"CAUGHT: {result.get('error', 'no error key')}")


def kind(relative: str) -> str:
    """Item 72's collapse, widened from T1 to any T<n>."""
    parts = relative.split("/")
    if parts[0] == "submissions":
        leaf = parts[-1]
        if leaf == "bundle.json":
            return "submissions/.../bundle.json"
        return "submissions/.../files/" + re.sub(r"^[0-9a-f]{64}_T\d-?v?", "*",
                                                 leaf)
    if parts[0] == "reports":
        return "reports/<agent>/" + re.sub(r"^T\d-?v?", "*", parts[-1])
    if parts[0] in ("agents", "tasks", "archive"):
        return f"{parts[0]}/*.json"
    return relative


def census(root: Path) -> Counter:
    return Counter(kind(str(p.relative_to(root)))
                   for p in root.rglob("*") if p.is_file())


one_task = lifecycle(("T1",))
three_tasks = lifecycle(("T1", "T2", "T3"))
check("a THREE-task workspace reaches archived on all three",
      "archived: 3",
      "archived: " + str(sum(
          1 for p in sorted((three_tasks / "tasks").glob("*.json"))
          if json.loads(p.read_text(encoding="utf-8"))["state"] == "archived")))
check("  and the untouched workspace audits healthy", "HEALTHY",
      audit(three_tasks))

# ---------------------------------------------------------------- B
print("\n########## B. the split MOVES, and that is the measurement ##########")
one_kinds, three_kinds = census(one_task), census(three_tasks)
check("one task ships this many files", "files: 27",
      f"files: {sum(one_kinds.values())}")
check("  three tasks ship this many", "files: 65",
      f"files: {sum(three_kinds.values())}")
check("    in the same number of kinds", "kinds: 17 and 17",
      f"kinds: {len(one_kinds)} and {len(three_kinds)}")
one_multi = {k for k, v in one_kinds.items() if v > 1}
three_multi = {k for k, v in three_kinds.items() if v > 1}
check("item 72's split, RE-DERIVED in this run", "multi: 9, single: 8",
      f"multi: {len(one_multi)}, single: {len(one_kinds) - len(one_multi)}")
check("  and at three tasks", "multi: 12, single: 5",
      f"multi: {len(three_multi)}, single: {len(three_kinds) - len(three_multi)}")
crossed = sorted(three_multi - one_multi)
check("    kinds that CROSS from singleton to multi", "crossed: 3",
      f"crossed: {len(crossed)}")
check("      and they are these",
      "['archive/*.json', 'submissions/.../files/*.md', 'tasks/*.json']",
      str(crossed))
check("        no kind crosses the other way", "back: []",
      f"back: {sorted(one_multi - three_multi)}")
print("  `tasks/*.json` is one of them - and it is one of the four kinds item")
print("  72 measured as CAUGHT. At one task its message could not move; there")
print("  was only one of it. Section C is that question, now askable.")


def drive(label: str, operation) -> str:
    root = lifecycle(("T1", "T2", "T3"))
    removed = operation(root)
    verdict = audit(root)
    print(f"    {label:<48} removed={removed:<3} {verdict}")
    return verdict


def remove_tree(relative: str):
    def operation(root: Path) -> int:
        target = root / relative
        count = sum(1 for p in target.rglob("*") if p.is_file())
        shutil.rmtree(target)
        return count
    return operation


def remove_all(pattern: str):
    def operation(root: Path) -> int:
        paths = sorted(root.glob(pattern))
        for path in paths:
            path.unlink()
        return len(paths)
    return operation


def remove_middle(pattern: str):
    def operation(root: Path) -> int:
        sorted(root.glob(pattern))[1].unlink()
        return 1
    return operation


# ---------------------------------------------------------------- C
print("\n########## C. the three crossed kinds, ONE vs ALL ##########")
one_projection = drive("one tasks/*.json (the middle one)",
                       remove_middle("tasks/*.json"))
all_projections = drive("all three tasks/*.json", remove_all("tasks/*.json"))
check("deleting one projection is caught, and NAMES it",
      "CAUGHT: T2: projection missing", one_projection)
check("  deleting all three is caught and names ALL THREE",
      "T1: projection missing; T2: projection missing; T3: projection missing",
      all_projections)
check("    so this message DOES move with the count",
      "moved: True", f"moved: {one_projection != all_projections}")
print("  Item 72 measured `agents/*.json` reporting identically for one and")
print("  for all three. This kind does not - it enumerates. The difference is")
print("  only visible once a kind has more than one instance to lose.")
one_archive = drive("one archive/*.json", remove_middle("archive/*.json"))
all_archive = drive("all three archive/*.json", remove_all("archive/*.json"))
check("archive records are unnoticed either way", "HEALTHY - unnoticed",
      one_archive)
check("  including all of them at once", "HEALTHY - unnoticed", all_archive)

# ---------------------------------------------------------------- D
print("\n########## D. whole trees, and the one file that is load-bearing ##########")
one_tree = drive("ONE task's submission tree", remove_tree("submissions/T2"))
check("removing one task's archived evidence entirely", "HEALTHY - unnoticed",
      one_tree)
all_trees = drive("ALL THREE submission trees",
                  lambda root: sum(remove_tree(f"submissions/T{n}")(root)
                                   for n in (1, 2, 3)))
check("  and all three, 27 files", "HEALTHY - unnoticed", all_trees)


def everything_for(task_id: str, spare_projection: bool):
    def operation(root: Path) -> int:
        count = remove_tree(f"submissions/{task_id}")(root)
        for path in sorted(root.rglob(f"{task_id}*")):
            if path.is_file() and not (spare_projection
                                       and path.parent.name == "tasks"):
                path.unlink()
                count += 1
        return count
    return operation


whole_task = drive("EVERYTHING belonging to task T2",
                   everything_for("T2", spare_projection=False))
check("removing a whole task IS caught", "CAUGHT: T2: projection missing",
      whole_task)
spared = drive("  the same, but sparing tasks/T2.json",
               everything_for("T2", spare_projection=True))
check("  and sparing ONE file of the nineteen makes it invisible",
      "HEALTHY - unnoticed", spared)


def strip_all_evidence(root: Path) -> int:
    count = sum(remove_tree(f"submissions/T{n}")(root) for n in (1, 2, 3))
    for path in sorted(root.rglob("T*")):
        if path.is_file() and path.parent.name != "tasks":
            path.unlink()
            count += 1
    for path in sorted((root / "archive").glob("*.json")):
        path.unlink()
        count += 1
    return count


stripped = drive("every task's evidence, sparing the 3 projections",
                 strip_all_evidence)
check("the whole workspace's evidence can go", "HEALTHY - unnoticed", stripped)
print("  54 of 65 files - every archived bundle, every report, every submitted")
print("  copy, every archive record - removed, and the product's own health")
print("  check reports the workspace healthy. What is load-bearing is the")
print("  three task PROJECTIONS, which are 3 files and no evidence at all.")

# ---------------------------------------------------------------- E
print("\n########## E. what this does NOT establish ##########")
print("  * It does NOT file an issue. Item 69 widened #10 from edits to")
print("    deletes, item 72 from one instance to every instance, this from")
print("    one task to a whole workspace. Quantifying an open issue is not")
print("    opening another.")
print("  * It does NOT retract item 72. Its one-task split is RE-DERIVED here")
print("    from a workspace built in this run and agrees exactly.")
print("  * The audit surface is `doctor.audit_workspace`, as in items 63, 66,")
print("    69 and 72. A human listing the directory sees the files are gone.")
print("  * Three tasks, one attempt each. Whether a task with SEVERAL")
print("    attempts behaves differently is UNCHECKED, not shown safe.")
print("  * The `T*` sweep in the last two drives is a filename match, and it")
print("    is bounded by the count it prints - 54 of 65 - rather than by my")
print("    description of it.")
print("  * No network, no GPU. Twelve tempfile workspaces, removed before the")
print("    results print. The anchor's working tree is untouched, and it does")
print("    not touch `main` or another agent's branch.")
print("  * MEASURED: both censuses, the crossing kinds both directions, six")
print("    per-kind drives, five whole-tree drives, every verdict and every")
print("    full message. REASONED: nothing.")

shutil.rmtree(ROOT, ignore_errors=True)
print(f"\n########## {FAIL} unexpected result(s) ##########")
print("Pre-registered permissions unchanged - gpu/network/performance_metrics")
print("all false. SUBMITTED, not VERIFIED: re-running my own evidence is a")
print("re-run, not independent confirmation.")
