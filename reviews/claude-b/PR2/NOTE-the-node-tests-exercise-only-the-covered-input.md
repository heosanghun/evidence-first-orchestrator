# The Node suite has a test for #13 and a test for #14 — and each feeds the guard the one input it already handles

Reproduce with `raw/probe_node_suite.mjs` (`node probe_node_suite.mjs`); raw
output in `raw/raw-node-suite.txt`. **13 checks, 0 unexpected.** No issue
filed — #13 and #14 already exist, and a re-confirmation is a comment, not a
new issue.

`NOTE-what-the-test-suite-cannot-catch.md` token-searched `web_tests/` and
stopped, naming the gap in its own scope: *"#13 and #14 live in
`functions/api/*.js`, and adjudicating `chat.test.mjs` and `snapshot.test.mjs`
line by line is a separate pass."* This is that pass.

**Unlike every Python probe in this review, this one executes.** Node v22 is
present and these handlers run offline, so where the Python side had to reason
about reachability this one calls the shipped function and reads what comes
back.

The answer for both issues is the same, and it is sharper than *"absent by
name"*: **the test exists, and it exercises only the input the guard already
handles.**

## Inventory

| File | Tests | Assertions |
|---|---|---|
| `snapshot.test.mjs` | 21 | 62 |
| `chat.test.mjs` | 10 | 37 |
| `local-health.test.mjs` | 6 | 21 |
| **total** | **37** | **120** |

37 matches the `# tests 37` the runner itself reports — the count is checked
against the runner, not assumed.

## #13, first finding — the refusal gate is Korean-only

`chat.js:204`:

```
    /실행|시작|중단|정지|재시작|삭제|수정|배포|학습해|돌려|할당/.test(query);
```

**11 alternatives, 0 containing a Latin letter.** The only test of it,
`chat.test.mjs:221-225`:

```
test("action requests are refused as read-only", () => {
  const body = internals.deterministicAnswer("GPU 0 학습을 중단해줘", snapshot());
  assert.match(body, /읽기 전용/);
  assert.match(body, /실행하거나 서버를 변경하지 않았습니다/);
});
```

Driven through the shipped `deterministicAnswer`, five phrasings:

| Input | Read-only refusal |
|---|---|
| `GPU 0 학습을 중단해줘` — the test's own | **refused** |
| `stop the training on GPU 0` | not refused |
| `restart the run` | not refused |
| `delete the checkpoint` | not refused |
| `deploy to the server` | not refused |

The test passes either way, because its input is one the gate already matches.
**It cannot fail on this defect.**

## #13, second finding — the test *asserts* the behaviour

```
    assert.match(captured.instructions, /최신 EFO 스냅샷 JSON/);
```

#13's second finding is that snapshot text is concatenated into the model
`instructions` block. The suite does not merely miss that — **it requires it.**
A fix that moved the snapshot out of `instructions` would turn this test red.

This is the **second instance of the shape #19 showed**: the test encodes the
same decision the issue objects to. There the test *excluded* `last_event_hash`
from a comparison; here it *asserts* the grounding placement. Neither test is
wrong on its own terms. What both mean is that the suite cannot be the thing
that notices.

One clarification while I am here, because the issue could be read too broadly:
**`sanitizeSnapshot` at `chat.js:235` does run.** #13's second finding is about
*placement*, not about the snapshot going in unsanitised.

## #14 — the guard is exact-match, and the test picks a listed key

`FORBIDDEN_KEYS` has **12** entries:

```
["password","passwd","secret","token","environment","env","command","cmdline","pid","uuid","ssh","authorization"]
```

The only test of it injects `snapshot.source.password = "must-not-pass"` — a key
**in** the set. Driven through the shipped `hasForbiddenKey`:

| Key | Result |
|---|---|
| `password` — the test's own | **caught** |
| `api_key` | passes |
| `gpu_uuid` | passes |
| `command_line` | passes |
| `ssh_key` | passes |
| `access_token` | passes |
| `env_vars` | passes |

**One of seven.** This is #14 driven through the code rather than argued from
it — a re-confirmation, reported here and not filed again. The point for *this*
pass is the test: it passes with the defect present.

This is the same snake_case-compound blind spot `SYNTHESIS.md` class 1
describes, now with the guard executed rather than read.

## `local-health.test.mjs` yielded nothing new

Six tests: a reproducible stress-index known answer, signature validation and
fail-closed on extra fields, session-aware smoothing, view-token protection, and
a health endpoint that reports configuration state without secrets.

`ADDENDUM-chat-refusal-and-grounding.md` already measured `local-health.js` as
the strongest shape in the repository, and reading its tests did not change that
or add a finding. **Said plainly rather than dressed up as a thorough pass.**

## Scope

`web_tests/*.mjs` and the exported internals of `functions/api/chat.js` and
`functions/api/snapshot.js` at `main` `5694ab45` (precondition verified: `HEAD`
matches, `git status --porcelain` empty — the anchor is unchanged even though
`origin/main` has moved to `0d67750`; see
`ADDENDUM-main-is-red-and-a-push-run-is-not-a-pr-run.md`).

Not established:

- This does **not** run the three files as a suite. That is CI's job, and the
  current 35/2 at `origin/main` is reported in the addendum above. This probe
  calls exported functions directly, which is a different thing.
- It does **not** claim the Node tests are weak. 37 tests and 120 assertions
  include several this review has cited *approvingly* — the transport-assertion
  projection tests are why #6's data contract holds. Nothing here asserts
  something false.
- #13's OpenAI path is exercised with a stubbed `globalThis.fetch`. Whether a
  real model ignores the read-only instruction is **unmeasured** and
  unmeasurable here — `network: false`.
- **MEASURED:** the inventory, the gate's 11 alternatives, all five phrasings,
  all seven key candidates, both test inputs. **REASONED:** that a test passing
  on the covered input cannot fail on the uncovered one — which for these two
  guards follows from the executed results above rather than from inspection.

Pre-registered permissions unchanged: `gpu: false`, `network: false`,
`performance_metrics: false`; gates `allow_skips: false`,
`require_validation: true`, `require_known_answer_check: true`,
`require_independent_verification: true`.

**SUBMITTED, not VERIFIED.**

| Artifact | SHA-256 |
|---|---|
| `raw/probe_node_suite.mjs` | `de54fd719d672cf5dcdf356e0e8d5367758510bde1d9fae65fde7bfa8fd0673a` |
| `raw/raw-node-suite.txt` | `b6f03e6d25610f6ba7ec01735ce6ecfd3298426576b52591c5f9ee5baa62d516` |
