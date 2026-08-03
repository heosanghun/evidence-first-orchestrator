#!/usr/bin/env python3
"""The 8 provenance-attack scripts: which REF did each one actually run against?

Queue item 40 asked whether `raw/`'s third category - the shell and Python
attack scripts that predate the `[ok]` convention - should stay historical or
be documented, and said to stop rather than invent a rationale if a script's
purpose could not be reconstructed.

**The premise is wrong, and that is the first finding.** The category is not
opaque: every one of the eight self-documents in its first three lines. Nothing
had to be reconstructed.

What was NEVER recorded is the thing that matters for evidence: **which ref each
one ran against.** Two of the eight point at
`/workspace/evidence-first-orchestrator` - the review branch's own working tree,
unpinned - and they were committed on 2026-07-30, four days before `c16df6d`
merged `origin/main` in. At that moment the branch was based on `dad3f4c4`,
which `SYNTHESIS.md` records as behind main by 9,457 lines including
`provenance.py` -341.

So two attack results describe a DIFFERENT implementation than main's. Both
were later re-run against a pinned ref, which is why the `_main` scripts exist -
but the branch never said that the originals were superseded, and a reader
would take all eight as evidence about main.

    python3 probe_attack_provenance.py
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

FAIL = 0
ANCHOR = Path("/tmp/efo-prov")
REPO = Path("/workspace/evidence-first-orchestrator")
RAW = REPO / "reviews/claude-b/PR2/raw"


def check(name: str, expected: str, observed: str) -> None:
    global FAIL
    ok = expected in observed
    if not ok:
        FAIL += 1
    print(f"  [{'ok' if ok else '!! UNEXPECTED !!'}] {name}")
    print(f"        expected: {expected}")
    print(f"        observed: {observed}")


scripts = sorted(p.name for p in RAW.iterdir()
                 if p.is_file() and not p.name.startswith(("probe_", "raw-")))
# THIS PROBE'S OWN OUTPUT matches `raw-attack*.txt` too, and counting it would
# make the census grow by one the moment the probe is committed - the same
# self-reference probe_inventory_selfcheck.py hit, one level down. Excluded by
# name, and the exclusion is asserted below so a second cannot hide.
# The exclusion is DERIVED, not a name list. Any `raw-X.txt` that has a
# `probe_X.py` beside it is a PROBE output, not an attack output - including
# this probe's own, and including `raw-attack4-provenance.txt`, which was added
# later and collided with this glob purely because of its name. Hardcoding
# SELF caught the first collision and would have missed the second.
def is_probe_output(name: str) -> bool:
    return (RAW / f"probe_{name[len('raw-'):-len('.txt')].replace('-', '_')}.py").is_file()


SELF = "raw-attack-provenance.txt"
excluded = sorted(p.name for p in RAW.glob("raw-attack*.txt")
                  if is_probe_output(p.name))
outputs = sorted(p.name for p in RAW.glob("raw-attack*.txt")
                 if not is_probe_output(p.name))

# ---------------------------------------------------------------- A
print("########## A. POSITIVE CONTROL ##########")
head = subprocess.run(["git", "-C", str(ANCHOR), "rev-parse", "HEAD"],
                      capture_output=True, text=True).stdout.strip()
check("the review's anchor is unmoved at 5694ab45",
      "5694ab455139f1e72d946bc2fe7e42c7c0c8a43a", head)
check("  the attack category is the size every inventory reports",
      "scripts: 8", f"scripts: {len(scripts)}")

# ---------------------------------------------------------------- B
print("\n########## B. the category is NOT opaque - every script says what it did ##########")
undocumented: list[str] = []
for name in scripts:
    text = (RAW / name).read_text(encoding="utf-8", errors="replace")
    header = [line.lstrip("#\" ").rstrip()
              for line in text.splitlines()[1:5]
              if line.startswith(("#", '"""')) or line.strip().startswith('"""')]
    purpose = next((line for line in header if len(line) > 20), "")
    if not purpose:
        undocumented.append(name)
    print(f"    {name:<24} {purpose[:74]}")
check("scripts whose purpose could not be read from the file itself",
      "undocumented: []", f"undocumented: {undocumented}")
print("  The item's premise was that this category is permanently opaque. It")
print("  is not, and saying so is better than writing a rationale I would have")
print("  had to invent.")

# ---------------------------------------------------------------- C
print("\n########## C. what WAS never recorded: the ref each ran against ##########")
UNPINNED = "/workspace/evidence-first-orchestrator"
refs: dict[str, str] = {}
for name in scripts:
    text = (RAW / name).read_text(encoding="utf-8", errors="replace")
    match = re.search(r'^REPO=(\S+)', text, re.M) or re.search(
        r'^SOURCE = Path\("([^"]+)"\)', text, re.M)
    refs[name] = match.group(1) if match else "(not declared)"
for name, ref in sorted(refs.items()):
    marker = "!!" if ref == UNPINNED else "  "
    print(f"  {marker}{name:<24} {ref}")
unpinned = sorted(n for n, r in refs.items() if r == UNPINNED)
check("scripts pointed at the branch's own working tree, unpinned",
      "unpinned: ['attack2.sh', 'attack3.sh']", f"unpinned: {unpinned}")

# ---------------------------------------------------------------- D
print("\n########## D. and at that time the branch was the STALE base ##########")


def added(path: str) -> str:
    return subprocess.run(
        ["git", "-C", str(REPO), "log", "--diff-filter=A",
         "--format=%h %ad", "--date=short", "-1", "--",
         f"reviews/claude-b/PR2/raw/{path}"],
        capture_output=True, text=True).stdout.strip()


for name in unpinned:
    print(f"    {name:<24} first committed {added(name)}")
merge = subprocess.run(
    ["git", "-C", str(REPO), "log", "--format=%h %ad", "--date=short", "-1",
     "c16df6d"], capture_output=True, text=True).stdout.strip()
print(f"    branch-base merge        {merge}")
check("  the unpinned runs predate the merge that brought main in",
      "2026-07-30", added(unpinned[0]))
check("  and the merge is later", "2026-08-03", merge)
print("  Until c16df6d the branch was based on dad3f4c4 - behind main by 9,457")
print("  lines, provenance.py -341, per SYNTHESIS.md. attack3.sh is the GIT")
print("  PROVENANCE suite (G1 wrong remote, G2 local-only commit, G3 replace-ref")
print("  swap, G4 partial submission), so its results describe a 193-line")
print("  provenance.py, not main's 341-line rewrite.")
print("  That is precisely why attack_prov_main.sh and attack_prov5_main.py")
print("  exist - they re-ran the same attacks against /tmp/efo-prov at main.")
print("  The re-runs were done. What was never written down is that the two")
print("  ORIGINALS are superseded, so a reader takes all eight as evidence")
print("  about main. Same defect as REPORT.md reviewing an unnamed ref.")

# ---------------------------------------------------------------- E
print("\n########## E. two smaller gaps in the same category ##########")
check("raw-attack outputs present, excluding this probe's own",
      "outputs: 9", f"outputs: {len(outputs)}")
check("  and the probe-output exclusions are named, not silent",
      "excluded: ['raw-attack-provenance.txt', 'raw-attack4-provenance.txt']",
      f"excluded: {excluded}")
check("    this probe's own output among them", "self excluded: True",
      f"self excluded: {SELF in excluded}")
print(f"    {outputs}")
orphan = [o for o in outputs
          if not any(o[len('raw-'):].replace('-', '_').startswith(
              s.rsplit('.', 1)[0].replace('-', '_')[:6]) for s in scripts)]
print("    raw-attack4.txt has NO attack4 script in raw/. Nine outputs, eight")
print("    scripts: one result on this branch cannot be reproduced from what")
print("    the branch ships. Named rather than quietly dropped from the count.")
# Counted BY POSITION. A first version used `text.count(...)` and reported 2
# findings in raw-attack-prov5-main.txt - one real (`G2b  !! UNEXPECTED !!`)
# and one a legend line reading `Any '!! UNEXPECTED !!' above is a finding`.
# The same substring bug counted this probe's own 10 checks as 12, because a
# check below is NAMED after the token it looks for. Both are now positional:
# bracketed at line start (the check() convention) or bare at line end (the
# older attack-script convention). Anywhere else on a line is prose.
def markers(name: str) -> tuple[int, int]:
    ok = bad = 0
    for line in (RAW / name).read_text(encoding="utf-8",
                                       errors="replace").splitlines():
        s = line.strip()
        if s.startswith("[ok]"):
            ok += 1
        if s.startswith("[!! UNEXPECTED !!]") or s.endswith("!! UNEXPECTED !!"):
            bad += 1
    return ok, bad


instrumented = [o for o in outputs if markers(o)[0]]
check("  none of the attack outputs uses the [ok] convention",
      "instrumented: []", f"instrumented: {instrumented}")
flagged = {o: markers(o)[1] for o in outputs if markers(o)[1]}
check("  but one carries a bare UNEXPECTED marker instead",
      "{'raw-attack-prov5-main.txt': 1}", str(flagged))
loose = {o: (RAW / o).read_text(encoding="utf-8",
                                errors="replace").count("!! UNEXPECTED !!")
         for o in flagged}
check("    and substring counting would have doubled it",
      "{'raw-attack-prov5-main.txt': 2}", str(loose))
print("    So `predate the [ok] convention` is exact for 8 of 9 and slightly")
print("    generous for the ninth, which uses the failure marker alone - ONE")
print("    marker, not the two a substring count reports.")

# ---------------------------------------------------------------- F
print("\n########## F. what this does NOT do ##########")
print("  * It does not re-run any attack. The scripts drive real git")
print("    repositories and several need refs that no longer exist in this")
print("    container; re-running them is not possible here and is not claimed.")
print("  * It does not retract any finding. #3, #4 and #5 were each re-run")
print("    against a PINNED ref - /tmp/efo-prov at main, or /tmp/efo-main*,")
print("    /tmp/efo-proxy for the named commits - and those re-runs are what")
print("    the issues cite. The gap is bookkeeping on this branch, not a")
print("    defect in the findings.")
print("  * MEASURED: every header, every declared REPO, both commit dates, the")
print("    output inventory. REASONED: that attack3's results describe the old")
print("    provenance.py - which follows from the date and the declared path,")
print("    not from re-reading the 193-line file.")

print(f"\n########## {FAIL} unexpected result(s) ##########")
print("This audits MY OWN evidence, not EFO. Static file reads and two git log")
print("queries; no attack was executed. No issue filed. Pre-registered")
print("permissions unchanged. SUBMITTED, not VERIFIED.")
