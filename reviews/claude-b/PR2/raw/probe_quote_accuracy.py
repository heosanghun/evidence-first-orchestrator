#!/usr/bin/env python3
"""Do this review's quoted code blocks say what the cited lines actually say?

`NOTE-citation-audit-of-this-review.md` proved every citation RESOLVES to a
real line. It named the next gap in its own scope: a citation can resolve and
still misquote. This closes that gap for the subset where the question is
mechanically decidable, and says plainly why the rest is not.

WHY ONLY A SUBSET. A first attempt paired any backticked span with the nearest
citation on the same line and reported 16 "misses" out of 19. Fifteen were the
PAIRING being wrong, not the quote: these write-ups routinely put two or three
citations and several inline spans in one sentence, so position does not
determine which span belongs to which citation. Shipping that checker would
have produced a wall of false accusations against my own documents.

The decidable subset is: exactly ONE citation on a line, immediately followed
by a fenced block. There the block is unambiguously a quote of that location.

    python3 probe_quote_accuracy.py
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

FAIL = 0
SOURCE = Path("/tmp/efo-prov")
REVIEWS = Path("/workspace/evidence-first-orchestrator/reviews/claude-b/PR2")
ROOTS = ("", "src/evidence_orchestrator", "docs", "functions/api",
         "public/assets", "monitor", "tests", "web_tests")
CITATION = re.compile(
    r"`?([A-Za-z0-9_./-]+\.(?:py|md|js|mjs|toml|yml|json))`?:(\d+)(?:-(\d+))?")


def check(name: str, expected: str, observed: str) -> None:
    global FAIL
    ok = expected in observed
    if not ok:
        FAIL += 1
    print(f"  [{'ok' if ok else '!! UNEXPECTED !!'}] {name}")
    print(f"        expected: {expected}")
    print(f"        observed: {observed}")


def resolve(path: str) -> Path | None:
    for prefix in ROOTS:
        candidate = SOURCE / prefix / path if prefix else SOURCE / path
        if candidate.is_file():
            return candidate
    return None


def squeeze(text: str) -> str:
    """Whitespace-insensitive, so a re-indented quote still matches."""
    return re.sub(r"\s+", "", text)


# ---------------------------------------------------------------- A
print("########## A. POSITIVE CONTROL ##########")
head = subprocess.run(["git", "-C", str(SOURCE), "rev-parse", "HEAD"],
                      capture_output=True, text=True).stdout.strip()
dirty = subprocess.run(["git", "-C", str(SOURCE), "status", "--porcelain"],
                       capture_output=True, text=True).stdout.strip()
check("probe source is main 5694ab45",
      "5694ab455139f1e72d946bc2fe7e42c7c0c8a43a", head)
check("  with no working-tree modification", "dirty: ''", f"dirty: {dirty!r}")

# ---------------------------------------------------------------- B
print("\n########## B. citation + fenced block, the decidable subset ##########")
pairs: list[tuple[str, str, int, int, str]] = []
for document in sorted(REVIEWS.glob("*.md")):
    lines = document.read_text(encoding="utf-8").splitlines()
    for index, line in enumerate(lines):
        if line.lstrip().startswith(">"):
            continue                      # a dated correction banner
        matches = list(CITATION.finditer(line))
        if len(matches) != 1:
            continue                      # ambiguous pairing - see the docstring
        cursor = index + 1
        while cursor < len(lines) and not lines[cursor].strip():
            cursor += 1
        if cursor >= len(lines) or not lines[cursor].lstrip().startswith("```"):
            continue
        block: list[str] = []
        cursor += 1
        while cursor < len(lines) and not lines[cursor].lstrip().startswith("```"):
            block.append(lines[cursor])
            cursor += 1
        candidates = [text.strip() for text in block if len(text.strip()) > 12]
        if not candidates:
            continue
        match = matches[0]
        start = int(match.group(2))
        end = int(match.group(3)) if match.group(3) else start
        pairs.append((document.name, match.group(1), start, end,
                      max(candidates, key=len)))

verified: list[tuple[str, str, int, str]] = []
unmatched: list[tuple[str, str, int, str]] = []
for document_name, path, start, end, quote in pairs:
    target = resolve(path)
    if target is None:
        continue
    source_lines = target.read_text(encoding="utf-8",
                                    errors="replace").splitlines()
    # The window must span the WHOLE cited range. A first version used the
    # start line only and flagged a correct quote whose text sat at :904 for a
    # citation reading `:893-912` - the checker was wrong, not the document.
    low = max(0, start - 8)
    high = min(len(source_lines), end + 10)
    window = squeeze("\n".join(source_lines[low:high]))
    (verified if squeeze(quote) in window else unmatched).append(
        (document_name, path, start, quote))

check("every decidable pair was examined", f"pairs: {len(pairs)}",
      f"pairs: {len(verified) + len(unmatched)}")
print(f"  verbatim-verified: {len(verified)}   not matched: {len(unmatched)}")

# document -> why the block is not a verbatim quote of the cited line
ADJUDICATED = {
    ("NOTE-implicit-exceptions-package-wide.md", "provenance.py"):
        "extractor artifact - the citation is INSIDE a fenced listing, so the "
        "following PROSE paragraph was captured as the block",
    ("NOTE-proxy-grant-holds.md", "workspace.py"):
        "extractor artifact - same shape, citation inside a fenced listing",
    ("NOTE-collector-redaction-holds.md", "collector.py"):
        "the block is PROBE OUTPUT, presented as output; it is not a source "
        "quote and does not claim to be",
    ("NOTE-remaining-docs-adjudicated.md", "src/evidence_orchestrator/adapter.py"):
        "PROBE OUTPUT again - the block is this review's own census line "
        "`adapter.py:180  shell=False`, not a quote of the source at :180. "
        "Caught by this check on the very round the note was written, which "
        "is the self-check working as intended",
    ("NOTE-class-2b-is-a-census-now-seven-of-seven.md", "test_independence.py"):
        "PROBE OUTPUT - the block is this census's own listing of the three "
        "attest_agent_identity call sites with the role of each agent, not a "
        "quote of any one line of the test file",
    ("NOTE-class-2b-is-a-census-now-seven-of-seven.md", "helpers.py"):
        "PROBE OUTPUT - `helpers.py:87 expected=4 observed=4 if "
        "known_answer_passed else 5` is the census line, which renders the "
        "dict's two values on one line; the source spells them across four",
    ("ADDENDUM-git-replace-regression.md", "provenance.py"):
        "deliberate before/after - the block quotes the argument list that "
        "was REMOVED, which is the whole point of the regression",
}
# monitor/collector.py:893-912 is NOT here: it was a probe bug, now fixed.
for document_name, path, line_number, quote in unmatched:
    key = (document_name, path)
    verdict = ADJUDICATED.get(key, "?")
    marker = "!!" if verdict == "?" else "  "
    print(f"  {marker}{document_name}  ->  {path}:{line_number}")
    print(f"        {verdict}")
uncovered = [f"{d} -> {p}" for d, p, _, _ in unmatched
             if (d, p) not in ADJUDICATED]
check("every unmatched block is adjudicated", "uncovered: []",
      f"uncovered: {uncovered}")

# ---------------------------------------------------------------- C
print("\n########## C. two blocks WERE condensed, and are now verbatim ##########")
print("  Before this probe, two fenced blocks read as verbatim source but were")
print("  reflowed renderings - accurate in substance, not literally present:")
print("    ADDENDUM-git-replace-regression.md  provenance.py:33-42")
print("      quoted a 9-line argument list collapsed onto one line, with")
print("      `repo`/`args` where the source says `repository`/`arguments`")
print("    ADDENDUM-proxy-status-freshness.md  monitor/collector.py:893-912")
print("      quoted a parenthesised multi-line `elif` flattened to one line")
print("  Neither changed what the finding says. Both are now the verbatim")
print("  source, which is why they no longer appear in section B's unmatched")
print("  list. That is the fix: make the document literal, not the checker")
print("  lenient. Whitespace normalisation was tried FIRST and did not resolve")
print("  them - the difference was tokens, not indentation.")
git_replace = (REVIEWS / "ADDENDUM-git-replace-regression.md").read_text(
    encoding="utf-8")
check("  the git-replace block is now verbatim", '            "-c",',
      git_replace)
freshness = (REVIEWS / "ADDENDUM-proxy-status-freshness.md").read_text(
    encoding="utf-8")
check("  and the collector block keeps its parenthesis",
      "and external_phase in PORTFOLIO_EXTERNAL_ACTIVE_PHASES", freshness)

# ---------------------------------------------------------------- D
print("\n########## D. what stays UNDECIDABLE, with a count ##########")
inline = 0
for document in sorted(REVIEWS.glob("*.md")):
    for line in document.read_text(encoding="utf-8").splitlines():
        if line.lstrip().startswith(">"):
            continue
        if len(CITATION.findall(line)) >= 1:
            inline += len(re.findall(r"`[^`\n]{6,}`", line))
print(f"  inline backticked spans sharing a line with a citation: {inline}")
print("  These are NOT checked. A sentence like \"`doctor.py:109` interpolates")
print("  `agent_id` into a path\" contains a citation and a span that is a")
print("  quote, and a sentence like \"`workspace.py:1182` reads it by direct")
print("  index\" contains a citation and a span that is not. Position does not")
print("  distinguish them, and guessing produced a 15-in-19 false-positive")
print("  rate on the first attempt. Named as a gap rather than papered over.")

# ---------------------------------------------------------------- E
print("\n########## E. does the write-up STATE the numbers this run measured? ##########")
print("  On 2026-08-03 NOTE-quote-accuracy.md read `Eleven such pairs exist`")
print("  and `194 inline backticked spans` while the committed raw output")
print("  beside it said 12 pairs and 215 spans. The table (7 verbatim, 5")
print("  adjudicated) had been refreshed and the prose had not. Both were true")
print("  when written; neither was true when read. A count that drifts")
print("  silently is indistinguishable from one that was never measured, so")
print("  the run now fails when prose and output disagree.")
note = (REVIEWS / "NOTE-quote-accuracy.md").read_text(encoding="utf-8")
STATED_PAIRS = re.compile(r"\*\*(\d+)\*\* such pairs exist")
STATED_VERBATIM = re.compile(r"verbatim-verified against the cited range \| (\d+)")
STATED_ADJUDICATED = re.compile(r"adjudicated non-quotes \| (\d+)")
STATED_INLINE = re.compile(r"\*\*(\d+) inline backticked spans")
for label, pattern, measured in (
        ("pairs", STATED_PAIRS, len(pairs)),
        ("verbatim-verified", STATED_VERBATIM, len(verified)),
        ("adjudicated non-quotes", STATED_ADJUDICATED, len(unmatched)),
        ("inline spans", STATED_INLINE, inline)):
    found = pattern.search(note)
    check(f"  the note states this run's {label}", f"{label}: {measured}",
          f"{label}: {found.group(1) if found else 'NO MACHINE-READABLE COUNT'}")
for label in ("NOTE-citation-audit-of-this-review.md", "SYNTHESIS.md"):
    text = (REVIEWS / label).read_text(encoding="utf-8")
    found = re.search(r"(\d+) inline spans remain undecidable", text)
    check(f"  {label} cross-reference agrees", f"inline: {inline}",
          f"inline: {found.group(1) if found else 'NOT FOUND'}")

print(f"\n########## {FAIL} unexpected result(s) ##########")
print("This audits MY OWN write-ups, not EFO. Static analysis only; nothing")
print("was executed against a workspace. Pre-registered permissions unchanged")
print("- gpu/network/performance_metrics all false.")
print("SUBMITTED, not VERIFIED.")
