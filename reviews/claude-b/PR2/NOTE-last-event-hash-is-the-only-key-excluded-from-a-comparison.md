# `last_event_hash` is the only key the product excludes from a comparison — a negative result

Reproduce with `raw/probe_every_key_excluded_from_a_comparison.py`; raw output
in `raw/raw-every-key-excluded-from-a-comparison.txt`. **26 checks, 0
unexpected.** A **map with a negative result** — no issue filed, nothing
retracted.

**Scope, stated first:** 16 package modules, 3 exclusion mechanisms, every site
of each classified, 5 filtered comprehensions of which **4** exclude a key by
name, **1** key name in total, 2 candidate second exemptions driven, 5 tamper
drives, 2 controls.

## The question item 71 raised

That round found `last_event_hash` excluded **by name** from all four
projection comparisons, which is what lets it be forged into a signed record.
The obvious next question is whether any **other** key has that property.

Three mechanisms can drop a key before an equality, all enumerated from the
AST rather than grepped:

| | mechanism | sites |
|---|---|---|
| **M1** | a mapping comprehension carrying an `if` filter | **5** |
| **M2** | a comparison that iterates *one* side's keys | **1** |
| **M3** | a `pop`/`del` of a named key on a mapping | **1** |

## M1: five sites, four exclusions, one key name

Four are the `last_event_hash` sites item 71 named — `workspace.py:469`,
`:494`, `:516`, `:1510` — re-derived here rather than cited. The **set of key
names excluded anywhere in the package is `['last_event_hash']`**, and every
site of it is the same task projection.

The fifth, `independence.py:121`, filters by **type** inside a policy parser,
not by key name before a comparison. My first sweep of this round matched `if`
conditions containing `!=` or `in` and never saw it; walking the AST does. The
split is asserted exhaustive in both directions.

## M2 and M3: driven, not argued away

`_require_proxy_grant` validates the grant against **five named keys** plus
three checked by hand, so any other key in the grant is never looked at
*there*. The question is whether anything else looks at it — and the whole
grant lives inside the task projection, which **is** compared:

| tamper | result |
|---|---|
| an extra key added to the grant | **CAUGHT** `IntegrityError: Task T1 projection differs from the signed ledger` |
| the grant's `branch` altered | **CAUGHT** |
| `consumed_at` set to a timestamp | **CAUGHT** |

M3's single site, `pending.pop("external_status", None)`, is a state **write**
in `requeue` — the field's absence is then signed, so nothing is hidden from a
comparison.

## Agent records are compared whole

| tamper | result |
|---|---|
| a non-id field forged | **CAUGHT** `Agent 'antigravity' registration differs from the signed ledger` |
| an extra key added | **CAUGHT** |

`list_agents` compares each record against the signed one **whole**, then
checks the id **set** separately — two guards, which is why item 72 measured
both an edit and deleting all three as caught.

## Two controls, each of which cost me a wrong answer first

1. Setting `consumed_at` to `None` read **UNCAUGHT** — until I noticed the
   field already held `None` at grant time. A mutation that writes the value
   already there is not a tamper.
2. The fix for that was a *moved* check — and its first version compared the
   **file's bytes**. Re-serialising alone changes those, so it called the
   no-op a real change. It compares the parsed **value** now.

> A driver that does not prove the input moved will report a guard as absent
> when nothing was ever driven at it.

## What this does not establish

- The answer is **negative**, and that is the result: `last_event_hash` is
  alone. **Item 71's finding does not generalise.**
- The three mechanisms are the ones enumerable from the AST. A key dropped by
  a helper that *returns* a filtered mapping would not appear as a
  comprehension at a comparison site — a stated bound, not a claim that none
  exists.
- **A lead, not driven this round:** `independence.py:121` silently **drops** a
  policy agent whose identity is not a dict, while the sibling check *raises*
  when `agents` itself is not a dict. A malformed entry is discarded where a
  malformed container is refused. Whether a dropped identity weakens an
  independence verdict is **unmeasured**.
- It does **not** re-open #19, and it does **not** file an issue — two
  candidate gaps were driven and both are covered.
- No network, no GPU. Tempfile workspaces, removed before the results print.
  The anchor's working tree is untouched, and it does **not** touch `main` or
  another agent's branch.
- **MEASURED:** all three mechanisms enumerated from the AST, every site
  classified, the excluded-key set, five tamper drives each with a
  value-moved assertion, two controls. **REASONED:** nothing.

Pre-registered permissions unchanged: `gpu: false`, `network: false`,
`performance_metrics: false`; gates `allow_skips: false`,
`require_validation: true`, `require_known_answer_check: true`,
`require_independent_verification: true`.

**SUBMITTED, not VERIFIED.** Re-running my own evidence is a re-run, not
independent confirmation.

| Artifact | SHA-256 |
|---|---|
| `raw/probe_every_key_excluded_from_a_comparison.py` | `0f8d47a01d8c06e5fc37c9ea20670e82ccbdd0856a4bedc81ca3e41951bb53dc` |
| `raw/raw-every-key-excluded-from-a-comparison.txt` | `b2b73a6f1683d606d15de22834142f64d534ee3f9137c9e3eb905065b3657795` |
