# What else can place an output — and the filter my own ground truth caught

Reproduce with `raw/probe_what_else_places_an_output.py`; raw output in
`raw/raw-what-else-places-an-output.txt`. **26 checks, 0 unexpected.** A
**map with a mostly-negative result** — no issue filed, nothing retracted.

**Scope, stated first:** 79 outputs at publication (**84** at `HEAD`, items 65-71's outputs having landed), 47 undecidable, 3 candidate classes
measured for coverage, 2 literal sets derived over full ancestry, 1 filter bug
caught by ground truth, 12 newly placed, **35 left open**.

## The question, and why the named classes do not answer it

Item 61 left **47 of 79** outputs undecidable. The item proposed asking what
other content class could place them — a ledger action set, a CLI usage line,
an error-message wording. Measured on the open set rather than guessed:

| class | coverage of the 47 |
|---|---|
| prints a suite size (`Ran N tests`) | **5** |
| prints a CLI usage line (`usage: efo`) | **1** |
| **between them, no overlap** | **6 of 47** |

Neither carries a round. But all three named classes are **subsumed by one
derivation**: an action name, an error wording and a CLI option are all
**string literals**. So the marker set is every distinctive literal each line's
source contains, differenced — taken over the **whole of each line**, not two
commits.

```
    literals on the anchor's line   861
    literals on the divergent line  1107
    distinctive, anchor-only         159
    distinctive, divergent-only      309
```

*Distinctive* is a **stated judgement, not a tuned threshold**: at least 12
characters, containing a space, underscore or hyphen, single-line. A bare
English word would match any prose — which is exactly what item 61's bare
`"independence"` was.

## And the ground truth caught it before it shipped

The raw difference **contradicted item 61's own placements on five outputs**:

```
    raw-attribute-subset.txt       item 61: anchor   raw literals: divergent
    raw-clean-verdict-census.txt   item 61: anchor   raw literals: divergent
    raw-dashboard-errors.txt       item 61: anchor   raw literals: divergent
    raw-module-exercise.txt        item 61: anchor   raw literals: divergent
    raw-test-suite-map.txt         item 61: anchor   raw literals: divergent
```

The cause is measured, not guessed. Four of the five turn on a single literal:

| | |
|---|---|
| `proxy_submit` present on the anchor's line **as source text** | **True** |
| …present there **as a string literal** | **False** |

On the anchor's line `proxy_submit` is an **identifier** — a method name. A
census of *literals* cannot see it and therefore calls it divergent-only.

> **Absence as a literal is not absence from the code.**

Corrected by subtracting any literal that appears anywhere in the other line's
source **text**:

| | raw | corrected |
|---|---|---|
| anchor-only | 159 | **159** |
| divergent-only | 309 | **302** |
| **contradictions** | **5** | **0** |
| agreements with known placements | — | **19 of 19** (20 of 20 at `HEAD`) |

*Checking a filter against ground truth in both directions* is item 50's rule.
Here the ground truth was item 61's own placements, and the raw filter
**failed** it — which is why this round has a correction section rather than
simply a result.

## What the corrected class places

| the 47 previously undecidable | |
|---|---|
| newly placed on the **anchor's** line | **9** |
| newly placed on the **divergent** line | **2** |
| carrying literals from **both** | **1** |
| **still undecidable** | **35** *(38 at `HEAD`)* |

And the union of both tests over all 79:

```
    anchor 35   divergent 5   mixed 4   undecidable 35      (36/5/4/35 at HEAD)
```

> **The union is not the sum of the parts**, and I predicted it wrongly. An
> output already placed by the token test can pick up the *other* line's marker
> from the literal test and become **mixed** rather than staying put. Four
> outputs do — where the token test alone found **none**. Corrected to the
> measured union, with the mixed class asserted rather than absorbed.
>
> **Adjudicated 2026-08-03 by item 67.** The four are named and classified:
> **2 genuine** (`raw-attack-prov-main.txt`, `raw-w4-replay.txt` — each names
> the other ref in its own text), **1 spurious** (`raw-full-final.txt`, whose
> only anchor mark is the literal `author_identity`, **2 of 2 occurrences
> swallowed** inside a divergent-only test method name — the substring trap a
> third time), and **1 that is not a program run at all**
> (`raw-quote-accuracy.txt`, a self-check over my own Markdown).
> `NOTE-the-four-mixed-outputs-two-are-real.md`.

## The headline is the negative

**35 of 79 outputs carry no marker of any class measured here** — 35 of 80 at `HEAD`, item 65's output being placed. The corpus is
mostly unplaceable — and that *is* the answer to item 64, not a shortfall in
it. What has changed is that the statement now rests on a test whose
false-positive rate against known answers is **measured at zero** rather than
assumed.

## What this does not do

- It does **not** claim the 35 are on the anchor's line. *Undecidable* means
  undecidable — item 61 proved the test one-way, and `raw-attack4.txt` is
  still in this set while being **known mixed**.
- It does **not** claim literals are the only remaining class. Output
  formatting, timestamps and file layout were **not** examined.
- The `distinctive` rule is a judgement stated in the source. A different rule
  would place a different number; what is measured is that **this** rule
  contradicts **zero** known answers.
- It does **not** retract item 61 or any placement. It **adds** to them, and
  the union is reported beside the parts.
- It does **not** file an issue. Nothing here is a defect in EFO — it is a
  fact about the **provenance of evidence this review inherited**.
- No network, no GPU, no workspace built. Two refs read and named. The
  anchor's working tree is untouched, and it does **not** touch `main` or
  another agent's branch.
- **MEASURED:** both literal corpora over full ancestry, the three candidate
  classes' coverage, the five contradictions and their cause, the corrected
  sets, the agreement count, the 47, the union. **REASONED:** nothing.

> **Three expectations of mine failed and were corrected to the measurement:**
> suite-size coverage of the open set (I predicted 2, it is **5**), usage-line
> coverage (0 → **1**), and the union arithmetic above (36/7 → **35/5** with
> **4 mixed**). This probe's own output joins the corpus it scans and prints
> marker literals, so it is excluded structurally — the **third** such
> exclusion, and the count is asserted so a fourth cannot appear unnoticed.
>
> **Updated 2026-08-03 by item 70.** The exclusion set is now **five**, and the
> assertion here is what forced each new one to be named. Item 70's
> corpus-wide swallowing sweep also found the marker set **short by one class**
> — test-module filenames — which moves the union reported above from
> **36/5/4/38** to **37 anchor / 6 divergent / 3 mixed / 37 undecidable**.
> Nothing in this note's own measurement is retracted; two outputs move,
> `raw-full-final.txt` and `raw-proxy-mocks.txt`.
>
> **Updated again by item 71**, whose output lands and is placed on the
> **anchor's** line by the string-literal test: population **83 → 84**,
> undecidable **50 → 51**, newly placed **9 → 10**, union anchor **36 → 37**.
> **Item 72's output** is undecidable by every class measured: population
> **85**, undecidable **52**, union still open **39**.

Pre-registered permissions unchanged: `gpu: false`, `network: false`,
`performance_metrics: false`; gates `allow_skips: false`,
`require_validation: true`, `require_known_answer_check: true`,
`require_independent_verification: true`.

**SUBMITTED, not VERIFIED.** Re-running my own evidence is a re-run, not
independent confirmation.

| Artifact | SHA-256 |
|---|---|
| `raw/probe_what_else_places_an_output.py` | `fb9bfef96eeca7349a5348d23f707e3d343dfbb4a56d1ca6e59337fbe74a8215` |
| `raw/raw-what-else-places-an-output.txt` | `c3cb4f052149a34a05e6b70444fa825052c405e804a7377ce279b257f97ff44f` |
