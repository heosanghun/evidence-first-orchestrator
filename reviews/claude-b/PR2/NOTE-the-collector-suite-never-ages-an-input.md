# The collector's 27 tests never age an input — which is why #6 has no test

Reproduce with `raw/probe_collector_stubs.py`; raw output in
`raw/raw-collector-stubs.txt`. **11 checks, 0 unexpected.** No issue filed —
#6 is already open, and this is about coverage shape, not a new defect.

Queue item 39. `NOTE-what-the-test-suite-cannot-catch.md` measured 21 mock
targets, 18 of them `monitor.collector.*`, and left the consequence unexamined.
The sharper question: **which properties are asserted only against stubbed
input, and is any of them one that could only fail against a real machine or a
real clock?**

## What is stubbed

**12 distinct targets over 18 call sites.** Stubbing `run_command`,
`query_gpus`, `read_meminfo`, `read_uptime` and `shutil.disk_usage` is what
makes a collector that shells out to `nvidia-smi` testable without a GPU host.
That is not a criticism — it is the boundary.

## The clock is stubbed once, to a constant, in an unrelated test

```
    @patch("monitor.collector.urllib.request.urlopen")
    @patch("monitor.collector.time.time", return_value=1000)
    def test_submit_hmac_covers_timestamp_and_exact_body(
```

One clock stub across 27 tests; it pins `now` to `1000`; and it belongs to a
**signature** test. **No test moves the clock to age anything.**

## The staleness vocabulary is absent

| Token | In the suite? |
|---|---|
| `stale`, `staleness`, `freshness` | absent |
| `PORTFOLIO_EXTERNAL_ACTIVE_PHASES` | absent |
| `age`, `elapsed`, `expired`, `seconds_since` | absent |

Matched as identifier **tokens**, not substrings — a first pass reported `age`
twice and both were inside `disk_usage_mock`. **Twelfth** hand-rolled filter in
this review to be the bug, and the exact trap the method already names: it
caught `worker` inside `worker_identity` two rounds ago and I repeated it here.

## #6's branch has no clock in it at all

`monitor/collector.py:898-901`:

```
            elif (
                state == "pending"
                and external_phase in PORTFOLIO_EXTERNAL_ACTIVE_PHASES
            ):
```

A pure set-membership test on `external_phase`. **No timestamp is involved**,
which *is* #6: a `ready` reported a month ago counts exactly as a `ready`
reported a second ago. A lease expires; a transport progress report does not.

So #6 has no test **not because the suite forgot a case**, but because the
concept of a transport report ageing does not exist anywhere in the collector
or its tests. That is why the token map found nothing — and it is a more useful
answer than *"absent"*.

This sharpens `SYNTHESIS.md` class 2b. The seven issues there have a test that
cannot fail on them. #6 is the other shape: **there is no vocabulary for the
property, so there is nothing for a test to be about.**

## Scope

Static analysis of `monitor/collector.py` and `tests/test_monitor_collector.py`
at `main` `5694ab45` (precondition verified: `HEAD` matches, `git status
--porcelain` empty). Nothing executed.

Not established:

- This does **not** re-measure #6. That was driven in the issue and is not
  re-confirmed here; a re-confirmation is a comment, not a note.
- It does **not** claim the 18 stubs are wrong. What is measured is the
  consequence: 27 tests exercise the collector's logic against inputs the test
  chooses, and no test supplies an input that is *old*.
- `external_phase` **does** appear in the tests (8 tokens) — the field is
  exercised, set and asserted on. What is absent is any test where the same
  field is exercised with **time having passed**.
- **MEASURED:** the stub census, the single clock stub and its constant, the
  vocabulary absence, the branch text. **REASONED:** that no test ages an input
  — which follows from the clock being stubbed once, to a constant, in an
  unrelated test.

Pre-registered permissions unchanged: `gpu: false`, `network: false`,
`performance_metrics: false`; gates `allow_skips: false`,
`require_validation: true`, `require_known_answer_check: true`,
`require_independent_verification: true`.

**SUBMITTED, not VERIFIED.**

| Artifact | SHA-256 |
|---|---|
| `raw/probe_collector_stubs.py` | `8841e5c561b4f585ee4f458f19b811b66aac0ea8c3c0f181d005ea44d692a995` |
| `raw/raw-collector-stubs.txt` | `214ab2cc3f1e88c867a28ac67450ebc779bd21578b3e7bb5dc49a60d1cd354ea` |
