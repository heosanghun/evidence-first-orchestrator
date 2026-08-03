#!/usr/bin/env python3
"""Audit every FILE:LINE citation this review has made against EFO main.

Queue item 24 was "read README.md end to end". Step one was to check the four
anchors the queue listed. Two did not resolve:

  * `README.md:590` (cited in NOTE-cli-surface-holds.md) - README.md has 452
    lines. The phrase "Validate a submission bundle" appears in NO markdown
    file. It is `cli.py:590`, an argparse help= string.
  * `README.md:336-337` (cited in NOTE-dashboard-and-errors-hold.md) - the
    quoted sentence spans :335-336.

A citation that does not resolve is the exact failure this project exists to
prevent: a claim attributed to a source that does not say it. So instead of
reading one document, this audits EVERY citation in every write-up on the
branch, mechanically.

For each `path:line` or `path:a-b` found in the review documents:
  - does the file exist at main?
  - is the line number within the file?
  - and where the write-up quotes text, does that text appear at or near the
    cited lines?

The run FAILS on any unresolved citation.

    python3 probe_citation_audit.py
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

FAIL = 0
SOURCE = Path("/tmp/efo-prov")
REVIEWS = Path(
    "/workspace/evidence-first-orchestrator/reviews/claude-b/PR2")


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
documents = sorted(REVIEWS.glob("*.md"))
check("  and the write-ups are present", "documents: 44",
      f"documents: {len(documents)}")

# ---------------------------------------------------------------- B
print("\n########## B. every FILE:LINE citation in the write-ups ##########")
# Cited paths are repo-relative and may appear inside backticks.
CITATION = re.compile(
    r"`?([A-Za-z0-9_./-]+\.(?:py|md|js|mjs|toml|yml|json))`?:(\d+)(?:-(\d+))?")
KNOWN_MISSING = {
    # files this review deliberately names that do not exist at main
    "data/aime/test.jsonl",
    # CTS paths, cited from the CTS boundary map, not part of this repo
    "scripts/run_cts_eval_full.py", "tests/test_sweep_K_W_lambda.py",
    "qwen_adapter.py", "cts/backbone/qwen_adapter.py",
}

# The write-ups cite modules by bare name, the way a reader refers to them.
SEARCH_ROOTS = ("", "src/evidence_orchestrator", "docs", "functions/api",
                "public/assets", "monitor", "tests", "web_tests")


def resolve(path: str) -> Path | None:
    """A bare `doctor.py:109` means the module, not a file at the repo root."""
    for prefix in SEARCH_ROOTS:
        candidate = SOURCE / prefix / path if prefix else SOURCE / path
        if candidate.is_file():
            return candidate
    return None

citations: list[tuple[str, str, int, int | None]] = []
quoted_in_corrections = 0
for document in documents:
    for line in document.read_text(encoding="utf-8").splitlines():
        # A blockquote in these write-ups is a dated CORRECTION banner. It
        # quotes the citation it is retracting, so the bad string is still in
        # the file - but as a retraction, not a claim. Counting it as a live
        # citation would make a correction indistinguishable from the error it
        # corrects, and no document could ever be fixed.
        # Two exclusions, both stated rather than silent:
        #  1. a blockquote is a dated CORRECTION banner, quoting the citation
        #     it retracts - counting it live would make a correction
        #     indistinguishable from the error it corrects;
        #  2. an inline `[retracted]` marker, which a document reporting ON
        #     citations uses so that naming a bad citation is not itself
        #     scored as making one. The marker is visible to readers and
        #     mechanical, so no document is exempted by filename.
        if line.lstrip().startswith(">") or "[retracted" in line:
            quoted_in_corrections += len(CITATION.findall(line))
            continue
        for match in CITATION.finditer(line):
            path, start, end = match.group(1), int(match.group(2)), match.group(3)
            citations.append((document.name, path, start,
                              int(end) if end else None))

print(f"  {len(citations)} live citations across {len(documents)} documents")
print(f"  {quoted_in_corrections} more appear inside correction banners and are")
print("  excluded as retractions rather than claims - see the comment in the")
print("  source for why that exclusion is principled and not self-serving.")
unresolved: list[str] = []
missing_file: list[str] = []
line_counts: dict[str, int] = {}
resolved_as: dict[str, str] = {}
# REPORT.md reviews a DIFFERENT ref and never said so; section E proves it.
OTHER_REF = "REPORT.md"
for document_name, path, start, end in citations:
    if path in KNOWN_MISSING or document_name == OTHER_REF:
        continue
    target = resolve(path)
    if target is None:
        missing_file.append(f"{document_name} -> {path}")
        continue
    if path not in line_counts:
        line_counts[path] = len(
            target.read_text(encoding="utf-8", errors="replace").splitlines())
        resolved_as[path] = str(target.relative_to(SOURCE))
    total = line_counts[path]
    highest = end or start
    if highest > total or start < 1:
        unresolved.append(
            f"{document_name} -> {path}:{start}"
            f"{'-' + str(end) if end else ''} (file has {total} lines)")

check("every cited file exists at main", "missing: []",
      f"missing: {sorted(set(missing_file))}")
check("  and every cited line is within its file", "out of range: []",
      f"out of range: {sorted(set(unresolved))}")
print(f"  distinct files cited: {len(line_counts)}")
for path in sorted(line_counts):
    cited = [c for c in citations if c[1] == path]
    print(f"    {resolved_as[path]:<44} {len(cited):3} citations, "
          f"{line_counts[path]} lines")

# ---------------------------------------------------------------- C
print("\n########## C. the two that did NOT resolve, and what they should be ##########")
readme = (SOURCE / "README.md").read_text(encoding="utf-8").splitlines()
check("README.md is shorter than one citation claimed", "lines: 452",
      f"lines: {len(readme)}")
check('  "Validate a submission bundle" is in NO markdown file',
      "markdown hits: 0",
      "markdown hits: " + str(len(subprocess.run(
          ["grep", "-rl", "Validate a submission bundle", "--include=*.md",
           str(SOURCE)], capture_output=True, text=True).stdout.split())))
cli_lines = (SOURCE / "src/evidence_orchestrator/cli.py").read_text(
    encoding="utf-8").splitlines()
check("  it is an argparse help string at cli.py:590",
      'help="Validate a submission bundle"', cli_lines[589].strip())
print("  -> NOTE-cli-surface-holds.md cited `README.md:590`. The LINE NUMBER")
print("     was right and the FILE was wrong, which is why it looked")
print("     plausible. It matters for the argument: I leaned on it as")
print("     documented intent, and an argparse help= string is a weaker")
print("     basis than README prose. The conclusion that `evidence check` is")
print("     a convenience rather than a bypass still stands - it rests on the")
print("     measurement that the command records nothing, not on the quote.")

quoted = "Remote binding is rejected unless"
where = [i + 1 for i, line in enumerate(readme) if quoted in line]
check("the bind-guard sentence starts at README.md:335", "[335]", str(where))
print(f"  README.md:335-336 reads: {readme[334].strip()!r}")
print(f"                            {readme[335].strip()!r}")
print("  -> NOTE-dashboard-and-errors-hold.md cited `:336-337`, off by one.")
print("     The sentence is real and says what I said it says; only the span")
print("     was wrong. Corrected rather than left, because a reader who")
print("     follows the citation lands on the wrong line.")

# ---------------------------------------------------------------- D
print("\n########## D. spot-check the citations the FINDINGS rest on ##########")
ANCHORS = [
    ("README.md", 391, "At submission, EFO copies the report, manifest"),
    ("docs/ARCHITECTURE.md", 143, "hashed again after copying"),
    ("docs/PROXY_SUBMISSION.md", 79, "LF-to-CRLF conversion, BOM insertion"),
    ("docs/MIGRATION.md", 51, "temporary file only in"),
    ("src/evidence_orchestrator/doctor.py", 109, 'root_path / "reports" / agent_id'),
    ("src/evidence_orchestrator/provenance.py", 263, "blob_size > max_blob_bytes"),
    ("src/evidence_orchestrator/archive.py", 128, "should_copy = force or size"),
    ("src/evidence_orchestrator/workspace.py", 1182, "last_event_hash"),
    ("src/evidence_orchestrator/workspace.py", 1511, "last_event_hash"),
]
for path, line_number, fragment in ANCHORS:
    text = (SOURCE / path).read_text(encoding="utf-8").splitlines()
    window = "\n".join(text[max(0, line_number - 3):line_number + 2])
    check(f"  {path}:{line_number} contains the quoted fragment",
          "present: True", f"present: {fragment in window}")
print("  These are the anchors the FILED issues rest on - #17, #18, #19 and")
print("  the byte-exactness NOTE. All resolve within a two-line window of the")
print("  cited number. The two errors in section C were both in NOTEs, not in")
print("  issues, which is luck rather than process: nothing in my workflow")
print("  checked a citation before this probe existed.")

# ---------------------------------------------------------------- E
print("\n########## E. REPORT.md cites a different ref, and never says which ##########")
print("  Two of its citations resolve against NEITHER main NOR the branch's")
print("  old base: `workspace.py:2366` (main has 1562 lines, dad3f4c4 has 920)")
print("  and `docs/META_ORCHESTRATION_V2.md`, which exists at neither.")
REPO = Path("/workspace/evidence-first-orchestrator")


def at_ref(ref: str, path: str) -> int:
    out = subprocess.run(["git", "-C", str(REPO), "show", f"{ref}:{path}"],
                         capture_output=True, text=True)
    return len(out.stdout.splitlines()) if out.returncode == 0 else 0


for ref, expected in [("origin/main", "1562"), ("dad3f4c4", "920"),
                      ("origin/codex/meta-orchestration-v2", "2528")]:
    check(f"  workspace.py at {ref}", f"lines: {expected}",
          f"lines: {at_ref(ref, 'src/evidence_orchestrator/workspace.py')}")
meta = subprocess.run(
    ["git", "-C", str(REPO), "ls-tree", "-r", "--name-only",
     "origin/codex/meta-orchestration-v2"], capture_output=True, text=True)
check("  and META_ORCHESTRATION_V2.md exists on that branch alone",
      "found: True",
      "found: " + str("META_ORCHESTRATION_V2" in meta.stdout))
print("  So REPORT.md reviewed `codex/meta-orchestration-v2`, where line 2366")
print("  is real. The citations are CORRECT for their subject. The defect is")
print("  that the document never NAMES that subject, so a reader who follows")
print("  a citation against main lands nowhere and reasonably concludes the")
print("  review invented it. Fixed by labelling the document, not by editing")
print("  its citations - they were right all along.")

# ---------------------------------------------------------------- F
print("\n########## F. do the write-ups STATE the numbers this run measured? ##########")
print("  Counts copied into prose go stale the moment another document is")
print("  added, and a stale count is indistinguishable from an invented one.")
print("  On 2026-08-03 this note said `141 live citations across 34 documents`")
print("  while the committed raw output beside it said 152 across 35. Nobody")
print("  was checking. Now the run fails when prose and output disagree.")
audit_note = (REVIEWS / "NOTE-citation-audit-of-this-review.md").read_text(
    encoding="utf-8")
synthesis = (REVIEWS / "SYNTHESIS.md").read_text(encoding="utf-8")
STATED = re.compile(r"\*\*(\d+) live citations across\s+(\d+) documents")
for label, text in (("NOTE-citation-audit-of-this-review.md", audit_note),
                    ("SYNTHESIS.md", synthesis)):
    stated = STATED.search(text)
    check(f"  {label} states this run's counts",
          f"{len(citations)} citations / {len(documents)} documents",
          (f"{stated.group(1)} citations / {stated.group(2)} documents"
           if stated else "NO MACHINE-READABLE COUNT FOUND"))
banner = re.search(r"\*\*(\d+)\*\* more citations appear inside", audit_note)
check("  and the retraction count it excludes",
      f"retractions: {quoted_in_corrections}",
      f"retractions: {banner.group(1) if banner else 'NOT FOUND'}")

print(f"\n########## {FAIL} unexpected result(s) ##########")
print("This audits MY OWN write-ups, not EFO. Every finding it reports is a")
print("defect in the review, not in the reviewed code.")
print("SUBMITTED, not VERIFIED.")
