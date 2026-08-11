# The remaining Git provenance attacks at `main` `5694ab45`

Issue #4 covered one of the six attacks I said did not transfer to the rewritten
`provenance.py`. This closes the other five, plus the two configuration probes.
Four of the five hold. One does not.

Every scenario runs against the same fixture and is preceded by a positive
control, so a rejection cannot be mistaken for a different gate firing.
`raw/attack_prov5_main.py` is self-contained and rerunnable.

| # | Attack | Verdict at `5694ab45` |
|---|---|---|
| G-BASE | honest submission, both claim-bearing files bound | **accepted** — control |
| G1 | declare somebody else's `remote_url` | rejected — `Git remote mismatch` |
| G2 | commit that was never pushed, tracking ref present | rejected — `merge-base --is-ancestor` fails |
| **G2b** | **same, with `refs/remotes/origin/main` deleted** | **accepted, `byte_exact: true`** |
| G3 | bind one file, hide the other claim-bearing one | rejected — `does not bind every claim-bearing evidence file` |
| G4 | bind the same `submitted_path` twice | rejected — `Duplicate submitted_path` |
| G5 | CRLF-mutate the bytes and re-stamp the manifest sha | rejected — `Git blob bytes differ from submitted evidence` |
| G6 | honest bytes with repo-local `core.autocrlf=true` | accepted — an honest delivery still succeeds |
| G7 | `url.insteadOf` rewriting the remote | declaring the pre-rewrite URL is rejected; declaring the rewritten URL is accepted **and recorded**, so this is not a bypass |

G5 is worth naming explicitly: `GIT_CONFIG_GLOBAL`/`_SYSTEM` are pinned to
`os.devnull`, but the manifest sha was re-stamped so only the raw-byte
comparison could catch it, and it did.

## Finding — a never-pushed commit is accepted when the tracking ref is absent

`validate_git_provenance` resolves the branch from an ordered candidate list
(`provenance.py:193-208`):

```python
candidates = [
    f"refs/remotes/{remote_name}/{branch}",
    f"refs/heads/{branch}",
]
```

Whoever prepares the source repository also decides whether the first candidate
exists. `git update-ref -d refs/remotes/origin/main` is one command, and the
ancestry check then runs against the local branch, which of course contains the
local commit.

Measured, `raw/probe_local_only_record.py`:

```
origin.git tip     : a85f6da26734
declared commit    : 3e8c90171385 (exists only in the work clone)

ACCEPTED record fields an auditor would read:
   remote_url     = /tmp/prov5b/origin.git
   branch         = main
   resolved_ref   = refs/heads/main
   ref_tip        = 3e8c90171385ab84d6b5aa20c6daa1e89dd0e375
   commit         = 3e8c90171385ab84d6b5aa20c6daa1e89dd0e375
   byte_exact     = True

is the declared commit fetchable from the declared remote?
   git --git-dir origin.git cat-file -e <commit> -> ABSENT (exit 1)
```

The record asserts `remote_url` and `byte_exact: true` for a commit that is not
on that remote at all. The property the whole manifest exists to give — *go to
this remote, fetch this commit, re-check the bytes yourself* — does not hold for
the accepted record.

**This is disclosed, not hidden.** `resolved_ref` reads `refs/heads/main` rather
than `refs/remotes/origin/main`, so an auditor who knows to compare those two
strings can tell. Nothing rejects it, flags it, or counts it, and no test covers
it — which is the same shape as issue #3: the affirmative record is what gets
trusted.

### Suggested fix

Drop the fallback, or make it explicit rather than silent. Either
(a) require `refs/remotes/{remote_name}/{branch}` and fail with "no
remote-tracking ref for the declared remote; fetch it first" when absent, or
(b) keep the fallback but record `remote_verified: false` and refuse it under
`require_independent_verification`. A verifier that intends to re-fetch anyway
would prefer (a).

### Minor, same area

When `merge-base --is-ancestor` legitimately rejects (G2), git exits 1 with an
empty stderr, so the surfaced error is
`Git provenance command failed (merge-base --is-ancestor <sha> <ref>): ` with a
blank reason. The correct rejection is unreadable to whoever has to act on it.

## Scope and boundary

All six provenance attacks and both configuration probes have now been run
against `main`'s rewritten file; the earlier "all rejected" result from the PR #2
pass no longer needs to carry any weight either way. Still unexamined:
`alias_of` / `alias_chain` / `shared_alias_lineage` in `independence.py`, and the
transport-attested progress / proxy-status / monitor-collector code.

Pre-registered permissions were unchanged: `gpu: false`, `network: false`,
`performance_metrics: false`; gates `allow_skips: false`,
`require_validation: true`, `require_known_answer_check: true`,
`require_independent_verification: true`. No performance claim is made.

**SUBMITTED, not VERIFIED.**

## Evidence

| Artifact | SHA-256 |
|---|---|
| `raw/attack_prov5_main.py` | `a2550696a104f71b620f15a695d2323aa34b80a6cc4532afa597f050552b3fd4` |
| `raw/raw-attack-prov5-main.txt` | `1a0613d7a26f2ceccd4b5a5ad4bd8ae3a5acb39c7a2d117382736f3670fb7d7f` |
| `raw/probe_local_only_record.py` | `f4840f6ebb78a875d04837cf198003d25c1925444e65674804457991ff3ee15e` |
| `raw/raw-local-only-record.txt` | `2066e088f53a05a95cd00baff70e97194579161e1f6641cddc732a157cfc1abb` |
