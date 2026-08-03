#!/usr/bin/env python3
"""EFO at main (5694ab45): the dynamic-key STORES that item 29 excluded.

`NOTE-the-144-was-my-own-misleading-number.md` split 144 dynamic-key subscripts
into 128 annotations, 9 stores and 7 runtime reads, and excluded the stores on
the ground that `d[k] = v` CREATES its key and cannot raise `KeyError`. It then
named the leftover question in its own scope:

    "A store into a dict that a LATER read depends on is a different question,
     not asked here."

This asks it. The queue item said to "say plainly if the answer is none".

**It is not none.** Two chains exist. One is visible to a name-scoped census
(`independence.py::resolved`, 3 stores feeding 2 reads); the other is NOT,
because the dict is renamed across a return - and that second one is the
interesting one: the single PARSED-INPUT read in the package,
`provenance.py:295`, reads a dict whose KEYS are also parsed input. Both sides
of that lookup come from a worker-supplied document.

Section B refuted my own first draft of section C, which asserted two visible
dicts and five fed stores. The census said one and three, and the census was
right. A census keyed on a variable NAME measures a SCOPE, not a VALUE.

    python3 probe_dynamic_stores.py
"""

from __future__ import annotations

import ast
import subprocess
from collections import Counter
from pathlib import Path

FAIL = 0
SOURCE = Path("/tmp/efo-prov")
PACKAGE = SOURCE / "src/evidence_orchestrator"
MODULES = ["adapter.py", "ledger.py", "evidence.py", "provenance.py",
           "independence.py", "model.py", "archive.py", "doctor.py",
           "util.py", "lock.py", "dashboard.py", "cli.py", "errors.py",
           "workspace.py"]


def check(name: str, expected: str, observed: str) -> None:
    global FAIL
    ok = expected in observed
    if not ok:
        FAIL += 1
    print(f"  [{'ok' if ok else '!! UNEXPECTED !!'}] {name}")
    print(f"        expected: {expected}")
    print(f"        observed: {observed}")


def annotation_subscripts(tree: ast.AST) -> set[int]:
    """Same structural collector item 29 used - every annotation position."""
    found: set[int] = set()
    for node in ast.walk(tree):
        annotations: list[ast.expr] = []
        if isinstance(node, ast.AnnAssign):
            annotations.append(node.annotation)
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if node.returns is not None:
                annotations.append(node.returns)
        elif isinstance(node, ast.arg) and node.annotation is not None:
            annotations.append(node.annotation)
        for annotation in annotations:
            for inner in ast.walk(annotation):
                if isinstance(inner, ast.Subscript):
                    found.add(id(inner))
    return found


def parents(tree: ast.AST) -> dict[int, ast.AST]:
    table: dict[int, ast.AST] = {}
    for node in ast.walk(tree):
        for child in ast.iter_child_nodes(node):
            table[id(child)] = node
    return table


# ---------------------------------------------------------------- A
print("########## A. POSITIVE CONTROL and the store census ##########")
head = subprocess.run(["git", "-C", str(SOURCE), "rev-parse", "HEAD"],
                      capture_output=True, text=True).stdout.strip()
dirty = subprocess.run(["git", "-C", str(SOURCE), "status", "--porcelain"],
                       capture_output=True, text=True).stdout.strip()
check("probe source is main 5694ab45",
      "5694ab455139f1e72d946bc2fe7e42c7c0c8a43a", head)
check("  with no working-tree modification", "dirty: ''", f"dirty: {dirty!r}")
package_modules = sorted(p.name for p in PACKAGE.glob("*.py")
                         if p.name not in {"__init__.py", "__main__.py"})
check("  and the module list is the whole package", "unlisted: []",
      f"unlisted: {[m for m in package_modules if m not in MODULES]}")

stores: list[tuple[str, int, str, str]] = []
for name in MODULES:
    tree = ast.parse((PACKAGE / name).read_text(encoding="utf-8"))
    annotated = annotation_subscripts(tree)
    for node in ast.walk(tree):
        if (isinstance(node, ast.Subscript)
                and not isinstance(node.slice, ast.Constant)
                and id(node) not in annotated
                and isinstance(node.ctx, ast.Store)):
            base = ast.unparse(node.value)
            stores.append((name, node.lineno, base, ast.unparse(node)))
stores.sort()
for name, line, base, expression in stores:
    print(f"    {name}:{line}  {expression}")
check("dynamic-key stores in the whole package", "stores: 10",
      f"stores: {len(stores)}")
outside = [s for s in stores if s[0] != "workspace.py"]
check("  of which item 29 counted, excluding workspace.py", "excluded: 9",
      f"excluded: {len(outside)}")
print("  9 + 1 = the 10 below. Item 29 reported 9 because it excluded")
print("  workspace.py from that population and counted it separately.")

# ---------------------------------------------------------------- B
print("\n########## B. every access to each stored-into dict, adjudicated ##########")
# (module, variable) -> how the module reads it back
ADJUDICATED = {
    ("adapter.py", "snapshot"):
        "built by _workspace_snapshot and RETURNED. Never subscripted in this "
        "module.",
    ("ledger.py", "tasks"):
        "built by projected_tasks and RETURNED. Its three consumers are all "
        "in workspace.py, which item 29 measured as having ZERO runtime "
        "dynamic-key reads - so none of them can subscript it with a "
        "variable.",
    ("provenance.py", "files"):
        "built by _evidence_file_map and RETURNED. Under THIS name it is "
        "never read back - the caller rebinds it as `expected_files`, which "
        "is where :241 and :295 read it. A name-scoped census cannot see "
        "that; section C does it by reading.",
    ("independence.py", "declarations"):
        "read only via .get() at :142 and :153, and iterated at :179.",
    ("independence.py", "resolved"):
        "read by subscript at :148 and :177, both adjudicated by item 29 as "
        "own-keyspace. See section C.",
    ("independence.py", "submissions"):
        "read only via .get() at :240.",
    ("workspace.py", "signed"):
        "read via .get() at :288 and set() at :293. Never subscripted.",
}
SUBSCRIPT_READ = "subscript-read"
accesses: dict[tuple[str, str], Counter] = {}
read_sites: dict[tuple[str, str], list[int]] = {}
for name in {store[0] for store in stores}:
    tree = ast.parse((PACKAGE / name).read_text(encoding="utf-8"))
    table = parents(tree)
    for base in {store[2] for store in stores if store[0] == name}:
        tally: Counter[str] = Counter()
        sites: list[int] = []
        for node in ast.walk(tree):
            if not (isinstance(node, ast.Name) and node.id == base):
                continue
            parent = table.get(id(node))
            if isinstance(parent, ast.Subscript) and parent.value is node:
                if isinstance(parent.ctx, ast.Store):
                    tally["subscript-store"] += 1
                elif isinstance(parent.ctx, ast.Del):
                    tally["subscript-del"] += 1
                elif isinstance(parent.slice, ast.Constant):
                    tally["subscript-read (constant key)"] += 1
                else:
                    tally[SUBSCRIPT_READ] += 1
                    sites.append(parent.lineno)
            elif isinstance(parent, ast.Attribute):
                tally[f".{parent.attr}()"] += 1
            elif isinstance(parent, ast.Compare):
                tally["membership / comparison"] += 1
            elif isinstance(parent, ast.For) and parent.iter is node:
                tally["iterated"] += 1
            elif isinstance(node.ctx, ast.Store):
                tally["rebound"] += 1
            else:
                tally["passed / returned / set()"] += 1
        accesses[(name, base)] = tally
        read_sites[(name, base)] = sorted(set(sites))

for key in sorted(accesses):
    name, base = key
    verdict = ADJUDICATED.get(key, "?")
    marker = "!!" if verdict == "?" else "  "
    print(f"  {marker}{name}  `{base}`")
    print(f"        {dict(accesses[key])}")
    print(f"        {verdict}")
uncovered = sorted(f"{n}::{b}" for n, b in accesses if (n, b) not in ADJUDICATED)
stale = sorted(f"{n}::{b}" for n, b in ADJUDICATED if (n, b) not in accesses)
check("every stored-into dict is adjudicated", "uncovered: []",
      f"uncovered: {uncovered}")
check("  and the map has no stale entries", "stale: []", f"stale: {stale}")

feeding = sorted(key for key in accesses
                 if accesses[key][SUBSCRIPT_READ] > 0)
check("  dicts read back by dynamic subscript UNDER THE SAME NAME",
      "feeding: ['independence.py::resolved']",
      f"feeding: {[f'{n}::{b}' for n, b in feeding]}")
fed_stores = [s for s in stores if (s[0], s[2]) in set(feeding)]
check("  stores belonging to it", "fed: 3", f"fed: {len(fed_stores)}")
print("  A CORRECTION TO MY OWN FIRST DRAFT. I wrote this section expecting")
print("  two such dicts and five such stores, counting provenance.py's")
print("  `files` because I knew it becomes `expected_files` and is read at")
print("  :295. The census says one and three, and the census is right: under")
print("  the name `files` that dict is stored into and RETURNED, nothing")
print("  more. The caller rebinds the return value, and a census keyed on a")
print("  variable NAME cannot follow a rename across a return.")
print("  That bounds this probe and, more usefully, bounds every name-scoped")
print("  census in this review: they measure a SCOPE, not a VALUE. Where a")
print("  value crosses a function boundary the chain has to be read, which")
print("  is what section C does - and the result is then REASONED FROM")
print("  READING, not measured by the census.")
print("  So the plain answer the queue asked for is NOT 'none'. Two chains")
print("  exist; one is visible to the census and one is not.")

# ---------------------------------------------------------------- C
print("\n########## C. the two chains, and why one of them matters ##########")
print("  CHAIN 1 - independence.py `resolved`")
print(f"    stores  :155 :162 :176   ->   reads  "
      f"{read_sites[('independence.py', 'resolved')]}")
print("    Item 29 classified both reads as OWN KEYSPACE. This traces WHY:")
print("    every key written is `agent_id`, the same parameter the reads use,")
print("    and :148 is guarded by `if agent_id in resolved` while :177 reads")
print("    the key assigned one line above. Nothing new; the chain confirms")
print("    the earlier classification rather than changing it.")

print("\n  CHAIN 2 - provenance.py `files`, which the caller renames to")
print("  `expected_files`. NOT visible to section B, established by reading.")
print(f"    stores  :119 :123   ->   read  "
      f"{read_sites[('provenance.py', 'files')]}")
provenance = (PACKAGE / "provenance.py").read_text(encoding="utf-8").splitlines()
for line_number in (119, 123, 241, 295):
    print(f"    provenance.py:{line_number}  {provenance[line_number - 1].strip()}")
check("  the store keys are built from the evidence manifest",
      'files[Path(artifact["path"]).resolve()]', provenance[118].strip())
check("  and the rename that hides the chain is a plain return + rebind",
      "expected_files = _evidence_file_map(evidence)", provenance[217].strip())
check("  and the read key is built from the provenance document",
      "expected_files[submitted]", provenance[294].strip())
print("  THIS is the result worth publishing. Item 29 already established")
print("  that `submitted` - the KEY - comes from parsed input. What the store")
print("  side adds is that the KEYSPACE comes from parsed input too:")
print("  `_evidence_file_map` keys the dict by the artifact and raw_output")
print("  paths declared in the EVIDENCE MANIFEST, and :295 indexes it with a")
print("  path declared in the PROVENANCE DOCUMENT. Two worker-supplied")
print("  documents on either side of one dict lookup.")
print("  It is still safe: :241 rejects any `submitted` not in the map, in the")
print("  same loop iteration, and item 29 proved the map is never mutated")
print("  after :218. But 'both sides are attacker-controlled and the only")
print("  thing between them is a membership test 54 lines up' is a sharper")
print("  statement of the same structure than item 29 could make alone.")

# ---------------------------------------------------------------- D
print("\n########## D. a near miss: where .get() is load-bearing ##########")
adapter = (PACKAGE / "adapter.py").read_text(encoding="utf-8").splitlines()
for line_number in (86, 87, 88, 89):
    print(f"    adapter.py:{line_number}  {adapter[line_number - 1].strip()}")
check("  the iteration is over the UNION of both keyspaces",
      "set(before) | set(after)", adapter[87].strip())
check("  and both dicts are read with .get, not a subscript",
      "before.get(path) != after.get(path)", adapter[88].strip())
print("  `changed` iterates keys present in EITHER dict, so a subscript here")
print("  WOULD raise KeyError on any file added or deleted during the run -")
print("  which is the normal case this function exists to detect. The `.get`")
print("  is doing real work. Worth naming because it is the shape that would")
print("  have been a finding had it been written the other way, and because a")
print("  census of stores that reported only 'no reads' would have walked")
print("  straight past it.")

# ---------------------------------------------------------------- E
print("\n########## E. what this does NOT cover ##########")
print("  * Cross-module flow is traced by READING the consumers, not by")
print("    static dataflow. `ledger.projected_tasks()` is resolved through")
print("    item 29's measurement that workspace.py has zero runtime")
print("    dynamic-key reads; that is a cross-reference, not a new proof.")
print("  * Nothing was executed. Whether a crafted evidence manifest plus a")
print("    crafted provenance document can reach :295 with a key the map")
print("    lacks is a BEHAVIOURAL question this probe does not answer - it")
print("    would need `verify_git_provenance` driven end to end against a")
print("    real repository, and `network: false` forbids the fetch that")
print("    would make that realistic.")
print("  * Constant-key stores are out of scope, as are stores through an")
print("    attribute (`self.x[k] = v`) - the census keys on a bare Name, and")
print("    there are none of the latter among these ten.")
print("  * MEASURED: the census, every access tally, both chains, the near")
print("    miss. REASONED: that .get()/membership/iteration cannot raise")
print("    KeyError, which is language semantics rather than a measurement.")

print(f"\n########## {FAIL} unexpected result(s) ##########")
print("Static analysis only; nothing was executed against a live workspace.")
print("No issue filed - every chain here is guarded. Pre-registered")
print("permissions unchanged - gpu/network/performance_metrics all false.")
print("SUBMITTED, not VERIFIED.")
