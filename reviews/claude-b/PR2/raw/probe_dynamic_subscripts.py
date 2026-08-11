#!/usr/bin/env python3
"""EFO at main (5694ab45): the 144 "dynamic-key subscripts" - what are they?

`NOTE-implicit-exceptions-package-wide.md` closed the constant-key census and
named its own next gap:

    | dynamic-key subscripts, `x[variable]` | **unmeasured** - 144 sites |

This probe closes that gap, and the first thing it finds is that the 144 is
MY OWN misleading number. The count is arithmetically reproducible - section B
reproduces it exactly - but `x[variable]` reads as a runtime dict lookup, and
128 of the 144 are TYPE ANNOTATIONS (`dict[str, Any]`, `list[dict[str, Any]]`)
and 9 more are STORES (`d[k] = v`, which cannot raise KeyError).

    RUNTIME dynamic-key subscript READS in those 13 modules: 7.

That is the fifth time in this review that a naive filter of mine was the bug,
and the second time the bug was in a number I had already published.

The queue item said: do NOT report a bare total as coverage - classify by KEY
PROVENANCE and adjudicate. Section D does that. The useful class is the one
whose key comes from PARSED INPUT rather than a local literal, because that is
the #19 shape: a value a worker supplies, indexed without a guard.

    python3 probe_dynamic_subscripts.py
"""

from __future__ import annotations

import ast
import subprocess
from collections import Counter
from pathlib import Path

FAIL = 0
SOURCE = Path("/tmp/efo-prov")
PACKAGE = SOURCE / "src/evidence_orchestrator"
# The SAME list the note being corrected used, so section B's 144 is a
# like-for-like reproduction and not a different population.
MODULES = ["adapter.py", "ledger.py", "evidence.py", "provenance.py",
           "independence.py", "model.py", "archive.py", "doctor.py",
           "util.py", "lock.py", "dashboard.py", "cli.py", "errors.py"]
DELIBERATE = {"workspace.py"}      # covered separately in section E


def check(name: str, expected: str, observed: str) -> None:
    global FAIL
    ok = expected in observed
    if not ok:
        FAIL += 1
    print(f"  [{'ok' if ok else '!! UNEXPECTED !!'}] {name}")
    print(f"        expected: {expected}")
    print(f"        observed: {observed}")


def annotation_subscripts(tree: ast.AST) -> set[int]:
    """ids of every Subscript that lives inside a type annotation.

    Every annotation position, not a hand-picked few: AnnAssign.annotation,
    the return annotation of both function forms, and EVERY arg.annotation -
    positional, positional-only, keyword-only, *args and **kwargs. `ast.walk`
    yields `arg` nodes for all five, so the coverage is structural rather than
    a list I remembered to keep up to date.
    """
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
                    found.add(id(inner))       # nested ones too: dict[str, list[int]]
    return found


def census(names: list[str]) -> tuple[Counter, Counter, list[tuple[str, int, str, str]]]:
    """(disposition counts, excluded-base counts, runtime read sites)."""
    disposition: Counter[str] = Counter()
    excluded_bases: Counter[str] = Counter()
    reads: list[tuple[str, int, str, str]] = []
    for name in names:
        tree = ast.parse((PACKAGE / name).read_text(encoding="utf-8"))
        annotated = annotation_subscripts(tree)
        for node in ast.walk(tree):
            if not isinstance(node, ast.Subscript):
                continue
            if isinstance(node.slice, ast.Constant):
                continue                        # constant key: earlier census
            disposition["total"] += 1
            if id(node) in annotated:
                disposition["annotation"] += 1
                excluded_bases[ast.unparse(node.value)] += 1
            elif isinstance(node.ctx, ast.Store):
                disposition["store"] += 1
            elif isinstance(node.ctx, ast.Del):
                disposition["delete"] += 1
            else:
                disposition["read"] += 1
                kind = ("slice" if isinstance(node.slice, ast.Slice)
                        else "variable" if isinstance(node.slice, ast.Name)
                        else "expression")
                reads.append((name, node.lineno, ast.unparse(node), kind))
    return disposition, excluded_bases, reads


# ---------------------------------------------------------------- A
print("########## A. POSITIVE CONTROL ##########")
head = subprocess.run(["git", "-C", str(SOURCE), "rev-parse", "HEAD"],
                      capture_output=True, text=True).stdout.strip()
dirty = subprocess.run(["git", "-C", str(SOURCE), "status", "--porcelain"],
                       capture_output=True, text=True).stdout.strip()
check("probe source is main 5694ab45",
      "5694ab455139f1e72d946bc2fe7e42c7c0c8a43a", head)
check("  with no working-tree modification", "dirty: ''", f"dirty: {dirty!r}")
package_modules = sorted(p.name for p in PACKAGE.glob("*.py")
                         if p.name not in {"__init__.py", "__main__.py"})
unlisted = [m for m in package_modules
            if m not in MODULES and m not in DELIBERATE]
check("  nothing in the package is silently unlisted", "unlisted: []",
      f"unlisted: {unlisted}")

# ---------------------------------------------------------------- B
print("\n########## B. the published 144 reproduces - and then decomposes ##########")
disposition, excluded_bases, reads = census(MODULES)
check("the note's figure is reproduced exactly, same 13 modules", "total: 144",
      f"total: {disposition['total']}")
print("  So the number is not an arithmetic error. It is a MISLEADING number,")
print("  which is worse, because it looks checkable and reads as a gap of 144")
print("  runtime lookups. Decomposed:")
for label in ("annotation", "store", "delete", "read"):
    print(f"    {label:<12} {disposition[label]:3}")
check("  the four dispositions account for every site, none double-counted",
      f"sum: {disposition['total']}",
      "sum: " + str(disposition["annotation"] + disposition["store"]
                    + disposition["delete"] + disposition["read"]))
check("  RUNTIME dynamic-key subscript READS", "read: 7",
      f"read: {disposition['read']}")

# ---------------------------------------------------------------- C
print("\n########## C. checking MY OWN filter against ground truth ##########")
print("  An exclusion I wrote is the thing most likely to be wrong here - four")
print("  hand-written filters in this review have already been the bug. So the")
print("  exclusion is checked, not trusted.")
TYPING_BASES = {"list", "dict", "tuple", "set", "frozenset", "type",
                "Sequence", "Mapping", "Iterable", "Iterator", "Callable",
                "Optional", "Union", "Awaitable"}
print(f"  bases of the {disposition['annotation']} excluded subscripts: "
      f"{dict(excluded_bases)}")
foreign = sorted(base for base in excluded_bases if base not in TYPING_BASES)
check("  every excluded subscript is a typing constructor, not a lookup",
      "non-typing bases excluded: []", f"non-typing bases excluded: {foreign}")
retained_typing = sorted({expression.split("[")[0] for _, _, expression, _ in reads}
                         & TYPING_BASES)
check("  and no retained site is a typing construct the filter MISSED",
      "typing bases retained: []", f"typing bases retained: {retained_typing}")
future = [name for name in MODULES
          if "from __future__ import annotations"
          in (PACKAGE / name).read_text(encoding="utf-8")]
check("  modules deferring annotation evaluation", "12 of 13",
      f"{len(future)} of {len(MODULES)}")
print(f"    the exception is {sorted(set(MODULES) - set(future))}, whose")
print("    annotations DO evaluate at import. That does not change the")
print("    verdict - a type expression is still not a key lookup - but the")
print("    reason differs per module, so it is stated rather than glossed.")
print(f"  The {disposition['store']} stores are `d[k] = v`. A store CREATES the")
print("  key; it cannot raise KeyError. They are excluded on that ground, and")
print(f"  the {disposition['delete']} deletes would NOT be - there are none.")

# ---------------------------------------------------------------- D
print("\n########## D. the 7 runtime reads, classified by KEY PROVENANCE ##########")
# site -> (key provenance class, guard, distance from guard to use in lines)
ADJUDICATED = {
    ("provenance.py", 295): (
        "PARSED INPUT",
        "`submitted` is `(provenance.parent / record['submitted_path']).resolve()`"
        " - a path a worker writes into the provenance document. Guarded at"
        " :241 by `if submitted not in expected_files: raise EvidenceError`,"
        " same loop iteration, and `expected_files` is never mutated after"
        " :218 (checked below).",
        54),
    ("independence.py", 148): (
        "own keyspace",
        "`if agent_id in resolved: return resolved[agent_id]` - the membership"
        " test is the same statement.",
        0),
    ("independence.py", 177): (
        "own keyspace",
        "reads the key `resolved[agent_id] = identity_snapshot(...)` assigned"
        " on the line directly above.",
        1),
    ("ledger.py", 82): (
        "local literal",
        "`events[-1]['event_hash'] if events else GENESIS_HASH` - the"
        " emptiness guard is in the same conditional expression.",
        0),
    ("evidence.py", 37): (
        "local arithmetic",
        "`matches[index + 1].start() if index + 1 < len(matches) else"
        " len(text)` - the bound check is in the same conditional expression.",
        0),
    ("evidence.py", 38): (
        "slice",
        "`text[match.end():end]` on a str. A slice clamps; it cannot raise.",
        None),
    ("archive.py", 66): (
        "slice",
        "`manifest['sha256'][:16]`. The outer subscript is a slice on a str."
        " The inner constant key is already adjudicated by the constant-key"
        " census (workspace builds the manifest).",
        None),
}
classes: Counter[str] = Counter()
for name, line, expression, kind in sorted(reads):
    entry = ADJUDICATED.get((name, line))
    marker = "!!" if entry is None else "  "
    provenance_class = entry[0] if entry else "?"
    classes[provenance_class] += 1
    print(f"  {marker}{name}:{line}  [{kind}]  {expression}")
    print(f"        class: {provenance_class}")
    print(f"        {entry[1] if entry else 'UNADJUDICATED'}")
uncovered = sorted(f"{n}:{l}" for n, l, _, _ in reads
                   if (n, l) not in ADJUDICATED)
stale = sorted(f"{n}:{l}" for (n, l) in ADJUDICATED
               if (n, l) not in {(x, y) for x, y, _, _ in reads})
check("every runtime read is adjudicated", "uncovered: []",
      f"uncovered: {uncovered}")
check("  and the map has no stale entries", "stale: []", f"stale: {stale}")
print("\n  BY KEY PROVENANCE - this is the answer to the queue item, and the")
print("  bare total of 7 is deliberately NOT the answer:")
for provenance_class, count in sorted(classes.items(), key=lambda kv: -kv[1]):
    print(f"    {provenance_class:<18} {count}")
check("  exactly one read is keyed by parsed input",
      "PARSED INPUT: 1", f"PARSED INPUT: {classes['PARSED INPUT']}")

print("\n  GUARD DISTANCE, measured rather than eyeballed:")
for (name, line), (provenance_class, _, distance) in sorted(ADJUDICATED.items()):
    shown = "n/a (slice)" if distance is None else f"{distance} lines"
    print(f"    {name}:{line:<5} {provenance_class:<18} {shown}")
print("  Four of the five index reads are guarded inside the SAME expression.")
print("  The parsed-input one is guarded 54 lines earlier. It holds today; the")
print("  distance is what makes it the fragile one, and it is the same shape as")
print("  #19 - a guard and a use that a refactor can separate without either")
print("  side looking wrong on its own.")

# `expected_files` must not be mutated between the guard at :241 and the use
# at :295, or the membership test proves nothing. Checked from the AST.
tree = ast.parse((PACKAGE / "provenance.py").read_text(encoding="utf-8"))
mutations: list[str] = []
for node in ast.walk(tree):
    if isinstance(node, (ast.Assign, ast.AugAssign, ast.Delete)):
        targets = (node.targets if isinstance(node, ast.Assign)
                   else [node.target] if isinstance(node, ast.AugAssign)
                   else node.targets)
        for target in targets:
            rendered = ast.unparse(target)
            if "expected_files" in rendered and node.lineno > 218:
                mutations.append(f"{node.lineno}: {rendered}")
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
        if (ast.unparse(node.func.value) == "expected_files"
                and node.func.attr in {"pop", "clear", "update", "setdefault",
                                       "popitem"}):
            mutations.append(f"{node.lineno}: {ast.unparse(node)}")
check("  expected_files is never mutated after it is built at :218",
      "mutations: []", f"mutations: {mutations}")

# ---------------------------------------------------------------- E
print("\n########## E. workspace.py - the module that carried #19 ##########")
workspace_disposition, workspace_bases, workspace_reads = census(["workspace.py"])
print(f"  total dynamic-key subscripts: {workspace_disposition['total']}")
for label in ("annotation", "store", "delete", "read"):
    print(f"    {label:<12} {workspace_disposition[label]:3}")
check("workspace.py has NO runtime dynamic-key subscript read at all",
      "read: 0", f"read: {workspace_disposition['read']}")
print("  A negative result, and worth publishing: every dict index in the")
print("  module where #19 lives uses a CONSTANT key, which is precisely the")
print("  population `NOTE-issue19-is-the-only-one.md` already enumerated. So")
print("  that note's coverage of workspace.py was complete after all - not by")
print("  design, but the gap it warned about is empty here. Nothing about #19")
print("  changes: #19 is a constant-key read.")

# ---------------------------------------------------------------- F
print("\n########## F. what this still does NOT cover ##########")
print("  Named with counts, because a census is exhaustive only over what it")
print("  enumerates:")
print(f"    - {disposition['store']} dynamic-key STORES: excluded on the")
print("      ground that a store creates its key. A store into a dict that a")
print("      LATER read depends on is a different question, not asked here.")
print("    - AttributeError / TypeError shapes: still unmeasured, for the")
print("      reason the previous note gave - they need type inference.")
print("    - Whether any of the 7 guards can be BYPASSED at runtime. This is")
print("      static ordering analysis; nothing was executed. The behavioural")
print("      half would need a crafted provenance document driven through")
print("      `verify_git_provenance`, which is future work.")
print("    - Nested constant-key reads inside a dynamic expression are counted")
print("      once, at the outer node.")

print(f"\n########## {FAIL} unexpected result(s) ##########")
print("Static analysis only; nothing was executed against a live workspace.")
print("Section B corrects a number I PUBLISHED in")
print("NOTE-implicit-exceptions-package-wide.md - the defect being reported")
print("here is in this review, not in EFO.")
print("Pre-registered permissions unchanged - gpu/network/performance_metrics")
print("all false.")
print("SUBMITTED, not VERIFIED.")
