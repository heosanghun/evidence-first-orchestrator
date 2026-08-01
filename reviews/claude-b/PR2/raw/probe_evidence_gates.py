#!/usr/bin/env python3
"""EFO evidence manifest gates at main (5694ab45).

`evidence.py` is the core of the premise: it decides what counts as evidence.
This probes the gates that matter - exit codes, failures, skips, the [FILL]
rule, permission-blocked performance claims, evidence binding - and then asks
whether a known-answer check can be satisfied by a tautology.

Section A is the positive control: an honest manifest must validate before any
refusal below means anything.  Every rejection is asserted on its MESSAGE.

    python3 probe_evidence_gates.py
"""

from __future__ import annotations

import hashlib
import json
import shutil
import sys
import tempfile
from pathlib import Path
from typing import Any

sys.path.insert(0, "/tmp/efo-prov/src")
from evidence_orchestrator.evidence import (  # noqa: E402
    validate_manifest,
    validate_report,
)

FAIL = 0
ROOT = Path(tempfile.mkdtemp(prefix="efo-evid-"))
GATES = {"allow_skips": False, "require_validation": True,
         "require_known_answer_check": True,
         "require_independent_verification": True}
PERMS = {"gpu": False, "network": False, "performance_metrics": False}


def check(name: str, expected: str, observed: str) -> None:
    global FAIL
    ok = expected in observed
    if not ok:
        FAIL += 1
    print(f"  [{'ok' if ok else '!! UNEXPECTED !!'}] {name}")
    print(f"        expected: {expected}")
    print(f"        observed: {observed}")


def artifact(stem: str) -> tuple[str, str]:
    path = ROOT / f"{stem}.txt"
    path.write_text(f"{stem} artifact\n", encoding="utf-8")
    return path.name, hashlib.sha256(path.read_bytes()).hexdigest()


NAME, SHA = artifact("a")


def manifest(**over: Any) -> dict[str, Any]:
    base = {
        "schema_version": 1,
        "artifacts": [{"path": NAME, "sha256": SHA}],
        "validations": [{"command": "pytest -q", "exit_code": 0, "passed": 12,
                         "failed": 0, "skipped": 0, "skip_reasons": []}],
        "known_answer_checks": [{"name": "two plus two", "expected": 4,
                                 "observed": 4, "passed": True}],
        "claims": [{"name": "functional behavior", "kind": "functional",
                    "measured": True, "value": "pass", "evidence": [NAME]}],
    }
    base.update(over)
    return base


def run(name: str, expected: str, **over: Any) -> None:
    path = ROOT / "m.json"
    path.write_text(json.dumps(manifest(**over), indent=2), encoding="utf-8")
    try:
        result = validate_manifest(path, gates=GATES, permissions=PERMS)
        summary = (f"accepted: passed={result['passed']} failed={result['failed']} "
                   f"skipped={result['skipped']} "
                   f"known_answer_checks={result['known_answer_checks']} "
                   f"unmeasured_claims={result['unmeasured_claims']}")
        check(name, expected, summary)
    except Exception as exc:
        check(name, expected, f"rejected ({type(exc).__name__}: {exc})")


print("########## A. POSITIVE CONTROL ##########")
run("an honest manifest validates", "accepted")

print("\n########## B. the gates that carry the premise ##########")
run("nonzero exit code", "did not pass: exit_code=1",
    validations=[{"command": "pytest", "exit_code": 1, "passed": 3, "failed": 0,
                  "skipped": 0, "skip_reasons": []}])
run("a failure with exit code 0", "did not pass: exit_code=0, failed=2",
    validations=[{"command": "pytest", "exit_code": 0, "passed": 3, "failed": 2,
                  "skipped": 0, "skip_reasons": []}])
run("a skip while allow_skips is false", "skip is not pass",
    validations=[{"command": "pytest", "exit_code": 0, "passed": 3, "failed": 0,
                  "skipped": 1, "skip_reasons": ["needs a GPU"]}])
run("skips without a reason for each", "lacks a reason for each",
    validations=[{"command": "pytest", "exit_code": 0, "passed": 3, "failed": 0,
                  "skipped": 2, "skip_reasons": ["one only"]}])
run("an unmeasured claim carrying a number", "must use the exact value [FILL]",
    claims=[{"name": "speedup", "kind": "performance", "measured": False,
             "value": 26.7}])
run("an unmeasured claim using [FILL]", "accepted",
    claims=[{"name": "speedup", "kind": "performance", "measured": False,
             "value": "[FILL]"}])
run("a measured performance claim while the permission is false",
    "Measured performance claims are forbidden",
    claims=[{"name": "speedup", "kind": "performance", "measured": True,
             "value": 26.7, "evidence": [NAME]}])
run("a claim citing evidence that was never bound",
    "references evidence not bound",
    claims=[{"name": "functional behavior", "kind": "functional",
             "measured": True, "value": "pass", "evidence": ["ghost.txt"]}])
run("an artifact whose sha does not match the file", "expected",
    artifacts=[{"path": NAME, "sha256": "0" * 64}])
run("a known-answer check whose values differ",
    "expected and observed values differ",
    known_answer_checks=[{"name": "k", "expected": 4, "observed": 5,
                          "passed": True}])
run("a known-answer check not marked passed", "is not explicitly passed",
    known_answer_checks=[{"name": "k", "expected": 4, "observed": 4,
                          "passed": False}])
run("no known-answer check at all",
    "At least one known-answer comparison is required",
    known_answer_checks=[])

print("\n########## C. can a known-answer check be vacuous? ##########")
print("  The gate compares expected against observed and requires passed=True.")
print("  Nothing requires the pair to be non-trivial.")
for label, value in [("null", None), ("empty string", ""), ("zero", 0),
                     ("the [FILL] marker itself", "[FILL]")]:
    run(f"expected == observed == {label}", "rejected",
        known_answer_checks=[{"name": "vacuous", "expected": value,
                              "observed": value, "passed": True}])

print("\n########## D. a validation that asserted nothing ##########")
print("  Disclosed rather than refused - the summary carries passed=0 - so this")
print("  is recorded as context for section C, not as a defect on its own.")
run("passed=0 failed=0 skipped=0 with exit code 0", "accepted",
    validations=[{"command": "true", "exit_code": 0, "passed": 0, "failed": 0,
                  "skipped": 0, "skip_reasons": []}])

print("\n########## E. the report gates ##########")
print("  contains_fill_marker IS consumed, at evidence.py:293 - a manifest with")
print("  unmeasured claims whose report lacks [FILL] is refused. The first run of")
print("  this probe asked the wrong question; the rule runs the other way and is")
print("  correct. What follows is the section-boundary check instead.")
from evidence_orchestrator.evidence import validate_submission  # noqa: E402
from evidence_orchestrator.errors import EvidenceError  # noqa: E402
report = ROOT / "r.md"
report.write_text("\n".join([
    "# report", "", "## 1. Files changed", "[FILL]", "",
    "## 2. Validation and raw output", "[FILL]", "",
    "## 3. Pass, fail, and skip counts", "[FILL]", "",
    "## 4. Known-answer comparison", "[FILL]", "",
    "## 5. Proposed changes outside ownership", "[FILL]", "",
    "## 6. Unmeasured items", "[FILL]", ""]), encoding="utf-8")
result = validate_report(report)
check("a report may legitimately be all [FILL]", "contains_fill_marker=True",
      f"accepted: contains_fill_marker={result['contains_fill_marker']}")

# POSITIVE CONTROL for the rule at evidence.py:293.
nofill = ROOT / "nofill.md"
nofill.write_text("\n".join([
    "# report", "", "## 1. Files changed", "x", "",
    "## 2. Validation and raw output", "x", "",
    "## 3. Pass, fail, and skip counts", "x", "",
    "## 4. Known-answer comparison", "x", "",
    "## 5. Proposed changes outside ownership", "x", "",
    "## 6. Unmeasured items", "x", ""]), encoding="utf-8")
mpath = ROOT / "m.json"
mpath.write_text(json.dumps(manifest(claims=[{"name": "speedup",
                                              "kind": "performance",
                                              "measured": False,
                                              "value": "[FILL]"}]), indent=2),
                 encoding="utf-8")
try:
    validate_submission(nofill, mpath, permissions=PERMS, gates=GATES)
    check("POSITIVE CONTROL - unmeasured claims with no [FILL] in the report",
          "report has no [FILL] marker", "accepted")
except EvidenceError as exc:
    check("POSITIVE CONTROL - unmeasured claims with no [FILL] in the report",
          "report has no [FILL] marker", f"rejected ({exc})")

# The body of a section is measured from just after the section NUMBER, so the
# heading's own words count as content. Only a bare "## 1." can be empty.
titled = ROOT / "titled.md"
titled.write_text("\n".join([
    "# report", "", "## 1. Files changed", "", "## 2. Validation and raw output",
    "x", "", "## 3. Pass, fail, and skip counts", "x", "",
    "## 4. Known-answer comparison", "x", "",
    "## 5. Proposed changes outside ownership", "x", "",
    "## 6. Unmeasured items", "x", ""]), encoding="utf-8")
try:
    validate_report(titled)
    check("a titled section with no content is refused", "section 1 is empty",
          "accepted")
except Exception as exc:
    check("a titled section with no content is refused", "section 1 is empty",
          f"rejected ({exc})")

bare = ROOT / "bare.md"
bare.write_text("\n".join([
    "# report", "", "## 1.", "", "## 2. Validation and raw output", "x", "",
    "## 3. Pass, fail, and skip counts", "x", "",
    "## 4. Known-answer comparison", "x", "",
    "## 5. Proposed changes outside ownership", "x", "",
    "## 6. Unmeasured items", "x", ""]), encoding="utf-8")
try:
    validate_report(bare)
    check("POSITIVE CONTROL - a bare '## 1.' heading is refused",
          "section 1 is empty", "accepted")
except Exception as exc:
    check("POSITIVE CONTROL - a bare '## 1.' heading is refused",
          "section 1 is empty", f"rejected ({exc})")

shutil.rmtree(ROOT, ignore_errors=True)
print(f"\n########## {FAIL} unexpected result(s) ##########")
print("SUBMITTED, not VERIFIED.")
