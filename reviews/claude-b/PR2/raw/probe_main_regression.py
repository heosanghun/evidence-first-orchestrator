#!/usr/bin/env python3
"""EFO main has been RED since 2026-08-03 06:19Z, and it is not a flake.

A `web-tests` failure arrived on PR #16 at head 2b0ca5c. My push was
documentation only. The failing assertion is a STATIC STRING CHECK against
`public/assets/app.js` - a thing that cannot flake - and the concurrent run on
the same head PASSED. That contradiction is the thread this probe pulls.

The answer: a `push` run and a `pull_request` run are NOT the same source. The
push run checks out the branch head; the pull_request run checks out
`refs/pull/N/merge`, the branch MERGED INTO MAIN. When main moves, they
legitimately diverge - and main moved five minutes before my push.

    5694ab4  last GREEN run on main       (30609261383, 2026-07-31)
    b78c63d  first RED run                (30789807796, 2026-08-03 06:19Z)
    ...      nine consecutive red pushes
    0d67750  current main                 (30791567354, 2026-08-03 06:51Z)

What the UI rewrite removed, in two stages, is security-relevant:

  b78c63d - the transport-badge rendering, and 17 inline `style=` attributes
  0d67750 - the ENTIRE security header block from `public/_headers`:
            Content-Security-Policy, Permissions-Policy, Referrer-Policy,
            X-Content-Type-Options, X-Frame-Options

Two shipped tests already catch it. They are failing, and have been for nine
pushes.

    python3 probe_main_regression.py

NOTE ON REFS. This review is anchored at main 5694ab45 and every other probe
asserts that. This one deliberately reads TWO refs and names both, because the
finding IS the difference between them. `/tmp/efo-prov` is untouched.
"""

from __future__ import annotations

import re
import shutil
import subprocess
import tempfile
from pathlib import Path

FAIL = 0
PINNED = Path("/tmp/efo-prov")          # the review's anchor, 5694ab45
REPO = Path("/workspace/evidence-first-orchestrator")
NODE = "/opt/node22/bin/node"
GREEN = "5694ab455139f1e72d946bc2fe7e42c7c0c8a43a"
FIRST_RED = "b78c63d"
# `main` is resolved LIVE, not hardcoded. The first version of this probe
# pinned RED = 0d67750 and started reporting UNEXPECTED the moment main moved -
# a harness failure dressed as a finding. The anchor stays pinned because the
# review depends on it; the ref under observation must not be, because the
# whole point is to watch it move. The head actually measured is printed.
RED = subprocess.run(["git", "-C", "/workspace/evidence-first-orchestrator",
                      "rev-parse", "origin/main"],
                     capture_output=True, text=True).stdout.strip()


def check(name: str, expected: str, observed: str) -> None:
    global FAIL
    ok = expected in observed
    if not ok:
        FAIL += 1
    print(f"  [{'ok' if ok else '!! UNEXPECTED !!'}] {name}")
    print(f"        expected: {expected}")
    print(f"        observed: {observed}")


def at(ref: str, path: str) -> str:
    result = subprocess.run(["git", "-C", str(REPO), "show", f"{ref}:{path}"],
                            capture_output=True, text=True)
    return result.stdout if result.returncode == 0 else ""


def count(text: str, pattern: str) -> int:
    return len(re.findall(pattern, text))


# ---------------------------------------------------------------- A
print("########## A. POSITIVE CONTROL ##########")
head = subprocess.run(["git", "-C", str(PINNED), "rev-parse", "HEAD"],
                      capture_output=True, text=True).stdout.strip()
dirty = subprocess.run(["git", "-C", str(PINNED), "status", "--porcelain"],
                       capture_output=True, text=True).stdout.strip()
check("the review's anchor is UNMOVED at 5694ab45", GREEN, head)
check("  with no working-tree modification", "dirty: ''", f"dirty: {dirty!r}")
print("  This probe does not re-point it. Every other write-up on this branch")
print("  is bound to 5694ab45, and moving the anchor would invalidate them.")
remote = subprocess.run(["git", "-C", str(REPO), "rev-parse", "origin/main"],
                        capture_output=True, text=True).stdout.strip()
check("  and main has MOVED past it", "moved: True",
      f"moved: {remote != GREEN}   (main is now {remote[:7]})")
check("  node is available for an independent run", "v22",
      subprocess.run([NODE, "--version"], capture_output=True,
                     text=True).stdout.strip())

# ---------------------------------------------------------------- B
print("\n########## B. what the two shipped tests assert, and what main now has ##########")
suite = at(RED, "web_tests/snapshot.test.mjs")
check("the assertions are UNCHANGED between the two refs",
      "identical: True",
      "identical: " + str(suite == at(GREEN, "web_tests/snapshot.test.mjs")))
print("  So nothing about the TEST changed. Only the source it reads.")

PROPERTIES = [
    ("public/assets/app.js", r'status_source === "transport_assertion"',
     "the transport-badge branch  (test 25)"),
    ("public/assets/app.js", r"agent-transport-badge",
     "the badge class            (test 25)"),
    ("public/assets/app.js", r"status_badge",
     "the badge text at all      (test 25)"),
    ("public/_headers", r"Content-Security-Policy",
     "the CSP header             (test 21)"),
    ("public/_headers", r"X-Frame-Options",
     "clickjacking protection    (no test)"),
    ("public/_headers", r"X-Content-Type-Options",
     "MIME sniffing protection   (no test)"),
    ("public/_headers", r"Referrer-Policy",
     "referrer suppression       (no test)"),
    ("public/_headers", r"Permissions-Policy",
     "camera/mic/geolocation     (no test)"),
]
print(f"  {'property':<44} {'5694ab45':>9} {'0d67750':>9}")
lost: list[str] = []
for path, pattern, label in PROPERTIES:
    before = count(at(GREEN, path), pattern)
    after = count(at(RED, path), pattern)
    if before > 0 and after == 0:
        lost.append(label.split("(")[0].strip())
    print(f"  {label:<44} {before:>9} {after:>9}")
check("properties present at the anchor and GONE at main", "lost: 8",
      f"lost: {len(lost)}")

print("\n  and what was ADDED - the thing test 21 forbids:")
INLINE_STYLE = r"style\s*="
for path in ("public/assets/app.js", "public/index.html"):
    before = count(at(GREEN, path), INLINE_STYLE)
    after = count(at(RED, path), INLINE_STYLE)
    print(f"    inline `style=` in {path:<26} {before:>4} -> {after:>4}")
# The COUNT at main is an observation of a moving ref, not an assertion - it
# was 32 when #20 was filed and is larger now. What is asserted is the
# direction: zero at the anchor, non-zero at main. Pinning the number would
# make the probe fail every time someone edits the dashboard, which is a
# harness failure dressed as a finding - the same mistake the hardcoded RED
# above already made once.
anchor_inline = count(at(GREEN, "public/assets/app.js"), INLINE_STYLE)
main_inline = count(at(RED, "public/assets/app.js"), INLINE_STYLE)
check("  inline styles: none at the anchor, some at main",
      "0 -> non-zero", f"{anchor_inline} -> "
      f"{'non-zero' if main_inline else 'zero'}  (exact count now {main_inline},"
      f" it was 32 when #20 was filed)")

# ---------------------------------------------------------------- C
print("\n########## C. an INDEPENDENT run, not a reading of CI's log ##########")
workspace = Path(tempfile.mkdtemp(prefix="efo-main-"))
observed: dict[str, tuple[int, int, int]] = {}
try:
    for label, ref in (("5694ab45 (anchor)", GREEN), (f"{RED[:7]} (main)", RED)):
        target = workspace / ref[:7]
        subprocess.run(["git", "-C", str(REPO), "worktree", "add", "-f",
                        "--detach", str(target), ref],
                       capture_output=True, text=True, check=True)
        run = subprocess.run(
            [NODE, "--test", "web_tests/chat.test.mjs",
             "web_tests/local-health.test.mjs", "web_tests/snapshot.test.mjs"],
            cwd=target, capture_output=True, text=True)
        text = run.stdout
        tests = int(re.search(r"^# tests (\d+)", text, re.M).group(1))
        passed = int(re.search(r"^# pass (\d+)", text, re.M).group(1))
        failed = int(re.search(r"^# fail (\d+)", text, re.M).group(1))
        observed[label] = (tests, passed, failed)
        print(f"    {label:<20} tests {tests}  pass {passed}  fail {failed}"
              f"   (exit {run.returncode})")
        for line in text.splitlines():
            if line.startswith("not ok"):
                print(f"        {line}")
        subprocess.run(["git", "-C", str(REPO), "worktree", "remove", "--force",
                        str(target)], capture_output=True, text=True)
finally:
    shutil.rmtree(workspace, ignore_errors=True)

check("the suite is GREEN at the review's anchor",
      "(37, 37, 0)", str(observed["5694ab45 (anchor)"]))
check("  and RED at current main", "(37, 35, 2)",
      str(observed[f"{RED[:7]} (main)"]))
print("  This is a KNOWN-ANSWER check in the strict sense: CI reported")
print("  `# tests 37 / # pass 35 / # fail 2` for job 91616795908, and this")
print("  container reproduces exactly that from the same ref. The anchor")
print("  passes 37/37, so the harness is not simply broken.")
print("  Executed here: `node --test` over three files that read local files")
print("  and a stubbed KV. No network, no GPU, no performance measurement -")
print("  the pre-registered permissions are unchanged.")

# ---------------------------------------------------------------- D
print("\n########## D. when it broke, per commit ##########")
TIMELINE = ["5694ab4", "b78c63d", "548b616", "b10b226", "2564f28",
            "86f2587", "e03baf9", "e754076", "c4d359d", "0d67750",
            # after #20 was filed - including an explicit ROLLBACK that
            # restored none of the eight properties
            "05cbb95", "6194c40", "f724211", "c9c4189", "a93e720", RED[:7]]
print(f"  {'commit':<9} {'CSP':>4} {'badge':>6} {'inline style=':>14}")
for ref in TIMELINE:
    csp = count(at(ref, "public/_headers"), r"Content-Security-Policy")
    badge = count(at(ref, "public/assets/app.js"), r"agent-transport-badge")
    inline = count(at(ref, "public/assets/app.js"), INLINE_STYLE)
    print(f"  {ref:<9} {csp:>4} {badge:>6} {inline:>14}")
check("  the badge and the inline styles arrive together at b78c63d",
      "badge 0, inline 17",
      f"badge {count(at(FIRST_RED, 'public/assets/app.js'), r'agent-transport-badge')}"
      f", inline {count(at(FIRST_RED, 'public/assets/app.js'), INLINE_STYLE)}")
check("  and the security headers survive until 0d67750, then go",
      "c4d359d: 1, 0d67750: 0",
      f"c4d359d: {count(at('c4d359d', 'public/_headers'), r'Content-Security-Policy')}"
      f", 0d67750: {count(at('0d67750', 'public/_headers'), r'Content-Security-Policy')}")
# I expected the rollback to have restored nothing. It restored the HEADER
# BLOCK and not the badge - and then the next commit deleted the headers
# again. Corrected to the measured facts rather than the guess.
check("  the ROLLBACK at 05cbb95 brought the header block BACK",
      "csp 1, badge 0",
      f"csp {count(at('05cbb95', 'public/_headers'), r'Content-Security-Policy')}"
      f", badge {count(at('05cbb95', 'public/assets/app.js'), r'agent-transport-badge')}")
check("  and 6194c40 deleted it a SECOND time", "csp 0, lines 7",
      f"csp {count(at('6194c40', 'public/_headers'), r'Content-Security-Policy')}"
      f", lines {len(at('6194c40', 'public/_headers').splitlines())}")
print("  So the header block has been deleted TWICE: at 0d67750, restored by")
print("  the explicit rollback at 05cbb95 (16 lines -> back to 16), and")
print("  deleted again at 6194c40 (16 -> 7). The rollback did NOT restore the")
print("  transport badge at any point. That is a materially different fact")
print("  from `still broken`, and the only reason to comment on #20 again.")
print("  Two stages, not one. The rendering regression is 32 minutes older")
print("  than the header deletion, and only the first has a test.")

# ---------------------------------------------------------------- E
print("\n########## E. what this does NOT establish ##########")
print("  * WHY the rewrite dropped them. The commit messages are about")
print("    gauge colours and goal text; none mentions the badge, inline")
print("    styles, or the headers. Whether the loss was intended is")
print("    UNMEASURED and not guessable from a diff.")
print("  * Whether the deployed Pages site actually serves without those")
print("    headers. `public/_headers` is Cloudflare's mechanism, and the")
print("    Pages project may set headers elsewhere. Checking the live site")
print("    is a NETWORK operation and `network: false` forbids it. What is")
print("    measured is the repository content, nothing more.")
print("  * Exploitability. No XSS was demonstrated. `escapeHtml` still")
print(f"    appears {count(at(RED, 'public/assets/app.js'), 'escapeHtml')} times in the new app.js, so the escaping")
print("    path was not wholesale removed - only the CSP that backstops it.")
print("  * MEASURED: every count above, the timeline, and both suite runs.")
print("    REASONED: that losing CSP + gaining 32 inline styles is a")
print("    weakening rather than a neutral refactor.")

print(f"\n########## {FAIL} unexpected result(s) ##########")
print("The failing check on PR #16 is INHERITED from main, not caused by this")
print("branch: the push run on 2b0ca5c passed, the pull_request run merged it")
print("with a broken main and failed. Nothing on this branch touches")
print("public/, web_tests/ or src/.")
print("Pre-registered permissions unchanged - gpu/network/performance_metrics")
print("all false. SUBMITTED, not VERIFIED.")
