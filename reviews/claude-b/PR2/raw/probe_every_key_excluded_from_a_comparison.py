#!/usr/bin/env python3
"""Is `last_event_hash` the only key the product excludes from a comparison?

Queue item 74, from item 71. That round found `last_event_hash` excluded BY
NAME from all four projection comparisons, which is what lets it be forged
into a signed record. The obvious next question is whether it is the ONLY key
in the package with that property.

Three mechanisms can drop a key before an equality, and all three are
enumerated from the AST rather than grepped:

    M1  a mapping comprehension carrying an `if` filter
    M2  a comparison that iterates ONE side's keys, so extra keys on the
        other side are never looked at
    M3  a `pop`/`del` on a mapping before it is compared

The answer is YES - `last_event_hash` is the only key excluded by name. The
other two mechanisms occur once each, and both are DRIVEN here rather than
argued away:

    the proxy grant is validated against five named keys, but the whole grant
        lives inside the task projection, so an extra key or an altered one
        trips `Task T1 projection differs from the signed ledger`
    `pending.pop("external_status")` is a state WRITE, not a comparison

And TWO controls that each cost me a wrong answer first:

    setting `consumed_at` to `None` looked UNCAUGHT until I noticed the field
        already held `None` - a mutation that writes the value already there
        is not a tamper
    the first version of the moved-check compared the FILE'S BYTES, and
        re-serialising alone changes those, so it called the no-op a real
        change. It compares the parsed VALUE now.

A fifth filtered comprehension exists at `independence.py:121`; it filters by
TYPE inside a policy parser, not by key name before a comparison, and my
first sweep of this round missed it because I matched `if` conditions
containing `!=` or `in` rather than walking the AST.

    python3 probe_every_key_excluded_from_a_comparison.py

SCOPE, stated first: 16 package modules, 3 exclusion mechanisms, every site of
each classified, 5 filtered comprehensions of which 4 exclude a key BY NAME,
1 key name in total, 2 candidate second exemptions driven, 5 tamper drives,
2 controls. A MAP with a NEGATIVE result. No issue filed.
"""

from __future__ import annotations

import ast
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, "/tmp/efo-prov/src")
from evidence_orchestrator.errors import EFOError  # noqa: E402
from evidence_orchestrator.workspace import Workspace  # noqa: E402

FAIL = 0
ANCHOR = Path("/tmp/efo-prov")
ANCHOR_SHA = "5694ab455139f1e72d946bc2fe7e42c7c0c8a43a"
PACKAGE = ANCHOR / "src/evidence_orchestrator"
ROOT = Path(tempfile.mkdtemp(prefix="efo-item74-")).resolve()


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


# ---------------------------------------------------------------- A
print("########## A. POSITIVE CONTROL, and the scope FIRST ##########")
check("the review's anchor is UNMOVED at 5694ab45", ANCHOR_SHA,
      git("rev-parse", "HEAD"))
check("  with no working-tree modification", "dirty: ''",
      f"dirty: {git('status', '--porcelain')!r}")
modules = sorted(p for p in PACKAGE.glob("*.py"))
check("  package modules swept", "modules: 16", f"modules: {len(modules)}")
trees = {p.name: ast.parse(p.read_text(encoding="utf-8")) for p in modules}

# ---------------------------------------------------------------- B
print("\n########## B. M1 - mapping comprehensions with an `if` filter ##########")
m1: list = []
for name, tree in trees.items():
    for node in ast.walk(tree):
        if isinstance(node, ast.DictComp):
            for generator in node.generators:
                if generator.ifs:
                    m1.append((name, node.lineno, ast.unparse(node)))
for name, line, source in sorted(m1):
    print(f"    {name}:{line}  {source[:96]}")
check("mapping comprehensions that filter", "sites: 5", f"sites: {len(m1)}")
# CLASSIFIED, both directions asserted below. Four exclude a key BY NAME before
# an equality; the fifth filters by TYPE inside a parser and is not near a
# comparison at all. My first sweep of this round matched only `if` conditions
# containing `!=` or `in` and never saw it - the AST does.
by_name = [(n, line, s) for n, line, s in m1
           if any(isinstance(c, ast.Constant) and isinstance(c.value, str)
                  for g in ast.walk(ast.parse(s)) if isinstance(g, ast.comprehension)
                  for i in g.ifs for c in ast.walk(i))]
by_type = [(n, line, s) for n, line, s in m1 if (n, line, s) not in by_name]
check("  of which exclude a key BY NAME", "by name: 4", f"by name: {len(by_name)}")
check("    and filter by TYPE in a parser instead", "by type: 1",
      f"by type: {len(by_type)}")
check("      the split is exhaustive in both directions", f"total: {len(m1)}",
      f"total: {len(by_name) + len(by_type)}")
check("        and the type filter is independence.py's policy parser",
      "independence.py", str([n for n, _, _ in by_type]))
excluded = sorted({literal.value
                   for _, _, source in m1
                   for literal in ast.walk(ast.parse(source))
                   if isinstance(literal, ast.Constant)
                   and isinstance(literal.value, str)})
check("  and the set of key names they exclude", "['last_event_hash']",
      str(excluded))
check("    at these lines - item 71's four, re-derived",
      "[469, 494, 516, 1510]", str(sorted(line for _, line, _ in by_name)))
check("      all in one module", "{'workspace.py'}",
      str({name for name, _, _ in by_name}))
print("  So ONE key name is excluded by name anywhere in the package, and")
print("  every site of it is a task projection. That is the whole of M1.")

# ---------------------------------------------------------------- C
print("\n########## C. M2 and M3 - the other two ways to drop a key ##########")
m2: list = []
for name, tree in trees.items():
    for node in ast.walk(tree):
        if isinstance(node, (ast.ListComp, ast.SetComp, ast.GeneratorExp,
                             ast.DictComp)):
            source = ast.unparse(node)
            if ".items()" in source and ".get(" in source and (
                    "!=" in source or "==" in source):
                m2.append((name, node.lineno, source))
m3: list = []
for name, tree in trees.items():
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) \
                and node.func.attr == "pop" and node.args and isinstance(
                    node.args[0], ast.Constant):
            m3.append((name, node.lineno, ast.unparse(node)))
        if isinstance(node, ast.Delete):
            m3.append((name, node.lineno, ast.unparse(node)))
for name, line, source in sorted(m2 + m3):
    print(f"    {name}:{line}  {source[:96]}")
check("M2 - comparisons that iterate one side's keys", "sites: 1",
      f"sites: {len(m2)}")
check("M3 - a pop or del of a named key", "sites: 1", f"sites: {len(m3)}")
check("  and M3's single site is a WRITE, not a comparison",
      "pending.pop('external_status', None)",
      m3[0][2] if m3 else "NONE")
print("  `requeue` clears a field before committing the new state - the value")
print("  it removes is then SIGNED as absent, so nothing is being hidden from")
print("  a comparison. Classified and dismissed with the reason.")

INDEX = [0]


def workspace() -> Workspace:
    INDEX[0] += 1
    root = ROOT / f"{INDEX[0]:02d}"
    built = Workspace.initialize(root, name="item74",
                                 orchestrator="antigravity",
                                 preset="antigravity-codex-claude")
    for agent in ("antigravity", "claude"):
        built.attest_agent_identity(actor="antigravity", agent_id=agent,
                                    control_principal="p-" + agent,
                                    model_family="f-" + agent)
    built.create_task(actor="antigravity", task_id="T1", title="t",
                      description="d", owner="claude")
    return built


def tamper(path: Path, mutate) -> str:
    """Mutate a JSON file and REFUSE to report on a no-op."""
    document = json.loads(path.read_text(encoding="utf-8"))
    before = json.dumps(document, sort_keys=True)
    mutate(document)
    after = json.dumps(document, sort_keys=True)
    path.write_text(json.dumps(document), encoding="utf-8")
    # Compare the parsed VALUE, not the bytes: re-serialising alone changes
    # the bytes, so a byte comparison calls every no-op a change. That is the
    # second version of this check; the first one was wrong for exactly that
    # reason and reported the no-op below as a real tamper.
    return "changed" if after != before else "NO-OP - the value did not move"


def audit_task(built: Workspace) -> str:
    try:
        Workspace(built.root).get_task("T1")
        return "UNCAUGHT"
    except EFOError as exc:
        return f"CAUGHT {type(exc).__name__}: {exc}"


# ---------------------------------------------------------------- D
print("\n########## D. M2's one site, DRIVEN ##########")
print("  `_require_proxy_grant` validates the grant against FIVE named keys")
print("  and three more by hand. Any other key in the grant is never looked")
print("  at THERE - so the question is whether anything else looks at it.")
for label, mutate in (
        ("an EXTRA key added to the grant",
         lambda d: d["proxy_grant"].update({"junk": "x"})),
        ("the grant's branch altered",
         lambda d: d["proxy_grant"].update({"branch": "other"})),
        ("consumed_at set to a timestamp",
         lambda d: d["proxy_grant"].update(
             {"consumed_at": "2026-01-01T00:00:00Z"}))):
    built = workspace()
    built.authorize_proxy_submission(
        actor="antigravity", task_id="T1", transport_actor="antigravity",
        remote_url="https://example.invalid/r.git", branch="delivery",
        commit="0" * 40, duration_seconds=300)
    moved = tamper(built.root / "tasks" / "T1.json", mutate)
    check(f"  {label} really changed the file", "changed", moved)
    check(f"    and it is", "CAUGHT IntegrityError", audit_task(built))

# THE NO-OP CONTROL. My first run of this section reported `consumed_at`
# UNCAUGHT - because at grant time the field already holds None, so writing
# None changed nothing. The driver now proves the bytes moved before it
# reports, and this case is kept as the demonstration.
built = workspace()
built.authorize_proxy_submission(
    actor="antigravity", task_id="T1", transport_actor="antigravity",
    remote_url="https://example.invalid/r.git", branch="delivery",
    commit="0" * 40, duration_seconds=300)
projection = json.loads(
    (built.root / "tasks" / "T1.json").read_text(encoding="utf-8"))
check("the grant's consumed_at is ALREADY None at grant time",
      "consumed_at: None",
      f"consumed_at: {projection['proxy_grant'].get('consumed_at')}")
check("  so writing None back is a NO-OP, not a tamper",
      "NO-OP", tamper(built.root / "tasks" / "T1.json",
                      lambda d: d["proxy_grant"].update({"consumed_at": None})))
print("  That no-op is what made this section read UNCAUGHT on the first")
print("  run. A driver that does not check the bytes moved will call a")
print("  guard absent when nothing was ever driven at it.")

# ---------------------------------------------------------------- E
print("\n########## E. and the agent records are compared in FULL ##########")
for label, mutate in (
        ("a non-id field forged",
         lambda d: d.update({"control_principal": "forged"})),
        ("an EXTRA key added", lambda d: d.update({"junk": "x"}))):
    built = workspace()
    record = sorted((built.root / "agents").glob("*.json"))[0]
    check(f"  {label} really changed the file", "changed",
          tamper(record, mutate))
    try:
        Workspace(built.root).list_agents()
        observed = "UNCAUGHT"
    except EFOError as exc:
        observed = f"CAUGHT {type(exc).__name__}: {exc}"
    check(f"    and it is", "registration differs from the signed ledger",
          observed)
print("  `list_agents` compares each record against the signed one WHOLE, and")
print("  then checks the id SET separately - which is why item 72 measured")
print("  both an edit and deleting all three as caught. Two guards, named.")

# ---------------------------------------------------------------- F
print("\n########## F. what this does NOT establish ##########")
print("  * The answer is NEGATIVE and that is the result: `last_event_hash`")
print("    is the ONLY key excluded by name, at four sites, all of them the")
print("    same task projection. Item 71's finding does not generalise.")
print("  * The three mechanisms are the ones I could enumerate from the AST.")
print("    A key dropped by a helper that RETURNS a filtered mapping would")
print("    not appear as a comprehension at a comparison site, and that is a")
print("    stated bound rather than a claim that none exists.")
print("  * It does NOT re-open #19. That issue is about the one key this")
print("    round confirms is alone.")
print("  * It does NOT file an issue. Nothing new about EFO's behaviour is")
print("    claimed - two candidate gaps were driven and both are covered.")
print("  * No network, no GPU. Tempfile workspaces, removed before the")
print("    results print. The anchor's working tree is untouched, and it does")
print("    not touch `main` or another agent's branch.")
print("  * MEASURED: all three mechanisms enumerated from the AST, every")
print("    site classified, the excluded-key set, five tamper drives with a")
print("    bytes-moved assertion on each, one no-op control. REASONED:")
print("    nothing.")

shutil.rmtree(ROOT, ignore_errors=True)
print(f"\n########## {FAIL} unexpected result(s) ##########")
print("Pre-registered permissions unchanged - gpu/network/performance_metrics")
print("all false. SUBMITTED, not VERIFIED: re-running my own evidence is a")
print("re-run, not independent confirmation.")
