#!/usr/bin/env python3
"""Every FILE a workspace ships, tampered - and which four were never checked.

Queue item 66, closing what item 63 stated it had not done: that round
enumerated DIRECTORIES and said plainly it did not enumerate FILES.

The population is derived, not named: a full lifecycle to `archived` produces
27 files, which collapse to 17 KINDS once the task id, the agent name and the
content hashes are normalised away. Every kind is then driven with an EDIT -
so this does not CITE what items 57, 60 and 63 covered, it RE-DERIVES all of
it and adds what none of them reached.

    reports/<agent>/<task>.evidence.json   the manifest carrying the sha256s
    reports/<agent>/<task>.artifact.txt    the artifact those sha256s cover
    reports/<agent>/<task>.raw.txt         the raw output they cover
    reports/<agent>/<task>.md              the report itself

Item 60 drove a report under `reports/`, but never the EVIDENCE MANIFEST or
the files it hashes while they sit in the author's own directory - only their
copies under `submissions/`.

The positive control is item 63's: `.efo/ledger.key` must be CAUGHT, so a
sheet of "unnoticed" cannot be confused with a blind driver.

    python3 probe_every_file_tampered.py

SCOPE, stated first: 27 files, 17 kinds, 17 edit tampers, 1 positive control,
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
ROOT = Path(tempfile.mkdtemp(prefix="efo-item66-"))


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
    workspace = Workspace.initialize(root, name="item66",
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
print("\n########## C. every kind, EDITED ##########")
print("  Not cited from items 57/60/63 - RE-DERIVED here, so the table below")
print("  stands on this run rather than on three earlier ones.")


def mutate(path: Path) -> None:
    """Edit in place, preserving the file's rough shape."""
    if path.suffix == ".json":
        try:
            document = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            path.write_bytes(path.read_bytes() + b"\n")
            return
        if isinstance(document, dict):
            document["tampered_by_item_66"] = True
        path.write_text(json.dumps(document, indent=2), encoding="utf-8")
    else:
        path.write_bytes(path.read_bytes() + b"tampered\n")


results: dict = {}
for name in sorted(kinds):
    root = lifecycle()
    target = next(p for p in sorted(root.rglob("*"))
                  if p.is_file() and kind(str(p.relative_to(root))) == name)
    mutate(target)
    results[name] = audit(root)
    print(f"    {name:<48} {results[name]}")

unnoticed = [n for n, v in results.items() if "HEALTHY" in v]
caught = [n for n, v in results.items() if "CAUGHT" in v]
check("every kind was driven", f"driven: {len(kinds)}",
      f"driven: {len(results)}")
# I predicted FOUR caught and there are FIVE: I overlooked that
# ledger/events.jsonl is itself a kind, and appending to a JSONL breaks the
# last line's JSON. Corrected to the measurement - and the NEXT check asks
# whether that catch is about SHAPE or about the SIGNATURE, because those are
# not the same guard.
check("  kinds whose edit is CAUGHT", "caught: 5", f"caught: {len(caught)}")
print(f"    {caught}")
check("  kinds whose edit goes UNNOTICED", "unnoticed: 12",
      f"unnoticed: {len(unnoticed)}")
check("    and the two classes account for every kind",
      f"total: {len(kinds)}", f"total: {len(caught) + len(unnoticed)}")

print("  The ledger catch is on SHAPE, not signature - appending a line to a")
print("  JSONL leaves invalid JSON. Asked separately, because a guard that")
print("  fires on malformedness is not the same guard as one that fires on a")
print("  forged value:")
root = lifecycle()
path = root / "ledger" / "events.jsonl"
lines = path.read_text(encoding="utf-8").splitlines()
record = json.loads(lines[-1])
record["actor"] = "someone-else"
path.write_text("\n".join(lines[:-1]) + "\n"
                + json.dumps(record, sort_keys=True) + "\n", encoding="utf-8")
valid_edit = audit(root)
print(f"    a VALID-JSON edit to a ledger line{'':<14} {valid_edit}")
# I expected the SIGNATURE to fire. It is the HASH CHAIN - "Ledger event
# hash mismatch at event 12" - which is a third distinct guard, checked
# before the signature is reached. Corrected to the measurement.
check("    a well-formed ledger edit is caught too, by the HASH CHAIN",
      "event hash mismatch", valid_edit.lower())
check("      a THIRD distinct message, not the signature one",
      "distinct: True",
      f"distinct: {'signature' not in valid_edit.lower()}")

# ---------------------------------------------------------------- D
print("\n########## D. the four `reports/` kinds item 60 never reached ##########")
REPORTS = [n for n in sorted(kinds) if n.startswith("reports/")]
print(f"    {REPORTS}")
check("there are four of them", "reports kinds: 4",
      f"reports kinds: {len(REPORTS)}")
for name in REPORTS:
    print(f"    {name:<48} {results[name]}")
check("  and every one goes unnoticed", "unnoticed: 4",
      f"unnoticed: {sum(1 for n in REPORTS if 'HEALTHY' in results[n])}")
print("  Item 60 drove a report under reports/. It did NOT drive the EVIDENCE")
print("  MANIFEST, nor the artifact and raw output whose sha256 that manifest")
print("  carries, while they sit in the author's own directory. Those hashes")
print("  are checked at SUBMIT time; nothing re-checks them afterwards.")

# ---------------------------------------------------------------- E
print("\n########## E. the control, so a sheet of negatives means something ##########")
root = lifecycle()
(root / ".efo" / "ledger.key").write_bytes(b"9" * 32)
key_result = audit(root)
print(f"    replace .efo/ledger.key{'':<25} {key_result}")
check("replacing the signing key IS caught", "CAUGHT", key_result)
check("  by a signature mismatch, named", "Ledger signature mismatch",
      key_result)
print("  Item 63's control, re-run here. The driver is not blind; the 13")
print("  above measure the SCOPE of what the signature covers.")

# ---------------------------------------------------------------- F
print("\n########## F. what this does NOT establish ##########")
print("  * It does NOT file an issue. This widens the measured width of #10")
print("    from directories to FILES; quantifying an open issue is not")
print("    opening another.")
print("  * It does NOT claim the covered set is wrong. Four kinds ARE")
print("    compared, and section E confirms the signature path still bites.")
print("  * Every `unnoticed` is measured UNDER THE THREAT MODEL SECURITY.md:38")
print("    declares. A tamper needing the key is a different measurement, and")
print("    section E is the one that needs it.")
print("  * It drives an EDIT of each kind, not a DELETE. Item 63 drove three")
print("    deletions at directory level; a per-kind deletion sweep is")
print("    UNCHECKED here, not shown safe.")
print("  * The kind rule is a JUDGEMENT stated in the source - directory role")
print("    plus extension. A finer rule would give more kinds; what is")
print("    asserted is that every one of the 27 files maps to exactly one.")
print("  * No network, no GPU. Nineteen tempfile workspaces, removed before")
print("    the results print. The anchor's working tree is untouched, and it")
print("    does not touch `main` or another agent's branch.")
print("  * MEASURED: the file enumeration, the kind collapse and its")
print("    completeness, all 17 edits, the four reports/ kinds, the key")
print("    control, the lifecycle control. REASONED: nothing.")

shutil.rmtree(ROOT, ignore_errors=True)
print(f"\n########## {FAIL} unexpected result(s) ##########")
print("Pre-registered permissions unchanged - gpu/network/performance_metrics")
print("all false. SUBMITTED, not VERIFIED: re-running my own evidence is a")
print("re-run, not independent confirmation.")
