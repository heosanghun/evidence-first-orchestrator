#!/usr/bin/env python3
"""The five Git provenance attacks not yet re-run against main's rewritten
validate_git_provenance (341 lines).  The sixth, `git replace`, is issue #4.

Every scenario is preceded by a positive control on the same fixture, so a
rejection can never be mistaken for the wrong gate firing.

    PYTHONPATH=/tmp/efo-prov/src python3 attack_prov5_main.py
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, "/tmp/efo-prov/src")
from evidence_orchestrator.provenance import validate_git_provenance  # noqa: E402

W = Path("/tmp/prov5")
ENV = {
    **os.environ,
    "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@e",
    "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@e",
    "GIT_AUTHOR_DATE": "2026-01-01T00:00:00Z",
    "GIT_COMMITTER_DATE": "2026-01-01T00:00:00Z",
}


def git(*args: str, cwd: Path | None = None, check: bool = True) -> str:
    r = subprocess.run(["git", *args], cwd=cwd or W / "work", env=ENV,
                       capture_output=True, text=True)
    if check and r.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} -> {r.returncode}: {r.stderr.strip()}")
    return r.stdout.strip()


def build() -> tuple[str, str]:
    """Fresh origin + work clone holding two claim-bearing files."""
    if W.exists():
        shutil.rmtree(W)
    W.mkdir(parents=True)
    subprocess.run(["git", "init", "-q", "--bare", str(W / "origin.git")], env=ENV, check=True)
    subprocess.run(["git", "clone", "-q", str(W / "origin.git"), str(W / "work")],
                   env=ENV, check=True, capture_output=True)
    (W / "work" / "report.txt").write_text("HONEST: 3 passed, 1 failed\n")
    (W / "work" / "raw.txt").write_text("raw output line\n")
    git("add", "report.txt", "raw.txt")
    git("commit", "-qm", "honest evidence")
    git("branch", "-M", "main")
    git("push", "-q", "origin", "main")
    git("fetch", "-q", "origin")
    return git("rev-parse", "HEAD"), git("remote", "get-url", "origin")


def root() -> Path:
    d = W / "reports" / "claude"
    d.mkdir(parents=True, exist_ok=True)
    return d


def evidence(*names: str) -> dict:
    arts = []
    for n in names:
        p = root() / n
        arts.append({"path": str(p), "sha256":
                     hashlib.sha256(p.read_bytes()).hexdigest()})
    return {"manifest": {"artifacts": arts, "validations": []}}


def manifest(commit: str, remote: str, files: list[dict], branch: str = "main",
             remote_name: str = "origin") -> Path:
    p = root() / "provenance.json"
    p.write_text(json.dumps({
        "schema_version": 1, "kind": "git", "author": "claude",
        "remote_name": remote_name, "remote_url": remote, "branch": branch,
        "commit": commit, "files": files}, indent=2))
    return p


def run(label: str, prov: Path, ev: dict, repo: Path | None = None) -> bool:
    try:
        r = validate_git_provenance(
            prov, source_repository=repo or (W / "work"), report_root=root(),
            expected_author="claude", evidence=ev, max_blob_bytes=1_000_000)
        print(f"  {label:<34} ACCEPTED  byte_exact={r['byte_exact']}")
        return True
    except Exception as exc:
        print(f"  {label:<34} REJECTED  {type(exc).__name__}: {exc}")
        return False


def copy_out(*names: str) -> None:
    for n in names:
        shutil.copyfile(W / "work" / n, root() / n)


BOTH = [{"source_path": "report.txt", "submitted_path": "report.txt"},
        {"source_path": "raw.txt", "submitted_path": "raw.txt"}]

results: dict[str, str] = {}


def record(key: str, accepted: bool, expect_accept: bool) -> None:
    results[key] = ("as designed" if accepted == expect_accept
                    else "!! UNEXPECTED !!")


print("########## G-BASE  positive control ##########")
commit, remote = build()
copy_out("report.txt", "raw.txt")
ok = run("honest, both files bound", manifest(commit, remote, BOTH),
         evidence("report.txt", "raw.txt"))
record("G-BASE", ok, True)
if not ok:
    print("\nfixture is broken; nothing below can be interpreted")
    raise SystemExit(1)

print("\n########## G1  wrong Git remote declared ##########")
ok = run("remote_url = someone else's",
         manifest(commit, "https://example.invalid/other.git", BOTH),
         evidence("report.txt", "raw.txt"))
record("G1", ok, False)

print("\n########## G2  commit that was never pushed ##########")
(W / "work" / "report.txt").write_text("HONEST: 3 passed, 1 failed\nlocal only\n")
git("commit", "-aqm", "local-only commit")
local = git("rev-parse", "HEAD")
copy_out("report.txt")
print(f"  local commit {local[:8]} is on refs/heads/main but not on origin")
ok = run("local-only commit, tracking ref present",
         manifest(local, remote, [{"source_path": "report.txt",
                                   "submitted_path": "report.txt"}]),
         evidence("report.txt"))
record("G2", ok, False)

print("  -- and with the remote-tracking ref deleted, so the fallback is exercised:")
git("update-ref", "-d", "refs/remotes/origin/main")
ok2 = run("same, refs/remotes/origin/main gone",
          manifest(local, remote, [{"source_path": "report.txt",
                                    "submitted_path": "report.txt"}]),
          evidence("report.txt"))
record("G2b", ok2, False)
git("fetch", "-q", "origin")
git("reset", "-q", "--hard", commit)
copy_out("report.txt", "raw.txt")

print("\n########## G3  partial submission - bind only one of two ##########")
ok = run("declares report.txt, hides raw.txt",
         manifest(commit, remote, [{"source_path": "report.txt",
                                    "submitted_path": "report.txt"}]),
         evidence("report.txt", "raw.txt"))
record("G3", ok, False)

print("\n########## G4  duplicate binding ##########")
ok = run("same submitted_path twice",
         manifest(commit, remote,
                  [{"source_path": "report.txt", "submitted_path": "report.txt"},
                   {"source_path": "raw.txt", "submitted_path": "report.txt"}]),
         evidence("report.txt", "raw.txt"))
record("G4", ok, False)

print("\n########## G5  CRLF mutation with the manifest sha re-stamped ##########")
crlf = (root() / "report.txt").read_bytes().replace(b"\n", b"\r\n")
(root() / "report.txt").write_bytes(crlf)
ev = evidence("report.txt", "raw.txt")  # re-stamped: manifest agrees with the file
print(f"  submitted sha re-stamped to {ev['manifest']['artifacts'][0]['sha256'][:16]}…")
ok = run("CRLF bytes, manifest consistent", manifest(commit, remote, BOTH), ev)
record("G5", ok, False)
copy_out("report.txt")

print("\n########## G6  repo-local core.autocrlf on an honest delivery ##########")
git("config", "core.autocrlf", "true")
ok = run("honest bytes, local autocrlf=true",
         manifest(commit, remote, BOTH), evidence("report.txt", "raw.txt"))
record("G6", ok, True)
git("config", "--unset", "core.autocrlf")

print("\n########## G7  url.insteadOf rewriting the declared remote ##########")
git("config", "url.https://evil.invalid/.insteadOf", str(W / "origin.git"))
observed = git("remote", "get-url", "origin")
print(f"  git remote get-url now reports: {observed}")
ok = run("declare the pre-rewrite URL",
         manifest(commit, remote, BOTH), evidence("report.txt", "raw.txt"))
record("G7-declare-real", ok, observed == remote)
ok2 = run("declare the rewritten URL",
          manifest(commit, observed, BOTH), evidence("report.txt", "raw.txt"))
record("G7-declare-rewritten", ok2, observed != remote)
git("config", "--unset", "url.https://evil.invalid/.insteadOf")

print("\n########## summary ##########")
for k, v in results.items():
    print(f"  {k:<22} {v}")
print("\nAny '!! UNEXPECTED !!' above is a finding; everything else behaved as the")
print("design promises.  SUBMITTED, not VERIFIED.")
