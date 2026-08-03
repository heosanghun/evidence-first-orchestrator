#!/usr/bin/env python3
"""A tamper that RE-SIGNS is healthy - and SECURITY.md says so in as many words.

Queue item 57, and the load-bearing assumption under items 45, 53 and 54. Every
tamper any of them drove was stopped by the ledger signature or the projection
comparison, and each concluded "the guard blocks the path". None asked WHAT THE
SIGNATURE COVERS, or whether that conclusion is a property or an artifact of
the tampers chosen.

It is an artifact, and the boundary is exactly where the document says it is.

    7  fields the signature covers, derived from ledger.py's own tuple:
       sequence, timestamp, actor, action, task_id, payload, previous_hash
    1  HMAC key, `os.urandom(32)`, chmod 600, stored INSIDE the workspace
       at `.efo/ledger.key`

Anyone who can write `tasks/C1.json` can also READ `.efo/ledger.key` - same
filesystem, same account - so the chain can be recomputed and re-signed:

    a naive projection edit                     caught
    the SAME edit, with the ledger payload
    updated and the whole chain re-signed       HEALTHY, valid: true,
                                                signed: true, tampered value
                                                live

SECURITY.md:38 states this precisely: "The local ledger signing key protects
against edits by parties that cannot read the key." So this is a DOCUMENTED
limit verified by driving BOTH directions, not a defect - the strongest shape
this review has measured, and the same one `functions/api/local-health.js` got.

WHAT IT MEANS FOR MY OWN NOTES: items 45, 53 and 54 each concluded a gap was
"unreachable" because the ledger guard fires first. That holds ONLY against an
adversary who cannot read `.efo/ledger.key`. None of the three said so. Stated
here, and in SYNTHESIS.

    python3 probe_ledger_signature_scope.py

SCOPE, stated first: 7 signed fields, 1 key, 3 comparison sites, 7 driven
tampers, 2 controls. A MAP that names a precondition. No issue filed.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, "/tmp/efo-prov/src")
from evidence_orchestrator import doctor  # noqa: E402
from evidence_orchestrator.util import canonical_json  # noqa: E402
from evidence_orchestrator.workspace import Workspace  # noqa: E402

FAIL = 0
ANCHOR = Path("/tmp/efo-prov")
SRC = ANCHOR / "src" / "evidence_orchestrator"
ROOT = Path(tempfile.mkdtemp(prefix="efo-item57-")).resolve()


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

# ---------------------------------------------------------------- B
print("\n########## B. what the signature COVERS ##########")
ledger_source = (SRC / "ledger.py").read_text(encoding="utf-8")
# DERIVED from _verify_events' own tuple, not typed here: if a field were added
# or dropped this check fails instead of silently measuring the wrong set.
covered = re.search(
    r"for key_name in \(\s*((?:\s*\"[a-z_]+\",)+)\s*\)", ledger_source)
fields = re.findall(r'"([a-z_]+)"', covered.group(1))
print(f"    core fields hashed : {fields}")
check("the signature covers seven fields, derived from ledger.py",
      "fields: ['sequence', 'timestamp', 'actor', 'action', 'task_id', "
      "'payload', 'previous_hash']", f"fields: {fields}")
check("  the chain is SHA-256 over canonical JSON",
      "hashlib.sha256(canonical_json(core)).hexdigest()", ledger_source)
check("    and the signature is an HMAC over that hash",
      "hmac.new(\n                key, calculated_hash.encode(\"ascii\"), "
      "hashlib.sha256\n            ).hexdigest()", ledger_source)
check("  with a key generated locally by os.urandom(32)",
      "self.key_path.write_bytes(os.urandom(32))", ledger_source)


def fresh(tag: str) -> Path:
    root = ROOT / tag
    workspace = Workspace.initialize(root, name="item57",
                                     orchestrator="antigravity",
                                     preset="antigravity-codex-claude")
    workspace.create_task(actor="antigravity", task_id="C1", title="t",
                          description="d", owner="claude")
    return root


def audit(root: Path) -> str:
    try:
        result = doctor.audit_workspace(root)
    except Exception as exc:  # noqa: BLE001 - a raise is still "caught"
        return f"caught (raised {type(exc).__name__})"
    if result["healthy"]:
        return "HEALTHY - unnoticed"
    return f"caught: {result.get('error', 'no error key')[:52]}"


baseline = fresh("control")
key_path = Workspace(baseline).ledger.key_path
print(f"    key file           : {key_path.relative_to(baseline)}")
print(f"    mode               : {oct(key_path.stat().st_mode & 0o777)}")
check("  the key lives INSIDE the workspace it protects",
      "inside: True", f"inside: {key_path.is_relative_to(baseline)}")
check("    readable by whoever owns the workspace", "mode: 0o600",
      f"mode: {oct(key_path.stat().st_mode & 0o777)}")
check("  and an untouched workspace audits healthy - CONTROL",
      "HEALTHY", audit(baseline))

# ---------------------------------------------------------------- C
print("\n########## C. what is COMPARED against it, driven ##########")
comparisons = sorted(set(re.findall(
    r'"([^"]*(?:differs from the signed ledger|no ledger event)[^"]*)"',
    (SRC / "workspace.py").read_text(encoding="utf-8"))))
for message in comparisons:
    print(f"    workspace.py  {message}")
# SIX, not two. I wrote two from the two messages I had already seen in
# items 45 and 54; workspace.py declares six. Corrected to the measurement.
check("comparison messages the package declares", "messages: 6",
      f"messages: {len(comparisons)}")


def edit_json(relative: str, mutate):
    def apply(root: Path) -> None:
        path = root / relative
        record = json.loads(path.read_text(encoding="utf-8"))
        mutate(record)
        path.write_text(json.dumps(record, indent=2), encoding="utf-8")
    return apply


simple = {}
for index, (tag, mutate) in enumerate([
    ("config: name", edit_json(".efo/workspace.json",
                               lambda d: d.__setitem__("name", "renamed"))),
    ("config: orchestrator", edit_json(
        ".efo/workspace.json", lambda d: d.__setitem__("orchestrator", "claude"))),
    ("config: defaults.lease_seconds", edit_json(
        ".efo/workspace.json",
        lambda d: d["defaults"].__setitem__("lease_seconds", 999999))),
    ("a stray file under tasks/", lambda root: (
        root / "tasks" / "ZZ.json").write_text(
            '{"id": "ZZ", "state": "pending"}', encoding="utf-8")),
    ("a stray file under runs/", lambda root: (
        root / "runs" / "stray.json").write_text('{"x": 1}', encoding="utf-8")),
]):
    # An INDEX, not a slug: the first version derived the directory from the
    # tag's first word, so the three `config:` drives collided and the second
    # one hit "Workspace already initialized". Caught by the exception.
    root = fresh(f"simple-{index}")
    mutate(root)
    simple[tag] = audit(root)
    print(f"    {tag:<34}{simple[tag]}")
check("every config field edit is caught",
      "unnoticed: []",
      "unnoticed: " + str([t for t, r in simple.items()
                           if t.startswith("config") and "HEALTHY" in r]))
check("  a task file with no ledger event is caught", "ZZ: no ledger event",
      simple["a stray file under tasks/"])
check("    but runs/ is NOT covered - and is scratch space by design",
      "HEALTHY - unnoticed", simple["a stray file under runs/"])

# ---------------------------------------------------------------- D
print("\n########## D. THE ANSWER: a tamper that RE-SIGNS ##########")


def resign(root: Path) -> None:
    """Recompute the whole chain with the workspace's OWN key."""
    key = (root / ".efo" / "ledger.key").read_bytes()
    path = root / "ledger" / "events.jsonl"
    events = [json.loads(line)
              for line in path.read_text(encoding="utf-8").splitlines()
              if line.strip()]
    previous = "0" * 64
    rewritten = []
    for event in events:
        core = {name: event.get(name) for name in fields}
        core["previous_hash"] = previous
        event_hash = hashlib.sha256(canonical_json(core)).hexdigest()
        signature = hmac.new(key, event_hash.encode("ascii"),
                             hashlib.sha256).hexdigest()
        rewritten.append({**core, "event_hash": event_hash,
                          "signature": signature})
        previous = event_hash
    path.write_text("\n".join(
        json.dumps(event, ensure_ascii=False, sort_keys=True)
        for event in rewritten) + "\n", encoding="utf-8")


naive = fresh("naive")
edit_json("tasks/C1.json", lambda d: d.__setitem__("title", "tampered"))(naive)
naive_result = audit(naive)

forged = fresh("forged")
edit_json("tasks/C1.json", lambda d: d.__setitem__("title", "tampered"))(forged)
ledger_path = forged / "ledger" / "events.jsonl"
events = [json.loads(line)
          for line in ledger_path.read_text(encoding="utf-8").splitlines()
          if line.strip()]
for event in events:
    task = event.get("payload", {}).get("task")
    if isinstance(task, dict):
        task["title"] = "tampered"
ledger_path.write_text("\n".join(
    json.dumps(event, ensure_ascii=False, sort_keys=True)
    for event in events) + "\n", encoding="utf-8")
resign(forged)
forged_result = audit(forged)
forged_verify = Workspace(forged).ledger.verify()
forged_title = json.loads(
    (forged / "tasks" / "C1.json").read_text(encoding="utf-8"))["title"]

print(f"    naive projection edit             {naive_result}")
print(f"    same edit + ledger + RE-SIGNED    {forged_result}")
print(f"      ledger verify                   valid={forged_verify['valid']}"
      f" signed={forged_verify['signed']} events={forged_verify['events']}")
print(f"      the task title now reads        {forged_title!r}")
check("the naive edit is caught - CONTROL",
      "projection differs from ledger", naive_result)
check("  but the re-signed one is HEALTHY", "HEALTHY - unnoticed",
      forged_result)
check("    and the ledger reports itself valid and signed",
      "valid True signed True",
      f"valid {forged_verify['valid']} signed {forged_verify['signed']}")
check("      with the tampered value live", "tampered", forged_title)
print("  So \"the ledger guard blocks the path\" is an ARTIFACT of the tampers")
print("  chosen, not a property. Every tamper items 45, 53 and 54 drove left")
print("  the signature stale; re-signing is a dozen lines and the key is in")
print("  the workspace.")

shutil.rmtree(ROOT, ignore_errors=True)

# ---------------------------------------------------------------- E
print("\n########## E. and SECURITY.md says exactly this ##########")
security = (ANCHOR / "SECURITY.md").read_text(encoding="utf-8").replace(
    "\n", " ")
check("the document states the limit in as many words",
      "The local ledger signing key protects against edits by parties that "
      "cannot read the key.", security)
check("  and names the stronger deployment",
      "use an external append-only store or a key held only by the "
      "orchestrator", security)
check("    and says application ownership does not stop direct file edits",
      "does not stop a process that directly edits files outside EFO",
      security)
print("  DOCUMENTED, DRIVEN IN BOTH DIRECTIONS, and holding: cannot read the")
print("  key -> caught; can read the key -> passes. Not a defect. The same")
print("  shape as `functions/api/local-health.js`, which is the strongest")
print("  this review has measured.")

# ---------------------------------------------------------------- F
print("\n########## F. what it means for THREE of my own notes ##########")
print("  Items 45, 53 and 54 each concluded a gap was UNREACHABLE because the")
print("  ledger or projection guard fires first:")
print("    45  model.lease_expired's raise, blocked by the projection guard")
print("    53  provenance.py's files-list guards, never fed a malformed record")
print("    54  doctor.py's 23 unguarded subscripts, all behind the guard")
print("  Each is correct AS MEASURED, and each holds ONLY against an adversary")
print("  who cannot read `.efo/ledger.key`. None of the three said so. That")
print("  precondition is stated here and added to SYNTHESIS rather than left")
print("  implicit - it is the difference between `unreachable` and")
print("  `unreachable under the threat model the document declares`.")

print("\n########## G. what this does NOT do ##########")
print("  * It does not file an issue. SECURITY.md:38 states the limit, and")
print("    the drive confirms the document rather than contradicting it.")
print("  * It does not retract items 45, 53 or 54. It names the precondition")
print("    each of them relied on without stating.")
print("  * It does not claim the covered set is complete beyond what was")
print("    driven: config, agents and tasks are compared, runs/ is not. It")
print("    did NOT enumerate reports/, submissions/ or archive/, which a")
print("    fresh workspace does not create - stated, not implied.")
print("  * It does not attempt a tamper WITHOUT the key. That is the case")
print("    already covered by items 45 and 54 and by the naive control here.")
print("  * No network. Every workspace is a tempfile directory, removed above.")
print("  * MEASURED: the seven covered fields derived from ledger.py, the key")
print("    location and mode, both comparison messages, all five simple")
print("    tampers, both controls, the re-signed tamper and its verify, three")
print("    SECURITY.md sentences. REASONED: nothing.")

print(f"\n########## {FAIL} unexpected result(s) ##########")
print("Seven tampers driven against temporary workspaces. Anchor untouched,")
print("no `main` write, no issue filed. Pre-registered permissions unchanged -")
print("gpu/network/performance_metrics all false. SUBMITTED, not VERIFIED.")
