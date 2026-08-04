# The four mixed outputs — two are real, and one is the substring trap a third time

Reproduce with `raw/probe_the_four_mixed_outputs.py`; raw output in
`raw/raw-the-four-mixed-outputs.txt`. **43 checks, 0 unexpected.** A **map
that corrects a count of mine** — no issue filed, nothing about EFO claimed.

**Scope, stated first:** 81 outputs at publication (**83** at `HEAD`), 4 mixed, 3 categories, 2 genuine, 1
swallowed literal measured occurrence-by-occurrence, 1 subject test.

> **EXTENDED 2026-08-03 by item 70 — nothing here is retracted.**
> This round said plainly that a **corpus-wide sweep for swallowed literals
> was UNCHECKED**. It has now been run over all 83 outputs
> (`NOTE-the-swallowing-rule-corpus-wide-and-the-marker-set-was-short.md`).
> `raw-full-final.txt`'s result below is reproduced **by rule** rather than by
> hand, and the other three mixed outputs are unchanged. The sweep moved
> **one further** verdict — `raw-class2b-census.txt` — and that one exposed an
> **incomplete marker set** rather than a mis-placement: test-module filenames
> were never matched. With them added the union moves **36/5/4/38 →
> 37/6/3/37**, so **the mixed class shrinks from 4 to 3** — `raw-full-final.txt`
> leaves it and no output joins.
>
> **CORRECTED 2026-08-03 by item 73 — one number in the table below was
> wrong.** `raw-w4-replay.txt`'s divergent marks were published as **5**; they
> are **4**. The marker "set" is a concatenated tuple and
> `transfer-orchestrator` occupies **two slots** — I hand-added it *and* the
> literal derivation produces it from the divergent source — so this count,
> taken over the tuple, counted it twice. The row is amended in place. The
> **verdict does not move**: four marks is still both lines, and this file
> names both refs by design. Three of the four rows reproduce exactly.

## What item 64 left open

That round's union found **four** outputs carrying markers from both lines,
where the token test alone found none — and it **counted them without naming
them**. Derived here rather than copied:

| output | anchor marks | divergent marks | verdict |
|---|---|---|---|
| `raw-attack-prov-main.txt` | 2 | 2 | **GENUINE** |
| `raw-w4-replay.txt` | 3 | 4 | **GENUINE** |
| `raw-full-final.txt` | 1 | 2 | **SPURIOUS** |
| `raw-quote-accuracy.txt` | 10 | 2 | **not a program run** |

## One is the substring trap, a third time

`raw-full-final.txt`'s **only** anchor evidence is the literal
`author_identity`. It occurs **twice**, and **2 of 2 occurrences are
swallowed** inside a longer identifier:

```
test_submission_freezes_author_identity_before_profile_changes
    (tests.test_meta_orchestration.MetaOrchestrationTests....)
```

— a **divergent-only** test method, in a **divergent-only** module.

> Item 61 fixed a **module name** being a prefix of a **method name** by
> parsing the identifier. Item 64 introduced **literals**, and a distinctive
> anchor-only *literal* is swallowed by a divergent *identifier* in exactly the
> same way. **Third instance of one lesson.**

So `raw-full-final.txt` is **not mixed**. Item 61's placement of it as purely
**divergent** stands — this round **removes a mark that should never have been
counted** rather than adding one.

> **My swallowing rule needed one refinement, caught by the run.** Checking
> both boundaries unconditionally reported `, submitted=` in
> `raw-attack-prov-main.txt` as swallowed, because it is preceded by a digit in
> `…549, submitted=950f…`. A comma cannot be part of an identifier. The
> boundary is only meaningful on a side where **the marker's own edge** is an
> identifier character.

## One is not a program run at all

`raw-quote-accuracy.txt` is the output of a self-check whose **subject is my
own Markdown**:

```
    probe_quote_accuracy.py   .md paths= 25   efo paths=3
    probe_w4_replay.py        .md paths=  0   efo paths=9
```

It carries text from both lines because the **notes it audits** quote both.
Neither its anchor marks nor its divergent marks are program output, and
calling it a *mixed run* would be a category error — it is not a run of either
line.

> The obvious test — *does the probe import `evidence_orchestrator`?* — does
> **not** separate these two: neither does, because `probe_w4_replay.py` drives
> the CLI through `subprocess`. Measured before relying on it, and discarded.

## Two are genuine, and say so in their own text

| output | names | swallowed anchor marks |
|---|---|---|
| `raw-attack-prov-main.txt` | **`cef5623`** | **0** |
| `raw-w4-replay.txt` | **`7a9553b`** | **0** |

`raw-attack-prov-main.txt` runs *"the SAME forged state against `cef5623`"* —
an explicit **A/B across the two lines**, with real refusal messages from each.
`raw-w4-replay.txt` is item 55's own probe, which names both refs **by
design**.

## The corrected count

```
    item 64 reported : mixed 4
    corrected        : 2 GENUINE, 1 SPURIOUS, 1 NOT A PROGRAM RUN
```

And the population of outputs **known to exercise two lines** is **three**:
`raw-attack4.txt` (item 55, by absent API and ancestry),
`raw-attack-prov-main.txt` and `raw-w4-replay.txt` (this round, by their own
text). Not four, and not one. `raw-attack4.txt` is **not** among item 64's
four — it remains undecidable by tokens while being known mixed by other means,
which is item 61's proven false negative still standing.

## What this does not do

- It does **not** retract item 64. Its union count of 4 is what that test
  reports; what this adds is **why** each of the four is in it.
- It does **not** change item 61's placement of `raw-full-final.txt`.
- It does **not** re-classify the corpus. Only the four are examined; the 36
  undecidable are untouched and still open.
- It does **not** claim the swallowing rule catches every such case. It is
  applied to the four mixed outputs only — a corpus-wide sweep for swallowed
  literals is **unchecked**, not shown clean.
- It does **not** file an issue. Nothing here is about EFO's behaviour; it is
  about the provenance of inherited evidence and about a filter of my own.
- This probe prints markers, so its output joins the marker-printing exclusion
  set — the **fourth**, and the count is asserted so a fifth cannot appear
  unnoticed.
- No network, no GPU, no workspace built. Two refs read and named. The anchor's
  working tree is untouched, and it does **not** touch `main` or another
  agent's branch.
- **MEASURED:** the four derived, every occurrence of the swallowed literal,
  both probes' path literals, both genuine files' refs and unswallowed marks.
  **REASONED:** nothing.

Pre-registered permissions unchanged: `gpu: false`, `network: false`,
`performance_metrics: false`; gates `allow_skips: false`,
`require_validation: true`, `require_known_answer_check: true`,
`require_independent_verification: true`.

**SUBMITTED, not VERIFIED.** Re-running my own evidence is a re-run, not
independent confirmation.

| Artifact | SHA-256 |
|---|---|
| `raw/probe_the_four_mixed_outputs.py` | `6684039f2df71b07a602f6538185c5d852695e83f914b0ba4b2cfbbd07d021d4` |
| `raw/raw-the-four-mixed-outputs.txt` | `e8bd1720f5e4a00c25e26f60b2720a36206ef7fa1f33f4edbc34e33791baf222` |
