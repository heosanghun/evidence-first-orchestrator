All required checks pass on the committed state.

# Worker Metadata

- Worker: Claude B (implementation)
- Repository: `D:\AI\System1.5 - Codex\.efo-deliveries\EFO-5-source`
- Branch: `claude-b/EFO-5-agent-attribution-hardening`
- Base: `0828c0b6ff792da29317228679f7e962aec457ad`
- Head: `5a7f7f6` — `fix(monitor): fail closed on agent attribution and order cards by recency`
- Worktree: clean

# Implementation

`monitor/collector.py`, three behavioral changes:

1. **Fail-closed attribution.** New `attested_actor()` (`monitor/collector.py:696`) replaces the two inline equality comparisons in `task_actor_ids`. It returns an actor only when the record is a dict, the actor is a non-empty string, the actor resolves to a **dict** in the signed identity registry, and the claimed snapshot is a **dict exactly equal** to that resolved identity. The old expression `record.get("identity") == identity_registry.get(actor)` evaluated `None == None` to true, so an unregistered actor with no identity attested itself; that path is gone. `task_actor_ids` now drives both the `verification`/`identity` and `external_status`/`author_identity` pairs through the same helper. The owner path (registered ID under a valid ledger) is unchanged.

2. **Display ID is presentation only.** In `collect_efo` (`monitor/collector.py:997`), `relevant_actor_ids` is now `{efo_id, *identity_groups.get(efo_id, ())}`. The profile's `id` no longer seeds attribution and no longer looks up an alias group, so a colliding display ID cannot inherit an unrelated agent's tasks. `profile_id` is still used for the card's rendered `id`.

3. **Recency-first card selection.** `choose_agent_task` now sorts by `(-timestamp, class_priority, task_id)` instead of `(is_live, -timestamp, task_id)`. New `card_state_class()` classifies a record as `attention` when the card it would render reads blocked (canonical blocked/rejected/invalidated, transport-reported blocked, or an expired lease on claimed/running), `live` for pending/claimed/running/submitted work or any transport phase, and `terminal` otherwise. `CARD_CLASS_PRIORITY = {"attention": 0, "live": 1, "terminal": 2}` is a module constant, applied only on an exact timestamp tie, then the lexicographically lower task ID. `choose_agent_task` moved below `agent_state` because the class helper calls it.

`docs/OPERATIONS_DASHBOARD.md` documents the fail-closed attestation rule, the display-ID rule, and the recency-first ordering with the preregistered class priority.

Untouched: `task_to_view`, the canonical task rows, history, alerts, the privacy projection, the 11-field card shape, and every JS path.

# Tests

`tests/test_monitor_collector.py`: new `FrozenKnownAnswerTests` class (11 tests) plus a rewrite of the ordering test in the existing class.

The existing `test_live_task_outranks_newer_terminal_and_ties_use_task_id` asserted that an older live record beats a newer terminal one — the exact class-first behavior requirement 3 replaces. It is now `test_card_selection_is_recency_first_across_state_classes`, asserting the newer terminal record wins and that the live record wins once it is newer. `test_card_state_class_follows_rendered_card_urgency` pins the classifier and the priority constant.

I verified the new tests are real regressions by checking out the base `collector.py` and running only `FrozenKnownAnswerTests`: 6 failures and 9 errors covering known answers 1, 2, 3, 4, 6, and 7. Known answer 5 also held under the old ordering; its test guards the requirement rather than a pre-existing defect.

Results on the committed state:

- `PYTHONPATH=src python -m unittest discover -s tests -t . -v` → Ran 98 tests, OK (98 `... ok`, 0 failures, 0 skips)
- `node --test web_tests/snapshot.test.mjs` → tests 18, pass 18, fail 0, skipped 0, todo 0
- `python -m py_compile monitor/collector.py tests/test_monitor_collector.py` → exit 0
- `node --check functions/api/snapshot.js` → exit 0
- `node --check public/assets/app.js` → exit 0
- `git diff --check 0828c0b6ff792da29317228679f7e962aec457ad..HEAD` → exit 0, no output

# Known Answers

1. **Unregistered verifier, missing identity → no card.** `test_known_answer_1_unregistered_verifier_without_identity`: task verified by `ghost-verifier` with no `identity` key; the `ghost-verifier` profile stays fully idle and the task row is retained. `test_known_answer_1_partial_and_arbitrary_identity_never_attest` sweeps `None`, `{}`, actor-only, a field-dropped subset, a superset, a mutated principal, a list, and a string — none attest; only the exact dict does, and only for a registered actor.
2. **External author, missing `author_identity` → no card.** `test_known_answer_2_external_author_without_author_identity`: the `ghost-transport` profile is idle while the task keeps `external_phase=working` and `status_source=transport_assertion`. `test_known_answer_2_registered_author_needs_exact_identity` shows a registered author with a partial snapshot idle, and the same author with the exact snapshot correctly assigned.
3. **`{id: victim, efo_id: real}` with unrelated signed roots.** `test_known_answer_3_display_id_collision_does_not_widen`: the card renders `id=victim` but stays idle; a control profile with `efo_id=victim` does receive the task.
4. **Blocked July 30 vs pending July 1 → blocked card.** `test_known_answer_4_newer_block_outranks_older_live_task`: card is `NEW-BLOCK`, state `blocked`, and both rows keep their canonical states.
5. **Newer pending/verified vs blocked July 1 → newer card, old row retained.** `test_known_answer_5_newer_live_or_verified_outranks_older_block`, subtested for both pending and verified; `OLD-BLOCK` remains `blocked` in the task table.
6. **Equal timestamps → class priority, then task ID.** `test_known_answer_6_equal_timestamps_use_class_then_task_id`: `Z-BLOCK` beats `A-LIVE` and `Z-LIVE` beats `A-DONE` (class decides before ID), `TASK-A` beats `TASK-B` within each class, plus an end-to-end `collect_efo` tie.
7. **Every non-idle card names a retained task.** `test_known_answer_7_every_non_idle_card_names_a_retained_task`: four profiles over a mixed snapshot; each card is either fully idle or has an 11-field shape whose `current_task_id` is in the snapshot and whose title, next action, progress, status source, badge, timestamp, and state all match that task. `test_agent_card_keeps_exact_eleven_field_projection` pins the field list and order.

# Source Scope

`git diff --name-only 0828c0b6ff792da29317228679f7e962aec457ad..HEAD`:

```
docs/OPERATIONS_DASHBOARD.md
monitor/collector.py
tests/test_monitor_collector.py
```

Exactly the three authorized paths; no other tracked file changed, and no evidence file was written inside the repository.

# Result

All six required commands pass on the committed state with zero failures and zero skips, the write scope is exactly the three owned paths, and the worktree is clean at `5a7f7f6`. I make no verification claim — submission and independent verification are Codex's.

RESULT: READY
