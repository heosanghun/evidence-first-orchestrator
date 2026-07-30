#!/usr/bin/env bash
# Claude B / sub-task (3): Git provenance attacks against proxy delivery.
#   G1 wrong Git remote
#   G2 local-only commit (never advertised by the remote)
#   G3 git replace-ref content swap
#   G4 partial file submission (fewer than the preregistered repo paths)
#   G5 CRLF tampering (working-tree bytes != blob bytes)
set -u
REPO=/workspace/evidence-first-orchestrator
SP=/tmp/claude-0/-home-user-System1-5/992ff3ac-68a2-507b-8410-c48708c0b55d/scratchpad/cb
G=$SP/git3
export PYTHONPATH=$REPO/src
export GIT_CONFIG_GLOBAL=$G/gitconfig GIT_CONFIG_SYSTEM=/dev/null
efo() { python3 -m evidence_orchestrator "$@"; }
step() { echo; echo "########## $* ##########"; }
run() { echo "\$ $*"; "$@"; echo "exit=$?"; }

rm -rf "$G"; mkdir -p "$G"
: > "$G/gitconfig"
git config --global user.email cb@example.invalid
git config --global user.name  "claude b"
git config --global init.defaultBranch main
git config --global protocol.file.allow always
cd "$REPO" || exit 1

step "G0 build origin + work repos"
git init --bare -q "$G/origin.git"
git init -q "$G/work"
printf 'alpha\n' > "$G/work/a.txt"
printf 'beta\n'  > "$G/work/b.txt"
git -C "$G/work" add a.txt b.txt
git -C "$G/work" commit -qm "honest commit"
git -C "$G/work" remote add origin "$G/origin.git"
git -C "$G/work" push -q origin HEAD:refs/heads/main
GOOD=$(git -C "$G/work" rev-parse HEAD)
echo "origin.git=$G/origin.git"
echo "GOOD commit=$GOOD"
git -C "$G/work" ls-remote --refs origin refs/heads/main

# ---- workspace + proxy task ---------------------------------------------
WS=$G/ws; export WS
efo init "$WS" --name g3 --orchestrator antigravity --preset meta-4-agent >/dev/null
efo task add "$WS" --actor antigravity --id P1 --title p --description d \
  --owner claude-a --risk-tier medium --verifier claude-b \
  --allow-proxy-delivery --proxy-remote-name origin \
  --proxy-remote-url "$G/origin.git" --proxy-ref refs/heads/main \
  --proxy-repo-path a.txt --proxy-repo-path b.txt >/dev/null
echo "proxy task P1 created, exit=$?"

# ---- helper: build report+manifest under reports/antigravity ------------
mkbundle() {  # $1 = subdir tag; copies given local files as artifacts
  local tag=$1; shift
  local d="$WS/reports/antigravity/$tag"
  rm -rf "$d"; mkdir -p "$d"
  local files=("$@")
  python3 - "$d" "${files[@]}" <<'PY'
import hashlib, json, os, shutil, sys
d = sys.argv[1]; srcs = sys.argv[2:]
open(os.path.join(d, "P1.md"), "w").write("\n".join([
    "# P1 report", "",
    "## 1. Files changed", "See evidence manifest.", "",
    "## 2. Validation and raw output", "Recorded in the evidence manifest.", "",
    "## 3. Pass, fail, and skip counts", "Recorded in the evidence manifest.", "",
    "## 4. Known-answer comparison", "Expected and observed values are recorded.", "",
    "## 5. Proposed changes outside ownership", "None.", "",
    "## 6. Unmeasured items", "[FILL]", "",
]))
arts = []
for s in srcs:
    dst = os.path.join(d, os.path.basename(s))
    shutil.copyfile(s, dst)
    arts.append({"path": os.path.basename(s),
                 "sha256": hashlib.sha256(open(dst, "rb").read()).hexdigest()})
json.dump({
    "schema_version": 1,
    "artifacts": arts,
    "validations": [{"command": "known-test", "exit_code": 0, "passed": 1,
                     "failed": 0, "skipped": 0, "skip_reasons": []}],
    "known_answer_checks": [{"name": "two plus two", "expected": 4,
                             "observed": 4, "passed": True}],
    "claims": [{"name": "functional behavior", "kind": "functional",
                "measured": True, "value": "pass",
                "evidence": [a["path"] for a in arts]}],
}, open(os.path.join(d, "P1.evidence.json"), "w"), indent=2)
PY
}

sfjson() {  # emit [{local_path, repo_path}, ...] for tag + pairs base:repopath
  local tag=$1; shift
  python3 - "$WS/reports/antigravity/$tag" "$@" <<'PY'
import json, os, sys
d = sys.argv[1]
out = []
for pair in sys.argv[2:]:
    base, repo_path = pair.split("=", 1)
    out.append({"local_path": os.path.join(d, base), "repo_path": repo_path})
print(json.dumps(out))
PY
}

step "G-BASE honest proxy submission (must SUCCEED, else the harness is wrong)"
mkbundle base "$G/work/a.txt" "$G/work/b.txt"
run efo task proxy-submit "$WS" --actor antigravity --id P1 --author claude-a \
  --report "$WS/reports/antigravity/base/P1.md" \
  --evidence "$WS/reports/antigravity/base/P1.evidence.json" \
  --source-repo "$G/work" --source-commit "$GOOD" \
  --source-files-json "$(sfjson base a.txt=a.txt b.txt=b.txt)"

step "G1 WRONG REMOTE: repo's 'origin' repointed at a different bare repo"
git init --bare -q "$G/evil.git"
git -C "$G/work" remote set-url origin "$G/evil.git"
git -C "$G/work" push -q origin HEAD:refs/heads/main
efo task requeue "$WS" --actor antigravity --id P1 --note retry >/dev/null 2>&1
mkbundle g1 "$G/work/a.txt" "$G/work/b.txt"
run efo task proxy-submit "$WS" --actor antigravity --id P1 --author claude-a \
  --report "$WS/reports/antigravity/g1/P1.md" \
  --evidence "$WS/reports/antigravity/g1/P1.evidence.json" \
  --source-repo "$G/work" --source-commit "$GOOD" \
  --source-files-json "$(sfjson g1 a.txt=a.txt b.txt=b.txt)"
git -C "$G/work" remote set-url origin "$G/origin.git"

step "G2 LOCAL-ONLY COMMIT: commit exists locally, never pushed to origin"
printf 'alpha-tampered\n' > "$G/work/a.txt"
git -C "$G/work" commit -qam "local-only commit"
LOCAL_ONLY=$(git -C "$G/work" rev-parse HEAD)
echo "LOCAL_ONLY=$LOCAL_ONLY"
echo "origin still advertises:"; git -C "$G/work" ls-remote --refs origin refs/heads/main
mkbundle g2 "$G/work/a.txt" "$G/work/b.txt"
run efo task proxy-submit "$WS" --actor antigravity --id P1 --author claude-a \
  --report "$WS/reports/antigravity/g2/P1.md" \
  --evidence "$WS/reports/antigravity/g2/P1.evidence.json" \
  --source-repo "$G/work" --source-commit "$LOCAL_ONLY" \
  --source-files-json "$(sfjson g2 a.txt=a.txt b.txt=b.txt)"
git -C "$G/work" reset -q --hard "$GOOD"

step "G3 REPLACE-REF: swap the honest commit's content via git replace"
printf 'alpha-evil\n' > "$G/work/a.txt"
git -C "$G/work" commit -qam "evil content"
EVIL=$(git -C "$G/work" rev-parse HEAD)
git -C "$G/work" reset -q --hard "$GOOD"
git -C "$G/work" replace -f "$GOOD" "$EVIL"
echo "replace refs:"; git -C "$G/work" replace -l
echo "with replacement active, GOOD:a.txt reads as:"
git -C "$G/work" cat-file blob "$GOOD:a.txt"
echo "with --no-replace-objects (what EFO uses):"
git -C "$G/work" --no-replace-objects cat-file blob "$GOOD:a.txt"
# deliver the EVIL bytes, claiming the GOOD commit
printf 'alpha-evil\n' > "$G/evil-a.txt"
mkbundle g3 "$G/evil-a.txt" "$G/work/b.txt"
run efo task proxy-submit "$WS" --actor antigravity --id P1 --author claude-a \
  --report "$WS/reports/antigravity/g3/P1.md" \
  --evidence "$WS/reports/antigravity/g3/P1.evidence.json" \
  --source-repo "$G/work" --source-commit "$GOOD" \
  --source-files-json "$(sfjson g3 evil-a.txt=a.txt b.txt=b.txt)"
git -C "$G/work" replace -d "$GOOD"

step "G4 PARTIAL SUBMISSION: bind only a.txt when a.txt+b.txt are preregistered"
mkbundle g4 "$G/work/a.txt"
run efo task proxy-submit "$WS" --actor antigravity --id P1 --author claude-a \
  --report "$WS/reports/antigravity/g4/P1.md" \
  --evidence "$WS/reports/antigravity/g4/P1.evidence.json" \
  --source-repo "$G/work" --source-commit "$GOOD" \
  --source-files-json "$(sfjson g4 a.txt=a.txt)"

step "G4b DUPLICATE BINDING: bind a.txt twice to fake the count"
mkbundle g4b "$G/work/a.txt"
run efo task proxy-submit "$WS" --actor antigravity --id P1 --author claude-a \
  --report "$WS/reports/antigravity/g4b/P1.md" \
  --evidence "$WS/reports/antigravity/g4b/P1.evidence.json" \
  --source-repo "$G/work" --source-commit "$GOOD" \
  --source-files-json "$(sfjson g4b a.txt=a.txt a.txt=a.txt)"

step "G5 CRLF TAMPERING: delivered file line-endings differ from the blob"
mkbundle g5 "$G/work/a.txt" "$G/work/b.txt"
python3 - <<'PY'
import os
p = os.path.join(os.environ["WS"], "reports/antigravity/g5/a.txt")
data = open(p, "rb").read()
open(p, "wb").write(data.replace(b"\n", b"\r\n"))
print("g5/a.txt bytes now:", open(p, "rb").read())
PY
echo "-- re-stamping the manifest SHA so ONLY the git-blob check can catch it --"
python3 - <<'PY'
import hashlib, json, os
d = os.path.join(os.environ["WS"], "reports/antigravity/g5")
m = json.load(open(f"{d}/P1.evidence.json"))
for art in m["artifacts"]:
    art["sha256"] = hashlib.sha256(open(f"{d}/{art['path']}", "rb").read()).hexdigest()
json.dump(m, open(f"{d}/P1.evidence.json", "w"), indent=2)
print("manifest SHAs re-stamped to the CRLF bytes")
PY
run efo task proxy-submit "$WS" --actor antigravity --id P1 --author claude-a \
  --report "$WS/reports/antigravity/g5/P1.md" \
  --evidence "$WS/reports/antigravity/g5/P1.evidence.json" \
  --source-repo "$G/work" --source-commit "$GOOD" \
  --source-files-json "$(sfjson g5 a.txt=a.txt b.txt=b.txt)"

step "G6 autocrlf checkout: does core.autocrlf make an HONEST delivery fail?"
git -C "$G/work" config core.autocrlf true
rm -f "$G/work/a.txt" "$G/work/b.txt"
git -C "$G/work" checkout -q -- a.txt b.txt
echo "working-tree a.txt bytes:"; python3 -c "print(open('$G/work/a.txt','rb').read())"
mkbundle g6 "$G/work/a.txt" "$G/work/b.txt"
run efo task proxy-submit "$WS" --actor antigravity --id P1 --author claude-a \
  --report "$WS/reports/antigravity/g6/P1.md" \
  --evidence "$WS/reports/antigravity/g6/P1.evidence.json" \
  --source-repo "$G/work" --source-commit "$GOOD" \
  --source-files-json "$(sfjson g6 a.txt=a.txt b.txt=b.txt)"
git -C "$G/work" config core.autocrlf false

step "G7 task state after all attacks"
efo task show "$WS" --id P1 2>/dev/null | python3 -c "import json,sys; t=json.load(sys.stdin); print('state=',t['state'],'attempt=',t['attempt'])"
