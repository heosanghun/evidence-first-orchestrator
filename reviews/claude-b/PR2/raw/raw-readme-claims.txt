########## A. POSITIVE CONTROL - the source is main, unmodified ##########
  [ok] probe source is main 5694ab45
        expected: 5694ab455139f1e72d946bc2fe7e42c7c0c8a43a
        observed: 5694ab455139f1e72d946bc2fe7e42c7c0c8a43a
  [ok]   with no working-tree modification
        expected: dirty: ''
        observed: dirty: ''
  [ok]   README.md is the file the audit measured
        expected: lines: 452
        observed: lines: 452
  [ok]   and the three corrected anchors resolve
        expected: ['Open `http://127.0.0.1:8765`. Remote binding is rejected unless', 'At submission, EFO copies the report, manifest, and evidence files up to 50 MB']
        observed: ['Open `http://127.0.0.1:8765`. Remote binding is rejected unless', 'At submission, EFO copies the report, manifest, and evidence files up to 50 MB']

########## B. :21 'no runtime dependencies beyond Python 3.10 or newer' ##########
  [ok] the package declares no runtime dependencies
        expected: dependencies: []
        observed: dependencies: []
  [ok]   and requires the stated Python
        expected: requires-python: >=3.10
        observed: requires-python: >=3.10
  [ok]   and imports nothing outside the standard library
        expected: non-stdlib: []
        observed: non-stdlib: []
  Checked by AST over every module in src/, not by reading the
  dependency list alone - a declared-empty list and a stray import
  would be two different lies, and only the second breaks an install.
  NOT checked: the optional dashboard under monitor/ and functions/,
  which the sentence does not cover.

########## C. :433 'never stores SSH passwords or API tokens in task files' ##########
  This is a claim about what EFO WRITES, so it is measured by driving
  a task whose free-text fields are full of credentials and then
  reading what landed on disk.
  [ok] EFO stores what the ORCHESTRATOR typed, verbatim
        expected: secret in task file: True
        observed: secret in task file: True
  -> The sentence is about EFO's own behaviour: it does not COLLECT or
     PERSIST credentials of its own accord - there is no password field
     in the schema and no credential is ever read from the environment
     into a task. It is NOT a filter on operator-supplied text, and
     nothing in the README says it is. Recorded as a MAP, not a finding.
  The neighbouring safeguard is real and already measured: `efo doctor`
  scans task JSON for secret-like values (ADDENDUM-doctor-repair-and-
  secret-scan.md), and its `\b` blind spot is issue #12.
  [ok]   and doctor DOES flag the planted values
        expected: findings: 2
        observed: findings: 2

########## D. :404-406 the legacy write test 'targets only the ##########
            selected agent's report directory'
  [ok] README states the containment promise a SECOND time
        expected: targets only the
        observed: The audit checks required files, event-line formatting, read access, and secret-like plaintext values. A write test is opt-in and targets only the selected agent's report directory:
  README.md:404-406 -> "The audit checks required files, event-line formatting, read access, and secret-like plaintext values. A write test is opt-in and targets only the selected agent's report directory:"
  This MATTERS for issue #17, which I filed citing MIGRATION.md:43-52
  alone. The same promise is in README.md - the document an operator
  actually follows - so the issue UNDERSTATED its scope. Measured
  behaviour is unchanged: `--agent ..`, `../..`, `.` and an absolute
  path all write outside `reports/<agent>/`, and `codex/../claude`
  writes into a different agent's directory. A comment on #17 naming
  this second source is owed; a new issue is not.

########## E. :365-366 the dashboard labels its sample as DEMO ##########
  [ok] the string DEMO appears in the shipped page
        expected: files: True
        observed: files: True
  found in: ['app.js']
  MEASURED: the marker exists in the shipped assets. NOT MEASURED:
  that it is VISIBLE to a viewer, or that it appears whenever the API
  is unconfigured - that needs the page rendered against an
  unconfigured backend, and `network: false` forbids fetching one.
  Stated as a partial check rather than counted as covered.

########## F. every falsifiable claim in README.md ##########
    :3-5 EFO is a local-first broker that does not treat exit code or prose as proof
        the thesis; the whole review tests it
    :10-16 the seven guarantees (single-owner claims, ownership, gates, evidence, independence, recovery, signed history)
        covered - raw-lifecycle-gates.txt and raw-evidence-gates.txt
    :18-19 config, agent roles and projections checked against signed snapshots before authorization
        covered - config binding measured in probe_doctor_coverage.py; projections are issue #12
  >>:21 no runtime dependencies beyond Python 3.10
        PROBED HERE - section B
    :25-28 a Markdown inbox cannot stop double claims or prove a test ran
        covered - NOTE-util-and-lock-hold.md, raw-evidence-gates.txt
    :45 SUBMITTED is intentionally not VERIFIED
        covered - raw-lifecycle-gates.txt
    :72-74 GPU, network, performance metrics, skips and relaxed gates are denied by default
        covered - issue #15 (a string 'false' opens them)
    :121-122 command mode launches a CLI without using a shell
        covered - ADDENDUM-adapter-sanctions-ledger-writes.md
    :136-146 the six adapter placeholders
        covered - ADDENDUM-adapter-sanctions-ledger-writes.md
    :150-157 the adapter claims, heartbeats, records output, detects writes outside ownership, submits only on passing gates
        covered - issue #11 (ledger/events.jsonl is inside the grant)
    :161-209 the manifest schema
        covered - raw-evidence-gates.txt
    :211-220 the eight default rejection conditions
        covered - raw-evidence-gates.txt; the [FILL] tautology is issue #8
    :224-236 identity, not actor name, is the independence boundary; an alias cannot be detached or reparented
        covered - NOTE-alias-lineage-holds.md, issue #3
    :260-262 the legacy identity policy is read-only and cannot make a future verification eligible
        covered - NOTE-cli-surface-holds.md
    :266-269 the proxy path never fabricates a claim, lease, start or submit
        covered - NOTE-proxy-grant-holds.md
    :271-272 the grant binds task, attempt, transport, remote, branch, workspace, expiration
        covered - NOTE-proxy-grant-holds.md
    :285-286 every claim-bearing artifact matches raw blob bytes; checkout line-ending changes are rejected
        covered - NOTE-byte-exactness-holds.md
    :313-320 proxy-status does not create a claim and the state stays pending
        covered - ADDENDUM-proxy-status-freshness.md, issue #6
    :322-324 independence is measured against the author; transport overlap is preserved not hidden
        covered - NOTE-proxy-grant-holds.md
    :335-336 remote binding is rejected unless --allow-remote
        covered - NOTE-dashboard-and-errors-hold.md (citation corrected)
    :356-361 the collector only reads; snapshots omit secrets, PIDs, GPU UUIDs, hashes
        covered - NOTE-collector-redaction-holds.md, issue #14
  >>:365-366 the bundled sample is visibly identified as DEMO
        PROBED HERE - section E, partially
    :368-373 no hostname/process/command-line leaves the Windows collector; no chat path can claim, start, stop or verify
        covered - ADDENDUM-chat-refusal-and-grounding.md, issue #13
    :384-386 an expired task moves to BLOCKED and is never silently requeued
        covered - raw-lifecycle-gates.txt
    :388-389 the ledger is the source of truth; projections are rebuildable
        covered - ADDENDUM-architecture-claims-and-repair-drops-a-field.md
    :391-394 files up to 50 MB are copied; larger stay external
        covered - issue #18 (true on the direct path, false on proxy)
  >>:404-406 the legacy write test targets only the selected agent's report directory
        PROBED HERE - section D; strengthens issue #17
    :418-433 the seven things EFO does not claim
        not falsifiable - stated limitations, and honest ones
  >>:433 it never stores SSH passwords or API tokens in task files
        PROBED HERE - section C
    :442-445 what the test suite covers
        covered - the suite was invoked; CI runs it on every push
  [ok] every headed section is represented
        expected: headings: 13
        observed: headings: 13
  [ok]   claims probed for the first time here
        expected: 4
        observed: 4
  [ok]   claims already covered by an existing write-up
        expected: 24
        observed: 24
  [ok]   the rest are the thesis or stated limitations
        expected: 2
        observed: 2
  Nothing in README.md is left unadjudicated.

########## 0 unexpected result(s) ##########
No network call. Pre-registered permissions unchanged -
gpu/network/performance_metrics all false.
SUBMITTED, not VERIFIED.
