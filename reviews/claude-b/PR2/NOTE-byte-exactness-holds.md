# Proxy submission's byte-exactness claim holds at `main` `5694ab45` — every documented mutation is a hard failure; no issue filed

Reproduce with `raw/probe_byte_exactness.py`; raw output in
`raw/raw-byte-exactness.txt`. **20 checks, 0 unexpected.**

`NOTE-proxy-grant-holds.md` measured the *grant* gates — replay, expiry, cross
workspace, state ordering. It did not measure the bytes. This does.

## The claim, and which paragraph each half sits in

`docs/PROXY_SUBMISSION.md:78-82`:

> The blob comparison intentionally happens before any checkout conversion.
> LF-to-CRLF conversion, BOM insertion, encoding conversion, or any other byte
> mutation is a hard failure even when rendered text looks identical.

`docs/MIGRATION.md:141-143` states the same rule more loosely — *"Its
claim-bearing files must be byte-identical to raw Git blobs. Do not copy them
through a text-mode tool."* The narrow document governs, and the difference
between the two turns out to matter (see the last section).

## Every mutation the document names, measured

Each mutation is applied to the **submitted** file *and* the manifest hash is
re-synced, so the guard under test is the blob comparison and not the earlier
manifest-hash check — see the three-layer section below for why that matters.

| Mutation | Result |
|---|---|
| LF → CRLF (the documented text-mode copy) | **refused** |
| UTF-8 BOM inserted | **refused** |
| encoding conversion to UTF-16LE | **refused** |
| one trailing newline added | **refused** |
| the trailing newline removed | **refused** |
| trailing whitespace on a line | **refused** |
| NUL byte appended | **refused** |
| empty file | **refused** |
| CRLF in the **raw output** file, not the artifact | **refused** |

Every one fails with the same message, which names the cause rather than
stating a bare mismatch:

```
Git blob bytes differ from submitted evidence; possible newline or transport
mutation for 'deliverables/C1.artifact.txt': blob=7594f159…, submitted=142cc704…
```

The last four rows are the ones a weaker implementation would miss. A trailing
newline added or removed, and trailing whitespace on a line, all render
identically in any viewer — exactly the case the document says must still fail,
and it does. The comparison is `hashlib.sha256` over the bytes of
`git cat-file blob`, never over a checkout, so `core.autocrlf` and smudge
filters cannot launder anything.

The positive control is live: the untouched envelope submits with
`byte_exact: true`, two files blob-verified and bound to the commit; a single
flipped byte in the artifact is refused.

## Three guards, not one — and one of them I did not reach

My first draft assumed two layers. There are three, and they fire in order:

| Layer | Where | Compares |
|---|---|---|
| 1 | `evidence.py:119` | manifest hash vs file, during evidence validation |
| 2 | `provenance.py:294-297` | manifest hash vs file **again**, inside the provenance loop |
| 3 | `provenance.py:298-303` | Git blob bytes vs file |

Mutating a file *without* re-syncing the manifest produces
`Evidence artifact SHA mismatch` — that is layer 1, raised before `provenance.py`
is entered at all.

Layer 2 is not reachable from outside: it can only fire if the file changes
**between** layers 1 and 3, i.e. a concurrent writer during a single
`proxy_submit`. It is a TOCTOU backstop, and **this probe did not reach it** —
recorded as unmeasured, not as covered.

The practical note for anyone probing this next: a run that forgets to re-sync
the manifest measures layer 1 and never exercises layer 3, and would report the
blob check as working when it had never executed.

## The completeness rule is mechanical, not advisory

`PROXY_SUBMISSION.md:73` — *"every claim-bearing artifact and raw output is
listed once."* Both directions are closed:

| Attempt | Result |
|---|---|
| drop the raw output from the provenance list | `Git provenance does not bind every claim-bearing evidence file` |
| list the same file twice | `Duplicate submitted_path in Git provenance` |
| two source paths pointing at one submitted file | `Duplicate submitted_path in Git provenance` |

The set equality at `provenance.py:320` is what makes "listed once" enforceable
rather than a convention. Nothing may be omitted and nothing may be doubled.

## The six-section report is not byte-bound, and that is documented

The report can be rewritten with no Git blob behind it and the submission is
still **accepted**. The manifest never references it.

**Not filed**, and the reason is which paragraph the claim sits in.
`PROXY_SUBMISSION.md:61-63` says the transport actor *creates* the six-section
report, and scopes exactness to *"claim-bearing **artifacts and raw validation
outputs**"* — a set that excludes it. That is self-consistent: a file the
transport actor authors cannot also be a blob from the author's commit.
`MIGRATION.md:141-143`'s *"its claim-bearing files"* is looser and, read alone,
would suggest otherwise; the narrow document governs.

Worth an operator knowing anyway, since it is the one thing here that could be
misread from the recorded provenance: **`byte_exact: true` covers the artifacts
and the raw outputs. The prose of the report around them is transport-authored
and commit-bound to nothing.** If the concern is a transport actor
mischaracterising an author's results, the numbers are protected and the
narrative is not.

## Harness bugs, disclosed

Three, all mine, only the corrected run reported. The recorded provenance is
`result["provenance"]`, not `result["provenance"]["git"]`. Two expectation
strings named refusals that do not exist: the code says
`Evidence artifact SHA mismatch` (not *"Submitted evidence changed after
validation"*, which is layer 2 and unreachable here) and `Git provenance does
not bind every claim-bearing evidence file` (not *"does not cover"*). Both were
correct refusals mislabelled by me — and the first is what exposed the third
layer.

## Scope

`validate_git_provenance`'s blob comparison driven through the real
`Workspace.proxy_submit` against a real Git repository: nine byte mutations,
the guard-ordering question, the completeness rule in both directions, and the
report's binding. Not examined: layer 2's TOCTOU window (unreachable without a
concurrent writer); the `max_blob_bytes` ceiling and the Git LFS pointer
rejection at `provenance.py:288-291`; and `_validate_source_path`'s rejection
shapes, which `NOTE-proxy-grant-holds.md` already covers.

**No network call was made.** Proxy submission never fetches, and the remote is
`example.invalid`. Pre-registered permissions unchanged: `gpu: false`,
`network: false`, `performance_metrics: false`; gates `allow_skips: false`,
`require_validation: true`, `require_known_answer_check: true`,
`require_independent_verification: true`.

**SUBMITTED, not VERIFIED.**

| Artifact | SHA-256 |
|---|---|
| `raw/probe_byte_exactness.py` | `00190ee66c70acec5e1273161957ddd2c6d393c6dd2d73dad4a9449d1cd754c6` |
| `raw/raw-byte-exactness.txt` | `fa623940aea7d7f683b7aec5232408e2459712af7a05016139c2c8770131e755` |
