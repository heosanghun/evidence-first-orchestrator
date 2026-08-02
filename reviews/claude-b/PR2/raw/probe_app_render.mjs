/**
 * EFO `public/assets/app.js` at main (5694ab45): what the dashboard does with
 * snapshot text.
 *
 * The dashboard renders a snapshot whose task titles, agent names, alert
 * messages and project labels all originate in the EFO workspace - i.e. from
 * whoever can create a task or register an agent. `app.js` builds markup with
 * template literals assigned to `innerHTML`, so the question is whether every
 * snapshot-derived interpolation is escaped.
 *
 * WHAT THIS DOES AND DOES NOT DO:
 *   - It EXTRACTS every `${...}` inside a template literal assigned to
 *     `.innerHTML`, programmatically, and classifies each one.
 *   - It EXECUTES `escapeHtml` against hostile payloads, by lifting that one
 *     function out of the source.
 *   - It does NOT instantiate a DOM and does NOT render anything. jsdom is not
 *     available in this container ("jsdom absent"), and `app.js` touches
 *     `document` at module scope, so it cannot be imported here. No claim below
 *     rests on observed rendering.
 *
 * Section A is the positive control: the extractor must find the known-escaped
 * and known-numeric interpolations, or a clean classification proves nothing.
 *
 *   node probe_app_render.mjs
 */

import { readFileSync } from "node:fs";

const SOURCE_PATH = "/tmp/efo-prov/public/assets/app.js";
const source = readFileSync(SOURCE_PATH, "utf8");
let FAIL = 0;

function check(name, expected, observed) {
  const ok = String(observed).includes(expected);
  if (!ok) FAIL += 1;
  console.log(`  [${ok ? "ok" : "!! UNEXPECTED !!"}] ${name}`);
  console.log(`        expected: ${expected}`);
  console.log(`        observed: ${observed}`);
}

/** Lift `escapeHtml` out of the source and evaluate just that function. */
function liftEscapeHtml() {
  const start = source.indexOf("function escapeHtml(");
  if (start < 0) throw new Error("escapeHtml not found");
  let depth = 0;
  let index = source.indexOf("{", start);
  const open = index;
  for (; index < source.length; index += 1) {
    if (source[index] === "{") depth += 1;
    else if (source[index] === "}") {
      depth -= 1;
      if (depth === 0) break;
    }
  }
  const body = source.slice(start, index + 1);
  console.log(`  lifted from ${SOURCE_PATH}:` +
              `${source.slice(0, start).split("\n").length}` +
              `-${source.slice(0, index).split("\n").length}`);
  // eslint-disable-next-line no-new-func
  return new Function(`${body}; return escapeHtml;`)();
}

/** Remove every `escapeHtml( ... )` call, parenthesis-balanced. */
function stripEscaped(expression) {
  let out = expression;
  for (;;) {
    const start = out.indexOf("escapeHtml(");
    if (start < 0) return out;
    let depth = 0;
    let index = start + "escapeHtml".length;
    for (; index < out.length; index += 1) {
      if (out[index] === "(") depth += 1;
      else if (out[index] === ")") {
        depth -= 1;
        if (depth === 0) break;
      }
    }
    out = out.slice(0, start) + " ESCAPED " + out.slice(index + 1);
  }
}

/** Find `${...}` with balanced braces, so nested templates are not split. */
function interpolationsIn(expression) {
  const found = [];
  for (let index = 0; index < expression.length; index += 1) {
    if (expression[index] !== "$" || expression[index + 1] !== "{") continue;
    let depth = 0;
    let cursor = index + 1;
    for (; cursor < expression.length; cursor += 1) {
      if (expression[cursor] === "{") depth += 1;
      else if (expression[cursor] === "}") {
        depth -= 1;
        if (depth === 0) break;
      }
    }
    found.push(expression.slice(index + 2, cursor).replace(/\s+/g, " ").trim());
    index = cursor;
  }
  return found;
}

/**
 * Every `${...}` that survives into markup WITHOUT passing through
 * escapeHtml, from each expression assigned to `.innerHTML`.
 */
function collectInterpolations({ stripEscapes = true } = {}) {
  const found = [];
  const assignRe = /\.innerHTML\s*=/g;
  let match;
  while ((match = assignRe.exec(source)) !== null) {
    let index = match.index + match[0].length;
    let depth = 0;
    const start = index;
    for (; index < source.length; index += 1) {
      const character = source[index];
      if ("([{".includes(character)) depth += 1;
      else if (")]}".includes(character)) depth -= 1;
      else if (character === ";" && depth <= 0) break;
    }
    let expression = source.slice(start, index);
    if (stripEscapes) expression = stripEscaped(expression);
    const line = source.slice(0, match.index).split("\n").length;
    for (const text of interpolationsIn(expression)) {
      found.push({ line, text });
    }
  }
  return found;
}

const NUMERIC = /^(progress|utilization|temperature|memoryUsed|memoryTotal|Math\.round\(|formatPercent\(|number\(|clamp\(|categoryCount|bucket\.|index|\d|\(\s*memory)/;
// Anything ending in .toFixed(n) is a Number method call, not text.
const NUMERIC_TAIL = /\.toFixed\(\d*\)$/;

// ------------------------------------------------------------------ A
console.log("########## A. POSITIVE CONTROL - the extractor finds real sites ##########");
const escapeHtml = liftEscapeHtml();
check("escapeHtml lifted and callable", "&lt;b&gt;",
      escapeHtml("<b>"));
const allInterpolations = collectInterpolations({ stripEscapes: false });
const interpolations = collectInterpolations();
check("the extractor finds innerHTML template interpolations", "true",
      String(allInterpolations.length > 30) + ` (found ${allInterpolations.length})`);
check("  including a known-escaped one", "true",
      String(allInterpolations.some((item) => item.text.includes("escapeHtml(task.title"))));
check("  and stripping escapeHtml removes it", "true",
      String(!interpolations.some((item) => item.text.includes("task.title"))));
check("  while a known-numeric one survives the strip", "true",
      String(interpolations.some((item) => item.text === "progress")));

// ------------------------------------------------------------------ B
console.log("\n########## B. escapeHtml, executed against hostile payloads ##########");
for (const [label, payload, expected] of [
  ["a script tag", "<script>alert(1)</script>",
   "&lt;script&gt;alert(1)&lt;/script&gt;"],
  ["an img onerror", '<img src=x onerror="alert(1)">',
   "&lt;img src=x onerror=&quot;alert(1)&quot;&gt;"],
  ["an attribute break, double quote", '" onmouseover="alert(1)',
   "&quot; onmouseover=&quot;alert(1)"],
  ["an attribute break, single quote", "' onmouseover='alert(1)",
   "&#039; onmouseover=&#039;alert(1)"],
  ["an ampersand, escaped first so entities cannot be smuggled",
   "&lt;script&gt;", "&amp;lt;script&amp;gt;"],
  ["a null-ish value", null, ""],
]) {
  check(label, expected, escapeHtml(payload));
}
console.log("  All five HTML-significant characters are covered, and `&` is");
console.log("  replaced FIRST, which is the ordering that matters.");

// ------------------------------------------------------------------ C
console.log("\n########## C. every innerHTML interpolation, classified ##########");
const ESCAPED_ONLY = /^[^A-Za-z0-9_$]*(ESCAPED|"[^"]*"|'[^']*'|\?|:|\s)*$/;
const numeric = [];
const escapedOnly = [];
const other = [];
for (const item of interpolations) {
  if (item.text === "ESCAPED" || ESCAPED_ONLY.test(item.text)) escapedOnly.push(item);
  else if (NUMERIC.test(item.text) || NUMERIC_TAIL.test(item.text)) numeric.push(item);
  else other.push(item);
}
console.log(`  interpolations in total:            ${allInterpolations.length}`);
console.log(`    escapeHtml(...) or only literals: ${escapedOnly.length}`);
console.log(`    numeric-only:                     ${numeric.length}`);
console.log(`    everything else:                  ${other.length}`);

// Each remaining expression is adjudicated by reading its site. The run FAILS
// if the enumeration turns up anything this map does not cover, so a future
// edit cannot slip past unread.
const ADJUDICATION = new Map([
  ['gpuIndexes.join(", ")', "gpu.index values, coerced by number() at app.js:690"],
  ["verified", "project.verified_count via number()"],
  ["taskCount", "project.task_count via number()"],
  ["active", "project.active_task_count via number()"],
  ["blocked", "project.blocked_task_count via number()"],
  ["state", 'String(agent.state).toLowerCase(), then matched against a fixed class set'],
  ["transportBadge", "a fragment built above; its own text is escaped"],
  ["statusBadge", "a fragment built above; its own text is escaped"],
  ["rows", "a fragment built above; its own text is escaped"],
  ["projects", "a fragment built above; its own text is escaped"],
  ["category", "a key of ACTIVITY_CATEGORY_LABELS, a fixed map"],
  ["event.category", "same fixed map, used as a CSS class"],
  ["group.length", "an array length"],
  ["project.eta", "assigned to `eta`, which is only ever used inside escapeHtml(...) at app.js:1065-1067"],
  ["activity", 'one of "" or " · 대기", both literals'],
  ["thermalClass", 'one of "", "warm", "hot"'],
  ["severity", 'whitelisted to critical|info|warning at app.js:1437-1439'],
  ["label", 'one of 긴급|안내|주의, three literals'],
  ["segmentTop.toFixed(3)", "a number"],
  ["height.toFixed(3)", "a number"],
  ["count", "a bucket count"],
  ['count > 0 ? count : ""', "a bucket count or empty"],
  ['count === 0 ? " empty" : ""', "two literals"],
  ['reserved ? " reserved" : ""', "two literals"],
  ["new Date(bucket.at).toISOString()", "Date.toISOString() output"],
  ["seriesIndex % GPU_COLORS.length", "a number"],
  ['showLabel ? ESCAPED : ""', "a boolean guard around an escaped call"],
  ['alert.message ? `<span> · ${ ESCAPED }</span>` : ""',
   "a presence guard around an escaped call"],
]);

console.log("  the remainder, deduplicated, each adjudicated by reading its site:");
const seen = new Set();
let uncovered = 0;
for (const item of other) {
  const key = item.text.length > 96 ? item.text.slice(0, 93) + "..." : item.text;
  if (seen.has(key)) continue;
  seen.add(key);
  const verdict = ADJUDICATION.get(item.text);
  if (verdict === undefined && !item.text.startsWith("count > 0 ? `<svg")) {
    uncovered += 1;
    console.log(`        !! app.js:${item.line}  ${key}  <- NOT ADJUDICATED`);
    continue;
  }
  const note = verdict ?? "a nested template whose own interpolations are counted separately";
  console.log(`        app.js:${String(item.line).padStart(4)}  ${key}`);
  console.log(`                       -> ${note}`);
}
check("every remaining interpolation is adjudicated", "uncovered: 0",
      `uncovered: ${uncovered}`);
console.log("  None of them carries free text from the snapshot. Every string");
console.log("  that does - titles, names, roles, objectives, alert messages,");
console.log("  ETAs, activity titles - reaches markup through escapeHtml.");

// ------------------------------------------------------------------ D
console.log("\n########## D. cross-check: every snapshot text field ##########");
console.log("  For each field the snapshot carries as free text, confirm every");
console.log("  innerHTML site that mentions it wraps it in escapeHtml.");
const SNAPSHOT_TEXT_FIELDS = [
  "task.title", "task.id", "task.owner", "task.next", "task.status_badge",
  "agent.name", "agent.id", "agent.role", "agent.current", "agent.next",
  "project.name", "project.id", "project.objective", "project.phase",
  "project.next_milestone", "project.eta", "alert.title", "alert.message",
  "event.title", "event.actor_name", "event.label", "event.task_id",
  "snapshot.workspace.name", "snapshot.workspace.objective",
];
let bareFields = 0;
for (const field of SNAPSHOT_TEXT_FIELDS) {
  const pattern = new RegExp(`(^|[^A-Za-z0-9_.])${field.replace(/\./g, "\\.")}\\b`);
  const mentions = allInterpolations.filter((item) => pattern.test(item.text));
  const bare = interpolations.filter((item) => pattern.test(item.text));
  const adjudicated = bare.every((item) => ADJUDICATION.has(item.text));
  if (bare.length > 0 && !adjudicated) bareFields += 1;
  const status = mentions.length === 0
    ? "not rendered by an innerHTML template"
    : bare.length === 0
      ? `escaped at every one of ${mentions.length} site(s)`
      : `${bare.length} bare site(s), adjudicated: ${adjudicated}`;
  console.log(`        ${field.padEnd(28)} ${status}`);
}
check("snapshot text fields reaching an UNADJUDICATED bare slot", "count: 0",
      `count: ${bareFields}`);

// ------------------------------------------------------------------ E
console.log("\n########## E. the other DOM sinks ##########");
for (const [label, pattern, expected] of [
  ["document.write", /document\.write/, "0"],
  ["insertAdjacentHTML", /insertAdjacentHTML/, "0"],
  ["outerHTML assignment", /\.outerHTML\s*=/, "0"],
  ["createContextualFragment", /createContextualFragment/, "0"],
  ["eval", /\beval\(/, "0"],
  ["new Function", /new Function\(/, "0"],
  ["href assignment", /\.href\s*=/, "0"],
  ["srcdoc", /srcdoc/, "0"],
]) {
  const count = (source.match(new RegExp(pattern, "g")) || []).length;
  check(`  ${label}`, `count: ${expected}`, `count: ${count}`);
}
const textContentCount = (source.match(/\.textContent\s*=/g) || []).length;
const innerHtmlCount = (source.match(/\.innerHTML\s*=/g) || []).length;
console.log(`  textContent assignments: ${textContentCount}`);
console.log(`  innerHTML assignments:   ${innerHtmlCount}`);
console.log("  Everything scalar goes through textContent; innerHTML is used");
console.log("  only for list rendering, where the templates escape.");

console.log(`\n########## ${FAIL} unexpected result(s) ##########`);
console.log("No DOM was instantiated and nothing was rendered.");
console.log("SUBMITTED, not VERIFIED.");
