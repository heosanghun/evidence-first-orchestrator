#!/usr/bin/env python3
"""EFO `dashboard.py` and `errors.py` at main (5694ab45).

`README.md:336-337` makes a concrete claim about `efo serve`:

    "Open http://127.0.0.1:8765. Remote binding is rejected unless
     --allow-remote is explicitly supplied."

That guard is tested exhaustively over a corpus of host spellings. NO SOCKET IS
BOUND: the guard runs before any bind, and what the handler would serve is
measured by calling the same Workspace methods the handler calls.

Section E enumerates every `raise` in the package and FAILS the run on any
exception type this probe has not adjudicated, so a new non-EFOError cannot
start escaping the CLI unnoticed.

    python3 probe_dashboard_and_errors.py
"""

from __future__ import annotations

import inspect
import re
import shutil
import sys
import tempfile
from pathlib import Path
from typing import Any

sys.path.insert(0, "/tmp/efo-prov/src")
from evidence_orchestrator import dashboard, errors  # noqa: E402
from evidence_orchestrator.workspace import Workspace  # noqa: E402

FAIL = 0
ROOT = Path(tempfile.mkdtemp(prefix="efo-dash-"))
SOURCE = Path("/tmp/efo-prov/src/evidence_orchestrator")


def check(name: str, expected: str, observed: str) -> None:
    global FAIL
    ok = expected in observed
    if not ok:
        FAIL += 1
    print(f"  [{'ok' if ok else '!! UNEXPECTED !!'}] {name}")
    print(f"        expected: {expected}")
    print(f"        observed: {observed}")


def bind_verdict(host: str, allow_remote: bool = False) -> str:
    """Call serve() and report what happened BEFORE any socket was created."""
    try:
        dashboard.serve(ROOT / "ws", host=host, port=0,
                        allow_remote=allow_remote)
        return "would have bound"
    except errors.ConfigurationError as exc:
        return f"refused ({exc})"
    except Exception as exc:  # a bind attempt, i.e. the guard let it through
        return f"PASSED THE GUARD ({type(exc).__name__}: {exc})"


# ---------------------------------------------------------------- A
print("########## A. POSITIVE CONTROL ##########")
ws = Workspace.initialize(ROOT / "ws", name="dash-probe",
                          orchestrator="antigravity",
                          preset="antigravity-codex-claude")
ws.attest_agent_identity(actor="antigravity", agent_id="claude",
                         control_principal="anthropic",
                         model_family="anthropic-claude")
ws.create_task(actor="antigravity", task_id="T1", title="T1",
               description="SECRETDESC work", owner="claude")
claim = ws.claim(actor="claude", task_id="T1")
ws.block(actor="claude", task_id="T1", lease_token=claim["lease_token"],
         reason="Evidence gate rejected output: /abs/SECRETPATH/run.sh")
check("the workspace is live", "tasks: 1", f"tasks: {len(ws.list_tasks())}")
source = (SOURCE / "dashboard.py").read_text(encoding="utf-8")
check("serve() checks the host before it constructs a server",
      "guard before bind: True",
      "guard before bind: " + str(
          source.index("allow_remote=True") < source.index("ThreadingHTTPServer(")))

# ---------------------------------------------------------------- B
print("\n########## B. the documented bind guard ##########")
print("  dashboard.py:218 allows exactly {'127.0.0.1', '::1', 'localhost'}.")
print("  No socket is bound: every refusal below happens before the server")
print("  object exists, and the three allowed spellings are NOT exercised.")
for host, expect_refused in [
    ("0.0.0.0", True),
    ("", True),
    ("::", True),
    ("192.168.1.10", True),
    ("example.invalid", True),
    ("127.0.0.1 ", True),
    (" 127.0.0.1", True),
    ("LOCALHOST", True),
    ("Localhost", True),
    ("127.1", True),
    ("127.0.0.2", True),
    ("0177.0.0.1", True),
    ("[::1]", True),
    ("localhost.", True),
]:
    verdict = bind_verdict(host)
    check(f"  host={host!r}",
          "refused (Remote dashboard binding requires explicit allow_remote=True)"
          if expect_refused else "would have bound",
          verdict)
print("  Every near-miss spelling of loopback fails CLOSED - the guard is a")
print("  strict allow-list, not a pattern match, so 127.1 and LOCALHOST are")
print("  refused even though both reach the loopback interface.")

# ---------------------------------------------------------------- C
print("\n########## C. what the dashboard would serve ##########")
print("  Measured by calling the same methods do_GET calls, not by binding.")
routes = re.findall(r'route == "([^"]+)"', source)
check("every route the handler answers", "['/', '/api/status', '/api/ledger']",
      str(routes))
status_payload: dict[str, Any] = {"status": ws.status(),
                                  "tasks": ws.list_tasks()}
blob = str(status_payload)
check("/api/status carries the task description", "SECRETDESC present: True",
      f"SECRETDESC present: {'SECRETDESC' in blob}")
check("  and the blocked_reason path", "SECRETPATH present: True",
      f"SECRETPATH present: {'SECRETPATH' in blob}")
print("  -> these are RAW task projections. The SSH collector deliberately")
print("     strips both (NOTE-collector-redaction-holds.md); this server does")
print("     not, and there is no authentication of any kind.")
check("the handler has no authorization check", "auth tokens in source: 0",
      "auth tokens in source: " + str(len(re.findall(
          r"authorization|Authorization|token|Bearer", source))))
print("  Not filed: nothing claims otherwise. README.md:336-337 promises the")
print("  bind is local unless opted out of, and that promise holds. What is")
print("  worth an operator knowing is that `--allow-remote` publishes full")
print("  task records - descriptions, blocked reasons, whole result bundles -")
print("  to anyone who can reach the port.")

check("the page is a module constant, not a file read", "DASHBOARD_HTML: True",
      f"DASHBOARD_HTML: {isinstance(getattr(dashboard, 'DASHBOARD_HTML', None), str)}")
check("  so no request can name a file", "open( in handler: 0",
      "open( in handler: " + str(
          source.split("def _handler")[1].split("def serve")[0].count("open(")))

# ---------------------------------------------------------------- D
print("\n########## D. errors.py ##########")
hierarchy = {name: obj for name, obj in vars(errors).items()
             if inspect.isclass(obj) and issubclass(obj, Exception)}
check("every exception derives from EFOError",
      "non-EFOError: []",
      "non-EFOError: " + str(sorted(
          name for name, obj in hierarchy.items()
          if name != "EFOError" and not issubclass(obj, errors.EFOError))))
print(f"  the family: {sorted(hierarchy)}")

# ---------------------------------------------------------------- E
print("\n########## E. can any failure escape the CLI as a traceback? ##########")
print("  My first premise here was WRONG and is corrected rather than filed:")
print("  I assumed cli.py catches only EFOError. It catches four families.")
cli_source = (SOURCE / "cli.py").read_text(encoding="utf-8")
caught = re.search(r"except \(([^)]+)\) as exc", cli_source).group(1)
caught_names = [name.strip() for name in caught.split(",")]
check("what main() actually catches",
      "['EFOError', 'OSError', 'ValueError', 'json.JSONDecodeError']",
      str(caught_names))

print("  Every raised exception CALL in the package, enumerated:")
raised: dict[str, list[str]] = {}
for path in sorted(SOURCE.glob("*.py")):
    for match in re.finditer(r"raise\s+([A-Z][A-Za-z0-9_.]*)\s*\(",
                             path.read_text(encoding="utf-8")):
        raised.setdefault(match.group(1), []).append(path.name)
ADJUDICATED = {
    "ConfigurationError": "EFOError - caught, exit 2",
    "AuthorizationError": "EFOError - caught, exit 2",
    "TransitionError": "EFOError - caught, exit 2",
    "LeaseError": "EFOError - caught, exit 2",
    "EvidenceError": "EFOError - caught, exit 2",
    "IntegrityError": "EFOError - caught, exit 2",
    "LockTimeout": "EFOError - caught, exit 2",
    "ValueError": "not an EFOError, but IN the catch tuple - exit 2",
    "SystemExit": "__main__.py:7, raise SystemExit(main()) - the exit itself",
}
uncovered = [name for name in raised if name not in ADJUDICATED]
for name in sorted(raised):
    kind = ADJUDICATED.get(name, "?")
    marker = "!!" if name in uncovered else "  "
    files = ", ".join(sorted(set(raised[name])))
    print(f"  {marker}{name:<22}{kind:<48}{files}")
check("every raised exception type is adjudicated", "uncovered: []",
      f"uncovered: {uncovered}")
check("  nothing raised falls outside the catch tuple", "escapes: []",
      "escapes: " + str(sorted(
          name for name in raised
          if name not in {"SystemExit"}
          and not (name in vars(errors) or name in {"ValueError"}))))

print("  and the two ValueError sites, driven through main():")
from evidence_orchestrator.cli import main as cli_main  # noqa: E402
import io  # noqa: E402
from contextlib import redirect_stderr, redirect_stdout  # noqa: E402
for label, argv in [
    ("task add with neither description flag - argparse gets there first",
     ["task", "add", str(ROOT / "ws"), "--actor", "antigravity", "--id", "T9",
      "--title", "T9", "--owner", "claude"]),
    ("agent add with a malformed --command-json",
     ["agent", "add", str(ROOT / "ws"), "--actor", "antigravity", "--id", "w9",
      "--role", "worker", "--mode", "command", "--command-json", "[1, 2]"]),
]:
    out, err = io.StringIO(), io.StringIO()
    try:
        with redirect_stdout(out), redirect_stderr(err):
            code = cli_main(argv)
    except SystemExit as exc:
        code = int(exc.code or 0)
    expected = "exit 2, usage:" if "description" in label else "exit 2, error:"
    check(f"  {label}", expected,
          f"exit {code}, {(err.getvalue() or out.getvalue()).splitlines()[0][:70]}")
print("  -> both exit 2 with a one-line message and no traceback. The first")
print("     never reaches cli.py:28's `raise ValueError`: argparse enforces the")
print("     required mutually-exclusive group first, so that raise is a dead")
print("     branch. Recorded, not filed - it is a belt-and-braces guard.")

shutil.rmtree(ROOT, ignore_errors=True)
print(f"\n########## {FAIL} unexpected result(s) ##########")
print("NO SOCKET WAS BOUND and no request was served.")
print("SUBMITTED, not VERIFIED.")
