# `public/assets/app.js` at `main` `5694ab45` — every snapshot string reaches markup through `escapeHtml`; no issue filed

Reproduce with `raw/probe_app_render.mjs` (Node v22.22.2); raw output in
`raw/raw-app-render.txt`. **21 checks, 0 unexpected.**

The dashboard renders a snapshot whose task titles, agent names, alert
messages, project labels and activity titles all originate in the EFO
workspace — i.e. from whoever can create a task or register an agent. `app.js`
builds markup with template literals assigned to `innerHTML`, so the question
is whether every snapshot-derived interpolation is escaped.

## What this measured, and what it did not

- It **extracted** every `${…}` inside a template literal assigned to
  `.innerHTML`, programmatically, with balanced braces so nested templates are
  not split, and with every `escapeHtml( … )` call removed first (parenthesis
  balanced) so what remains is exactly what reaches markup unescaped.
- It **executed** `escapeHtml` against hostile payloads, by lifting that one
  function out of the source (`app.js:144-151`) and evaluating it.
- It did **not** instantiate a DOM and did **not** render anything. `jsdom` is
  absent from this container and `app.js` touches `document` at module scope,
  so it cannot be imported here. **No claim below rests on observed
  rendering.**

## `escapeHtml` is complete

```
<script>alert(1)</script>       -> &lt;script&gt;alert(1)&lt;/script&gt;
<img src=x onerror="alert(1)">  -> &lt;img src=x onerror=&quot;alert(1)&quot;&gt;
" onmouseover="alert(1)         -> &quot; onmouseover=&quot;alert(1)
' onmouseover='alert(1)         -> &#039; onmouseover=&#039;alert(1)
&lt;script&gt;                  -> &amp;lt;script&amp;gt;
null                            -> ""
```

All five HTML-significant characters are covered, and `&` is replaced **first**,
which is the ordering that matters — otherwise `&lt;` produced by a later
replacement would be re-encoded and an attacker could smuggle entities through.
Both attribute-quote styles are escaped, so an interpolation inside
`title="…"` or `aria-label="…"` cannot break out.

## Every interpolation, enumerated then adjudicated

```
interpolations in total:            89
  escapeHtml(...) or only literals: 37
  numeric-only:                     27
  everything else:                  25
```

The 25 are listed in full in the raw output, deduplicated, each with the reason
it is safe — and the probe **fails the run if the enumeration turns up anything
the adjudication map does not cover**, so a future edit cannot slip past
unread. The categories:

| Kind | Examples | Why it is not text |
|---|---|---|
| pre-built fragments | `transportBadge`, `statusBadge`, `rows`, `projects` | assembled above; their own contents are escaped |
| fixed maps | `category`, `event.category` | keys of `ACTIVITY_CATEGORY_LABELS` |
| whitelisted values | `severity` (`critical\|info\|warning`), `state`, `thermalClass`, `label` | constrained to a fixed set at the assignment |
| counts and numbers | `verified`, `taskCount`, `group.length`, `temperature.toFixed(0)` | passed through `number()` / `clamp()` |
| literal pairs | `reserved ? " reserved" : ""`, `count === 0 ? " empty" : ""` | two string literals |

One is worth naming because it looks alarming and is not: `project.eta` at
`app.js:1037`. It appears bare because it is assigned to a local, but that
local is only ever consumed inside `escapeHtml( … )` at `app.js:1065-1067`.
That matters more than it sounds — `eta` comes from `parse_progress` in the
collector, i.e. from container **log text**, and `snapshot.js` does not
shape-check `gpus[].projects[]` at all (issue #14), so it is one of the few
genuinely free-form strings in the snapshot. It is escaped.

## Cross-check: every snapshot text field

| Field | Sites |
|---|---|
| `task.title`, `task.owner`, `task.next`, `task.status_badge` | escaped at every site |
| `task.id` | escaped at all 3 sites |
| `agent.name`, `agent.id` | escaped at both sites each |
| `agent.role`, `agent.current`, `agent.next` | escaped at every site |
| `project.name`, `project.id` | escaped at both sites each |
| `project.objective`, `project.phase`, `project.next_milestone` | escaped at every site |
| `project.eta` | one bare mention, adjudicated above |
| `alert.title`, `alert.message` | escaped at every site |
| `event.title`, `event.actor_name`, `event.label`, `event.task_id` | escaped at every site |
| `snapshot.workspace.name`, `snapshot.workspace.objective` | rendered via `textContent`, not `innerHTML` |

## The other DOM sinks are absent

Counted across the whole file:

```
document.write            0      eval                   0
insertAdjacentHTML        0      new Function           0
outerHTML assignment      0      href assignment        0
createContextualFragment  0      srcdoc                 0

textContent assignments:  80
innerHTML assignments:    18
```

Eighty scalar writes go through `textContent`; `innerHTML` is used only for
list rendering, where the templates escape. That ratio is the design working —
the risky sink is confined to the places that genuinely need markup, and every
one of those was checked.

## Harness bugs, caught before any conclusion

Three, all mine, only the corrected run reported.

The first mattered. My initial extractor used a non-greedy `\$\{(.*?)\}`, which
truncates a nested template at its first `}`. It reported `alert.message` as
reaching an unescaped slot — a finding I would have filed had I stopped there.
The site is
`${alert.message ? \`<span> · ${escapeHtml(alert.message)}</span>\` : ""}`, i.e.
escaped. Rewritten with balanced-brace scanning.

The second: `escapeHtml( … )` calls were not removed before scanning, so
escaped interpolations were still counted as candidates. Fixed by
parenthesis-balanced stripping.

The third: my numeric classifier missed `utilization`, `temperature.toFixed(0)`
and the two `(memoryX / 1024).toFixed(1)` forms, leaving six items unadjudicated
and the run failing. Broadened, and the two remaining `ESCAPED`-guard forms
were adjudicated explicitly rather than pattern-matched away.

## Scope

Every `.innerHTML` assignment in `public/assets/app.js`, `escapeHtml`, and a
sink census over the whole file. Not examined: the fetch/auth path, the chart
rendering beyond its interpolations, `public/index.html`'s own markup, and any
behaviour that requires a DOM.

Pre-registered permissions unchanged: `gpu: false`, `network: false`,
`performance_metrics: false`; gates `allow_skips: false`,
`require_validation: true`, `require_known_answer_check: true`,
`require_independent_verification: true`.

**SUBMITTED, not VERIFIED.**

| Artifact | SHA-256 |
|---|---|
| `raw/probe_app_render.mjs` | `c100d59254f07ed54cc4cc65d25d12ec498ec4220e301fd7b707576a15ef5a4d` |
| `raw/raw-app-render.txt` | `041c10e3ca82846942d6e1ee45e932fb53efc67977119095a253ac0ce403db23` |
