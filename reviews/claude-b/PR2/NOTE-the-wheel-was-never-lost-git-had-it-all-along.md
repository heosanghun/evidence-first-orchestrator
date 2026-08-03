# The wheel was never lost — git had it all along, and W1/W2 re-ran

Reproduce with `raw/probe_wheel_restored.py`; raw output in
`raw/raw-wheel-restored.txt`. **18 checks, 0 unexpected.** No issue filed —
this **corrects my own earlier verdict**.

**Scope, stated first:** one wheel, 14 modules, **2 of the 8 sections** of
`raw-attack4.txt` (W1 and W2). W3–W8 drive a live v0.1-against-v2 workspace and
are **not** attempted here.

## The correction, first

Items 43 and 46 concluded `raw-attack4.txt` was unreproducible because *"the
artifact under test is not in the tree"*. That is true **at the anchor** and
**wrong as "permanently lost"**. A git repository keeps a file after the tree
stops carrying it — and I wrote the verdict without trying `git show`.

That is the method's own rule — *do not declare something unreproducible until
you have tried it* — applied to me, one round after I wrote it down for
`unittest`.

## git restores it, byte-exact, with no network and no build

```
    git show 7a9553b:tests/fixtures/…whl   →  40269 bytes, exit 0
    sha256                                 →  18ed72c3…b103b2354
    tests/fixtures/README.md at 7a9553b    →  18ed72c3…b103b2354   MATCH
```

A valid zip, **20 members**, and `py3-none-any` — pure python, so there is no
build step to run. Unzip it, put it on `PYTHONPATH`, and the v0.1 CLI executes
(`exit 0`, listing `init,status,agent,task,…`).

> **Which README.** A first version of the probe read the **root** `README.md`
> and found no hash at all — the claim lives in `tests/fixtures/README.md`,
> beside the wheel. `raw-attack4.txt` says only *"README claims:"* without
> qualifying which, and I assumed the root one. Corrected to the file that
> carries it, and the probe now also asserts the root README never did.

## W1 and W2, re-run against the committed output

| | expectation (from `raw-attack4.txt`) | this run |
|---|---|---|
| **W1** wheel sha256 vs README claim | `18ed72c3…` | **match** |
| **W2** modules byte-identical to `git archive f827f29` | 6 | **6** |
| **W2** modules differing | 8 | **8** |
| every difference is exactly one byte | — | **True** |

```
    DIFFERS __init__.py       127 -> 128 bytes
    DIFFERS __main__.py       160 -> 161 bytes
    DIFFERS archive.py       4938 -> 4939 bytes
    DIFFERS dashboard.py     8115 -> 8116 bytes
    DIFFERS errors.py         816 -> 817 bytes
    DIFFERS lock.py          2339 -> 2340 bytes
    DIFFERS model.py         4416 -> 4417 bytes
    DIFFERS util.py          3434 -> 3435 bytes
```

A trailing newline the wheel build added — the committed output recorded
`stripped_equal=True` for all eight. The six byte-identical modules are the
security-relevant ones: `workspace.py`, `ledger.py`, `cli.py`, `evidence.py`,
`adapter.py`, `doctor.py`.

**Neither side of the W2 comparison is typed in by me**: the byte-identical list
is parsed out of the committed output and compared against a fresh extract.

## What stands, and what does not

**Still true, unchanged:**

- **No `attack4` script ever existed** — `git log --all --diff-filter=D` finds
  nothing, and the only path matching the name is the output itself.
- **`REPORT.md`'s provenance sentence is still false** — §3 ④ contains two
  fenced blocks and zero command-shaped lines.

**Corrected:** *"unreproducible"* was too strong. W1 and W2 are re-runnable and
have been re-run; W3–W8 are un-re-run but their stated blocker — *the client is
gone* — does not hold.

## What this does not do

- It does **not** re-run W3–W8, and does **not** claim P2-1 or P2-2 are
  re-verified. It removes their blocker; driving a live v0.1-vs-v2 workspace
  scenario is a separate job.
- It does **not** retract P2-1, P2-2 or P2-3.
- It does **not** install anything — unzip to `/tmp`, `PYTHONPATH`, no pip, no
  network, no build.
- It does **not** touch `main`, the anchor's working tree, or any other agent's
  branch. `git show` writes nothing back.
- **MEASURED:** the restored bytes and their hash, the README claim at
  `7a9553b`, the zip integrity, both W1 and W2 comparisons, the CLI exit code.
  **REASONED:** nothing.

Pre-registered permissions unchanged: `gpu: false`, `network: false`,
`performance_metrics: false`; gates `allow_skips: false`,
`require_validation: true`, `require_known_answer_check: true`,
`require_independent_verification: true`.

**SUBMITTED, not VERIFIED.** Re-running my own evidence is a re-run, not
independent confirmation.

| Artifact | SHA-256 |
|---|---|
| `raw/probe_wheel_restored.py` | `4c42df94d913a435ee985ff8b356ee089a862e4f67181dfacff6aa49e2dd6c04` |
| `raw/raw-wheel-restored.txt` | `b36b3614deee2ca6f106d2d969884eba82b3d2d2ddd3675eba63465de7d4900d` |
