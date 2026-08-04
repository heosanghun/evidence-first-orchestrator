# Every published mark tally, re-derived — and one of them double-counted

Reproduce with `raw/probe_published_mark_tallies.py`; raw output in
`raw/raw-published-mark-tallies.txt`. **26 checks, 0 unexpected.**
A **map that corrects a count of mine** — no issue filed, nothing about EFO
claimed.

**Scope, stated first:** 2 marker sets, 5 doubled slots, 4 published table rows
parsed from the note, 8 numbers in them, 2 further published counts, 1 that
moves, 0 verdicts that move.

## What item 70 left open, in its own words

That round found the marker "sets" are concatenated tuples whose groups
overlap — **162 slots for 160 anchor markers, 309 for 306 divergent** — and
measured that de-duplicating changes no *verdict*, because presence is
presence. It then said plainly:

> *It would have mattered to any tally of **occurrences**, and this review has
> published such tallies.*

This is that pass.

## The population is read out of the document

The four rows of item 67's mixed-outputs table are **parsed from the note**
rather than typed into the probe. A tally typed into the probe would go on
agreeing with a number the note no longer states; a parsed one moves when the
document moves.

## One of eight numbers was wrong

| output | published | slotted | de-duplicated |
|---|---|---|---|
| `raw-attack-prov-main.txt` | 2 / 2 | 2 / 2 | 2 / 2 |
| `raw-w4-replay.txt` | ~~3 / 5~~ → **3 / 4** | 3 / **5** | 3 / **4** |
| `raw-full-final.txt` | 1 / 2 | 1 / 2 | 1 / 2 |
| `raw-quote-accuracy.txt` | 10 / 2 | 10 / 2 | 10 / 2 |

`raw-w4-replay.txt`'s divergent marks were published as **five**. They are
**four**. `transfer-orchestrator` occupies **two slots** in the tuple — I
hand-added it as a "known" token *and* the literal derivation produces it from
the divergent source — and a count taken over the tuple counted it twice. Both
halves of that are measured here (`hand: True derived: True`), not asserted.

The row is amended in place in item 67's note, with a dated banner.

> **A published number was wrong and the conclusion it supported was not.**
> Four marks is still both lines, and `raw-w4-replay.txt` names both refs by
> design — its verdict stays **GENUINE**.

## The tallies that cannot move, and why

Two other published counts are of a different kind, and the difference is the
reason the sweep finds one mover rather than five:

| tally | value | can it double? |
|---|---|---|
| item 67: `author_identity` occurs **twice** in `raw-full-final.txt` | 2 | **no** — one named token, one slot |
| item 70: `raw-class2b-census.txt` carries **two** anchor marks | 2 | **no** — neither is a doubled token |

A count of **one named token's occurrences** cannot be inflated by a set that
lists that token twice. The inflation needs a count taken **over the set**.
Both surviving tallies are of the first kind.

## What this does not establish

- It does **not** retract item 67. Three of its four rows reproduce exactly,
  the fourth moves by **one**, and no verdict in it changes.
- It does **not** re-open the classification. Item 70 already measured that
  de-duplication changes **0 of 83** verdicts; this round is about the counts
  printed beside them.
- The population is the tallies this review **published in Markdown** — parsed
  from the note for the table, named for the rest. A tally that exists only
  inside a raw output and was never quoted in a write-up is **out of scope**,
  and that is a stated bound rather than a claim that none exists.
- It does **not** file an issue. Nothing here is about EFO's behaviour.
- This probe prints the doubled tokens themselves, so its own output joins the
  **marker-printing exclusion set** — the **sixth** — and the four corpus pins
  assert that count so a seventh cannot appear unnoticed.
- No network, no GPU, no workspace built. Two refs read and **both named**. The
  anchor's working tree is untouched, and it does **not** touch `main` or
  another agent's branch.
- **MEASURED:** both marker sets as slots and as markers, the five doubled
  tokens, all four published rows re-derived twice, the one that moved and its
  cause, the two single-token tallies that cannot move. **REASONED:** nothing.

Pre-registered permissions unchanged: `gpu: false`, `network: false`,
`performance_metrics: false`; gates `allow_skips: false`,
`require_validation: true`, `require_known_answer_check: true`,
`require_independent_verification: true`.

**SUBMITTED, not VERIFIED.** Re-running my own evidence is a re-run, not
independent confirmation.

| Artifact | SHA-256 |
|---|---|
| `raw/probe_published_mark_tallies.py` | `9dbcecee822a9a543218d182dae74c91747dabc0eda889796ee621c4edaeb1ea` |
| `raw/raw-published-mark-tallies.txt` | `e56d9b05181faf73d1509559183f53e577547d70fded15a39a1067152f859a77` |
