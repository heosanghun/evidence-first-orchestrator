#!/usr/bin/env python3
"""EFO evidence archival at main (5694ab45).

`archive.py` calls itself "Immutable-ish local retention for reports and
bounded evidence artifacts".  Issue #9 named it as the one thing left open:
what archival does to the hash chain and to the projections.

This probes the copy guards inside `archive_evidence_bundle`, then asks the
question the module name raises: once evidence is retained, does anything ever
look at it again?

Section A is the positive control - an honest submit must archive cleanly
before any refusal below means anything.  Every rejection is asserted on its
MESSAGE, by substring.

    python3 probe_archive_bundle.py
"""

from __future__ import annotations

import hashlib
import json
import shutil
import sys
import tempfile
from pathlib import Path
from typing import Any

sys.path.insert(0, "/tmp/efo-prov/src")
from evidence_orchestrator.archive import (  # noqa: E402
    _safe_name,
    archive_evidence_bundle,
)
from evidence_orchestrator.doctor import audit_workspace  # noqa: E402
from evidence_orchestrator.workspace import Workspace  # noqa: E402

FAIL = 0
ROOT = Path(tempfile.mkdtemp(prefix="efo-archive-"))


def check(name: str, expected: str, observed: str) -> None:
    global FAIL
    ok = expected in observed
    if not ok:
        FAIL += 1
    print(f"  [{'ok' if ok else '!! UNEXPECTED !!'}] {name}")
    print(f"        expected: {expected}")
    print(f"        observed: {observed}")


def attempt(name: str, expected: str, fn) -> None:
    try:
        value = fn()
        check(name, expected, f"accepted ({value})")
    except Exception as exc:
        check(name, expected, f"rejected ({type(exc).__name__}: {exc})")


def sha_of(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(path: Path, text: str) -> tuple[Path, str]:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path, sha_of(path)


REPORT_BODY = "\n".join([
    "# report", "",
    "## 1. Scope", "archival probe", "",
    "## 2. What was done", "one passing check", "",
    "## 3. Counts", "passed=1 failed=0 skipped=0", "",
    "## 4. Known-answer comparison", "expected 4, observed 4", "",
    "## 5. Outside ownership", "none", "",
    "## 6. Not verified", "nothing", "",
])


def build(worker: str = "w") -> tuple[Workspace, Path]:
    """A workspace with an attested worker and one task, ready to claim."""
    root = Path(tempfile.mkdtemp(prefix="ws-", dir=ROOT))
    ws = Workspace.initialize(root / "ws", name="archive-probe",
                              orchestrator="antigravity",
                              preset="antigravity-codex-claude")
    ws.attest_agent_identity(actor="antigravity", agent_id="antigravity",
                             control_principal="google",
                             model_family="google-antigravity")
    ws.add_agent(actor="antigravity", agent_id=worker, role="worker",
                 mode="manual", control_principal="openai",
                 model_family="openai-codex")
    ws.attest_agent_identity(actor="antigravity", agent_id=worker,
                             control_principal="openai",
                             model_family="openai-codex")
    ws.add_agent(actor="antigravity", agent_id="v", role="verifier",
                 mode="manual", control_principal="anthropic",
                 model_family="anthropic-claude")
    ws.attest_agent_identity(actor="antigravity", agent_id="v",
                             control_principal="anthropic",
                             model_family="anthropic-claude")
    ws.create_task(actor="antigravity", task_id="T1", title="T1",
                   description="work", owner=worker)
    return ws, root


def evidence_for(ws: Workspace, worker: str, artifact_text: str,
                 artifact_bytes: int | None = None
                 ) -> tuple[Path, Path, Path]:
    """Write a report, an artifact, and a manifest binding both."""
    home = ws.reports_dir / worker
    report, _ = write(home / "report.md", REPORT_BODY)
    art, art_sha = write(home / "artifact.txt", artifact_text)
    if artifact_bytes is not None:
        # Sparse: apparent size is what archive.py bounds on; costs no disk.
        with art.open("r+b") as handle:
            handle.truncate(artifact_bytes)
        art_sha = sha_of(art)
    raw, raw_sha = write(home / "raw.txt", "1 passed in 0.01s\n")
    manifest = home / "manifest.json"
    manifest.write_text(json.dumps({
        "schema_version": 1,
        "artifacts": [{"path": str(art), "sha256": art_sha}],
        "validations": [{"command": "pytest -q", "exit_code": 0, "passed": 1,
                         "failed": 0, "skipped": 0, "skip_reasons": [],
                         "raw_output_path": str(raw),
                         "raw_output_sha256": raw_sha}],
        "known_answer_checks": [{"name": "two plus two", "expected": 4,
                                 "observed": 4, "passed": True}],
        "claims": [{"name": "functional behavior", "kind": "functional",
                    "measured": True, "value": "pass",
                    "evidence": [str(art)]}],
    }, indent=2), encoding="utf-8")
    return report, manifest, art


def verifier_manifest(ws: Workspace) -> Path:
    home = ws.reports_dir / "v"
    raw, raw_sha = write(home / "vraw.txt", "1 passed in 0.02s\n")
    path = home / "vmanifest.json"
    path.write_text(json.dumps({
        "schema_version": 1,
        "artifacts": [{"path": str(raw), "sha256": raw_sha}],
        "validations": [{"command": "pytest -q", "exit_code": 0, "passed": 1,
                         "failed": 0, "skipped": 0, "skip_reasons": []}],
        "known_answer_checks": [{"name": "two plus two", "expected": 4,
                                 "observed": 4, "passed": True}],
        "claims": [{"name": "reproduced", "kind": "functional",
                    "measured": True, "value": "pass",
                    "evidence": [str(raw)]}],
    }, indent=2), encoding="utf-8")
    return path


def healthy(ws: Workspace) -> str:
    return str(audit_workspace(ws.root)["healthy"])


# ---------------------------------------------------------------- A
print("########## A. POSITIVE CONTROL - an honest submit archives ##########")
ws, _ = build()
report, manifest, artifact = evidence_for(ws, "w", "measured artifact\n")
lease = ws.claim(actor="w", task_id="T1")
token = lease["lease_token"]
ws.start(actor="w", task_id="T1", lease_token=token)
submitted = ws.submit(actor="w", task_id="T1", lease_token=token,
                      report_path=report, manifest_path=manifest)
bundle = submitted["result"]["archive"]
check("the submission archives report, manifest, artifact and raw output",
      "'retained': 4",
      f"retained={bundle['retained']} external={bundle['external']} "
      f"files={len(bundle['files'])} -> 'retained': {bundle['retained']}")
print(f"        bundle_id  = {bundle['bundle_id']}")
print(f"        path       = .../{Path(bundle['path']).relative_to(ws.root)}")
for record in bundle["files"]:
    name = Path(record["archive_path"]).name if record["archive_path"] else None
    print(f"        {record['kind']:<10} retained={record['retained']} "
          f"size={record['size_bytes']:<6} {name}")
copied = sorted(p.name for p in (Path(bundle["path"]) / "files").iterdir())
check("  every file is stored under its own content hash",
      f"{sha_of(artifact)[:16]}", " ".join(copied))
check("  and doctor is healthy afterwards", "healthy=True",
      "healthy=" + healthy(ws))

# ---------------------------------------------------------------- B
print("\n########## B. the copy guards, called directly ##########")
DIRECT = ROOT / "direct"
src, src_sha = write(DIRECT / "src" / "evidence.txt", "honest bytes\n")
mpath, msha = write(DIRECT / "src" / "m.json", json.dumps({"artifacts": []}))
MANIFEST_ARG = {"path": str(mpath), "sha256": msha, "artifacts": []}


def direct(**over: Any) -> dict[str, Any]:
    kwargs: dict[str, Any] = {
        "submissions_root": DIRECT / "out",
        "task_id": "T9",
        "attempt": 1,
        "label": "worker",
        "report": None,
        "manifest": dict(MANIFEST_ARG, sha256=msha),
        "max_artifact_bytes": 1024,
        "extra_files": [{"path": str(src), "sha256": src_sha,
                         "kind": "artifact", "force": True}],
    }
    kwargs.update(over)
    return archive_evidence_bundle(**kwargs)


attempt("POSITIVE CONTROL - an honest direct call", "accepted", direct)

attempt("evidence swapped between hashing and archival",
        "Evidence changed while being archived",
        lambda: direct(extra_files=[{"path": str(src), "sha256": "0" * 64,
                                     "kind": "artifact", "force": True}]))

attempt("a source that no longer exists",
        "Evidence disappeared before archival",
        lambda: direct(extra_files=[{"path": str(DIRECT / "gone.txt"),
                                     "sha256": "0" * 64, "kind": "artifact",
                                     "force": True}]))

attempt("a negative byte bound", "max_artifact_bytes cannot be negative",
        lambda: direct(max_artifact_bytes=-1))

# The archive path is files/<sha>_<name>, so a collision with DIFFERENT content
# can only be produced by a writer outside this API. Seed one and confirm the
# guard fires rather than overwriting.
collide = (DIRECT / "out" / "T9" / "attempt-001"
           / f"worker-{msha[:16]}" / "files"
           / f"{src_sha}_{_safe_name(src)}")
collide.parent.mkdir(parents=True, exist_ok=True)
collide.write_text("substituted bytes\n", encoding="utf-8")
attempt("a destination already holding different content",
        "Archived evidence path already has different content", direct)
collide.unlink()

print("  filename sanitisation (the archived name is derived from path.name):")
for hostile in ("...", "a/b", "..", "x;rm -rf /.txt", ""):
    print(f"        _safe_name({hostile!r}) -> {_safe_name(Path('q') / hostile)!r}"
          if hostile else
          f"        _safe_name('') -> {_safe_name(Path('q'))!r}")
attempt("a task id that would escape the submissions root",
        "Task id must start with an alphanumeric character",
        lambda: ws.create_task(actor="antigravity", task_id="../escape",
                               title="x", description="x", owner="w"))

# ---------------------------------------------------------------- C
print("\n########## C. is retained evidence ever looked at again? ##########")
ws, _ = build()
report, manifest, artifact = evidence_for(ws, "w", "measured artifact\n")
lease = ws.claim(actor="w", task_id="T1")
token = lease["lease_token"]
ws.start(actor="w", task_id="T1", lease_token=token)
submitted = ws.submit(actor="w", task_id="T1", lease_token=token,
                      report_path=report, manifest_path=manifest)
bundle_dir = Path(submitted["result"]["archive"]["path"])
archived_artifact = next(
    Path(r["archive_path"]) for r in submitted["result"]["archive"]["files"]
    if r["kind"] == "artifact"
)
recorded_sha = next(r["sha256"] for r in submitted["result"]["archive"]["files"]
                    if r["kind"] == "artifact")

print("  the ledger DOES hold the per-file hashes - the data to check exists:")
event = [e for e in ws.ledger.read() if e["action"] == "task.submitted"][-1]
for record in event["payload"]["task"]["result"]["archive"]["files"]:
    print(f"        ledger: {record['kind']:<10} {record['sha256'][:16]}... "
          f"retained={record['retained']}")

archived_artifact.write_text("REWRITTEN AFTER ARCHIVAL\n", encoding="utf-8")
print(f"  archived artifact rewritten in place")
print(f"        recorded sha = {recorded_sha[:16]}...")
print(f"        on-disk sha  = {sha_of(archived_artifact)[:16]}...")
attempt("does the ledger notice?", "accepted", ws.ledger.verify)
attempt("  does reading the task notice?", "accepted",
        lambda: ws.get_task("T1")["state"])
check("  does doctor notice?", "healthy=", "healthy=" + healthy(ws))
attempt("  does audit_projections notice?", "accepted",
        lambda: ws.audit_projections()["mismatches"])

(bundle_dir / "bundle.json").write_text('{"files": []}', encoding="utf-8")
check("bundle.json replaced - doctor?", "healthy=", "healthy=" + healthy(ws))

shutil.rmtree(bundle_dir)
print("  the whole bundle directory deleted")
attempt("does the ledger notice?", "accepted", ws.ledger.verify)
attempt("  does reading the task notice?", "accepted",
        lambda: ws.get_task("T1")["state"])
check("  does doctor notice?", "healthy=", "healthy=" + healthy(ws))

surface = sorted(
    name for name in dir(Workspace)
    if not name.startswith("_")
    and any(word in name for word in ("archive", "submission", "audit", "verify"))
)
print(f"  every public Workspace method that could re-check it: {surface}")

# ---------------------------------------------------------------- D
print("\n########## D. an artifact over the byte bound is not retained ##########")
ws, _ = build()
# First: the bound cannot simply be lowered. Editing the config is caught, and
# there is no API to change it - a result in the code's favour, and the reason
# this section needs a genuinely oversized artifact.
config = json.loads(ws.config_path.read_text(encoding="utf-8"))
print(f"  configured max_evidence_bytes = "
      f"{config['defaults']['max_evidence_bytes']} "
      f"({config['defaults']['max_evidence_bytes'] // (1024 * 1024)} MiB)")
original = ws.config_path.read_text(encoding="utf-8")
config["defaults"]["max_evidence_bytes"] = 8
ws.config_path.write_text(json.dumps(config, indent=2), encoding="utf-8")
attempt("POSITIVE CONTROL - can the bound be lowered by editing the config?",
        "Workspace configuration differs from the signed ledger",
        lambda: Workspace(ws.root))
ws.config_path.write_text(original, encoding="utf-8")
setters = sorted(name for name in dir(Workspace)
                 if not name.startswith("_")
                 and any(w in name for w in ("config", "default", "set_")))
print(f"  public Workspace methods that could change it: {setters}")
print("  so the artifact itself has to exceed 50 MiB (sparse, costs no disk).")
report, manifest, artifact = evidence_for(ws, "w", "x\n",
                                          artifact_bytes=50 * 1024 * 1024 + 1)
lease = ws.claim(actor="w", task_id="T1")
token = lease["lease_token"]
ws.start(actor="w", task_id="T1", lease_token=token)
submitted = ws.submit(actor="w", task_id="T1", lease_token=token,
                      report_path=report, manifest_path=manifest)
bundle = submitted["result"]["archive"]
check("the submission is still accepted", "'external': 1",
      f"retained={bundle['retained']} external={bundle['external']} "
      f"-> 'external': {bundle['external']}")
for record in bundle["files"]:
    print(f"        {record['kind']:<10} retained={record['retained']} "
          f"size={record['size_bytes']:<6} archive_path={record['archive_path']}")
artifact.unlink()
print("  the un-retained artifact deleted from the worker's own report dir")
attempt("does reading the task notice?", "accepted",
        lambda: ws.get_task("T1")["state"])
check("  does doctor notice?", "healthy=", "healthy=" + healthy(ws))
attempt("  can a verifier still accept it?", "accepted",
        lambda: ws.verify(actor="v", task_id="T1", decision="accept",
                          note="reproduced",
                          verification_manifest=verifier_manifest(ws)
                          )["state"])

# ---------------------------------------------------------------- E
print("\n########## E. Workspace.archive() - the state machine and the chain ##########")
ws, _ = build()
report, manifest, artifact = evidence_for(ws, "w", "measured artifact\n")
attempt("archive a pending task", "cannot transition pending -> archived",
        lambda: ws.archive(actor="antigravity", task_id="T1"))
lease = ws.claim(actor="w", task_id="T1")
token = lease["lease_token"]
ws.start(actor="w", task_id="T1", lease_token=token)
ws.submit(actor="w", task_id="T1", lease_token=token,
          report_path=report, manifest_path=manifest)
attempt("archive a submitted task", "cannot transition submitted -> archived",
        lambda: ws.archive(actor="antigravity", task_id="T1"))
ws.verify(actor="v", task_id="T1", decision="accept", note="reproduced",
          verification_manifest=verifier_manifest(ws))
attempt("archive a worker", "Only orchestrator 'antigravity' may perform this action",
        lambda: ws.archive(actor="w", task_id="T1"))
before = len(ws.ledger.read())
attempt("archive a verified task", "accepted",
        lambda: ws.archive(actor="antigravity", task_id="T1")["state"])
after = len(ws.ledger.read())
check("  the archival is committed to the chain", "events 14 -> 15",
      f"events {before} -> {after}")
check("  the live projection is retained", "exists=True",
      f"exists={(ws.tasks_dir / 'T1.json').is_file()}")
check("  a second copy is written to archive/", "exists=True",
      f"exists={(ws.archive_dir / 'T1.json').is_file()}")
attempt("archive twice", "cannot transition archived -> archived",
        lambda: ws.archive(actor="antigravity", task_id="T1"))
attempt("  the chain still verifies", "accepted", ws.ledger.verify)
check("  and doctor is healthy", "healthy=True", "healthy=" + healthy(ws))

copy = ws.archive_dir / "T1.json"
tampered = json.loads(copy.read_text(encoding="utf-8"))
tampered["state"] = "verified"
tampered["owner"] = "someone-else"
copy.write_text(json.dumps(tampered, indent=2), encoding="utf-8")
print("  archive/T1.json rewritten (state -> verified, owner -> someone-else)")
attempt("does reading the task notice?", "accepted",
        lambda: ws.get_task("T1")["state"])
check("  does doctor notice?", "healthy=", "healthy=" + healthy(ws))
readers = sorted(name for name in dir(Workspace)
                 if not name.startswith("_") and "archive" in name)
print(f"  public Workspace methods touching archive/: {readers}")

shutil.rmtree(ROOT, ignore_errors=True)
print(f"\n########## {FAIL} unexpected result(s) ##########")
print("SUBMITTED, not VERIFIED.")
