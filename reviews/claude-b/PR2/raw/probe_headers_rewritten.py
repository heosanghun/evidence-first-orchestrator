#!/usr/bin/env python3
"""`public/_headers` is not neglected - it is being MAINTAINED without the block.

#20 and its first update reported that the security-header block was deleted,
restored by a rollback, and deleted again. The natural reading of that is
neglect: nobody has noticed.

That reading is now wrong, and this measures why. Since `a93e720` the file has
been edited by **two commits whose own subjects name it**, it has GROWN from 12
lines to 14, and not one of the five security headers came back. A third commit
in the range is a SECOND rollback - `RESTORE: Rollback to stable clean state` -
and unlike the rollback at `05cbb95`, it did not restore them either.

Two expectations written into this probe were wrong and are corrected to the
measurement, not the other way round: I expected THREE editing commits (there
are two) and a THIRD rollback (it is the second). The anchor file is 16 lines,
not the 15 I first wrote.

    python3 probe_headers_rewritten.py

Resolves `origin/main` LIVE. The review's anchor stays pinned at 5694ab45;
the ref under observation must not be, because the point is to watch it move.
"""

from __future__ import annotations

import subprocess

FAIL = 0
ANCHOR_SHA = "5694ab455139f1e72d946bc2fe7e42c7c0c8a43a"
REPO = "/tmp/efo-prov"
HEADERS = "public/_headers"
SECURITY = ["Content-Security-Policy", "Permissions-Policy", "Referrer-Policy",
            "X-Content-Type-Options", "X-Frame-Options"]


def git(*args: str) -> str:
    return subprocess.run(["git", "-C", REPO, *args],
                          capture_output=True, text=True).stdout


def check(name: str, expected: str, observed: str) -> None:
    global FAIL
    ok = expected in observed
    if not ok:
        FAIL += 1
    print(f"  [{'ok' if ok else '!! UNEXPECTED !!'}] {name}")
    print(f"        expected: {expected}")
    print(f"        observed: {observed}")


def headers_at(ref: str) -> str:
    return git("show", f"{ref}:{HEADERS}")


# ---------------------------------------------------------------- A
print("########## A. POSITIVE CONTROL ##########")
head = git("rev-parse", "HEAD").strip()
dirty = git("status", "--porcelain").strip()
check("the review's anchor is UNMOVED at 5694ab45", ANCHOR_SHA, head)
check("  with no working-tree modification", "dirty: ''", f"dirty: {dirty!r}")
subprocess.run(["git", "-C", REPO, "fetch", "origin", "main", "--quiet"])
main = git("rev-parse", "--short", "origin/main").strip()
check("  and main has MOVED past it", "moved: True",
      f"moved: {git('rev-parse', 'origin/main').strip() != head}"
      f"   (main is now {main})")

anchor_text = headers_at(ANCHOR_SHA[:7])
check("  the anchor's file carries every security header",
      f"present: {len(SECURITY)}",
      f"present: {sum(h in anchor_text for h in SECURITY)}")
print("  The anchor is the known answer. If it ever stops carrying all five,")
print("  the comparison below is meaningless and this check says so first.")

# ---------------------------------------------------------------- B
print("\n########## B. what the file is at main ##########")
main_text = headers_at("origin/main")
present = [h for h in SECURITY if h in main_text]
check("security headers still present at main", "present: []",
      f"present: {present}")
check("  the file is not empty or missing - it GREW",
      "anchor 16 -> main 14",
      f"anchor {len(anchor_text.splitlines())} -> "
      f"main {len(main_text.splitlines())}")
cache = sum(1 for line in main_text.splitlines()
            if "Cache-Control" in line or "Pragma" in line
            or "Expires" in line)
check("  and every directive it now carries is a CACHE directive",
      f"cache directives: {sum(1 for l in main_text.splitlines() if l.strip() and not l.startswith('/'))}",
      f"cache directives: {cache}")
print("  So the file was not truncated or lost in a merge. It was REWRITTEN,")
print("  as a cache-control file, and the security block was not carried over.")

# ---------------------------------------------------------------- C
print("\n########## C. it has been edited TWICE since, by commits that NAME it ##########")
revs = git("rev-list", "--reverse", "a93e720..origin/main").split()
print(f"  {len(revs)} commits on main since a93e720 (the last commit #20's")
print("  update measured); the ones that touch the file itself:")
touching: list[tuple[str, str, int, int]] = []
for rev in revs:
    changed = git("show", "--name-only", "--format=", rev).split()
    if HEADERS in changed:
        text = headers_at(rev)
        touching.append((git("rev-parse", "--short", rev).strip(),
                         git("log", "-1", "--format=%s", rev).strip(),
                         len(text.splitlines()),
                         sum(h in text for h in SECURITY)))
for sha, subject, lines, sec in touching:
    print(f"    {sha}  lines={lines:<3} security={sec}  {subject[:62]}")
# BOTH SIDES DERIVED. The left side is git's own pathspec filter; the right is
# my --name-only enumeration above. Writing `len(touching)` on both sides would
# be a check that cannot fail - the #8 defect, reintroduced in my own probe.
pathspec = git("rev-list", "a93e720..origin/main", "--", HEADERS).split()
check("commits that EDIT the headers file since a93e720",
      f"editing: {len(pathspec)}", f"editing: {len(touching)}")
check("  every one of them leaves zero security headers",
      "max security headers after any edit: 0",
      f"max security headers after any edit: "
      f"{max((t[3] for t in touching), default=-1)}")
check("  and the file grows rather than shrinks", "grew: True",
      f"grew: {touching[-1][2] > touching[0][2]}"
      f"   ({touching[0][2]} -> {touching[-1][2]} lines)")
print("  BOTH name the header file in their own subject line - `CDN: Strict")
print("  no-cache headers for Cloudflare Pages index.html` and `CDN: Add")
print("  s-maxage=0 max-age=0 to _headers for Cloudflare Edge POP nodes`.")
print("  This is not a file nobody is looking at.")
print("  I went in expecting THREE such commits. There are two. The")
print("  expectation was corrected to the measurement.")

# ---------------------------------------------------------------- D
print("\n########## D. a SECOND rollback, and this one did not restore them ##########")
rollbacks = [(git("rev-parse", "--short", r).strip(),
              git("log", "-1", "--format=%s", r).strip(),
              sum(h in headers_at(r) for h in SECURITY))
             for r in git("rev-list", "--reverse",
                          f"{ANCHOR_SHA}..origin/main").split()
             if git("log", "-1", "--format=%s", r).startswith("RESTORE:")]
for sha, subject, sec in rollbacks:
    print(f"    {sha}  security headers after it: {sec}  {subject[:58]}")
# Same guard: git's --grep against my subject-prefix enumeration.
grepped = git("rev-list", f"{ANCHOR_SHA}..origin/main",
              "--grep", "^RESTORE:", "--extended-regexp").split()
check("explicit rollback commits since the anchor",
      f"rollbacks: {len(grepped)}", f"rollbacks: {len(rollbacks)}")
check("  the FIRST one restored the block", "05cbb95 -> 5",
      f"{rollbacks[0][0]} -> {rollbacks[0][2]}" if rollbacks else "none found")
check("  the SECOND one did not", "-> 0",
      f"-> {rollbacks[-1][2]}" if len(rollbacks) > 1 else "only one rollback")
print("  Expected a third rollback going in; there are two. Corrected.")
print("  `RESTORE: Rollback to stable clean state` is the strongest signal")
print("  available that someone intended to return to a known-good state. The")
print("  state it returns to no longer contains the headers, so a rollback")
print("  now PRESERVES the regression instead of undoing it. That is the")
print("  materially new fact, and the reason this is worth a comment.")

# ---------------------------------------------------------------- E
print("\n########## E. what is and is not covered by a test ##########")
print("  Unchanged and re-stated rather than assumed: web_tests asserts the")
print("  CSP line only (test 21, currently failing). X-Frame-Options,")
print("  X-Content-Type-Options, Referrer-Policy and Permissions-Policy are")
print("  asserted by no test, so four of the five could stay gone with a")
print("  fully green suite. Measured in raw-main-regression.txt, not here.")

# ---------------------------------------------------------------- F
print("\n########## F. what this does NOT do ##########")
print("  * It does not touch main, open a PR against it, or propose a patch.")
print("    #20 is a report; fixing main is not this review's licence.")
print("  * It does not re-run the web suite - probe_main_regression.py does")
print("    that, and it is the citation for 37/35/2.")
print("  * It does not claim to know INTENT. Every subject line quoted is")
print("    quoted verbatim; why the block was dropped is not measured.")
print("  * MEASURED: every file body, line count, header presence, commit")
print("    subject and range. REASONED: that a rollback now preserves the")
print("    regression - which follows from the measured state of the two")
print("    rollback commits, not from any statement by their author.")

print(f"\n########## {FAIL} unexpected result(s) ##########")
print("Read-only git queries against /tmp/efo-prov; nothing executed against a")
print("workspace, nothing written to main. Pre-registered permissions")
print("unchanged - gpu/network/performance_metrics all false.")
print("SUBMITTED, not VERIFIED.")
