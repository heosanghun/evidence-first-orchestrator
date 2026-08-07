#!/usr/bin/env python3
"""What the collector's 27 tests measure, and what the stubs put out of reach.

Queue item 39. `NOTE-what-the-test-suite-cannot-catch.md` measured 21 mock
targets, 18 of them `monitor.collector.*`. Those 18 are what make the collector
testable at all - it shells out to `nvidia-smi` and reads `/proc`. The question
this asks is narrower and sharper: **which properties are asserted only against
stubbed input, and is any of them a property that could only fail against a
real machine or a real clock?**

#6 lives in this component: a month-old `ready` still counts as active. #6 is
one of the ten issues `NOTE-what-the-test-suite-cannot-catch.md` found with no
defect token in any test source. This pass says WHY, which is more useful than
"absent".

    python3 probe_collector_stubs.py
"""

from __future__ import annotations

import ast
import re
import subprocess
from collections import Counter
from pathlib import Path

FAIL = 0
SOURCE = Path("/tmp/efo-prov")
COLLECTOR = SOURCE / "monitor/collector.py"
TESTS = SOURCE / "tests/test_monitor_collector.py"


def check(name: str, expected: str, observed: str) -> None:
    global FAIL
    ok = expected in observed
    if not ok:
        FAIL += 1
    print(f"  [{'ok' if ok else '!! UNEXPECTED !!'}] {name}")
    print(f"        expected: {expected}")
    print(f"        observed: {observed}")


collector_source = COLLECTOR.read_text(encoding="utf-8")
test_source = TESTS.read_text(encoding="utf-8")


def tokens(text: str) -> set[str]:
    """Identifier tokens, so a search cannot match a SUBSTRING.

    A first pass counted `age_` and found 2 - both inside `disk_usage_mock`.
    The method already says never match an identifier by substring, and the
    scan did it anyway. Twelfth filter bug of this review, caught here.
    """
    return set(re.findall(r"[A-Za-z_][A-Za-z0-9_]*", text))


# ---------------------------------------------------------------- A
print("########## A. POSITIVE CONTROL ##########")
head = subprocess.run(["git", "-C", str(SOURCE), "rev-parse", "HEAD"],
                      capture_output=True, text=True).stdout.strip()
dirty = subprocess.run(["git", "-C", str(SOURCE), "status", "--porcelain"],
                       capture_output=True, text=True).stdout.strip()
check("probe source is main 5694ab45",
      "5694ab455139f1e72d946bc2fe7e42c7c0c8a43a", head)
check("  with no working-tree modification", "dirty: ''", f"dirty: {dirty!r}")
functions = [node.name for node in ast.walk(ast.parse(test_source))
             if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
             and node.name.startswith("test")]
check("  and the collector suite is the size the earlier note measured",
      "tests: 27", f"tests: {len(functions)}")

# ---------------------------------------------------------------- B
print("\n########## B. what is stubbed, by target ##########")
patched: Counter[str] = Counter()
for node in ast.walk(ast.parse(test_source)):
    if (isinstance(node, ast.Call)
            and getattr(node.func, "id", getattr(node.func, "attr", "")) == "patch"
            and node.args and isinstance(node.args[0], ast.Constant)):
        patched[node.args[0].value] += 1
for target, count in sorted(patched.items()):
    print(f"    {count}x  {target}")
check("distinct stub targets", "distinct: 12", f"distinct: {len(patched)}")
check("  over this many call sites", "sites: 18",
      f"sites: {sum(patched.values())}")
print("  Stubbing `run_command`, `query_gpus`, `read_meminfo`, `read_uptime`")
print("  and `shutil.disk_usage` is what makes the collector testable without")
print("  a GPU host. That is not a criticism; it is the boundary.")

# ---------------------------------------------------------------- C
print("\n########## C. the clock - stubbed ONCE, to a constant ##########")
clock = [node.lineno for node in ast.walk(ast.parse(test_source))
         if isinstance(node, ast.Call)
         and getattr(node.func, "id", getattr(node.func, "attr", "")) == "patch"
         and node.args and isinstance(node.args[0], ast.Constant)
         and node.args[0].value == "monitor.collector.time.time"]
check("time.time is stubbed exactly once in 27 tests", "clock stubs: 1",
      f"clock stubs: {len(clock)}")
window = test_source.splitlines()[clock[0] - 1:clock[0] + 3]
for line in window:
    print(f"    {line.strip()}")
check("  and it pins the clock to a CONSTANT", "return_value=1000",
      " ".join(window))
check("  in a test about the HMAC, not about freshness",
      "test_submit_hmac_covers_timestamp_and_exact_body", " ".join(window))
print("  So the one place the collector's notion of `now` is controlled is a")
print("  signature test. No test moves the clock to age anything.")

# ---------------------------------------------------------------- D
print("\n########## D. the staleness vocabulary is ABSENT from the suite ##########")
test_tokens = tokens(test_source)
VOCABULARY = ["stale", "staleness", "freshness", "PORTFOLIO_EXTERNAL_ACTIVE_PHASES",
              "age", "elapsed", "expired", "seconds_since"]
present = [word for word in VOCABULARY if word in test_tokens]
for word in VOCABULARY:
    print(f"    {word:<34} {'PRESENT' if word in test_tokens else 'absent'}")
check("none of the staleness vocabulary appears as a TOKEN", "present: []",
      f"present: {present}")
print("  Matched as identifier TOKENS, not substrings: a first pass reported")
print("  `age` twice, and both were inside `disk_usage_mock`. That is the")
print("  twelfth hand-rolled filter in this review to be the bug, and it is")
print("  the exact trap the method names - it caught `worker` inside")
print("  `worker_identity` two rounds ago and I repeated it here.")

# ---------------------------------------------------------------- E
print("\n########## E. #6's branch has no clock in it at all ##########")
lines = collector_source.splitlines()
branch = lines[896:901]
for offset, line in enumerate(branch, start=897):
    print(f"    collector.py:{offset}  {line.strip()}")
check("  the branch that makes an external phase count as active",
      "external_phase in PORTFOLIO_EXTERNAL_ACTIVE_PHASES", " ".join(branch))
check("  and PORTFOLIO_EXTERNAL_ACTIVE_PHASES is never named in the tests",
      "in tests: False",
      f"in tests: {'PORTFOLIO_EXTERNAL_ACTIVE_PHASES' in test_tokens}")
print("  The branch is a pure set-membership test on `external_phase`. There")
print("  is no timestamp in it, which IS #6: a `ready` reported a month ago")
print("  counts exactly as a `ready` reported a second ago. A lease expires;")
print("  a transport progress report does not.")
print("  So #6 has no test not because the suite forgot a case, but because")
print("  the CONCEPT of a transport report ageing does not exist anywhere in")
print("  the collector or its tests. That is why the token map found nothing.")

# ---------------------------------------------------------------- F
print("\n########## F. what this does NOT establish ##########")
print("  * It does not re-measure #6. That was driven in the issue and is not")
print("    re-confirmed here; a re-confirmation is a comment, not a note.")
print("  * It does not claim the 18 stubs are wrong. They are the only way to")
print("    test a collector that shells out to nvidia-smi. What is measured is")
print("    the CONSEQUENCE: 27 tests exercise the collector's logic against")
print("    inputs the test chooses, and no test supplies an input that is old.")
print("  * `external_phase` DOES appear in the tests (8 tokens), so the field")
print("    is exercised - the tests set it and assert the resulting counts.")
print("    What is absent is any test where the same field is exercised with")
print("    TIME having passed.")
print("  * MEASURED: the stub census, the single clock stub and its constant,")
print("    the vocabulary absence, the branch text. REASONED: that no test")
print("    ages an input - which follows from the clock being stubbed once, to")
print("    a constant, in an unrelated test.")

print(f"\n########## {FAIL} unexpected result(s) ##########")
print("Static analysis only; nothing was executed. No issue filed - #6 is")
print("already open and this is about coverage shape, not a new defect.")
print("Pre-registered permissions unchanged - gpu/network/performance_metrics")
print("all false. SUBMITTED, not VERIFIED.")
