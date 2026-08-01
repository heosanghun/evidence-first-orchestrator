# P2-5 → P1-2 — `git replace` forges byte-exact provenance on `main`

Checked at `main` = `5694ab45`. This closes the gap I named in issue #3 and in
`ADDENDUM-proxy-submission.md`: *"`provenance.py` here is 341 lines against the
193 I reviewed, so the six Git provenance attacks were not re-run and their
earlier 'all rejected' result does not transfer."* It does not transfer. One of
the six now succeeds.

**Finding: `_run_git` lost `--no-replace-objects`, and a `refs/replace/*` object
makes `validate_git_provenance` return `byte_exact: True` for content that is
not in the declared commit.**

At `cef5623` the git invocation was
(`provenance.py:47`):

```python
["git", "--no-replace-objects", "-C", str(repo), *args]
```

On `main` it is (`provenance.py:33-42`) — the flag is gone:

```python
["git", "-c", f"safe.directory={repository}", "-C", str(repository), *arguments]
```

`GIT_CONFIG_GLOBAL` / `GIT_CONFIG_SYSTEM` are pinned to `os.devnull`, which
neutralises global `insteadOf` and `core.autocrlf`. Replace refs are not
configuration — they live in the repository as `refs/replace/*`, so that
hardening does not reach them.

## Reproduction — measured, `raw/attack_prov_main.sh`

| Step | Observed at `5694ab45` |
|---|---|
| P1 honest submission, bytes match the commit | **ACCEPTED** (positive control) |
| P2 tampered bytes, no replace object | **rejected** — `Git blob bytes differ from submitted evidence` |
| P3 **same** tampered bytes + `git replace C C'` | **ACCEPTED, `byte_exact: True`** |

At P3 the two views of the same commit disagree, in the same working tree:

```
git cat-file blob C:report.txt      = FORGED: 4 passed, 0 failed
with --no-replace-objects           = HONEST: 3 passed, 1 failed
origin.git holds                    = HONEST: 3 passed, 1 failed
declared commit                     = c9acd5456752b1494d0412379726c53a43e230c4
```

The returned record also carries `blob_oid = 08b42cd8…`, which is not the blob
in `c9acd54`'s real tree (`698b6494…`). So the record is not merely permissive:
it asserts a binding that the repository it names does not contain.

## A/B against `cef5623`, same repository state, same replace ref

| Runner | Verdict |
|---|---|
| `cef5623` `verify_git_delivery`, forged + replace | **rejected** — `expected 045aa3ee…` (the honest blob; git ignored the replacement) |
| `cef5623` `verify_git_delivery`, honest bytes | **ACCEPTED** — control, so the rejection above is the byte check and not a different gate |
| `main` `validate_git_provenance`, forged + replace | **ACCEPTED**, `byte_exact: True` |

This is a regression, not a pre-existing gap I previously mis-measured.

Two harness bugs of mine were caught before any conclusion was drawn, and only
the corrected runs are reported:

1. The first `cef5623` call passed `source_ref="main"` and failed on
   `source_ref must be a full refs/heads/<branch> reference` — a different gate
   than the one under test. Corrected to `refs/heads/main`, and the honest
   control was added so a rejection cannot be mistaken for the wrong gate again.
2. The first suite run used `unittest discover -s tests` without `-t .` and
   produced `37 tests, 7 errors`, all `ImportError: attempted relative import`.
   That was my invocation, not the suite.

## Suggested fix

Restore the flag, or set `GIT_NO_REPLACE_OBJECTS=1` in the `_run_git`
environment alongside the two `GIT_CONFIG_*` pins. A verifier that also wants to
say so out loud can assert `git for-each-ref refs/replace/` is empty for the
source repository and refuse otherwise, but the flag alone closes this.

## Scope and boundary

Only the replace attack was re-run against the rewritten file. The other five
provenance attacks from ③ (wrong remote, local-only commit, partial file
submission, duplicate binding, CRLF re-stamp) were **not** re-run here and their
earlier "all rejected" result still does not transfer to `main`. The
`alias_of` / `alias_chain` / `shared_alias_lineage` machinery remains
unexamined.

Suite at `5694ab45`: **93 tests, OK, 0 skipped, exit 0** — measured,
`raw/raw-prov-main-suite.txt`. No test in `tests/` exercises `refs/replace/*`.

Pre-registered permissions were unchanged throughout: `gpu: false`,
`network: false`, `performance_metrics: false`; gates `allow_skips: false`,
`require_validation: true`, `require_known_answer_check: true`,
`require_independent_verification: true`. No performance claim is made here.

**SUBMITTED, not VERIFIED.** `raw/attack_prov_main.sh` is self-contained and
rerunnable; it creates and destroys `/tmp/prov-attack` and needs only a worktree
of `main` at `/tmp/efo-prov` and of `cef5623` at `/tmp/efo-cef5623`.

## Evidence

| Artifact | SHA-256 |
|---|---|
| `raw/attack_prov_main.sh` | `1f3ca96146e562ef00bf3c109fd89e8b548171072616aa4ff3bbace22e0d8547` |
| `raw/raw-attack-prov-main.txt` | `36f39bbf1e34f36b73888a299069376f3f48672f6a38961af831efc4625a8cd7` |
| `raw/raw-prov-main-suite.txt` | `ba9b8b2c3e84d154cf31d14655d1b5d1f5b827fd8a03c7146006a320c076a758` |
