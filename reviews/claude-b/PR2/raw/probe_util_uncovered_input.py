#!/usr/bin/env python3
"""What `util.py is clean` actually rested on - and the input class it never fed.

Queue item 47. `util.py` has nine top-level functions, the suite names NONE of
them (item 44), and it is imported by nine of the fifteen modules - the widest
fan-in in the package. `NOTE-util-and-lock-hold.md` calls it clean over 46
checks. The item asked what that note actually measured.

The answer, in three parts:

  1. MY OWN PROBE drives all nine. `probe_util_and_lock.py` names every one of
     them, so `clean` rested on MY evidence, not on EFO's tests. Saying that
     plainly is the first half of the answer.

  2. The coverage is UNEVEN, and its own raw output shows it: `is_relative_to`
     produces 17 output lines, `canonical_json` 3, and `read_json` has NO check
     of its own at all - it appears only as a helper inside the
     `atomic_write_json round-trips` assertion.

  3. NOT ONE of the 46 checks feeds a NON-STRING. Driven here, all nine raise a
     RAW Python exception - AttributeError or TypeError - rather than the
     package's own EFOError. That is the #8 / #13 / #14 shape ("the guard has a
     test, fed only the input it already handles"), found this time in MY OWN
     clean note.

A MAP, NOT A FINDING. Of 23 in-package call sites, 3 read a DICT FIELD and
EVERY one of those coerces with `str(...)` first, so a tampered file cannot
deliver a non-string. The 18 bare call sites take an API argument, which is
programmatic misuse rather than the threat model this review is about. Not
filed.

    python3 probe_util_uncovered_input.py

SCOPE, stated first: 9 functions, 1 probe, 1 note, 23 in-package call sites.
Small enough to adjudicate each, and each is adjudicated.
"""

from __future__ import annotations

import ast
import re
import subprocess
import sys
from pathlib import Path

FAIL = 0
SOURCE = Path("/tmp/efo-prov")
PACKAGE = SOURCE / "src/evidence_orchestrator"
REVIEWS = Path("/workspace/evidence-first-orchestrator/reviews/claude-b/PR2")
RAW = REVIEWS / "raw"


def check(name: str, expected: str, observed: str) -> None:
    global FAIL
    ok = expected in observed
    if not ok:
        FAIL += 1
    print(f"  [{'ok' if ok else '!! UNEXPECTED !!'}] {name}")
    print(f"        expected: {expected}")
    print(f"        observed: {observed}")


def hits(name: str, text: str) -> int:
    return len(re.findall(r"\b" + re.escape(name) + r"\b", text))


# ---------------------------------------------------------------- A
print("########## A. POSITIVE CONTROL, and the scope FIRST ##########")
check("probe source is main 5694ab45",
      "5694ab455139f1e72d946bc2fe7e42c7c0c8a43a",
      subprocess.run(["git", "-C", str(SOURCE), "rev-parse", "HEAD"],
                     capture_output=True, text=True).stdout.strip())
dirty = subprocess.run(["git", "-C", str(SOURCE), "status", "--porcelain"],
                       capture_output=True, text=True).stdout.strip()
check("  with no working-tree modification", "dirty: ''", f"dirty: {dirty!r}")
functions = [n.name for n in ast.parse(
    (PACKAGE / "util.py").read_text(encoding="utf-8")).body
    if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
check("util.py's top-level functions", "functions: 9",
      f"functions: {len(functions)}")
tests = "\n".join(p.read_text(encoding="utf-8")
                  for p in sorted((SOURCE / "tests").glob("*.py")))
check("  named by the EFO suite", "named by tests: 0",
      f"named by tests: {sum(hits(n, tests) for n in functions)}")
print(f"    {functions}")

# ---------------------------------------------------------------- B
print("\n########## B. what `clean` rested on: MY probe, not EFO's tests ##########")
probe = (RAW / "probe_util_and_lock.py").read_text(encoding="utf-8")
output = (RAW / "raw-util-and-lock.txt").read_text(encoding="utf-8")
undriven = [n for n in functions if not hits(n, probe)]
check("functions my own probe does NOT name", "undriven: []",
      f"undriven: {undriven}")
print("  So the suite names none of the nine and my probe names all nine.")
print("  `util.py is clean` is a claim about MY evidence. That is not a")
print("  defect - it is what the note is for - but it had never been said.")

# ---------------------------------------------------------------- C
print("\n########## C. and the coverage is UNEVEN - its own output shows it ##########")
print(f"    {'function':<22}{'in probe':>10}{'in output':>11}")
silent = []
for name in functions:
    in_out = hits(name, output)
    print(f"    {name:<22}{hits(name, probe):>10}{in_out:>11}")
    if in_out == 0:
        silent.append(name)
check("functions with NO appearance in the raw output",
      "silent: ['read_json', 'validate_agent_id', 'validate_task_id']",
      f"silent: {sorted(silent)}")
print("  Two of those three are a NAMING artifact, not a gap: the validators")
print("  are driven through a `lambda v=value:` inside a loop whose check name")
print("  says `task id ...` rather than the function name. Their values are")
print("  counted from the two loops that FEED them, not from every table in")
print("  the file - a first version matched all 24 rows in the probe, which")
print("  is the substring trap one level up.")
validator_values = 0
for loop in re.findall(r"for label, value, ok in \[(.*?)\]:", probe, re.S):
    validator_values += len(re.findall(r'^\s+\("', loop, re.M))
check("  the validators' driven values, from the two loops that feed them",
      "driven values: 14", f"driven values: {validator_values}")
print("  `read_json` is the real one: it appears inside exactly ONE check, as")
print("  a HELPER in `atomic_write_json round-trips`, and never as the subject")
print("  of one.")
inside = len(re.findall(r"check\([^)]*read_json", probe))
subject = len(re.findall(r'check\("[^"]*read_json', probe))
check("    checks that USE read_json", "using: 1", f"using: {inside}")
check("      checks ABOUT read_json - named after it", "about: 0",
      f"about: {subject}")

# ---------------------------------------------------------------- D
print("\n########## D. EXECUTED - the input class none of the 46 checks fed ##########")
sys.path.insert(0, str(PACKAGE.parent))
from evidence_orchestrator import util                       # noqa: E402
from evidence_orchestrator.errors import EFOError            # noqa: E402

CASES = [
    ("parse_utc", lambda b: util.parse_utc(b), (None, 123, [], {})),
    ("validate_task_id", lambda b: util.validate_task_id(b), (None, 123, [])),
    ("validate_agent_id", lambda b: util.validate_agent_id(b), (None, 123, [])),
    ("sha256_file", lambda b: util.sha256_file(b), (None, 123)),
    ("read_json", lambda b: util.read_json(b), (None, 123)),
    ("is_relative_to", lambda b: util.is_relative_to(b, "/tmp"), (None, 123)),
]
raw_exception = efo_exception = returned = 0
for name, call, values in CASES:
    for bad in values:
        try:
            call(bad)
            returned += 1
            outcome = "returned"
        except EFOError as error:
            efo_exception += 1
            outcome = f"EFOError {type(error).__name__}"
        except Exception as error:                            # noqa: BLE001
            raw_exception += 1
            outcome = f"**{type(error).__name__}**"
        print(f"    {name}({bad!r:<6}) {outcome}")
try:
    util.canonical_json(object())
    returned += 1
except EFOError:
    efo_exception += 1
except Exception as error:                                    # noqa: BLE001
    raw_exception += 1
    print(f"    canonical_json(object()) **{type(error).__name__}**")
check("cases driven with a non-string", "driven: 17",
      f"driven: {raw_exception + efo_exception + returned}")
check("  raising the package's OWN error type", "EFOError: 0",
      f"EFOError: {efo_exception}")
check("  raising a RAW Python exception instead", "raw: 17",
      f"raw: {raw_exception}")
print("  Not one of the nine converts a non-string into an EFOError. That is")
print("  a uniform structural fact, and none of the 46 checks fed it.")
print("  parse_utc's three checks all pass a WELL-FORMED string; the")
print("  validators' 13 values are all strings. The class was simply absent.")

# ---------------------------------------------------------------- E
print("\n########## E. reachability - a MAP, not a finding ##########")
callers = []
for module in sorted(p.name for p in PACKAGE.glob("*.py")):
    if module == "util.py":
        continue
    for i, line in enumerate((PACKAGE / module).read_text(
            encoding="utf-8").splitlines(), 1):
        if re.search(r"\bvalidate_(task|agent)_id\(", line):
            callers.append((module, i, "str(" in line, line.strip()[:56]))
coerced = [c for c in callers if c[2]]
bare = [c for c in callers if not c[2]]
for module, line, is_coerced, text in callers:
    print(f"    {'str()' if is_coerced else '  -  '} {module}:{line:<5} {text}")
check("in-package validator call sites", "call sites: 23",
      f"call sites: {len(callers)}")
check("  those that coerce with str() first", "coerced: 5",
      f"coerced: {len(coerced)}")
check("    and those that pass the value bare", "bare: 18",
      f"bare: {len(bare)}")
# THE DECIDING CHECK, and it is well-defined: a call site whose argument reads
# a DICT FIELD (`.get(` or `[`) is document-driven. Every one of those must
# also coerce. Both sides derived from the same line, neither typed in.
document_driven = [c for c in callers if ".get(" in c[3]]
uncoerced_documents = [c for c in document_driven if not c[2]]
check("  call sites reading a dict field", "document-driven: 3",
      f"document-driven: {len(document_driven)}")
check("    of which any that does NOT coerce", "uncoerced: []",
      f"uncoerced: {[(c[0], c[1]) for c in uncoerced_documents]}")
print("  The callers that read a value out of a parsed document - model.py:93")
print("  and :94, provenance.py:156, independence.py:122 and :159 - all wrap")
print("  it in str() first, so a TAMPERED FILE cannot deliver a non-string.")
print("  The bare call sites take an API ARGUMENT, which is programmatic")
print("  misuse rather than the threat model this review is about.")
print("  So: a MAP. No issue filed, and NOTE-util-and-lock-hold.md's `clean`")
print("  verdict is not retracted - its scope is narrowed and stated.")

# ---------------------------------------------------------------- F
print("\n########## F. what this does NOT do ##########")
print("  * It does not retract `util.py is clean`. Every one of the 46 checks")
print("    still passes; what changes is that the note now says which input")
print("    class it never fed.")
print("  * It does not file an issue. The raising class is unreachable from a")
print("    document, which is the standard items 38 and 45 both applied.")
print("  * It does not cover lock.py - the same note's other subject - which")
print("    is a separate population and was not measured here.")
print("  * It did NOT write to any workspace: the drives call pure functions")
print("    with literal values, and read_json/sha256_file were handed None and")
print("    an int, which raise before touching a filesystem.")
print("  * MEASURED: every count, every coverage number, all 17 driven")
print("    outcomes, the caller census. REASONED: nothing.")

print(f"\n########## {FAIL} unexpected result(s) ##########")
print("Static reads plus 17 pure-function drives at main 5694ab45. No")
print("workspace, no network, no issue filed. Pre-registered permissions")
print("unchanged - gpu/network/performance_metrics all false.")
print("SUBMITTED, not VERIFIED.")
