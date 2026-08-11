#!/usr/bin/env bash
# Claude B / sub-task (2): can a declared-identity mutation forge verifier
# independence on a CRITICAL-tier task, and is it detectable afterwards?
set -u
REPO=/workspace/evidence-first-orchestrator
SP=/tmp/claude-0/-home-user-System1-5/992ff3ac-68a2-507b-8410-c48708c0b55d/scratchpad/cb
WS=$SP/ws2
export WS
export PYTHONPATH=$REPO/src
efo() { python3 -m evidence_orchestrator "$@"; }
step() { echo; echo "########## $* ##########"; }

rm -rf "$WS"; mkdir -p "$WS"
cd "$REPO" || exit 1

step "A0 init meta-4-agent preset"
efo init "$WS" --name attack2 --orchestrator antigravity --preset meta-4-agent
echo "exit=$?"

step "A1 declared identities as shipped by the preset"
for a in claude-a claude-b; do python3 -c "
import json,sys
d=json.load(open('$WS/agents/$a.json'))
r=d.get('record',d)
print('$a', json.dumps({'id':r.get('id'),'role':r.get('role'),**r.get('identity',{})}, sort_keys=True))
"; done

step "A2 HONEST: critical task, owner=claude-a verifier=claude-b, 3 dimensions"
efo task add "$WS" --actor antigravity --id T1 --title t --description d --owner claude-a \
  --risk-tier critical --verifier claude-b \
  --independence-dimension actor --independence-dimension controller \
  --independence-dimension model_family
echo "exit=$?  <-- expect NONZERO (model_family both claude-code)"

step "A3 FORGE: orchestrator rewrites claude-b's declared model_family"
efo agent update "$WS" --actor antigravity --id claude-b \
  --controller-id claude-b --provider anthropic --model-family gpt
echo "exit=$?"

step "A4 REPLAY the identical critical task add"
efo task add "$WS" --actor antigravity --id T1 --title t --description d --owner claude-a \
  --risk-tier critical --verifier claude-b \
  --independence-dimension actor --independence-dimension controller \
  --independence-dimension model_family
echo "exit=$?  <-- 0 means the critical-tier control was bypassed"

step "A5 drive T1 to verified"
mkdir -p "$WS/reports/claude-a"
python3 - <<'PY'
import hashlib, json, os
ws = os.environ["WS"]
d = f"{ws}/reports/claude-a"
os.makedirs(d, exist_ok=True)
art = f"{d}/T1.artifact.txt"
open(art, "w").write("artifact\n")
sha = hashlib.sha256(open(art, "rb").read()).hexdigest()
open(f"{d}/T1.md", "w").write("\n".join([
    "# T1 report", "",
    "## 1. Files changed", "See evidence manifest.", "",
    "## 2. Validation and raw output", "Recorded in the evidence manifest.", "",
    "## 3. Pass, fail, and skip counts", "Recorded in the evidence manifest.", "",
    "## 4. Known-answer comparison", "Expected and observed values are recorded.", "",
    "## 5. Proposed changes outside ownership", "None.", "",
    "## 6. Unmeasured items", "[FILL]", "",
]))
json.dump({
    "schema_version": 1,
    "artifacts": [{"path": "T1.artifact.txt", "sha256": sha}],
    "validations": [{"command": "known-test", "exit_code": 0,
                     "passed": 1, "failed": 0, "skipped": 0, "skip_reasons": []}],
    "known_answer_checks": [{"name": "two plus two", "expected": 4,
                             "observed": 4, "passed": True}],
    "claims": [{"name": "functional behavior", "kind": "functional",
                "measured": True, "value": "pass",
                "evidence": ["T1.artifact.txt"]},
               {"name": "future metric", "kind": "performance",
                "measured": False, "value": "[FILL]", "evidence": []}],
}, open(f"{d}/T1.evidence.json", "w"), indent=2)
PY
TOKEN=$(efo task claim "$WS" --actor claude-a --id T1 | python3 -c "import json,sys; print(json.load(sys.stdin)['lease_token'])")
echo "lease_token acquired: ${TOKEN:0:8}..."
efo task start  "$WS" --actor claude-a --id T1 --lease-token "$TOKEN" >/dev/null; echo "start exit=$?"
efo task submit "$WS" --actor claude-a --id T1 --lease-token "$TOKEN" \
  --report "$WS/reports/claude-a/T1.md" \
  --evidence "$WS/reports/claude-a/T1.evidence.json" >/dev/null; echo "submit exit=$?"
python3 - <<'PY2'
import hashlib, json, os
ws = os.environ["WS"]
for suffix in ("attest", "verify"):
    d = f"{ws}/reports/claude-b"
    os.makedirs(d, exist_ok=True)
    art = f"{d}/T1.{suffix}.artifact.txt"
    open(art, "w").write(f"claude-b {suffix} artifact\n")
    sha = hashlib.sha256(open(art, "rb").read()).hexdigest()
    json.dump({
        "schema_version": 1,
        "artifacts": [{"path": f"T1.{suffix}.artifact.txt", "sha256": sha}],
        "validations": [{"command": f"reverify-{suffix}", "exit_code": 0,
                         "passed": 1, "failed": 0, "skipped": 0, "skip_reasons": []}],
        "known_answer_checks": [{"name": "two plus two", "expected": 4,
                                 "observed": 4, "passed": True}],
        "claims": [{"name": "reproduced author result", "kind": "functional",
                    "measured": True, "value": "pass",
                    "evidence": [f"T1.{suffix}.artifact.txt"]}],
    }, open(f"{d}/T1.{suffix}.evidence.json", "w"), indent=2)
PY2
efo task attest "$WS" --actor claude-b --id T1 --decision accept --note ok \
  --evidence "$WS/reports/claude-b/T1.attest.evidence.json" >/dev/null; echo "attest exit=$?"
efo task verify "$WS" --actor claude-b --id T1 --decision accept --note ok \
  --evidence "$WS/reports/claude-b/T1.verify.evidence.json" >/dev/null; echo "verify exit=$?  <-- 0 means claude-b VERIFIED claude-a on a critical task"

step "A6 audit independence on the forged history"
efo audit independence "$WS"
echo "exit=$?"

step "A7 REVERT the declaration to the truth, then re-audit"
efo agent update "$WS" --actor antigravity --id claude-b \
  --controller-id claude-b --provider anthropic --model-family claude-code >/dev/null
echo "revert exit=$?"
efo audit independence "$WS"
echo "exit=$?"

step "A8 does anything else flag it?"
echo "--- ledger verify ---"; efo ledger verify "$WS"; echo "exit=$?"
echo "--- doctor ---";        efo doctor "$WS" 2>&1 | tail -25; echo "exit=$?"

step "A9 ledger record of the mutations"
python3 -c "
import json
for l in open('$WS/ledger/events.jsonl'):
    e=json.loads(l); p=e.get('payload',{})
    if e['action'] in ('agent.added','agent.updated'):
        a=p['agent']
        if a['id']=='claude-b':
            print(e['sequence'], e['action'], json.dumps(a.get('identity',{}), sort_keys=True))
    elif e['action']=='task.verified':
        print(e['sequence'], e['action'])
"
