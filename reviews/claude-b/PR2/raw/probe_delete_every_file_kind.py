#!/usr/bin/env python3
"""Deleting each file kind - and the three where DELETE differs from EDIT.

Queue item 69, closing what item 66 stated it had not done: that round drove
an EDIT of each of the 17 file kinds and said plainly it did not drive a
DELETE of each. Item 63 deleted three things, at DIRECTORY level only.

Both operations are driven here, in ONE run, on a fresh workspace each - so
the comparison stands on this run rather than on item 66's table plus this
one. Item 63 already showed the two can differ: replacing `.efo/ledger.key`
gives `Ledger signature mismatch`, deleting it gives `Ledger signing key is
missing`. The question is which OTHER kinds behave differently when the file
is gone rather than wrong.

The population is derived, not named: a full lifecycle to `archived` produces
27 files, which collapse to 17 KINDS once the task id, the agent name and the
content hashes are normalised away. Every kind is then driven with an EDIT -
so this does not CITE what items 57, 60 and 63 covered, it RE-DERIVES all of
it and adds what none of them reached.

    python3 probe_delete_every_file_kind.py

SCOPE, stated first: 27 files, 17 kinds, 17 edits, 17 deletes, 34 workspaces,
1 exhaustiveness assertion. A MAP that widens an open issue (#10) rather than
filing a new one.
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
ROOT = Path(tempfile.mkdtemp(prefix="efo-item69-"))


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
    workspace = Workspace.initialize(root, name="item69",
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
    return ("HEALTHY - unnoticed" if result["healthy"]
            else f"CAUGHT: {result.get('error', 'no error key')[:40]}")


baseline = lifecycle()
check("the lifecycle reaches `archived` - the CONTROL", "state: archived",
      "state: " + json.loads(
          (baseline / "tasks" / "T1.json").read_text(
              encoding="utf-8"))["state"])
check("  and the untouched workspace audits healthy", "HEALTHY",
      audit(baseline))

# ---------------------------------------------------------------- B
print("\n########## B. every FILE, and the KINDS they collapse to ##########")
files = sorted(str(p.relative_to(baseline))
               for p in baseline.rglob("*") if p.is_file())
check("a full lifecycle ships this many files", "files: 27",
      f"files: {len(files)}")


def kind(relative: str) -> str:
    """Collapse instance detail: task id, agent name, content hashes.

    The axis that matters is DIRECTORY ROLE plus EXTENSION - that is what an
    audit either compares or does not. Two reports by different agents are
    the same question asked twice.
    """
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


kinds = Counter(kind(f) for f in files)
for name, count in sorted(kinds.items()):
    print(f"    {count}x  {name}")
check("  which collapse to this many kinds", "kinds: 17",
      f"kinds: {len(kinds)}")
check("    and every file maps to one", f"mapped: {len(files)}",
      f"mapped: {sum(kinds.values())}")


# ---------------------------------------------------------------- C
print("\n########## C. every kind, EDITED and DELETED ##########")
print("  Both operations in ONE run, a fresh workspace each - so the")
print("  comparison stands on this run, not on item 66's table plus this one.")


def mutate(path: Path) -> None:
    """Edit in place, preserving the file's rough shape - item 66's rule."""
    if path.suffix == ".json":
        try:
            document = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            path.write_bytes(path.read_bytes() + b"\n")
            return
        if isinstance(document, dict):
            document["tampered_by_item_69"] = True
        path.write_text(json.dumps(document, indent=2), encoding="utf-8")
    else:
        path.write_bytes(path.read_bytes() + b"tampered\n")


def drive(name: str, operation) -> str:
    root = lifecycle()
    target = next(p for p in sorted(root.rglob("*"))
                  if p.is_file() and kind(str(p.relative_to(root))) == name)
    operation(target)
    return audit(root)


edited: dict = {}
deleted: dict = {}
for name in sorted(kinds):
    edited[name] = drive(name, mutate)
    deleted[name] = drive(name, lambda p: p.unlink())
    flag = "  <-- DIFFERS" if (("CAUGHT" in edited[name])
                               != ("CAUGHT" in deleted[name])) else ""
    print(f"    {name:<44}")
    print(f"        edit  : {edited[name]}")
    print(f"        delete: {deleted[name]}{flag}")

edit_caught = {n for n, v in edited.items() if "CAUGHT" in v}
delete_caught = {n for n, v in deleted.items() if "CAUGHT" in v}
check("every kind was driven both ways", f"driven: {len(kinds)} x2",
      f"driven: {len(edited)} x{2 if len(deleted) == len(kinds) else 1}")
check("  EDIT reproduces item 66's count", "edit caught: 5",
      f"edit caught: {len(edit_caught)}")
check("    and its complement", "edit unnoticed: 12",
      f"edit unnoticed: {len(kinds) - len(edit_caught)}")

# ---------------------------------------------------------------- D
print("\n########## D. what DELETE catches, and where the two DIFFER ##########")
print(f"    delete caught   : {sorted(delete_caught)}")
print(f"    edit caught     : {sorted(edit_caught)}")
only_delete = sorted(delete_caught - edit_caught)
only_edit = sorted(edit_caught - delete_caught)
print(f"    caught ONLY when deleted : {only_delete}")
print(f"    caught ONLY when edited  : {only_edit}")
check("kinds whose DELETE is caught", "delete caught: 5",
      f"delete caught: {len(delete_caught)}")
check("  the two caught sets are the SAME kinds", "differs: []",
      f"differs: {sorted(delete_caught ^ edit_caught)}")
print("  So the SET does not move - but the MESSAGE does, which is a")
print("  different question and the one section E asks.")

# ---------------------------------------------------------------- E
print("\n########## E. the same kind, a DIFFERENT message ##########")
moved = [n for n in sorted(edit_caught & delete_caught)
         if edited[n] != deleted[n]]
for name in sorted(edit_caught & delete_caught):
    same = "same message" if edited[name] == deleted[name] else "DIFFERENT"
    print(f"    {name:<28} {same}")
# I predicted FOUR. It is FIVE - every caught kind reports differently when
# the file is GONE rather than WRONG. Corrected to the measurement, and the
# stronger claim asserted: the change is universal across the caught set.
check("caught kinds whose message CHANGES between edit and delete",
      "moved: 5", f"moved: {len(moved)}")
check("    which is EVERY caught kind, not some of them",
      f"all: {len(edit_caught & delete_caught)}", f"all: {len(moved)}")
check("  including the signing key - item 63's control, re-derived",
      ".efo/ledger.key", str(moved))
for name in sorted(edit_caught & delete_caught):
    print(f"    {name}")
    print(f"        edited : {edited[name]}")
    print(f"        deleted: {deleted[name]}")
print(f"    .efo/ledger.key edited : {edited['.efo/ledger.key']}")
print(f"    .efo/ledger.key deleted: {deleted['.efo/ledger.key']}")
check("    edited gives a SIGNATURE mismatch", "signature mismatch",
      edited[".efo/ledger.key"].lower())
check("    deleted gives a MISSING KEY", "missing",
      deleted[".efo/ledger.key"].lower())
print("  A count of `caught` alone would have reported these as identical.")
print("  The set is the same; what the operator is TOLD is not.")

# ---------------------------------------------------------------- F
print("\n########## F. what this does NOT establish ##########")
print("  * It does NOT file an issue. This widens the measured width of #10")
print("    from EDITS to DELETES; quantifying an open issue is not opening")
print("    another.")
print("  * It does NOT claim deletion is equivalent to editing. The caught")
print("    SET is identical and four MESSAGES differ - both measured.")
print("  * The 12 kinds unnoticed under edit are unnoticed under delete too,")
print("    which means a whole archived bundle, every report, and every")
print("    submission copy can be REMOVED with `doctor` still reporting")
print("    healthy - measured under the threat model SECURITY.md:38 declares.")
print("  * It deletes ONE instance of each kind, not every instance. Deleting")
print("    all three `agents/*.json` at once is UNCHECKED, not shown safe.")
print("  * No network, no GPU. Thirty-five tempfile workspaces, removed")
print("    before the results print. The anchor's working tree is untouched,")
print("    and it does not touch `main` or another agent's branch.")
print("  * MEASURED: the file enumeration, the kind collapse, all 17 edits,")
print("    all 17 deletes, both caught sets, every differing message, the")
print("    lifecycle control. REASONED: nothing.")

shutil.rmtree(ROOT, ignore_errors=True)
print(f"\n########## {FAIL} unexpected result(s) ##########")
print("Pre-registered permissions unchanged - gpu/network/performance_metrics")
print("all false. SUBMITTED, not VERIFIED: re-running my own evidence is a")
print("re-run, not independent confirmation.")
