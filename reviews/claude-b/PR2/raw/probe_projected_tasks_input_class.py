#!/usr/bin/env python3
"""What `projected_tasks` is clean ON - and the payload shape it never fed.

Queue item 62, from items 50/53. `NOTE-projected-tasks-holds.md` fed the fold
six malformed shapes and none of them retracted the verdict. This asks the
item-47 question of it: WHAT INPUT CLASS did those checks actually feed?

Classified from the published probe's OWN SOURCE by AST, not read off the
note: every one of its `payload=` arguments is a **dict**. The un-fed class is
therefore `payload` PRESENT BUT NOT A DICT - and `ledger.py:161` is

    snapshot = event.get("payload", {}).get("task")

`.get` on a str/list/int/None raises `AttributeError`. The default `{}` only
covers payload being ABSENT; it does nothing when payload is present and of
the wrong type.

AND THE CONTRAST IS THE POINT. `Ledger.read` at `ledger.py:64-65` DOES carry
the guard the collector lacked - a line that is valid JSON but not an object
is refused with `IntegrityError`. So this package does check shape at the line
level and then stops one field short. Both directions driven.

Reachability is asked separately, because "the absence is real" and "the
absence is reachable" are two different measurements: the event is signed with
the workspace's OWN key, `verify()` is asked whether it accepts it, and the
public API is then called.

    python3 probe_projected_tasks_input_class.py

SCOPE, stated first: 17 published checks classified, 2 input classes, 1 guard
driven both ways, 6 payload shapes, 4 falsy task ids, 1 signed chain, 2 public
entry points. A NARROWED SCOPE on a clean verdict - the verdict is NOT
retracted and no issue is filed.
"""

from __future__ import annotations

import ast
import hashlib
import hmac
import json
import shutil
import sys
import tempfile
from pathlib import Path
from typing import Any

sys.path.insert(0, "/tmp/efo-prov/src")
from evidence_orchestrator.ledger import Ledger  # noqa: E402
from evidence_orchestrator.util import canonical_json  # noqa: E402
from evidence_orchestrator.workspace import Workspace  # noqa: E402

FAIL = 0
ANCHOR = Path("/tmp/efo-prov")
SOURCE = ANCHOR / "src" / "evidence_orchestrator"
RAW = Path("/workspace/evidence-first-orchestrator/reviews/claude-b/PR2/raw")
ROOT = Path(tempfile.mkdtemp(prefix="efo-item62-"))


def check(name: str, expected: str, observed: str) -> None:
    global FAIL
    ok = expected in observed
    if not ok:
        FAIL += 1
    print(f"  [{'ok' if ok else '!! UNEXPECTED !!'}] {name}")
    print(f"        expected: {expected}")
    print(f"        observed: {observed}")


def attempt(name: str, expected: str, call) -> None:
    try:
        observed = f"returned {call()!r}"
    except Exception as exc:  # noqa: BLE001 - the type IS the measurement
        observed = f"{type(exc).__name__}: {exc}"
    check(name, expected, observed)


# ---------------------------------------------------------------- A
print("########## A. POSITIVE CONTROL, and the scope FIRST ##########")
import subprocess  # noqa: E402


def git(*arguments: str) -> str:
    return subprocess.run(["git", "-C", str(ANCHOR), *arguments],
                          capture_output=True, text=True).stdout.strip()


check("the review's anchor is UNMOVED at 5694ab45",
      "5694ab455139f1e72d946bc2fe7e42c7c0c8a43a", git("rev-parse", "HEAD"))
check("  with no working-tree modification", "dirty: ''",
      f"dirty: {git('status', '--porcelain')!r}")

workspace = Workspace.initialize(ROOT / "control", name="control",
                                 orchestrator="antigravity",
                                 preset="antigravity-codex-claude")
for agent in ("antigravity", "claude"):
    workspace.attest_agent_identity(
        actor="antigravity", agent_id=agent,
        control_principal="principal-" + agent,
        model_family="family-" + agent)
workspace.create_task(actor="antigravity", task_id="T1", title="t",
                      description="d", owner="claude")
check("a real workspace folds its own task - the CONTROL", "'T1'",
      str(sorted(workspace.ledger.projected_tasks())))

# ---------------------------------------------------------------- B
print("\n########## B. what the PUBLISHED checks fed, classified by AST ##########")
published = (RAW / "probe_projected_tasks.py").read_text(encoding="utf-8")
tree = ast.parse(published)
payload_kinds: dict[str, int] = {}
task_kinds: dict[str, int] = {}
for node in ast.walk(tree):
    if not isinstance(node, ast.keyword) or node.arg != "payload":
        continue
    value = node.value
    kind = type(ast.literal_eval(value)).__name__ if isinstance(
        value, (ast.Dict, ast.Constant, ast.List)) else "expr"
    payload_kinds[kind] = payload_kinds.get(kind, 0) + 1
    if isinstance(value, ast.Dict):
        literal = ast.literal_eval(value)
        inner = literal.get("task", "<absent>")
        name = ("<absent>" if inner == "<absent>"
                else type(inner).__name__)
        task_kinds[name] = task_kinds.get(name, 0) + 1
# the module-level default in the `event()` helper counts too
for node in ast.walk(tree):
    if isinstance(node, ast.Dict):
        # Pair keys with values POSITIONALLY - a filtered key list would not
        # index into node.values correctly if any key were non-constant.
        pairs = {k.value: v for k, v in zip(node.keys, node.values)
                 if isinstance(k, ast.Constant) and isinstance(k.value, str)}
        if "payload" not in pairs or "previous_hash" not in pairs:
            continue
        # Not every such dict is a literal: the signed-chain event at
        # probe_projected_tasks.py:201 computes `last["sequence"] + 1`, an
        # ast.Subscript that literal_eval refuses. Evaluate the payload VALUE
        # alone, and COUNT what cannot be evaluated rather than raising.
        try:
            kind = type(ast.literal_eval(pairs["payload"])).__name__
        except (ValueError, TypeError):
            kind = "non-literal"
        payload_kinds[kind] = payload_kinds.get(kind, 0) + 1
print(f"    payload argument kinds : {payload_kinds}")
print(f"    payload['task'] kinds  : {task_kinds}")
check("every payload the published probe fed is a DICT",
      "non-dict payloads: 0",
      f"non-dict payloads: {sum(v for k, v in payload_kinds.items() if k != 'dict')}")
# I expected TWO inner kinds and there are three - dict, str and absent.
# Corrected to the measurement; the claim that matters is unchanged, because
# all three sit INSIDE a dict payload.
check("  and it DID vary the inner task value - three kinds, not two",
      "kinds: 3", f"kinds: {len(task_kinds)}")
check("    dict, str and absent - the variation is all one level DOWN",
      "{'dict': 2, 'str': 1, '<absent>': 1}", str(task_kinds))
print("  So the note's six shapes all live INSIDE a dict payload. The class")
print("  it never fed is the payload ITSELF not being a dict.")
published_note = (RAW.parent / "NOTE-projected-tasks-holds.md").read_text(
    encoding="utf-8")
check("  and the note claims 17 checks, which is what is being narrowed",
      "**17 checks, 0 unexpected.**", published_note)

# ---------------------------------------------------------------- C
print("\n########## C. the guard that DOES exist, driven BOTH ways ##########")
line64 = SOURCE.joinpath("ledger.py").read_text(
    encoding="utf-8").splitlines()[63:65]
print(f"    ledger.py:64  {line64[0].strip()}")
print(f"    ledger.py:65  {line64[1].strip()}")
check("read() refuses a line that is not an object - quoted from the file",
      "is not an object", line64[1])


def read_line(raw: str):
    directory = Path(tempfile.mkdtemp(dir=ROOT))
    path = directory / "events.jsonl"
    path.write_text(raw + "\n", encoding="utf-8")
    return Ledger(path, directory / "lock", ROOT / "k").read()


(ROOT / "k").write_bytes(b"0" * 32)
attempt("  a JSON ARRAY line is refused", "IntegrityError",
        lambda: read_line('[1, 2, 3]'))
attempt("  a JSON STRING line is refused", "IntegrityError",
        lambda: read_line('"just a string"'))
attempt("  a JSON NUMBER line is refused", "IntegrityError",
        lambda: read_line('42'))
attempt("  a JSON null line is refused", "IntegrityError",
        lambda: read_line('null'))
attempt("  and a genuine object is ACCEPTED - the other direction",
        "returned [{'a': 1}]", lambda: read_line('{"a": 1}'))
print("  This is the guard `monitor/collector.py` did NOT have (item 59):")
print("  there, valid JSON of the wrong shape walked past a handler that")
print("  caught only JSONDecodeError. Here the line-level shape IS checked.")

# ---------------------------------------------------------------- D
print("\n########## D. the UN-FED class: payload present, not a dict ##########")
fold_line = SOURCE.joinpath("ledger.py").read_text(
    encoding="utf-8").splitlines()[160]
print(f"    ledger.py:161  {fold_line.strip()}")
check("  the fold calls .get on whatever payload holds - from the file",
      'event.get("payload", {}).get("task")', fold_line)


def fold(events: list[dict[str, Any]]):
    directory = Path(tempfile.mkdtemp(dir=ROOT))
    path = directory / "events.jsonl"
    path.write_text("\n".join(json.dumps(e, sort_keys=True)
                              for e in events) + "\n", encoding="utf-8")
    return Ledger(path, directory / "lock", ROOT / "k").projected_tasks()


def one(payload: Any) -> dict[str, Any]:
    return {"sequence": 1, "timestamp": "2026-08-02T00:00:00Z", "actor": "a",
            "action": "task.created", "task_id": "T1", "payload": payload,
            "previous_hash": "0" * 64, "event_hash": "x", "signature": "y"}


raised = 0
for label, payload in (("a string", "not a dict"),
                       ("a list", [{"task": {"id": "T1"}}]),
                       ("an integer", 7),
                       ("null", None),
                       ("a boolean", True)):
    try:
        observed = f"returned {fold([one(payload)])!r}"
    except Exception as exc:  # noqa: BLE001
        observed = f"{type(exc).__name__}: {exc}"
        raised += 1
    print(f"    payload is {label:<12} {observed}")
check("every non-dict payload raises, and the default {} does not help",
      "raised: 5", f"raised: {raised}")
attempt("  and the exception is a RAW AttributeError, not an EFOError",
        "AttributeError", lambda: fold([one("not a dict")]))
check("  payload ABSENT is the case the default {} was written for",
      "returned {}",
      "returned " + str(fold([{k: v for k, v in one(None).items()
                               if k != "payload"}])))

# ---------------------------------------------------------------- E
print("\n########## E. a FALSY task_id is not an ABSENT one ##########")
for label, task_id in (("null", None), ("empty string", ""),
                       ("integer 0", 0), ("false", False)):
    result = fold([{**one({"task": {"id": "X"}}), "task_id": task_id}])
    print(f"    task_id is {label:<14} -> {result}")
check("all four falsy task ids are silently dropped by `if task_id and ...`",
      "dropped: 4",
      f"dropped: {sum(1 for t in (None, '', 0, False) if not fold([{**one({'task': {'id': 'X'}}), 'task_id': t}]))}")
print("  Only `null` was fed by the published probe. The other three reach")
print("  the same outcome by the same truthiness test, so this NARROWS the")
print("  note's row rather than contradicting it.")

# ---------------------------------------------------------------- F
print("\n########## F. is the absence REACHABLE? signed with the real key ##########")
ws2 = Workspace.initialize(ROOT / "reach", name="reach",
                           orchestrator="antigravity",
                           preset="antigravity-codex-claude")
key = (ws2.root / ".efo" / "ledger.key").read_bytes()
lines = ws2.ledger.path.read_text(encoding="utf-8").splitlines()
last = json.loads(lines[-1])
core = {
    "sequence": last["sequence"] + 1,
    "timestamp": "2026-08-02T00:00:00Z",
    "actor": "antigravity",
    "action": "task.created",
    "task_id": "T1",
    "payload": "not a dict",
    "previous_hash": last["event_hash"],
}
event_hash = hashlib.sha256(canonical_json(core)).hexdigest()
signature = hmac.new(key, event_hash.encode("ascii"),
                     hashlib.sha256).hexdigest()
ws2.ledger.path.write_text(
    "\n".join(lines) + "\n"
    + json.dumps({**core, "event_hash": event_hash,
                  "signature": signature}, sort_keys=True) + "\n",
    encoding="utf-8")
attempt("verify() ACCEPTS an event whose payload is a string", "'valid': True",
        ws2.ledger.verify)
attempt("  so the fold is reached, and it raises", "AttributeError",
        ws2.ledger.projected_tasks)
attempt("  list_tasks() - a PUBLIC entry point - raises the same",
        "AttributeError", ws2.list_tasks)
# I expected get_task to raise it too. It does NOT - and finding out why is
# the useful part: `tasks/T1.json` does not exist in that workspace, so an
# earlier existence check fires before the fold is ever consulted. That is a
# statement about what the GUARD covers, not about the fold.
attempt("  but get_task() does NOT - it short-circuits first",
        "Unknown task: T1", lambda: ws2.get_task("T1"))
print("  So ask what that check actually covers: it covers a task that does")
print("  not exist, not a payload of the wrong type. Driven with a task that")
print("  DOES exist:")

ws3 = Workspace.initialize(ROOT / "reach2", name="reach2",
                           orchestrator="antigravity",
                           preset="antigravity-codex-claude")
for agent in ("antigravity", "claude"):
    ws3.attest_agent_identity(actor="antigravity", agent_id=agent,
                              control_principal="principal-" + agent,
                              model_family="family-" + agent)
ws3.create_task(actor="antigravity", task_id="T1", title="t",
                description="d", owner="claude")
check("    the task file now exists - the CONTROL for this sub-case",
      "exists: True", f"exists: {(ws3.root / 'tasks' / 'T1.json').is_file()}")
check("    and get_task works before the tamper", "id: 'T1'",
      f"id: {ws3.get_task('T1').get('id')!r}")
key3 = (ws3.root / ".efo" / "ledger.key").read_bytes()
lines3 = ws3.ledger.path.read_text(encoding="utf-8").splitlines()
last3 = json.loads(lines3[-1])
core3 = {
    "sequence": last3["sequence"] + 1,
    "timestamp": "2026-08-02T00:00:00Z",
    "actor": "antigravity",
    "action": "task.created",
    "task_id": "T1",
    "payload": "not a dict",
    "previous_hash": last3["event_hash"],
}
hash3 = hashlib.sha256(canonical_json(core3)).hexdigest()
ws3.ledger.path.write_text(
    "\n".join(lines3) + "\n"
    + json.dumps({**core3, "event_hash": hash3,
                  "signature": hmac.new(key3, hash3.encode("ascii"),
                                        hashlib.sha256).hexdigest()},
                 sort_keys=True) + "\n", encoding="utf-8")
attempt("    now get_task() reaches the fold and raises too", "AttributeError",
        lambda: ws3.get_task("T1"))
print("  So all three public paths crash once the task exists; the earlier")
print("  check masked one of them. The absence is REAL and reachable ONLY")
print("  with the signing key - the same precondition items 45/53/54/57")
print("  record, and the limit SECURITY.md:38 declares. It is a CRASH, not a")
print("  bypass: nothing is accepted that should be refused.")

# ---------------------------------------------------------------- G
print("\n########## G. what this does NOT establish ##########")
print("  * It does NOT retract `NOTE-projected-tasks-holds.md`. Its 17 checks")
print("    stand; what is added is the input class they did not feed.")
print("  * It does NOT file an issue. The crash needs the ledger key, and a")
print("    holder of that key can already rewrite the chain (#9). Under the")
print("    declared threat model this is unreachable, and quantifying an open")
print("    precondition is not opening a new issue.")
print("  * It is NOT a new instance of #19. #19 is a KeyError escaping the")
print("    CLI on a repaired projection; this is an AttributeError inside the")
print("    fold on a signed non-dict payload. Related shape, different path,")
print("    and it is recorded here rather than appended there.")
print("  * It does NOT measure `Ledger.append` under concurrency, nor")
print("    `_verify_events` beyond what #9 already covers.")
print("  * No network, no GPU. Three tempfile workspaces, removed before the")
print("    results print. The anchor's working tree is untouched, and it does")
print("    not touch `main` or another agent's branch.")
print("  * MEASURED: the AST classification of the published probe, both")
print("    directions of the read() guard, five non-dict payloads, the absent")
print("    case, four falsy task ids, the signed chain, three public entry")
print("    points. REASONED: nothing.")

shutil.rmtree(ROOT, ignore_errors=True)
print(f"\n########## {FAIL} unexpected result(s) ##########")
print("Pre-registered permissions unchanged - gpu/network/performance_metrics")
print("all false. SUBMITTED, not VERIFIED: re-running my own evidence is a")
print("re-run, not independent confirmation.")
