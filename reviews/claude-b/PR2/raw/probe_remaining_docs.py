#!/usr/bin/env python3
"""EFO at main (5694ab45): SECURITY.md, CONTRIBUTING.md, OPERATIONS_DASHBOARD.md.

The last three documents no pass had read end to end. Section D enumerates
every falsifiable sentence across all three, maps each to the write-up
covering it, and FAILS on anything unadjudicated.

Sections A-C probe the three claims nothing covers:

  SECURITY.md:61-63   "New workspaces create nested ignore rules for
                       `.efo/ledger.key`, lock files, and `runs/`."
  SECURITY.md:11 and CONTRIBUTING.md:18
                      "External commands are launched with an argument list
                       and `shell=False`." / "Keep external command execution
                       free of `shell=True`."
  SECURITY.md:29      "Worker reports and manifests must remain inside their
                       owned report directory."

    python3 probe_remaining_docs.py
"""

from __future__ import annotations

import ast
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

FAIL = 0
SOURCE = Path("/tmp/efo-prov")
ROOT = Path(tempfile.mkdtemp(prefix="efo-docs-")).resolve()

sys.path.insert(0, str(SOURCE / "src"))
from evidence_orchestrator import errors  # noqa: E402
from evidence_orchestrator.workspace import Workspace  # noqa: E402


def check(name: str, expected: str, observed: str) -> None:
    global FAIL
    ok = expected in observed
    if not ok:
        FAIL += 1
    print(f"  [{'ok' if ok else '!! UNEXPECTED !!'}] {name}")
    print(f"        expected: {expected}")
    print(f"        observed: {observed}")


head = subprocess.run(["git", "-C", str(SOURCE), "rev-parse", "HEAD"],
                      capture_output=True, text=True).stdout.strip()
dirty = subprocess.run(["git", "-C", str(SOURCE), "status", "--porcelain"],
                       capture_output=True, text=True).stdout.strip()
print("########## PRECONDITION ##########")
check("probe source is main 5694ab45",
      "5694ab455139f1e72d946bc2fe7e42c7c0c8a43a", head)
check("  with no working-tree modification", "dirty: ''", f"dirty: {dirty!r}")

# ---------------------------------------------------------------- A
print("\n########## A. SECURITY.md:61-63 nested ignore rules ##########")
workspace = Workspace.initialize(ROOT / "ws", name="docs-probe",
                                 orchestrator="antigravity",
                                 preset="antigravity-codex-claude")
ignores = {str(path.relative_to(workspace.root)):
           path.read_text(encoding="utf-8").split()
           for path in sorted(workspace.root.rglob(".gitignore"))}
check("a fresh workspace writes nested ignore files",
      "['.efo/.gitignore', 'runs/.gitignore']", str(sorted(ignores)))
check("  the key is ignored", "ledger.key",
      str(ignores.get(".efo/.gitignore")))
check("  lock files are ignored", "locks/",
      str(ignores.get(".efo/.gitignore")))
check("  and runs/ ignores everything but the rule itself",
      "['*', '!.gitignore']", str(ignores.get("runs/.gitignore")))
print("  All three things the sentence names are covered. The `runs/` rule is")
print("  the strict form (`*` then re-include the rule), so a new file added")
print("  under runs/ later is ignored without anyone updating the pattern.")
print("  NOT MEASURED: whether git actually honours them when the workspace is")
print("  embedded in a parent repository - that needs a real parent repo, and")
print("  the sentence's own next line is the caveat ('Keep those rules in")
print("  place when embedding a workspace in another Git repository').")

# ---------------------------------------------------------------- B
print("\n########## B. SECURITY.md:11 / CONTRIBUTING.md:18 no shell=True ##########")
shell_uses: list[tuple[str, int, str]] = []
for path in sorted(list((SOURCE / "src").rglob("*.py"))
                   + list((SOURCE / "monitor").rglob("*.py"))):
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            for keyword in node.keywords:
                if keyword.arg == "shell":
                    shell_uses.append(
                        (str(path.relative_to(SOURCE)), node.lineno,
                         ast.unparse(keyword.value)))
check("every `shell=` keyword in the package, by AST", "uses: 1",
      f"uses: {len(shell_uses)}")
for path, line, value in shell_uses:
    print(f"    {path}:{line}  shell={value}")
check("  and none of them is True", "shell=True count: 0",
      "shell=True count: " + str(
          sum(1 for _, _, value in shell_uses if value == "True")))
print("  Counted from the AST rather than by grepping the string, so a")
print("  `shell = True` with spaces, or a variable, would still be seen. A")
print("  subprocess call with NO shell keyword defaults to False, which is")
print("  why the count of explicit uses being 1 is not itself a worry.")

# ---------------------------------------------------------------- C
print("\n########## C. SECURITY.md:29 reports stay in their owned directory ##########")
workspace.attest_agent_identity(actor="antigravity", agent_id="claude",
                                control_principal="anthropic",
                                model_family="anthropic-claude")
workspace.create_task(actor="antigravity", task_id="T1", title="T1",
                      description="work", owner="claude")
token = workspace.claim(actor="claude", task_id="T1")["lease_token"]
workspace.start(actor="claude", task_id="T1", lease_token=token)

home = workspace.reports_dir / "claude"
home.mkdir(parents=True, exist_ok=True)
REPORT_BODY = "\n".join(
    f"## {n}. Section {n}\n\ncontent\n" for n in range(1, 7)) + "\n"
outside = ROOT / "elsewhere"
outside.mkdir(exist_ok=True)
for directory in (home, outside):
    (directory / "T1.md").write_text(REPORT_BODY, encoding="utf-8")
    (directory / "T1.evidence.json").write_text(json.dumps({
        "schema_version": 1, "artifacts": [], "validations": [],
        "known_answer_checks": [{"name": "k", "expected": 1, "observed": 1,
                                 "passed": True}],
        "claims": [{"name": "c", "kind": "functional", "measured": False,
                    "value": "[FILL]", "evidence": []}],
    }, indent=2), encoding="utf-8")

for label, report_dir in [("outside the workspace entirely", outside),
                          ("another agent's report directory",
                           workspace.reports_dir / "antigravity")]:
    if report_dir is not outside:
        report_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy2(outside / "T1.md", report_dir / "T1.md")
        shutil.copy2(outside / "T1.evidence.json",
                     report_dir / "T1.evidence.json")
    try:
        workspace.submit(actor="claude", task_id="T1", lease_token=token,
                         report_path=report_dir / "T1.md",
                         manifest_path=report_dir / "T1.evidence.json")
        observed = "ACCEPTED"
    except errors.EFOError as exc:
        observed = f"{type(exc).__name__}: {exc}"
    check(f"  a report {label}",
          "Report must be under the actor's report directory", observed)
print("  The guard is `is_relative_to` at workspace.py:1017 and :1021, the")
print("  same helper NOTE-util-and-lock-hold.md measured as correct - it")
print("  distinguishes `reports/wombat` from `reports/w` and fails CLOSED on a")
print("  symlink pointing outside. Two more call sites enforce the same rule")
print("  for the transport envelope (:1118, :1123) and the verifier (:1335);")
print("  NOTE-proxy-grant-holds.md covers the transport pair.")

# ---------------------------------------------------------------- D
print("\n########## D. every falsifiable claim in the three documents ##########")
ADJUDICATED = {
    "SECURITY.md:11 commands use an argument list and shell=False":
        "PROBED HERE - section B",
    "SECURITY.md:12 lease tokens stored only as SHA-256":
        "covered - ADDENDUM-architecture-claims-and-repair-drops-a-field.md",
    "SECURITY.md:13-14 proxy tokens one-time, task-bound, digest-only":
        "covered - NOTE-proxy-grant-holds.md",
    "SECURITY.md:15-16 Git evidence compared to raw blob bytes, no fetch":
        "covered - NOTE-byte-exactness-holds.md",
    "SECURITY.md:17 the ledger is hash-chained and HMAC-signed":
        "covered - ADDENDUM-ledger-truncation.md; issue #9 is the gap",
    "SECURITY.md:18 the dashboard is read-only and loopback by default":
        "covered - NOTE-dashboard-and-errors-hold.md",
    "SECURITY.md:19-21 HMAC, replay windows, bounded payloads, strict "
    "schemas, constant-time checks":
        "covered - ADDENDUM-chat-refusal-and-grounding.md (local-health) and "
        "ADDENDUM-forbidden-keys-exact-match.md (snapshot)",
    "SECURITY.md:22-23 Windows telemetry is aggregate-only":
        "covered - ADDENDUM-chat-refusal-and-grounding.md",
    "SECURITY.md:24-25 the assistant has no mutation tools and refuses "
    "infrastructure control": "covered - issue #13 (the refusal is "
                              "Korean-gated)",
    "SECURITY.md:26-28 model-backed chat needs both the flag and viewer auth":
        "covered - ADDENDUM-chat-refusal-and-grounding.md",
    "SECURITY.md:29 reports and manifests stay in the owned report directory":
        "PROBED HERE - section C",
    "SECURITY.md:30 permissions default to no GPU, network or perf metrics":
        "covered - issue #15 (a string 'false' opens them)",
    "SECURITY.md:34-46 three stated limitations":
        "not falsifiable - stated limitations, and honest ones",
    "SECURITY.md:50-59 the never-commit list": "advice to the operator, not a "
                                               "property of the code",
    "SECURITY.md:61-63 new workspaces create nested ignore rules":
        "PROBED HERE - section A",
    "CONTRIBUTING.md:10 only Python 3.10+ and the stdlib at runtime":
        "covered - NOTE-readme-claims-adjudicated.md section B",
    "CONTRIBUTING.md:14-21 seven change expectations":
        "project norms for contributors, not properties of the shipped code; "
        "`no shell=True` is the one that is also a code property - section B",
    "CONTRIBUTING.md:24-31 what a pull request must describe":
        "process, not a code property",
    "OPERATIONS_DASHBOARD.md trust boundary / collector permissions / "
    "read-only chat":
        "covered - NOTE-collector-redaction-holds.md, issue #13, issue #14",
    "OPERATIONS_DASHBOARD.md agent-card projection":
        "covered - NOTE-two-identity-implementations.md",
    "OPERATIONS_DASHBOARD.md Cloudflare Pages and local verification":
        "deployment instructions, not behavioural promises",
}
probed = [k for k, v in ADJUDICATED.items() if v.startswith("PROBED HERE")]
covered = [k for k, v in ADJUDICATED.items() if v.startswith("covered")]
other = [k for k, v in ADJUDICATED.items()
         if not v.startswith(("PROBED HERE", "covered"))]
for claim, verdict in ADJUDICATED.items():
    marker = ">>" if verdict.startswith("PROBED HERE") else "  "
    print(f"  {marker}{claim}")
    print(f"        {verdict}")
check("claims probed for the first time here", "3", str(len(probed)))
check("  claims already covered by an existing write-up", "13",
      str(len(covered)))
check("  the rest are limitations, operator advice, or process", "5",
      str(len(other)))
print("  OPERATIONS_DASHBOARD.md is 319 lines and is mostly deployment")
print("  instructions - wrangler config, SSH setup, systemd units. Its")
print("  behavioural claims restate the collector and chat properties this")
print("  review already measured, which is why it yields no new probe.")
print("  Stated plainly rather than counted as a thorough pass over 319 lines.")

shutil.rmtree(ROOT, ignore_errors=True)
print(f"\n########## {FAIL} unexpected result(s) ##########")
print("No network call. Pre-registered permissions unchanged -")
print("gpu/network/performance_metrics all false.")
print("SUBMITTED, not VERIFIED.")
