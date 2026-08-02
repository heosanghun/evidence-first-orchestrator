# One config key, two opposite behaviours: `max_evidence_bytes` is a copy threshold on the direct path and a hard ceiling on the proxy path

Reproduce with `raw/probe_blob_limit_and_lfs.py`; raw output in
`raw/raw-blob-limit-lfs.txt`. **12 checks, 0 unexpected.** Filed as issue #18.

The 50 MB default is exercised for real — no reduced stand-in limit — because
the question is whether the **documented number** behaves as documented.

## The documented claim

`README.md:391-394`:

> At submission, EFO copies the report, manifest, and evidence files up to
> 50 MB into `submissions/<task>/<attempt>/`. **Larger artifacts such as
> checkpoints stay external; their absolute path, byte size, and SHA-256 remain
> in the signed record.** The size limit is stored in the workspace
> configuration.

`docs/ARCHITECTURE.md:138-142` restates it: larger files *"remain external and
are bound by path"*. Both describe a **graceful degradation** — the artifact is
not copied, but the submission succeeds and the record still binds it.

## What actually happens

One key, `max_evidence_bytes`, is read by two callers:

| Caller | Line | Treats the limit as |
|---|---|---|
| `archive(...)` | `workspace.py:1227` → `archive.py:128` | a **copy threshold** — `should_copy = force or size <= max_artifact_bytes` |
| `validate_git_provenance(...)` | `workspace.py:1159` → `provenance.py:263` | a **hard ceiling** — `raise EvidenceError` |

Measured on the same 50 MB + 1 artifact:

```
DIRECT path:  ACCEPTED, state: submitted, left external: 1 (artifact=52428801B),
              still bound by sha256: True
PROXY path:   EvidenceError: Git source blob exceeds the proxy verification
              limit: deliverables/C1.artifact.bin (52428801 > 52428800)
```

**The documented sentence is true on the direct path and false on the proxy
path.** Nothing in `README.md` or `docs/*.md` mentions `max_blob_bytes`, or says
the proxy path differs — the words `max_blob_bytes` and `LFS` appear in no
Markdown file in the repository.

## Why it can bite

`PROXY_SUBMISSION.md` exists for the case where an author can publish Git but
cannot reach the workspace. An offline author delivering a >50 MB checkpoint —
the artifact class `README.md:392` names explicitly, *"larger artifacts such as
checkpoints"* — cannot submit at all. The submission is refused outright rather
than degrading to the documented external binding, and the refusal cites a
limit the documentation describes as a copy threshold.

The operator's recourse is invisible from the message: raise
`max_evidence_bytes` in the workspace configuration, which also silently raises
the archival copy threshold, changing how much every future submission copies
into `submissions/`. One number, two policies, one lever.

## The boundary itself is clean

| Blob | Result |
|---|---|
| exactly 52,428,800 bytes (at the limit) | **accepted** |
| 52,428,801 bytes (one over) | refused |

`blob_size > max_blob_bytes` is inclusive at the boundary and off-by-one clean.
The positive control confirms the shipped default is the documented 50 MB
(`52428800`) and that a small artifact submits by proxy.

## Suggested fix

Either make the proxy path degrade the way the direct path does — record path,
size and SHA-256 without reading the blob — or give the ceiling its own
configuration key and document it. The two behaviours are both defensible; what
is not defensible is one number meaning both, with only one of the two meanings
written down. If the hard ceiling is deliberate (reading a large blob into
memory to hash it is a real cost), a sentence in `PROXY_SUBMISSION.md` saying so
would close the gap on its own.

## The Git LFS guard — measured, and not filed

`provenance.py:288-291` rejects any blob starting with
`version https://git-lfs.github.com/spec/v1\n`. This is **undocumented
defence** — no Markdown file in the repository mentions LFS — so the bar is
"does it do something sensible", not "does it match a promise".

| Input | Result |
|---|---|
| a real LFS pointer | **refused** |
| the header with CRLF instead of LF | accepted |
| the header uppercased | accepted |
| the header on line 2 | accepted |
| a leading space before the header | accepted |
| prose whose first line quotes the pointer format | **refused** |

An exact-prefix match on the canonical first line. The four accepted near
misses are correct: none is a pointer Git would smudge, so a CRLF or uppercased
header really is just a file.

The last row is the guard's honest cost — a legitimate artifact whose first line
quotes the pointer format is refused. **Not filed**: nothing claims otherwise,
the false-positive class is narrow (the quote must be byte-exact *and* at offset
0), and refusing evidence is the safe direction for a check whose job is to stop
a 130-byte stub standing in for a checkpoint.

## Harness bug, disclosed

One, mine. `direct()` read `result["evidence"]["archive"]["files"]`; the real
shape is `result["archive"]["files"]`, with retention flagged as `retained`, not
`copied`. The submission had succeeded — I crashed reading its result — so the
first run reported `KeyError: 'evidence'` where the code was behaving correctly.
Only the corrected run is reported, and it now also measures the thing that
matters for the documented claim: the over-limit file is left external **and**
still carries its `sha256`.

## Scope

`max_evidence_bytes` at the real 50 MB boundary on both submission paths, the
`archive` / `provenance` divergence, and the LFS prefix guard with four near
misses. Not examined: `max_evidence_bytes` at other configured values (it is
hardcoded at `workspace.py:154` with no `initialize` parameter, and the config
is ledger-bound, so changing it in a fixture is not possible without forging the
ledger); and memory behaviour when hashing a blob at the ceiling.

**No network call was made.** Proxy submission never fetches, the remote is
`example.invalid`, and no LFS object was resolved. Pre-registered permissions
unchanged: `gpu: false`, `network: false`, `performance_metrics: false`; gates
`allow_skips: false`, `require_validation: true`,
`require_known_answer_check: true`, `require_independent_verification: true`.
No measured performance claim appears here — the byte counts are file sizes,
not timings.

**SUBMITTED, not VERIFIED.**

| Artifact | SHA-256 |
|---|---|
| `raw/probe_blob_limit_and_lfs.py` | `2039af7a3615d2c2fdfc0e759e6e3940a5bd3f441c5f265a86569b4c1eccdd59` |
| `raw/raw-blob-limit-lfs.txt` | `3bb14823416dc48ef414347482132bef56a2b1917216924c565c89b49e01a7c8` |
