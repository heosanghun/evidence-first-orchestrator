#!/usr/bin/env bash
# Does P1-1 survive codex/proxy-submission (e2cf6b4), the reimplementation?
# Same question as before: can the orchestrator forge verifier independence by
# rewriting a declared identity, and does the audit surface it?
set -u
REPO=/tmp/efo-main
SP=/tmp/claude-0/-home-user-System1-5/992ff3ac-68a2-507b-8410-c48708c0b55d/scratchpad/cb
WS=$SP/wsm; export WS
export PYTHONPATH=$REPO/src
efo() { python3 -m evidence_orchestrator "$@"; }
step() { echo; echo "########## $* ##########"; }

mkverifier() {  # build a verification manifest for claude-verifier
python3 - <<'PY2'
import hashlib, json, os
ws = os.environ["WS"]; d = f"{ws}/reports/claude-verifier"; os.makedirs(d, exist_ok=True)
art = f"{d}/T1.verify.artifact.txt"; open(art, "w").write("reverified\n")
sha = hashlib.sha256(open(art, "rb").read()).hexdigest()
json.dump({"schema_version": 1,
  "artifacts": [{"path": "T1.verify.artifact.txt", "sha256": sha}],
  "validations": [{"command": "reverify", "exit_code": 0, "passed": 1,
                   "failed": 0, "skipped": 0, "skip_reasons": []}],
  "known_answer_checks": [{"name": "two plus two", "expected": 4,
                           "observed": 4, "passed": True}],
  "claims": [{"name": "reproduced author result", "kind": "functional",
              "measured": True, "value": "pass",
              "evidence": ["T1.verify.artifact.txt"]}]},
  open(f"{d}/T1.verify.evidence.json", "w"), indent=2)
PY2
}


rm -rf "$WS"; cd "$REPO" || exit 1

step "B0 init antigravity-codex-claude preset"
efo init "$WS" --name proxyattack --orchestrator antigravity \
  --preset antigravity-codex-claude >/dev/null; echo "init exit=$?"
for a in antigravity codex claude; do python3 -c "
import json; d=json.load(open('$WS/agents/$a.json'))
print('$a', json.dumps({'role':d.get('role'),**(d.get('identity') or {})}, sort_keys=True))
"; done

step "B1 register a verifier that SHARES claude's declared identity"
efo agent add "$WS" --actor antigravity --id claude-verifier --role verifier \
  --mode manual --control-principal claude --model-family anthropic-claude \
  >/dev/null; echo "add exit=$?"

step "B2 task owned by claude, then submit"
efo task add "$WS" --actor antigravity --id T1 --title t --description d \
  --owner claude >/dev/null; echo "task add exit=$?"
python3 - <<'PY'
import hashlib, json, os
ws = os.environ["WS"]; d = f"{ws}/reports/claude"; os.makedirs(d, exist_ok=True)
art = f"{d}/T1.artifact.txt"; open(art, "w").write("artifact\n")
sha = hashlib.sha256(open(art, "rb").read()).hexdigest()
open(f"{d}/T1.md", "w").write("\n".join([
    "# T1 report", "",
    "## 1. Files changed", "See evidence manifest.", "",
    "## 2. Validation and raw output", "Recorded in the evidence manifest.", "",
    "## 3. Pass, fail, and skip counts", "Recorded in the evidence manifest.", "",
    "## 4. Known-answer comparison", "Expected and observed values are recorded.", "",
    "## 5. Proposed changes outside ownership", "None.", "",
    "## 6. Unmeasured items", "[FILL]", ""]))
json.dump({"schema_version": 1,
  "artifacts": [{"path": "T1.artifact.txt", "sha256": sha}],
  "validations": [{"command": "known-test", "exit_code": 0, "passed": 1,
                   "failed": 0, "skipped": 0, "skip_reasons": []}],
  "known_answer_checks": [{"name": "two plus two", "expected": 4,
                           "observed": 4, "passed": True}],
  "claims": [{"name": "functional behavior", "kind": "functional",
              "measured": True, "value": "pass",
              "evidence": ["T1.artifact.txt"]}]},
  open(f"{d}/T1.evidence.json", "w"), indent=2)
PY
TOKEN=$(efo task claim "$WS" --actor claude --id T1 | python3 -c "import json,sys; print(json.load(sys.stdin)['lease_token'])")
efo task start  "$WS" --actor claude --id T1 --lease-token "$TOKEN" >/dev/null; echo "start exit=$?"
efo task submit "$WS" --actor claude --id T1 --lease-token "$TOKEN" \
  --report "$WS/reports/claude/T1.md" \
  --evidence "$WS/reports/claude/T1.evidence.json" >/dev/null 2>"$SP/p_submit.err"; echo "submit exit=$?"; cat "$SP/p_submit.err"

step "B3 HONEST: claude-verifier (same declared identity) tries to verify"
mkverifier
efo task verify "$WS" --actor claude-verifier --id T1 --decision accept --note ok \
  --evidence "$WS/reports/claude-verifier/T1.verify.evidence.json" 2>&1 | tail -2
echo "<-- expect REJECT (shared control_principal + model_family)"

step "B4 FORGE: orchestrator re-attests claude-verifier with a different identity"
efo agent attest "$WS" --actor antigravity --id claude-verifier \
  --control-principal openai --model-family openai-codex 2>&1 | tail -3
echo "attest exit=$?"

step "B5 REPLAY the identical verify"
efo task verify "$WS" --actor claude-verifier --id T1 --decision accept --note ok \
  --evidence "$WS/reports/claude-verifier/T1.verify.evidence.json" >/dev/null 2>"$SP/p_verify.err"
echo "verify exit=$?  <-- 0 means independence was forged"; cat "$SP/p_verify.err"
efo task show "$WS" --id T1 2>/dev/null | python3 -c "import json,sys; print('state =', json.load(sys.stdin)['state'])"

step "B6 does ledger audit-independence surface it?"
efo ledger audit-independence "$WS" 2>&1 | tail -40
echo "exit=$?"

step "B7 ledger record of the identity attestation"
python3 -c "
import json
for l in open('$WS/ledger/events.jsonl'):
    e=json.loads(l); p=e.get('payload',{})
    a=p.get('agent')
    if e['action'] in ('agent.added','agent.identity_attested') and a and a.get('id')=='claude-verifier':
        print(e['sequence'], e['action'], json.dumps(a.get('identity'), sort_keys=True))
    elif e['action'] in ('task.verified','task.submitted'):
        print(e['sequence'], e['action'])
"
