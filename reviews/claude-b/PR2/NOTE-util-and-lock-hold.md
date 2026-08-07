# `util.py` and `lock.py` at `main` `5694ab45` — the primitives hold; no issue filed

Reproduce with `raw/probe_util_and_lock.py`; raw output in
`raw/raw-util-and-lock.txt`. **46 checks, 0 unexpected.**

These are the functions everything else stands on. `canonical_json` defines
what the event hash covers, so anything it drops or normalises is outside the
chain's protection. `is_relative_to` gates every *"must be under the actor's
directory"* check in the codebase. `FileLock` serialises every ledger append.

## `canonical_json`

Determinism and distinctness both hold:

```
key order independent          {"b":2,"a":1} -> {"a":1,"b":2}
nested dicts sorted too        {"a":"x","z":[1,{"a":null,"b":true}]}
non-ASCII kept as UTF-8        {"k":"검증"}   (not \uXXXX escapes)
repeated encodings identical   stable: True
```

| Pair | Collide? |
|---|---|
| `1` vs `1.0` | no |
| `true` vs `1` | no |
| `null` vs the key being absent | no |
| `"1"` vs `1` | no |

**One collision**, and it is a property of JSON rather than a bug: an integer
key and its string form encode identically (`{1:'a'}` and `{'1':'a'}`). JSON has
no integer keys, and every payload key in this codebase is a literal string, so
it is not reachable.

**One portability note.** `json.dumps` emits non-standard tokens by default:

```
canonical_json({"v": float("nan")})  ->  {"v":NaN}
canonical_json({"v": float("inf")})  ->  {"v":Infinity}
```

Neither is valid JSON. A ledger line carrying one parses in Python and fails in
any strict reader — `jq`, `JSON.parse`, most non-Python tooling. `allow_nan=False`
would make `canonical_json` refuse at write time instead. Recorded rather than
filed: nothing in the API produces a non-finite number, and the hash chain
itself stays self-consistent either way.

### A hypothesis of mine that was wrong

I expected the `NaN` path to be a real finding: `NaN != NaN`, so a task
projection containing one should never equal its own ledger snapshot, making
the task permanently unreadable through `get_task`. Measured:

```
two separately parsed NaN dicts compare EQUAL -> True
```

CPython's dict comparison checks identity before equality, so the two `NaN`
values compare equal inside the dict and the projection check passes. The
hypothesis was wrong, nothing is filed, and it is written down here because it
is exactly the shape that becomes a false finding if you stop at the first
plausible step.

## `is_relative_to`

| Probe | Observed |
|---|---|
| a file inside the owned root | `True` |
| the owned root itself | `True` |
| **a sibling sharing a name prefix** (`reports/wombat` vs `reports/w`) | `False` |
| the parent directory | `False` |
| a path that does not exist yet | `True` |
| an unrelated tree | `False` |
| a traversal spelled out (`owned/../wombat/a.md`) | `False` |
| **a symlink inside the owned root pointing outside** | `False` |

The sibling-prefix row is the one a string comparison would get wrong, and
`relative_to` gets it right. The symlink row matters more: `resolve()` follows
the link, so the gate **fails closed**. That is why the adapter's snapshot blind
spot (issue #11, where a write through such a symlink is not reported) does not
extend to the ownership gate — the two use different machinery, and the one that
authorises is the strict one.

## The id validators

Task ids: dots allowed, a leading dot refused, `..` refused, `/` refused, 80
accepted, 81 refused, a null byte and a newline both refused. Agent ids:
lower-case only, no leading digit, 40 accepted, 41 refused. `fullmatch` with an
anchored pattern, so no embedded-newline bypass.

## `parse_utc`

`utc_now()` round-trips. A timestamp with no zone parses **naive**, and
comparing it with an aware one raises
`TypeError: can't compare offset-naive and offset-aware datetimes`. Not
reachable — every timestamp in the workspace comes from `utc_now()`, which
always emits `Z` — and it fails loudly rather than silently, which is the right
direction for a lease-expiry comparison.

## `FileLock`

`O_CREAT | O_EXCL` acquisition, a second acquirer times out with
`LockTimeout: Timed out waiting for lock …`, release removes the file, and a
lock older than `stale_seconds` is recovered.

The stale recovery is a stat followed by an unlink. Constructed — an observer
that saw a 3600-second-old lock, then the file replaced by a fresh one before
it unlinks:

```
a freshly written lock survives the stale check -> still there: True
   (observer had seen age 3600s)
```

It re-stats inside `_remove_if_stale` before unlinking, so the fresh mtime saves
it. The remaining window is between that stat and the unlink. **This probe could
not make that window deterministic, so no race is measured or claimed here** —
the constructed case is reported for what it is, and the real interleaving is
left open. `tests/test_concurrency.py` exists in the project and was not
re-run as part of this pass.

## Scope

`canonical_json`, `read_json`, `atomic_write_json`, `sha256_file`, `utc_now`,
`parse_utc`, `validate_task_id`, `validate_agent_id`, `is_relative_to`, and
`FileLock`. Not examined: `atomic_write_json`'s behaviour on a full disk, and
`FileLock` under real concurrent load.

Pre-registered permissions unchanged: `gpu: false`, `network: false`,
`performance_metrics: false`; gates `allow_skips: false`,
`require_validation: true`, `require_known_answer_check: true`,
`require_independent_verification: true`.

**SUBMITTED, not VERIFIED.**

| Artifact | SHA-256 |
|---|---|
| `raw/probe_util_and_lock.py` | `e458c3a25db7d94bac3c4a57f59489554ba5d3122689209038e25a5337e5bee7` |
| `raw/raw-util-and-lock.txt` | `03a104471a6ec5f18cd3c97421e8dc7f49a3eeb07e2593e4be9f4c0ff89c8dfb` |
