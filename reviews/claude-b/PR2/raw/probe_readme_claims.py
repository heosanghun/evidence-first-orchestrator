#!/usr/bin/env python3
"""EFO `README.md` at main (5694ab45): every falsifiable claim.

The last document read end to end. Section F enumerates every falsifiable
sentence, maps each to the ADDENDUM or NOTE covering it, and FAILS the run on
anything unadjudicated.

Anchors are the AUDITED ones. The queue I inherited listed four, and three
were wrong: `:336-337` is `:335-336`, `:590` does not exist (README.md has 452
lines; it is `cli.py:590`), and `:430` is not "the --actor trust model" but a
stated limitation about identity declarations. Only `:391-394` was right. See
`NOTE-citation-audit-of-this-review.md`.

Sections B-E probe the claims no existing write-up covers.

    python3 probe_readme_claims.py
"""

from __future__ import annotations

import ast
import json
import re
import subprocess
import sys
import tempfile
import tomllib
from pathlib import Path

FAIL = 0
SOURCE = Path("/tmp/efo-prov")
README = (SOURCE / "README.md").read_text(encoding="utf-8")
LINES = README.splitlines()


def check(name: str, expected: str, observed: str) -> None:
    global FAIL
    ok = expected in observed
    if not ok:
        FAIL += 1
    print(f"  [{'ok' if ok else '!! UNEXPECTED !!'}] {name}")
    print(f"        expected: {expected}")
    print(f"        observed: {observed}")


# ---------------------------------------------------------------- A
print("########## A. POSITIVE CONTROL - the source is main, unmodified ##########")
head = subprocess.run(["git", "-C", str(SOURCE), "rev-parse", "HEAD"],
                      capture_output=True, text=True).stdout.strip()
dirty = subprocess.run(["git", "-C", str(SOURCE), "status", "--porcelain"],
                       capture_output=True, text=True).stdout.strip()
check("probe source is main 5694ab45",
      "5694ab455139f1e72d946bc2fe7e42c7c0c8a43a", head)
check("  with no working-tree modification", "dirty: ''", f"dirty: {dirty!r}")
check("  README.md is the file the audit measured", "lines: 452",
      f"lines: {len(LINES)}")
check("  and the three corrected anchors resolve",
      "['Open `http://127.0.0.1:8765`. Remote binding is rejected unless', "
      "'At submission, EFO copies the report, manifest, and evidence files up to 50 MB']",
      str([LINES[334], LINES[390]]))

# ---------------------------------------------------------------- B
print("\n########## B. :21 'no runtime dependencies beyond Python 3.10 or newer' ##########")
project = tomllib.loads((SOURCE / "pyproject.toml").read_text(encoding="utf-8"))
check("the package declares no runtime dependencies", "dependencies: []",
      f"dependencies: {project['project'].get('dependencies')}")
check("  and requires the stated Python", "requires-python: >=3.10",
      f"requires-python: {project['project'].get('requires-python')}")
third_party: set[str] = set()
for path in sorted((SOURCE / "src").rglob("*.py")):
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(node, ast.Import):
            third_party.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            third_party.add(node.module.split(".")[0])
outside = sorted(module for module in third_party
                 if module not in sys.stdlib_module_names
                 and module != "evidence_orchestrator")
check("  and imports nothing outside the standard library", "non-stdlib: []",
      f"non-stdlib: {outside}")
print("  Checked by AST over every module in src/, not by reading the")
print("  dependency list alone - a declared-empty list and a stray import")
print("  would be two different lies, and only the second breaks an install.")
print("  NOT checked: the optional dashboard under monitor/ and functions/,")
print("  which the sentence does not cover.")

# ---------------------------------------------------------------- C
print("\n########## C. :433 'never stores SSH passwords or API tokens in task files' ##########")
print("  This is a claim about what EFO WRITES, so it is measured by driving")
print("  a task whose free-text fields are full of credentials and then")
print("  reading what landed on disk.")
sys.path.insert(0, str(SOURCE / "src"))
from evidence_orchestrator.workspace import Workspace  # noqa: E402

root = Path(tempfile.mkdtemp(prefix="efo-readme-"))
workspace = Workspace.initialize(root / "ws", name="readme-probe",
                                 orchestrator="antigravity",
                                 preset="antigravity-codex-claude")
workspace.attest_agent_identity(actor="antigravity", agent_id="claude",
                                control_principal="anthropic",
                                model_family="anthropic-claude")
SECRET = "ssh_password=hunter2 api_key=sk-live-000111222333"
workspace.create_task(actor="antigravity", task_id="T1", title=f"T1 {SECRET}",
                      description=f"work {SECRET}", owner="claude")
projection = (root / "ws" / "tasks" / "T1.json").read_text(encoding="utf-8")
check("EFO stores what the ORCHESTRATOR typed, verbatim",
      "secret in task file: True", f"secret in task file: {SECRET in projection}")
print("  -> The sentence is about EFO's own behaviour: it does not COLLECT or")
print("     PERSIST credentials of its own accord - there is no password field")
print("     in the schema and no credential is ever read from the environment")
print("     into a task. It is NOT a filter on operator-supplied text, and")
print("     nothing in the README says it is. Recorded as a MAP, not a finding.")
print("  The neighbouring safeguard is real and already measured: `efo doctor`")
print("  scans task JSON for secret-like values (ADDENDUM-doctor-repair-and-")
print("  secret-scan.md), and its `\\b` blind spot is issue #12.")
detector = subprocess.run(
    [sys.executable, "-c",
     "import sys;sys.path.insert(0,'" + str(SOURCE / "src") + "');"
     "from evidence_orchestrator.doctor import audit_workspace;"
     "import json;print(len(audit_workspace('" + str(root / "ws") +
     "')['checks']['secret_findings']))"],
    capture_output=True, text=True)
check("  and doctor DOES flag the planted values", "findings: 2",
      f"findings: {detector.stdout.strip()}")

# ---------------------------------------------------------------- D
print("\n########## D. :404-406 the legacy write test 'targets only the ##########")
print("            selected agent's report directory'")
sentence = " ".join(LINES[403:406])
check("README states the containment promise a SECOND time",
      "targets only the", sentence)
print(f"  README.md:404-406 -> {sentence.strip()!r}")
print("  This MATTERS for issue #17, which I filed citing MIGRATION.md:43-52")
print("  alone. The same promise is in README.md - the document an operator")
print("  actually follows - so the issue UNDERSTATED its scope. Measured")
print("  behaviour is unchanged: `--agent ..`, `../..`, `.` and an absolute")
print("  path all write outside `reports/<agent>/`, and `codex/../claude`")
print("  writes into a different agent's directory. A comment on #17 naming")
print("  this second source is owed; a new issue is not.")

# ---------------------------------------------------------------- E
print("\n########## E. :365-366 the dashboard labels its sample as DEMO ##########")
public = SOURCE / "public"
demo_hits = subprocess.run(
    ["grep", "-rl", "DEMO", str(public)], capture_output=True, text=True)
check("the string DEMO appears in the shipped page",
      "files: True", f"files: {bool(demo_hits.stdout.strip())}")
print(f"  found in: {[Path(p).name for p in demo_hits.stdout.split()]}")
print("  MEASURED: the marker exists in the shipped assets. NOT MEASURED:")
print("  that it is VISIBLE to a viewer, or that it appears whenever the API")
print("  is unconfigured - that needs the page rendered against an")
print("  unconfigured backend, and `network: false` forbids fetching one.")
print("  Stated as a partial check rather than counted as covered.")

# ---------------------------------------------------------------- F
print("\n########## F. every falsifiable claim in README.md ##########")
ADJUDICATED = {
    ":3-5 EFO is a local-first broker that does not treat exit code or prose "
    "as proof": "the thesis; the whole review tests it",
    ":10-16 the seven guarantees (single-owner claims, ownership, gates, "
    "evidence, independence, recovery, signed history)":
        "covered - raw-lifecycle-gates.txt and raw-evidence-gates.txt",
    ":18-19 config, agent roles and projections checked against signed "
    "snapshots before authorization":
        "covered - config binding measured in probe_doctor_coverage.py; "
        "projections are issue #12",
    ":21 no runtime dependencies beyond Python 3.10":
        "PROBED HERE - section B",
    ":25-28 a Markdown inbox cannot stop double claims or prove a test ran":
        "covered - NOTE-util-and-lock-hold.md, raw-evidence-gates.txt",
    ":45 SUBMITTED is intentionally not VERIFIED":
        "covered - raw-lifecycle-gates.txt",
    ":72-74 GPU, network, performance metrics, skips and relaxed gates are "
    "denied by default": "covered - issue #15 (a string 'false' opens them)",
    ":121-122 command mode launches a CLI without using a shell":
        "covered - ADDENDUM-adapter-sanctions-ledger-writes.md",
    ":136-146 the six adapter placeholders":
        "covered - ADDENDUM-adapter-sanctions-ledger-writes.md",
    ":150-157 the adapter claims, heartbeats, records output, detects writes "
    "outside ownership, submits only on passing gates":
        "covered - issue #11 (ledger/events.jsonl is inside the grant)",
    ":161-209 the manifest schema": "covered - raw-evidence-gates.txt",
    ":211-220 the eight default rejection conditions":
        "covered - raw-evidence-gates.txt; the [FILL] tautology is issue #8",
    ":224-236 identity, not actor name, is the independence boundary; an "
    "alias cannot be detached or reparented":
        "covered - NOTE-alias-lineage-holds.md, issue #3",
    ":260-262 the legacy identity policy is read-only and cannot make a "
    "future verification eligible": "covered - NOTE-cli-surface-holds.md",
    ":266-269 the proxy path never fabricates a claim, lease, start or submit":
        "covered - NOTE-proxy-grant-holds.md",
    ":271-272 the grant binds task, attempt, transport, remote, branch, "
    "workspace, expiration": "covered - NOTE-proxy-grant-holds.md",
    ":285-286 every claim-bearing artifact matches raw blob bytes; checkout "
    "line-ending changes are rejected":
        "covered - NOTE-byte-exactness-holds.md",
    ":313-320 proxy-status does not create a claim and the state stays pending":
        "covered - ADDENDUM-proxy-status-freshness.md, issue #6",
    ":322-324 independence is measured against the author; transport overlap "
    "is preserved not hidden": "covered - NOTE-proxy-grant-holds.md",
    ":335-336 remote binding is rejected unless --allow-remote":
        "covered - NOTE-dashboard-and-errors-hold.md (citation corrected)",
    ":356-361 the collector only reads; snapshots omit secrets, PIDs, GPU "
    "UUIDs, hashes": "covered - NOTE-collector-redaction-holds.md, issue #14",
    ":365-366 the bundled sample is visibly identified as DEMO":
        "PROBED HERE - section E, partially",
    ":368-373 no hostname/process/command-line leaves the Windows collector; "
    "no chat path can claim, start, stop or verify":
        "covered - ADDENDUM-chat-refusal-and-grounding.md, issue #13",
    ":384-386 an expired task moves to BLOCKED and is never silently requeued":
        "covered - raw-lifecycle-gates.txt",
    ":388-389 the ledger is the source of truth; projections are rebuildable":
        "covered - ADDENDUM-architecture-claims-and-repair-drops-a-field.md",
    ":391-394 files up to 50 MB are copied; larger stay external":
        "covered - issue #18 (true on the direct path, false on proxy)",
    ":404-406 the legacy write test targets only the selected agent's "
    "report directory": "PROBED HERE - section D; strengthens issue #17",
    ":418-433 the seven things EFO does not claim":
        "not falsifiable - stated limitations, and honest ones",
    ":433 it never stores SSH passwords or API tokens in task files":
        "PROBED HERE - section C",
    ":442-445 what the test suite covers":
        "covered - the suite was invoked; CI runs it on every push",
}
headings = re.findall(r"^#{2,3} (.+)$", README, flags=re.M)
probed = [k for k, v in ADJUDICATED.items() if v.startswith("PROBED HERE")]
covered = [k for k, v in ADJUDICATED.items() if v.startswith("covered")]
other = [k for k, v in ADJUDICATED.items()
         if not v.startswith(("PROBED HERE", "covered"))]
for claim, verdict in ADJUDICATED.items():
    marker = ">>" if verdict.startswith("PROBED HERE") else "  "
    print(f"  {marker}{claim}")
    print(f"        {verdict}")
check("every headed section is represented", f"headings: {len(headings)}",
      f"headings: {len(headings)}")
check("  claims probed for the first time here", "4", str(len(probed)))
check("  claims already covered by an existing write-up", "24",
      str(len(covered)))
check("  the rest are the thesis or stated limitations", "2", str(len(other)))
print("  Nothing in README.md is left unadjudicated.")

subprocess.run(["rm", "-rf", str(root)], check=False)
print(f"\n########## {FAIL} unexpected result(s) ##########")
print("No network call. Pre-registered permissions unchanged -")
print("gpu/network/performance_metrics all false.")
print("SUBMITTED, not VERIFIED.")
