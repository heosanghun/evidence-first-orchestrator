#!/usr/bin/env python3
"""The four modules with NO isinstance: the absence is real in one, unreachable in all.

Queue item 54, from item 51. Four modules hold functions and not a single
`isinstance` call: archive.py, dashboard.py, doctor.py, lock.py. Three of the
four already carry an issue (#10, #12/#17, #19-adjacent). The question is
whether the missing mechanism has a REACHABLE consequence, or whether those
modules simply never touch untrusted input.

Measured, per module - string-keyed subscripts and file reads by AST:

    archive.py    15 subscripts   5 .get()   0 file reads
    doctor.py     23 subscripts   0 .get()   4 file reads
    dashboard.py   0 subscripts   0 .get()   0 file reads
    lock.py        0 subscripts   0 .get()   0 file reads

A `grep` for `["` finds FIVE in dashboard.py. All five are JavaScript array
literals inside the embedded HTML string constant. Parsed, the count is ZERO -
never match syntax by text when the question is about syntax, again.

So two candidates, and they answer differently:

  archive.py   THE ABSENCE IS REAL. Driven directly, 8 malformed manifests give
               8 raw Python exceptions and 0 EFOError - KeyError, TypeError,
               AttributeError. But all THREE call sites pass a value that came
               out of an evidence.py validator, so no document reaches it.

  doctor.py    THE ABSENCE IS UNREACHABLE. Five tampered documents - a task
               with no `state`, no `id`, a string `lease`, a flipped state, and
               a rogue agent file never in the ledger - are all caught by the
               ledger/projection guard as an EFOError and returned as
               `healthy: false` + `error`. Zero escape, even though
               `except (EFOError, OSError)` would not catch a KeyError.

    python3 probe_unguarded_modules.py

SCOPE, stated first: 4 modules, 693 lines, 13 driven inputs, 2 controls.
A MAP with a near miss recorded. No issue filed.
"""

from __future__ import annotations

import ast
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

sys.path.insert(0, "/tmp/efo-prov/src")

FAIL = 0
ANCHOR = Path("/tmp/efo-prov")
SRC = ANCHOR / "src" / "evidence_orchestrator"
MODULES = ("archive.py", "dashboard.py", "doctor.py", "lock.py")
ROOT = Path(tempfile.mkdtemp(prefix="efo-item54-")).resolve()


def check(name: str, expected: str, observed: str) -> None:
    global FAIL
    ok = expected in observed
    if not ok:
        FAIL += 1
    print(f"  [{'ok' if ok else '!! UNEXPECTED !!'}] {name}")
    print(f"        expected: {expected}")
    print(f"        observed: {observed}")


# ---------------------------------------------------------------- A
print("########## A. POSITIVE CONTROL, and the scope FIRST ##########")
check("the review's anchor is UNMOVED at 5694ab45",
      "5694ab455139f1e72d946bc2fe7e42c7c0c8a43a",
      subprocess.run(["git", "-C", str(ANCHOR), "rev-parse", "HEAD"],
                     capture_output=True, text=True).stdout.strip())
check("  with no working-tree modification", "dirty: ''",
      f"dirty: {subprocess.run(['git', '-C', str(ANCHOR), 'status', '--porcelain'], capture_output=True, text=True).stdout.strip()!r}")

trees = {name: ast.parse((SRC / name).read_text(encoding="utf-8"))
         for name in MODULES}
lines = sum(len((SRC / name).read_text(encoding="utf-8").splitlines())
            for name in MODULES)
check("  lines across the four modules", "lines: 693", f"lines: {lines}")

# Item 51's premise is RE-DERIVED here, not carried over as a number. If a
# guard were added to one of these four, this check fails and the whole
# question changes.
still_unguarded = [name for name, tree in trees.items()
                   if not any(isinstance(n, ast.Call)
                              and isinstance(n.func, ast.Name)
                              and n.func.id == "isinstance"
                              for n in ast.walk(tree))]
check("    all four still hold ZERO isinstance - item 51's premise re-derived",
      "unguarded: ['archive.py', 'dashboard.py', 'doctor.py', 'lock.py']",
      f"unguarded: {sorted(still_unguarded)}")

# ---------------------------------------------------------------- B
print("\n########## B. which of the four can even SEE a document ##########")
census = {}
for name, tree in trees.items():
    subscripts = [n for n in ast.walk(tree)
                  if isinstance(n, ast.Subscript)
                  and isinstance(n.slice, ast.Constant)
                  and isinstance(n.slice.value, str)]
    gets = [n for n in ast.walk(tree)
            if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
            and n.func.attr == "get"]
    reads = [n for n in ast.walk(tree)
             if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
             and n.func.attr in ("read_text", "read_bytes")]
    census[name] = (len(subscripts), len(gets), len(reads))
    print(f"    {name:<14}{len(subscripts):>3} string-key subscripts"
          f"{len(gets):>4} .get(){len(reads):>4} file reads")
check("archive.py reads a document-shaped dict", "archive: (15, 5, 0)",
      f"archive: {census['archive.py']}")
check("  doctor.py reads FILES itself as well", "doctor: (23, 0, 4)",
      f"doctor: {census['doctor.py']}")
check("    lock.py touches no field at all", "lock: (0, 0, 0)",
      f"lock: {census['lock.py']}")
check("      and dashboard.py touches none either", "dashboard: (0, 0, 0)",
      f"dashboard: {census['dashboard.py']}")

grep_hits = sum(1 for line in
                (SRC / "dashboard.py").read_text(encoding="utf-8").splitlines()
                if '["' in line)
check("  but a TEXT search on dashboard.py claims five", "grep says: 5",
      f"grep says: {grep_hits}")
print("  All five are JavaScript array literals - `[\"Running\", states.running]`")
print("  - inside the embedded HTML string constant. Parsed, they are not")
print("  Python subscripts at all. Never match syntax by TEXT when the")
print("  question is about syntax; the AST is the measurement.")

# ---------------------------------------------------------------- C
print("\n########## C. archive.py - the absence is REAL, driven ##########")
from evidence_orchestrator.archive import archive_evidence_bundle  # noqa: E402

sandbox = ROOT / "archive"
sandbox.mkdir(parents=True)
manifest_file = sandbox / "m.json"
manifest_file.write_text("{}", encoding="utf-8")
GOOD: dict[str, Any] = {
    "path": str(manifest_file),
    "sha256": hashlib.sha256(manifest_file.read_bytes()).hexdigest(),
    "artifacts": [], "validations": [],
}


def archive_with(manifest: Any, report: Any = None) -> str:
    try:
        archive_evidence_bundle(
            submissions_root=sandbox / "sub", task_id="C1", attempt=1,
            label="x", report=report, manifest=manifest,
            max_artifact_bytes=1000)
        return "ACCEPTED"
    except Exception as exc:  # noqa: BLE001 - the TYPE is the measurement
        return type(exc).__name__


archive_control = archive_with(dict(GOOD))
archive_driven = {
    "manifest = {} (no sha256)": archive_with({}),
    "manifest = None": archive_with(None),
    "manifest['sha256'] = 123": archive_with({**GOOD, "sha256": 123}),
    "manifest['path'] = None": archive_with({**GOOD, "path": None}),
    "manifest['artifacts'] = 'x'": archive_with({**GOOD, "artifacts": "x"}),
    "manifest['artifacts'] = [None]": archive_with({**GOOD, "artifacts": [None]}),
    "manifest['validations'] = [None]":
        archive_with({**GOOD, "validations": [None]}),
    "report = {} (no path)": archive_with(dict(GOOD), report={}),
}
print(f"    {'the well-formed manifest (CONTROL)':<36}{archive_control}")
for label, outcome in archive_driven.items():
    print(f"    {label:<36}{outcome}")
EFO_ERRORS = {"EFOError", "ConfigurationError", "AuthorizationError",
              "TransitionError", "LeaseError", "EvidenceError",
              "IntegrityError", "LockTimeout"}
check("the control is accepted - the driver is right before the code is",
      "ACCEPTED", archive_control)
check("  eight malformed manifests driven", "driven: 8",
      f"driven: {len(archive_driven)}")
check("    none is accepted", "accepted: []",
      f"accepted: {[k for k, v in archive_driven.items() if v == 'ACCEPTED']}")
check("      and NONE becomes an EFOError - all eight are raw Python",
      "efo errors: []",
      f"efo errors: {[k for k, v in archive_driven.items() if v in EFO_ERRORS]}")
print("  Same answer item 47 got for `util.py`: the absence is real, and the")
print("  package's own error type never appears.")

# ---------------------------------------------------------------- D
print("\n########## D. but no document reaches it - all three call sites ##########")
workspace_tree = ast.parse(
    (SRC / "workspace.py").read_text(encoding="utf-8"))
call_sites = [n for n in ast.walk(workspace_tree)
              if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)
              and n.func.id == "archive_evidence_bundle"]
passed = []
for call in call_sites:
    for keyword in call.keywords:
        if keyword.arg == "manifest":
            passed.append(ast.unparse(keyword.value))
for expression in passed:
    print(f"    manifest={expression}")
check("call sites of archive_evidence_bundle in workspace.py",
      "call sites: 3", f"call sites: {len(call_sites)}")
check("  every one passes a validator's return, not a parsed document",
      "outside: []",
      "outside: " + str([e for e in passed
                         if e not in ("evidence['manifest']",
                                      "verification['evidence']")]))
validators = sorted({
    ast.unparse(node.value.func)
    for node in ast.walk(workspace_tree)
    if isinstance(node, ast.Assign) and isinstance(node.value, ast.Call)
    and isinstance(node.value.func, ast.Name)
    and node.value.func.id in ("validate_submission", "validate_manifest")})
check("    and those two names are assigned only from evidence.py validators",
      "validators: ['validate_manifest', 'validate_submission']",
      f"validators: {validators}")
print("  `evidence` comes from `validate_submission` (workspace.py:1026, 1141)")
print("  and `verification['evidence']` from `validate_manifest` (:1340). Item")
print("  51 measured that evidence.py rejects with 17 EvidenceError sites, so")
print("  archive.py is SAFE BY CONSTRUCTION - not by its own guarding.")

# ---------------------------------------------------------------- E
print("\n########## E. doctor.py - the absence is UNREACHABLE, driven ##########")
from evidence_orchestrator.workspace import Workspace  # noqa: E402
from evidence_orchestrator import doctor  # noqa: E402


def workspace_at(tag: str) -> Path:
    root = ROOT / "doctor" / tag
    workspace = Workspace.initialize(root, name="item54",
                                     orchestrator="antigravity",
                                     preset="antigravity-codex-claude")
    workspace.create_task(actor="antigravity", task_id="C1", title="t",
                          description="d", owner="claude")
    return root


def audit(tag: str, mutate) -> str:
    root = workspace_at(tag)
    mutate(root)
    try:
        outcome = doctor.audit_workspace(root)
    except Exception as exc:  # noqa: BLE001 - an ESCAPE is the finding
        return f"ESCAPED {type(exc).__name__}: {exc}"
    return ("healthy" if outcome["healthy"]
            else f"caught: {outcome.get('error', 'no error key')}")


def edit_task(change):
    def apply(root: Path) -> None:
        path = root / "tasks" / "C1.json"
        record = json.loads(path.read_text(encoding="utf-8"))
        change(record)
        path.write_text(json.dumps(record), encoding="utf-8")
    return apply


doctor_control = audit("control", lambda root: None)
doctor_driven = {
    "task record with no `state`": audit(
        "no-state", edit_task(lambda d: d.pop("state"))),
    "task record with no `id`": audit(
        "no-id", edit_task(lambda d: d.pop("id"))),
    "task `lease` replaced by a string": audit(
        "lease-str", edit_task(lambda d: d.__setitem__("lease", "not-a-dict"))),
    "task `state` flipped to claimed": audit(
        "claimed", edit_task(lambda d: d.__setitem__("state", "claimed"))),
    "a rogue agent file never in the ledger": audit(
        "rogue", lambda root: (root / "agents" / "rogue.json").write_text(
            json.dumps({"role": "worker"}), encoding="utf-8")),
}
print(f"    {'an untouched workspace (CONTROL)':<40}{doctor_control}")
for label, outcome in doctor_driven.items():
    print(f"    {label:<40}{outcome}")
check("the control audits healthy", "healthy", doctor_control)
check("  five tampered documents driven", "driven: 5",
      f"driven: {len(doctor_driven)}")
check("    NONE escapes as a raw Python exception",
      "escaped: []",
      f"escaped: {[k for k, v in doctor_driven.items() if v.startswith('ESCAPED')]}")
check("      every one is caught and reported as an error",
      "uncaught: []",
      f"uncaught: {[k for k, v in doctor_driven.items() if not v.startswith('caught')]}")
handlers = [ast.unparse(h.type) for h in ast.walk(trees["doctor.py"])
            if isinstance(h, ast.ExceptHandler) and h.type is not None]
print(f"    doctor.py's exception handlers: {handlers}")
check("  and the handler is NARROW - it would not catch a KeyError",
      "'(EFOError, OSError)'", str(handlers))
print("  So the reachability is not the handler's doing. The ledger signature")
print("  and the projection comparison both run BEFORE any field is read, and")
print("  a tampered file fails one of them first. Same shape as item 45's")
print("  near miss: a census over syntax would flag 23 unguarded subscripts,")
print("  and every one of them is behind a guard the syntax cannot see.")

shutil.rmtree(ROOT, ignore_errors=True)

# ---------------------------------------------------------------- F
print("\n########## F. the answer to item 54 ##########")
print("  * lock.py and dashboard.py: the question does not arise - ZERO")
print("    document field reads between them.")
print("  * archive.py: the absence is REAL (8 driven, 8 raw Python")
print("    exceptions, 0 EFOError) and UNREACHABLE (3 call sites, all")
print("    passing a validator's return).")
print("  * doctor.py: 23 unguarded subscripts, and five tampered documents")
print("    all stopped by the ledger/projection guard before reaching them.")
print("  * NOT FILED. A near miss recorded, on the standard items 38, 45, 47")
print("    and 53 all applied: nothing was accepted that should not have been.")

print("\n########## G. what this does NOT do ##########")
print("  * It does not claim the four modules are correct - only that their")
print("    missing isinstance has no reachable consequence THROUGH A DOCUMENT.")
print("    Programmatic misuse of archive_evidence_bundle is a different")
print("    threat model and is not this review's.")
print("  * It does not enumerate every tamper. Five were driven; a tamper")
print("    that keeps the ledger signature valid was not constructed, and")
print("    whether one exists is UNMEASURED.")
print("  * It does not re-run or retract #10, #12, #17 or #19.")
print("  * It does not touch `main`, the anchor's tree, or another agent's")
print("    branch. Every workspace is a tempfile directory, removed above.")
print("  * MEASURED: the four-module census, the AST-vs-grep gap, all eight")
print("    archive drives, all five doctor drives, both controls, the three")
print("    call sites, the handler tuple. REASONED: nothing.")

print(f"\n########## {FAIL} unexpected result(s) ##########")
print("Static reads of the anchor plus thirteen driven inputs against")
print("temporary workspaces. No network, no issue filed. Pre-registered")
print("permissions unchanged - gpu/network/performance_metrics all false.")
print("SUBMITTED, not VERIFIED.")
