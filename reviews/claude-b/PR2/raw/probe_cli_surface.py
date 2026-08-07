#!/usr/bin/env python3
"""EFO `cli.py` at main (5694ab45): what the command line exposes.

The CLI is the surface an operator actually touches. The questions worth
asking are whether it can reach anything the Python API gates, and whether any
command writes to the workspace without leaving a ledger event.

Section A is the positive control. Section B enumerates every subcommand from
the parser itself and FAILS the run on any command this probe has not
adjudicated, so a new command cannot ship unexamined.

    python3 probe_cli_surface.py
"""

from __future__ import annotations

import argparse
import io
import json
import shutil
import sys
import tempfile
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from typing import Any

sys.path.insert(0, "/tmp/efo-prov/src")
from evidence_orchestrator.cli import build_parser, main  # noqa: E402

FAIL = 0
ROOT = Path(tempfile.mkdtemp(prefix="efo-cli-"))
WS = ROOT / "ws"


def check(name: str, expected: str, observed: str) -> None:
    global FAIL
    ok = expected in observed
    if not ok:
        FAIL += 1
    print(f"  [{'ok' if ok else '!! UNEXPECTED !!'}] {name}")
    print(f"        expected: {expected}")
    print(f"        observed: {observed}")


def run(*argv: str) -> tuple[int, str, str]:
    out, err = io.StringIO(), io.StringIO()
    try:
        with redirect_stdout(out), redirect_stderr(err):
            code = main(list(argv))
    except SystemExit as exc:  # argparse
        code = int(exc.code or 0)
    return code, out.getvalue(), err.getvalue()


def events() -> int:
    path = WS / "ledger" / "events.jsonl"
    if not path.is_file():
        return 0
    return len([line for line in
                path.read_text(encoding="utf-8").splitlines() if line.strip()])


def tasks_mtimes() -> dict[str, float]:
    directory = WS / "tasks"
    if not directory.is_dir():
        return {}
    return {p.name: p.stat().st_mtime_ns for p in directory.glob("*.json")}


# ---------------------------------------------------------------- A
print("########## A. POSITIVE CONTROL - the CLI drives a real workspace ##########")
code, out, err = run("init", str(WS), "--name", "cli-probe",
                     "--orchestrator", "antigravity")
check("efo init", "exit 0", f"exit {code}")
check("  and the ledger opens with its own events", "events: 2",
      f"events: {events()}")

code, out, err = run("agent", "add", str(WS), "--actor", "antigravity",
                     "--id", "claude", "--role", "worker",
                     "--control-principal", "anthropic",
                     "--model-family", "anthropic-claude")
check("efo agent add", "exit 0", f"exit {code}")
code, out, err = run("task", "add", str(WS), "--actor", "antigravity",
                     "--id", "T1", "--title", "T1",
                     "--description", "work", "--owner", "claude")
check("efo task add", "exit 0", f"exit {code}")
created = json.loads(out)
check("  emits the task as JSON", "'state': 'pending'",
      f"'state': {created['state']!r}")
check("  with everything denied by default",
      "{'gpu': False, 'network': False, 'performance_metrics': False}",
      str(dict(sorted(created["permissions"].items()))))
code, out, err = run("status", str(WS))
check("efo status", "exit 0", f"exit {code}")
before = events()
check("  and reading did not append", f"events: {before}", f"events: {events()}")

# ---------------------------------------------------------------- B
print("\n########## B. every subcommand, enumerated from the parser ##########")


def subcommands(parser: argparse.ArgumentParser, prefix: str = "") -> list[str]:
    found: list[str] = []
    for action in parser._actions:
        if not isinstance(action, argparse._SubParsersAction):
            continue
        for name, sub in action.choices.items():
            path = f"{prefix}{name}"
            nested = subcommands(sub, prefix=f"{path} ")
            found.extend(nested or [path])
    return found


ADJUDICATED = {
    # command                       -> (writes?, appends a ledger event?)
    "init": ("writes", "yes - workspace.initialized"),
    "status": ("read-only", "no"),
    "agent add": ("writes", "yes - agent.added"),
    "agent attest": ("writes", "yes - agent.identity_attested"),
    "agent list": ("read-only", "no"),
    "task add": ("writes", "yes - task.created"),
    "task list": ("read-only", "no"),
    "task show": ("read-only", "no"),
    "task claim": ("writes", "yes - task.claimed"),
    "task start": ("writes", "yes - task.started"),
    "task heartbeat": ("writes", "yes - task.heartbeat"),
    "task block": ("writes", "yes - task.blocked"),
    "task submit": ("writes", "yes - task.submitted"),
    "task proxy-authorize": ("writes", "yes - task.proxy_authorized"),
    "task proxy-status": ("writes", "yes - task.external_status_reported"),
    "task proxy-submit": ("writes", "yes - task.proxy_submitted"),
    "task verify": ("writes", "yes - task.verified or task.rejected"),
    "task requeue": ("writes", "yes - task.requeued"),
    "task archive": ("writes", "yes - task.archived"),
    "recover": ("writes", "yes - task.blocked per expired lease"),
    "ledger verify": ("read-only", "no"),
    "ledger audit-projections": ("read-only", "no"),
    "ledger repair-projections": ("WRITES", "NO - rewrites tasks/*.json only"),
    "ledger audit-independence": ("read-only", "no"),
    "doctor": ("read-only", "no"),
    "legacy audit": ("read-only", "no - separate legacy tree"),
    "evidence check": ("read-only", "no"),
    "worker once": ("writes", "yes - via the adapter"),
    "worker loop": ("writes", "yes - via the adapter"),
    "serve": ("read-only", "no - dashboard"),
}
found = sorted(subcommands(build_parser()))
print(f"  {len(found)} subcommands found")
uncovered = [name for name in found if name not in ADJUDICATED]
extra = [name for name in ADJUDICATED if name not in found]
for name in found:
    writes, ledger = ADJUDICATED.get(name, ("?", "?"))
    marker = "!!" if name in uncovered else "  "
    print(f"  {marker}{name:<28}{writes:<12}{ledger}")
check("every subcommand is adjudicated", "uncovered: []", f"uncovered: {uncovered}")
check("  and the map has no stale entries", "stale: []", f"stale: {extra}")

# ---------------------------------------------------------------- C
print("\n########## C. the one command that writes without a ledger event ##########")
path = WS / "tasks" / "T1.json"
data = json.loads(path.read_text(encoding="utf-8"))
data["title"] = "quietly edited"
path.write_text(json.dumps(data, indent=2), encoding="utf-8")
code, out, err = run("ledger", "audit-projections", str(WS))
check("audit-projections notices the edit", "exit 2", f"exit {code}")
check("  and names it", "projection differs from ledger", err or out)

before_events, before_mtimes = events(), tasks_mtimes()
code, out, err = run("ledger", "repair-projections", str(WS),
                     "--actor", "antigravity")
check("repair-projections succeeds", "exit 0", f"exit {code}")
check("  it rewrote the projection", "changed: True",
      f"changed: {tasks_mtimes() != before_mtimes}")
check("  and appended NOTHING to the ledger",
      f"events: {before_events} -> {before_events}",
      f"events: {before_events} -> {events()}")
print("        -> the only mutating command with no signed record of itself.")
print("           Issue #12 is about what it does to a truncated chain; this")
print("           records the narrower fact that the repair is itself")
print("           unlogged, so an auditor sees the effect and not the cause.")

# ---------------------------------------------------------------- D
print("\n########## D. does the CLI weaken any API gate? ##########")
code, out, err = run("task", "add", str(WS), "--actor", "claude",
                     "--id", "T2", "--title", "T2",
                     "--description", "work", "--owner", "claude")
check("a worker claiming to be the orchestrator", "exit 2", f"exit {code}")
check("  is refused by the same check as the API",
      "Only orchestrator 'antigravity' may perform this action", err or out)

code, out, err = run("task", "claim", str(WS), "--actor", "antigravity",
                     "--id", "T1")
check("the orchestrator claiming a worker's task", "exit 2", f"exit {code}")

code, out, err = run("agent", "add", str(WS), "--actor", "antigravity",
                     "--id", "UPPER", "--role", "worker")
check("an invalid agent id from the command line", "exit 2", f"exit {code}")
check("  same validator as the API",
      "Agent id must start with a lower-case letter", err or out)

code, out, err = run("status", str(ROOT / "not-a-workspace"))
check("a --path that is not a workspace", "exit 2", f"exit {code}")
check("  refuses rather than creating one",
      "Not an Evidence First Orchestrator workspace", err or out)

print("  evidence check validates ARBITRARY paths - by design, and read-only:")
report = ROOT / "loose.md"
report.write_text("# not under any report directory\n", encoding="utf-8")
before_events = events()
code, out, err = run("evidence", "check", str(WS), "--id", "T1",
                     "--report", str(report), "--evidence", str(report))
check("  it accepts a path outside the workspace", "exit 2", f"exit {code}")
check("  and fails on the CONTENT, not on ownership",
      "Report is missing required numbered sections", err or out)
check("  having appended nothing", f"events: {before_events}",
      f"events: {events()}")
print("        -> README.md:590 calls this 'Validate a submission bundle'.")
print("           Workspace.submit still requires the report to be under")
print("           reports/<actor>/; this command records nothing, so the")
print("           looser path check is a convenience, not a bypass.")

shutil.rmtree(ROOT, ignore_errors=True)
print(f"\n########## {FAIL} unexpected result(s) ##########")
print("SUBMITTED, not VERIFIED.")
