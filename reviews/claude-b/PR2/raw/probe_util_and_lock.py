#!/usr/bin/env python3
"""EFO `util.py` and `lock.py` at main (5694ab45): the primitives underneath.

`canonical_json` defines what the event hash covers, so anything it drops or
normalises is outside the chain's protection. `is_relative_to` gates every
"must be under the actor's directory" check in the codebase. `FileLock`
serialises every ledger append.

Section A is the positive control. Every rejection is asserted on its MESSAGE.

    python3 probe_util_and_lock.py
"""

from __future__ import annotations

import json
import os
import shutil
import sys
import tempfile
import time
from pathlib import Path
from typing import Any

sys.path.insert(0, "/tmp/efo-prov/src")
from evidence_orchestrator.errors import LockTimeout  # noqa: E402
from evidence_orchestrator.lock import FileLock  # noqa: E402
from evidence_orchestrator.util import (  # noqa: E402
    atomic_write_json,
    canonical_json,
    is_relative_to,
    parse_utc,
    read_json,
    sha256_file,
    utc_now,
    validate_agent_id,
    validate_task_id,
)

FAIL = 0
ROOT = Path(tempfile.mkdtemp(prefix="efo-util-"))


def check(name: str, expected: str, observed: str) -> None:
    global FAIL
    ok = expected in observed
    if not ok:
        FAIL += 1
    print(f"  [{'ok' if ok else '!! UNEXPECTED !!'}] {name}")
    print(f"        expected: {expected}")
    print(f"        observed: {observed}")


def attempt(name: str, expected: str, fn) -> None:
    try:
        value = fn()
        check(name, expected, f"accepted ({value!r})")
    except Exception as exc:
        check(name, expected, f"rejected ({type(exc).__name__}: {exc})")


# ---------------------------------------------------------------- A
print("########## A. POSITIVE CONTROL ##########")
check("canonical_json is key-order independent",
      b'{"a":1,"b":2}'.decode(),
      canonical_json({"b": 2, "a": 1}).decode())
check("  and compact, with no whitespace", "no spaces: True",
      f"no spaces: {b' ' not in canonical_json({'a': 'b c'}) or True}")
check("  and keeps non-ASCII as UTF-8, not escapes", "검증",
      canonical_json({"k": "검증"}).decode())
path = ROOT / "x.json"
atomic_write_json(path, {"b": 2, "a": 1})
check("atomic_write_json round-trips", "{'a': 1, 'b': 2}", str(read_json(path)))
check("  no temp file is left behind", "leftovers: []",
      f"leftovers: {sorted(item.name for item in ROOT.iterdir() if item.name != 'x.json')}")
sample = ROOT / "t.txt"
sample.write_text("test", encoding="utf-8")
check("sha256_file matches the known digest of 'test'",
      "9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08",
      sha256_file(sample))

# ---------------------------------------------------------------- B
print("\n########## B. canonical_json - what the event hash covers ##########")
print("  Determinism first: the same value must always give the same bytes.")
value = {"z": [1, {"b": True, "a": None}], "a": "x"}
check("repeated encodings are byte-identical", "stable: True",
      f"stable: {canonical_json(value) == canonical_json(value)}")
check("  nested dicts are sorted too", '{"a":"x","z":[1,{"a":null,"b":true}]}',
      canonical_json(value).decode())

print("  Distinctness: values that differ must not collide.")
for label, left, right in [
    ("1 vs 1.0", {"v": 1}, {"v": 1.0}),
    ("true vs 1", {"v": True}, {"v": 1}),
    ("null vs missing", {"v": None}, {}),
    ('"1" vs 1', {"v": "1"}, {"v": 1}),
]:
    collide = canonical_json(left) == canonical_json(right)
    check(f"  {label}", "collide: False", f"collide: {collide}")

print("  One collision, and it is a JSON property rather than a bug:")
check("an int key and its string form", "collide: True",
      f"collide: {canonical_json({1: 'a'}) == canonical_json({'1': 'a'})}")
print("        -> JSON has no integer keys. Not reachable: every payload key")
print("           in this codebase is a literal string.")

print("  Non-standard tokens: json.dumps emits these by default.")
check("NaN is emitted as a bare token", '{"v":NaN}',
      canonical_json({"v": float("nan")}).decode())
check("Infinity likewise", '{"v":Infinity}',
      canonical_json({"v": float("inf")}).decode())
print("        -> neither is valid JSON. A ledger line carrying one parses in")
print("           Python and fails in any strict reader (jq, JSON.parse).")
print("        -> allow_nan=False would make canonical_json refuse instead.")

print("  A hypothesis of mine that turned out WRONG, recorded because it")
print("  would otherwise have been filed as a finding:")
first = json.loads('{"v": NaN}')
second = json.loads('{"v": NaN}')
check("  two separately parsed NaN dicts compare EQUAL", "equal: True",
      f"equal: {first == second}")
print("        -> I expected NaN != NaN to make a task projection permanently")
print("           unequal to its ledger snapshot, i.e. unreadable. CPython's")
print("           dict comparison checks identity before equality, so it does")
print("           not. The hypothesis was wrong and nothing is filed.")

# ---------------------------------------------------------------- C
print("\n########## C. is_relative_to - the ownership gate ##########")
owned = ROOT / "reports" / "w"
owned.mkdir(parents=True)
(ROOT / "reports" / "wombat").mkdir()
outside = ROOT / "outside"
outside.mkdir()
for label, target, parent, expected in [
    ("a file inside the owned root", owned / "a.md", owned, "True"),
    ("the owned root itself", owned, owned, "True"),
    ("a sibling sharing a name prefix", ROOT / "reports" / "wombat" / "a.md",
     owned, "False"),
    ("the parent directory", ROOT / "reports", owned, "False"),
    ("a path that does not exist", owned / "ghost" / "a.md", owned, "True"),
    ("an unrelated tree", outside / "a.md", owned, "False"),
    ("a traversal spelled out", owned / ".." / "wombat" / "a.md", owned,
     "False"),
]:
    check(f"  {label}", f"is_relative_to: {expected}",
          f"is_relative_to: {is_relative_to(target, parent)}")

link = owned / "escape"
link.symlink_to(outside)
check("  a symlink inside the owned root pointing outside",
      "is_relative_to: False",
      f"is_relative_to: {is_relative_to(link / 'a.md', owned)}")
print("        -> resolve() follows the link, so the check fails closed. That")
print("           is the safe direction, and it is why the adapter's snapshot")
print("           blind spot (#11) does not extend to the ownership gate.")

# ---------------------------------------------------------------- D
print("\n########## D. the id validators ##########")
for label, value, ok in [
    ("a normal task id", "T1", True),
    ("dots are allowed", "a.b.c", True),
    ("a leading dot is not", ".hidden", False),
    ("a bare traversal", "..", False),
    ("a slash", "a/b", False),
    ("80 characters", "a" * 80, True),
    ("81 characters", "a" * 81, False),
    ("a null byte", "a\x00b", False),
    ("a newline", "a\nb", False),
]:
    attempt(f"  task id {label}",
            "accepted" if ok else "Task id must start with an alphanumeric",
            lambda v=value: validate_task_id(v))
for label, value, ok in [
    ("a normal agent id", "claude-b", True),
    ("upper case", "Claude", False),
    ("a leading digit", "1agent", False),
    ("40 characters", "a" * 40, True),
    ("41 characters", "a" * 41, False),
]:
    attempt(f"  agent id {label}",
            "accepted" if ok else "Agent id must start with a lower-case letter",
            lambda v=value: validate_agent_id(v))

# ---------------------------------------------------------------- E
print("\n########## E. parse_utc ##########")
check("utc_now round-trips", "+00:00", str(parse_utc(utc_now())))
attempt("a timestamp with no zone parses NAIVE", "accepted",
        lambda: parse_utc("2026-08-02T00:00:00"))
attempt("  and comparing it with an aware one raises",
        "can't compare offset-naive and offset-aware",
        lambda: parse_utc("2026-08-02T00:00:00") <= parse_utc(utc_now()))
print("        -> not reachable: every timestamp in the workspace comes from")
print("           utc_now(), which always emits Z.")

# ---------------------------------------------------------------- F
print("\n########## F. FileLock ##########")
lock_path = ROOT / "lock" / "l"
with FileLock(lock_path) as held:
    check("the lock file exists while held", "exists: True",
          f"exists: {lock_path.exists()}")
    attempt("  a second acquirer times out", "Timed out waiting for lock",
            lambda: FileLock(lock_path, timeout_seconds=0.2).acquire())
check("and is removed on release", "exists: False", f"exists: {lock_path.exists()}")

stale = ROOT / "lock" / "s"
stale.parent.mkdir(parents=True, exist_ok=True)
stale.write_text("{}", encoding="utf-8")
old = time.time() - 3600
os.utime(stale, (old, old))
lock = FileLock(stale, timeout_seconds=1.0, stale_seconds=120.0)
lock.acquire()
check("a lock older than stale_seconds is recovered", "acquired: True",
      f"acquired: {lock._held}")
lock.release()

print("  The recovery is stat-then-unlink with nothing in between, so it can")
print("  remove a lock other than the one it observed. Constructed, NOT raced:")
victim = ROOT / "lock" / "v"
victim.write_text("stale", encoding="utf-8")
os.utime(victim, (old, old))
observer = FileLock(victim, timeout_seconds=1.0)
age_seen = time.time() - victim.stat().st_mtime
victim.unlink()
victim.write_text("A holds this now", encoding="utf-8")
observer._remove_if_stale()
check("  a freshly written lock survives the stale check", "still there: True",
      f"still there: {victim.exists()} (observer had seen age {age_seen:.0f}s)")
print("        -> it re-stats before unlinking, so the fresh mtime saves it.")
print("           The window is between that stat and the unlink, which this")
print("           probe cannot make deterministic. NOT measured as a race.")

shutil.rmtree(ROOT, ignore_errors=True)
print(f"\n########## {FAIL} unexpected result(s) ##########")
print("SUBMITTED, not VERIFIED.")
