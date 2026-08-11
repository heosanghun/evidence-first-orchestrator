#!/usr/bin/env bash
# Does the rewritten provenance.py on main (5694ab45, 341 lines) still reject a
# `git replace` substitution?  At cef5623 (193 lines) _run_git passed
# --no-replace-objects and the attack was rejected; that flag is gone on main.
set -u
REPO=/tmp/efo-prov                      # worktree at main 5694ab45
SP=/tmp/claude-0/-home-user-System1-5/992ff3ac-68a2-507b-8410-c48708c0b55d/scratchpad/cb
W=/tmp/prov-attack
export PYTHONPATH=$REPO/src
step() { echo; echo "########## $* ##########"; }

rm -rf "$W"; mkdir -p "$W"
export GIT_AUTHOR_NAME=t GIT_AUTHOR_EMAIL=t@e GIT_COMMITTER_NAME=t GIT_COMMITTER_EMAIL=t@e
export GIT_AUTHOR_DATE="2026-01-01T00:00:00Z" GIT_COMMITTER_DATE="2026-01-01T00:00:00Z"

step "P0 build a real origin + work clone"
git init -q --bare "$W/origin.git"
git clone -q "$W/origin.git" "$W/work" 2>/dev/null
cd "$W/work" || exit 1
printf 'HONEST: 3 passed, 1 failed\n' > report.txt
git add report.txt && git commit -qm "honest evidence"
git branch -M main && git push -q origin main 2>/dev/null
git fetch -q origin 2>/dev/null
C=$(git rev-parse HEAD); echo "commit C = $C"
echo "remote  = $(git remote get-url origin)"
echo "blob    = $(git cat-file blob "$C:report.txt")"

mkroot() {  # $1 = content to place in the submitted evidence file
python3 - "$1" <<'PY'
import hashlib, json, os, sys
content = sys.argv[1]
root = "/tmp/prov-attack/reports/claude"; os.makedirs(root, exist_ok=True)
sub = f"{root}/report.txt"
open(sub, "w").write(content)
sha = hashlib.sha256(open(sub, "rb").read()).hexdigest()
json.dump({"schema_version": 1, "kind": "git", "author": "claude",
           "remote_name": "origin",
           "remote_url": open("/tmp/prov-attack/remote_url").read().strip(),
           "branch": "main",
           "commit": open("/tmp/prov-attack/commit").read().strip(),
           "files": [{"source_path": "report.txt", "submitted_path": "report.txt"}]},
          open(f"{root}/provenance.json", "w"), indent=2)
json.dump({"manifest": {"artifacts": [{"path": sub, "sha256": sha}],
                        "validations": []}},
          open("/tmp/prov-attack/evidence.json", "w"))
print("submitted sha256 =", sha)
PY
}

run() {
python3 - <<'PY'
import json, sys, traceback
sys.path.insert(0, "/tmp/efo-prov/src")
from evidence_orchestrator.provenance import validate_git_provenance
ev = json.load(open("/tmp/prov-attack/evidence.json"))
try:
    r = validate_git_provenance(
        "/tmp/prov-attack/reports/claude/provenance.json",
        source_repository="/tmp/prov-attack/work",
        report_root="/tmp/prov-attack/reports/claude",
        expected_author="claude",
        evidence=ev,
        max_blob_bytes=1_000_000,
    )
    print("ACCEPTED  byte_exact=%s blob_oid=%s" % (r["byte_exact"], r["files"][0]["blob_oid"]))
except Exception as exc:
    print("REJECTED  %s: %s" % (type(exc).__name__, exc))
PY
}

git remote get-url origin > "$W/remote_url"; echo "$C" > "$W/commit"

step "P1 POSITIVE CONTROL - honest submission (bytes match the commit)"
mkroot 'HONEST: 3 passed, 1 failed
'
run
echo "<-- expect ACCEPTED"

step "P2 plain tamper, no git replace (submitted bytes differ from the commit)"
mkroot 'FORGED: 4 passed, 0 failed
'
run
echo "<-- expect REJECTED"

step "P3 THE ATTACK - same forged bytes, plus a git replace object"
cd "$W/work" || exit 1
printf 'FORGED: 4 passed, 0 failed\n' > report.txt
git add report.txt && git commit -qm "forged tree"
CF=$(git rev-parse HEAD)
git reset -q --hard "$C"
git replace "$C" "$CF"
echo "replace ref: $(git replace -l)  ->  $CF"
echo "git cat-file blob C:report.txt      = $(git cat-file blob "$C:report.txt")"
echo "with --no-replace-objects           = $(git --no-replace-objects cat-file blob "$C:report.txt")"
mkroot 'FORGED: 4 passed, 0 failed
'
run
echo "<-- ACCEPTED here means the replace object forged byte-exactness"

step "P4 what an independent re-check sees in the real history"
echo "origin.git holds: $(git --git-dir="$W/origin.git" cat-file blob "$C:report.txt")"
echo "declared commit : $C"

step "P5 A/B - the SAME forged state against cef5623, which passes --no-replace-objects"
cat > /tmp/ab_cef.py <<'PY'
import sys
sys.path.insert(0, "/tmp/efo-cef5623/src")
from evidence_orchestrator.provenance import verify_git_delivery
def check(label):
    try:
        r = verify_git_delivery(
            repo_path="/tmp/prov-attack/work", remote_name="origin",
            expected_remote_url=open("/tmp/prov-attack/remote_url").read().strip(),
            source_ref="refs/heads/main",
            source_commit=open("/tmp/prov-attack/commit").read().strip(),
            files=[{"local_path": "/tmp/prov-attack/reports/claude/report.txt",
                    "repo_path": "report.txt"}])
        print("%s ACCEPTED sha256=%s" % (label, r["files"][0]["sha256"]))
    except Exception as exc:
        print("%s REJECTED %s: %s" % (label, type(exc).__name__, exc))
check("cef5623 forged+replace:")
PY
python3 /tmp/ab_cef.py
printf 'HONEST: 3 passed, 1 failed\n' > /tmp/prov-attack/reports/claude/report.txt
sed -i 's/cef5623 forged+replace:/cef5623 honest control:  /' /tmp/ab_cef.py
python3 /tmp/ab_cef.py
echo "<-- the honest control must ACCEPT, otherwise the rejection above is the wrong gate"
printf 'FORGED: 4 passed, 0 failed\n' > /tmp/prov-attack/reports/claude/report.txt
