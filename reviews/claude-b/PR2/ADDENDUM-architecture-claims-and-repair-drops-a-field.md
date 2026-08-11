# `ARCHITECTURE.md` read end to end: four claims hold, and one repair path drops a load-bearing field

Reproduce with `raw/probe_architecture_claims.py`; raw output in
`raw/raw-architecture-claims.txt`. **27 checks, 0 unexpected.** Filed as
issue #19.

`ARCHITECTURE.md` was the only long document this review had never read
straight through. That is where an unprobed promise is most likely to hide, so
the probe enumerates every falsifiable sentence in it and **fails the run on
any claim it has not adjudicated**.

| Disposition | Count |
|---|---|
| probed here for the first time | 5 |
| already covered by an existing ADDENDUM or NOTE | 28 |
| stated limitations, not testable promises | 3 |

Five, not four: `:70-72` and `:159` are separate sentences that one experiment
answers. Counting *sections* instead of *claims* is how a document gets
reported as fully covered while a sentence in it was never read — my first
tally made exactly that mistake.

The three limitations are the document being honest about itself: identity
declarations cannot be provider-verified (`:106-110`), broker bypass is
detectable but not preventable (`:162`), and hard isolation needs the OS
(`:166-169`). They are counted as such rather than as coverage.

## The finding: repair produces a projection that crashes proxy submission

Three facts compose.

**Repair drops the field.** `repair_projections` rebuilds from the signed
snapshot, which deliberately has no `last_event_hash` — `workspace.py:470/495/517`
strip it before signing, since an event cannot contain its own hash, and `:529`
re-attaches it to the projection on the normal write path. The repair path
never re-attaches it.

**The audit cannot see it.** `workspace.py:1511` excludes that key when
comparing a projection to the ledger:

```python
key: value for key, value in disk_task.items() if key != "last_event_hash"
```

Right for content equality, blind to *absence*.

**The field is load-bearing.** `workspace.py:1182`, inside `proxy_submit`:

```python
"grant_event_hash": task_for_validation["last_event_hash"],
```

Measured in sequence:

```
a live proxy grant exists, task carries the field   last_event_hash present: True
the operator repairs the projection                 repaired: ['C1']
the audit reports NO mismatch                       mismatches: []
but the field is gone                               last_event_hash present: False
an OTHERWISE VALID proxy submission dies            UNCAUGHT KeyError: 'last_event_hash'
```

Through the real CLI this is a **traceback**, not a message.

The operator sequence is ordinary: a projection is lost, `ledger
repair-projections` is run — the documented remedy, which reports success —
every audit says healthy, and the next proxy submission for that task crashes.

Filed separately from #12 because the failure mode differs: #12 is repair
laundering a *truncated chain*, this is repair producing an *incomplete
projection*. Same command, same fix surface, and the branch says so.

## This corrects an earlier result of mine

`NOTE-dashboard-and-errors-hold.md` reported **`escapes: []`** — that nothing
raised in the package falls outside `cli.main`'s catch tuple
`(EFOError, OSError, ValueError, json.JSONDecodeError)`.

That census enumerated `raise` **statements**. It structurally could not see an
exception arriving from a dict index, and `KeyError` is a `LookupError`, in
none of those four families. **The conclusion was too strong.** It is corrected
here rather than left standing, and issue #19 is the counterexample.

The general lesson, which is now in the carried-forward method: an exhaustive
census is exhaustive over *the thing it enumerates*, and the shape it cannot
enumerate is where the counterexample lives.

## The four claims that hold

- **`:55-56`** — *"The private local key is stored at `.efo/ledger.key`. It is
  runtime state and must never be committed."* The path is as documented;
  `.efo/` is in the shipped `.gitignore`; a real `git ls-files` census shows
  nothing tracked under it. Checked against the **repository**, not the fixture
  — a fixture in `/tmp` proves nothing about what is committed.
- **`:79-80`** — *"Its token is returned once and only a SHA-256 digest is
  stored."* The raw token appears in neither the ledger nor the projection; the
  digest appears in the projection. Both files are searched, because a digest
  that merely looks stored would still let the token leak through the ledger.
- **`:70-72` and `:159`** — the ledger retains enough to rebuild a lost
  projection, and repair appends no event. Boundary stated: this measures what
  the *ledger retains*, which is what the sentence claims. It does **not**
  measure write ordering under an actual mid-write crash — that needs a killed
  process, and none was killed.
- **`:143-144`** — *"A source file is hashed again after copying."*
  `_atomic_copy_verified` hashes the **temp copy it just wrote**, not a fresh
  read of the source. That is the stronger choice: a file mutated mid-copy
  yields a torn copy whose hash cannot match, so the window is closed by
  construction rather than by re-reading a file that could change again. The
  refusal is `Evidence changed while being archived`. **Unmeasured, and stated
  as such:** I did not win an actual race; what is measured is that the guard
  exists, fires, and names the condition.

## Harness bugs, disclosed

Two expectations of mine were wrong and corrected before any conclusion: the
document is 169 lines, not 170, and the lease token is 32 hex characters, not
64. A third — the claim tally — is described above. The `archive_evidence_bundle`
signature also took `submissions_root` / `extra_files`, not the parameters I
first guessed. Only the corrected run is reported.

## Scope

Every falsifiable sentence in `docs/ARCHITECTURE.md` at `5694ab45`, adjudicated
against the existing write-ups; the four previously unprobed claims; and the
repair/audit/proxy chain that section D exposed, driven through both the Python
API and the real `cli.main`.

Not examined: a real mid-write crash, and a genuinely won archival race.

**No network call and no process kill.** Pre-registered permissions unchanged:
`gpu: false`, `network: false`, `performance_metrics: false`; gates
`allow_skips: false`, `require_validation: true`,
`require_known_answer_check: true`, `require_independent_verification: true`.

**SUBMITTED, not VERIFIED.**

| Artifact | SHA-256 |
|---|---|
| `raw/probe_architecture_claims.py` | `2bdb45d0414d7b52d47fc0a198d43670cf48bc252f0122d6720305d7e06e20b9` |
| `raw/raw-architecture-claims.txt` | `3b4020732aa0ba00b8ff30dbf9178af6e13bc7fb4457e99081607855d7db343d` |
