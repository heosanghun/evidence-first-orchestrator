#!/usr/bin/env python3
"""Deleting EVERY instance of a kind - and the whole attempt tree at once.

Queue item 72, closing what item 69 stated it had not done: that round deleted
ONE instance of each of the 17 kinds and said plainly that deleting ALL three
`agents/*.json`, or the whole `submissions/T1/attempt-001/` tree at once, was
UNCHECKED - not shown safe.

The population is derived, not named. A full lifecycle to `archived` ships 27
files in 17 kinds; NINE kinds have more than one instance and EIGHT have
exactly one. For a singleton, "delete one" and "delete all" are the same file
set, which is measured here rather than argued, and those eight then serve as
the positive control: they must reproduce item 69's delete column exactly.

    python3 probe_delete_every_instance_of_a_kind.py

SCOPE, stated first: 27 files, 17 kinds, 9 multi-instance, 8 singleton, 26
deletion drives, 1 whole-subtree delete, 1 exhaustiveness assertion. A MAP
that widens the measured width of #10 again, rather than filing a new issue.
Roughly 170s - it builds 28 workspaces and drives each to `archived`.
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
ROOT = Path(tempfile.mkdtemp(prefix="efo-item72-"))


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

INDEX = [0]


def lifecycle() -> Path:
    """A workspace driven to `archived`, keyed by INDEX rather than by name."""
    INDEX[0] += 1
    root = ROOT / f"{INDEX[0]:02d}"
    workspace = Workspace.initialize(root, name="item72",
                                     orchestrator="antigravity",
                                     preset="antigravity-codex-claude")
    for agent in ("antigravity", "claude"):
        workspace.attest_agent_identity(
            actor="antigravity", agent_id=agent,
            control_principal="p-" + agent, model_family="f-" + agent)
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
    # NOT truncated. Item 69's helper cut the message at 40 characters, and
    # this round's whole question is whether the message MOVES - a truncation
    # would hide exactly the difference being tested for.
    return ("HEALTHY - unnoticed" if result["healthy"]
            else f"CAUGHT: {result.get('error', 'no error key')}")


baseline = lifecycle()
check("the lifecycle reaches `archived` - the CONTROL", "state: archived",
      "state: " + json.loads(
          (baseline / "tasks" / "T1.json").read_text(
              encoding="utf-8"))["state"])
check("  and the untouched workspace audits healthy", "HEALTHY",
      audit(baseline))

# ---------------------------------------------------------------- B
print("\n########## B. the kinds, and how many INSTANCES each has ##########")


def kind(relative: str) -> str:
    """Item 69's collapse, re-derived rather than imported."""
    parts = relative.split("/")
    if parts[0] == "submissions":
        leaf = parts[-1]
        if leaf == "bundle.json":
            return "submissions/.../bundle.json"
        return "submissions/.../files/" + re.sub(r"^[0-9a-f]{64}_T1-?v?", "*",
                                                 leaf)
    if parts[0] in ("reports",):
        return f"reports/<agent>/{re.sub(r'^T1-?v?', '*', parts[-1])}"
    if parts[0] in ("agents", "tasks", "archive"):
        return f"{parts[0]}/*.json"
    return relative


files = sorted(str(p.relative_to(baseline))
               for p in baseline.rglob("*") if p.is_file())
kinds = Counter(kind(f) for f in files)
check("a full lifecycle ships this many files", "files: 27",
      f"files: {len(files)}")
check("  collapsing to this many kinds", "kinds: 17", f"kinds: {len(kinds)}")
MULTI = sorted(name for name, count in kinds.items() if count > 1)
SINGLE = sorted(name for name, count in kinds.items() if count == 1)
for name in MULTI:
    print(f"    {kinds[name]}x  {name}")
check("kinds with MORE THAN ONE instance - the only ones this round can move",
      "multi: 9", f"multi: {len(MULTI)}")
check("  and singletons, where delete-one IS delete-all", "single: 8",
      f"single: {len(SINGLE)}")
check("    the split is exhaustive in both directions", f"total: {len(kinds)}",
      f"total: {len(MULTI) + len(SINGLE)}")
check("      and accounts for every file", f"files: {len(files)}",
      f"files: {sum(kinds.values())}")
check("  the biggest is agents/*.json, the one item 69 named", "agents: 3",
      f"agents: {kinds['agents/*.json']}")


def drive(name: str, every: bool) -> tuple[str, int]:
    """Delete one instance of a kind, or all of them, then audit."""
    root = lifecycle()
    targets = [p for p in sorted(root.rglob("*"))
               if p.is_file() and kind(str(p.relative_to(root))) == name]
    chosen = targets if every else targets[:1]
    for path in chosen:
        path.unlink()
    return audit(root), len(chosen)


# ---------------------------------------------------------------- C
print("\n########## C. the eight singletons - the POSITIVE CONTROL ##########")
print("  For a singleton the two operations delete the same file, so these")
print("  must reproduce item 69's delete column. If they do not, the driver")
print("  is wrong and nothing in section D can be trusted.")
single_result = {}
for name in SINGLE:
    verdict, count = drive(name, True)
    single_result[name] = verdict
    check(f"    {name}", "deleted: 1", f"deleted: {count}")
single_caught = {n for n, v in single_result.items() if "CAUGHT" in v}
check("  singleton kinds whose deletion is CAUGHT", "caught: 4",
      f"caught: {len(single_caught)}")
check("    and they are item 69's four singletons",
      "['.efo/ledger.key', '.efo/workspace.json', 'ledger/events.jsonl', "
      "'tasks/*.json']", str(sorted(single_caught)))
for name in sorted(single_caught):
    print(f"      {name:<28} {single_result[name]}")

# ---------------------------------------------------------------- D
print("\n########## D. the nine multi-instance kinds, ONE vs ALL ##########")
one: dict = {}
every: dict = {}
counts: dict = {}
for name in MULTI:
    one[name], _ = drive(name, False)
    every[name], counts[name] = drive(name, True)
    flag = "  <-- DIFFERS" if one[name] != every[name] else ""
    print(f"    {name:<44} ({counts[name]} instances)")
    print(f"        one: {one[name]}")
    print(f"        all: {every[name]}{flag}")
check("every multi-instance kind driven BOTH ways", f"driven: {len(MULTI)}",
      f"driven: {len(one)}")
check("  and `all` really deleted more than `one` each time",
      "more: 9", f"more: {sum(1 for n in MULTI if counts[n] > 1)}")
moved = sorted(n for n in MULTI if one[n] != every[n])
check("kinds whose VERDICT or MESSAGE changes when every instance goes",
      "moved: 0", f"moved: {len(moved)} {moved}")
one_caught = {n for n in MULTI if "CAUGHT" in one[n]}
all_caught = {n for n in MULTI if "CAUGHT" in every[n]}
check("  caught when ONE instance is deleted", "one caught: 1",
      f"one caught: {len(one_caught)}")
check("    and when EVERY instance is", "all caught: 1",
      f"all caught: {len(all_caught)}")
check("      the same kind, agents/*.json", "['agents/*.json']",
      str(sorted(all_caught)))
print("      one agent record deleted : "
      f"{one['agents/*.json']}")
print("      all three deleted         : "
      f"{every['agents/*.json']}")
check("        and the two messages are identical in FULL, not truncated",
      one["agents/*.json"], every["agents/*.json"])
print("  So EIGHT multi-instance kinds can be removed ENTIRELY - every")
print("  report, every submitted copy, both bundles - with doctor healthy.")

# ---------------------------------------------------------------- E
print("\n########## E. the whole attempt tree, in one operation ##########")
tree_root = lifecycle()
attempt = next(p for p in sorted(tree_root.rglob("attempt-*")) if p.is_dir())
removed = sorted(str(p.relative_to(tree_root))
                 for p in attempt.rglob("*") if p.is_file())
shutil.rmtree(attempt)
tree_verdict = audit(tree_root)
check("the archived submission tree holds this many files", "removed: 9",
      f"removed: {len(removed)}")
check("  and removing the whole of it is", "HEALTHY - unnoticed", tree_verdict)
check("    with the task still reporting archived", "state: archived",
      "state: " + json.loads(
          (tree_root / "tasks" / "T1.json").read_text(
              encoding="utf-8"))["state"])
print("  Item 63 deleted TOP-LEVEL directories. This is a sub-tree, the one")
print("  that holds the archived evidence itself, and it is the shape an")
print("  operator would actually reach for - `rm -rf` on one attempt.")

# ---------------------------------------------------------------- F
print("\n########## F. what this does NOT establish ##########")
print("  * It does NOT file an issue. This widens the measured width of #10")
print("    a second time - item 69 went from edits to deletes, this goes")
print("    from one instance to every instance. Quantifying an open issue is")
print("    not opening another.")
print("  * It does NOT retract item 69. Its one-instance column is")
print("    re-derived here for the eight singletons and agrees.")
print("  * The audit surface is `doctor.audit_workspace`, the same one items")
print("    63, 66 and 69 used. A human listing the directory sees the files")
print("    are gone; the product's own health check does not.")
print("  * It does NOT delete across TASKS - one task, one attempt. Whether a")
print("    workspace with several archived tasks behaves differently is")
print("    UNCHECKED, not shown safe.")
print("  * No network, no GPU. Twenty-eight tempfile workspaces, removed")
print("    before the results print. The anchor's working tree is untouched,")
print("    and it does not touch `main` or another agent's branch.")
print("  * MEASURED: the file enumeration, the kind collapse, the instance")
print("    counts, all eight singleton deletes, all nine kinds both ways, the")
print("    whole-subtree delete, the lifecycle control. REASONED: nothing.")

shutil.rmtree(ROOT, ignore_errors=True)
print(f"\n########## {FAIL} unexpected result(s) ##########")
print("Pre-registered permissions unchanged - gpu/network/performance_metrics")
print("all false. SUBMITTED, not VERIFIED: re-running my own evidence is a")
print("re-run, not independent confirmation.")
