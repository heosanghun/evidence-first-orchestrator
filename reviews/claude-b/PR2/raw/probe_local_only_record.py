#!/usr/bin/env python3
"""What does the accepted record say when the declared commit was never pushed?

    PYTHONPATH=/tmp/efo-prov/src python3 probe_local_only_record.py
"""
import hashlib, json, os, shutil, subprocess, sys
from pathlib import Path
sys.path.insert(0, "/tmp/efo-prov/src")
from evidence_orchestrator.provenance import validate_git_provenance

W = Path("/tmp/prov5b"); shutil.rmtree(W, ignore_errors=True); W.mkdir()
E = {**os.environ, "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@e",
     "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@e",
     "GIT_AUTHOR_DATE": "2026-01-01T00:00:00Z",
     "GIT_COMMITTER_DATE": "2026-01-01T00:00:00Z"}
g = lambda *a: subprocess.run(["git", *a], cwd=W / "work", env=E,
                              capture_output=True, text=True).stdout.strip()
subprocess.run(["git", "init", "-q", "--bare", str(W / "origin.git")], env=E, check=True)
subprocess.run(["git", "clone", "-q", str(W / "origin.git"), str(W / "work")],
               env=E, check=True, capture_output=True)
(W / "work" / "report.txt").write_text("PUSHED\n")
g("add", "report.txt"); g("commit", "-qm", "pushed"); g("branch", "-M", "main")
g("push", "-q", "origin", "main"); g("fetch", "-q", "origin")
(W / "work" / "report.txt").write_text("NEVER PUSHED: 4 passed, 0 failed\n")
g("commit", "-aqm", "never pushed")
c = g("rev-parse", "HEAD"); remote = g("remote", "get-url", "origin")
print("origin.git tip     :", subprocess.run(
    ["git", "--git-dir", str(W / "origin.git"), "rev-parse", "main"],
    capture_output=True, text=True).stdout.strip()[:12])
print("declared commit    :", c[:12], "(exists only in the work clone)")
g("update-ref", "-d", "refs/remotes/origin/main")   # the whole attack
d = W / "reports" / "claude"; d.mkdir(parents=True)
shutil.copyfile(W / "work" / "report.txt", d / "report.txt")
sha = hashlib.sha256((d / "report.txt").read_bytes()).hexdigest()
(d / "provenance.json").write_text(json.dumps({
    "schema_version": 1, "kind": "git", "author": "claude", "remote_name": "origin",
    "remote_url": remote, "branch": "main", "commit": c,
    "files": [{"source_path": "report.txt", "submitted_path": "report.txt"}]}))
r = validate_git_provenance(
    d / "provenance.json", source_repository=W / "work", report_root=d,
    expected_author="claude",
    evidence={"manifest": {"artifacts": [{"path": str(d / "report.txt"),
                                          "sha256": sha}], "validations": []}},
    max_blob_bytes=10 ** 6)
print("\nACCEPTED record fields an auditor would read:")
for k in ("remote_url", "branch", "resolved_ref", "ref_tip", "commit", "byte_exact"):
    print(f"   {k:<14} = {r[k]}")
print("\nis the declared commit fetchable from the declared remote?")
p = subprocess.run(["git", "--git-dir", str(W / "origin.git"), "cat-file", "-e", c],
                   capture_output=True)
print("   git --git-dir origin.git cat-file -e <commit> ->",
      "present" if p.returncode == 0 else f"ABSENT (exit {p.returncode})")
