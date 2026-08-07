// EFO at main (5694ab45): what do the three Node test files actually assert,
// and which of #13 / #14 could they catch?
//
// Queue item 32. `NOTE-what-the-test-suite-cannot-catch.md` token-searched
// `web_tests/` and stopped there, naming the gap in its own scope: "#13 and
// #14 live in functions/api/*.js, and adjudicating chat.test.mjs and
// snapshot.test.mjs line by line is a separate pass."
//
// This is that pass, and unlike the Python side it can EXECUTE. Node v22 is
// present and these handlers run offline against a stubbed KV, so where the
// Python probes had to reason about reachability this one calls the shipped
// function and reads what it returns.
//
// The answer for both issues is the same shape, and it is sharper than
// "absent by name": THE TEST EXISTS, AND IT EXERCISES ONLY THE INPUT THE GUARD
// ALREADY HANDLES.
//
//   node probe_node_suite.mjs

import { webcrypto } from "node:crypto";
import { readFileSync } from "node:fs";
import { execFileSync } from "node:child_process";

if (!globalThis.crypto) {
  Object.defineProperty(globalThis, "crypto", { value: webcrypto });
}

const SOURCE = "/tmp/efo-prov";
let FAIL = 0;

function check(name, expected, observed) {
  const ok = String(observed).includes(String(expected));
  if (!ok) FAIL += 1;
  console.log(`  [${ok ? "ok" : "!! UNEXPECTED !!"}] ${name}`);
  console.log(`        expected: ${expected}`);
  console.log(`        observed: ${observed}`);
}

const read = (p) => readFileSync(`${SOURCE}/${p}`, "utf8");

// ---------------------------------------------------------------- A
console.log("########## A. POSITIVE CONTROL ##########");
const head = execFileSync("git", ["-C", SOURCE, "rev-parse", "HEAD"], {
  encoding: "utf8",
}).trim();
const dirty = execFileSync("git", ["-C", SOURCE, "status", "--porcelain"], {
  encoding: "utf8",
}).trim();
check("probe source is main 5694ab45",
  "5694ab455139f1e72d946bc2fe7e42c7c0c8a43a", head);
check("  with no working-tree modification", "dirty: ''", `dirty: '${dirty}'`);

const FILES = ["chat.test.mjs", "local-health.test.mjs", "snapshot.test.mjs"];
let tests = 0;
let asserts = 0;
for (const file of FILES) {
  const text = read(`web_tests/${file}`);
  const t = (text.match(/^test\(/gm) || []).length;
  const a = (text.match(/assert\./g) || []).length;
  tests += t;
  asserts += a;
  console.log(`    ${file.padEnd(24)} ${String(t).padStart(3)} tests, ` +
    `${String(a).padStart(3)} assertions`);
}
check("Node test functions", "tests: 37", `tests: ${tests}`);
check("  assertions across them", "assertions: 120", `assertions: ${asserts}`);
console.log("  37 matches the `# tests 37` the runner itself reports, so the");
console.log("  count is checked against the runner rather than assumed.");

// ---------------------------------------------------------------- B
console.log("\n########## B. #13 first finding - the refusal gate is Korean-only ##########");
const chatSource = read("functions/api/chat.js");
const gate = chatSource.split("\n")[203].trim();
console.log(`    chat.js:204  ${gate}`);
const alternatives = gate.match(/\/([^/]+)\/\.test/)[1].split("|");
const latin = alternatives.filter((word) => /[A-Za-z]/.test(word));
check("  the gate has this many alternatives", "alternatives: 11",
  `alternatives: ${alternatives.length}`);
check("  and not one contains a Latin letter", "latin: 0",
  `latin: ${latin.length} ${JSON.stringify(latin)}`);

const theTest = read("web_tests/chat.test.mjs").split("\n").slice(220, 225);
console.log("    the only test of it, chat.test.mjs:221-225:");
for (const line of theTest) console.log(`      ${line}`);
check("  its input is Korean, so it exercises only the covered path",
  "중단해줘", theTest.join("\n"));

// EXECUTED, not reasoned: drive the shipped function with each phrasing.
const { internals: chat } = await import(`${SOURCE}/functions/api/chat.js`);
const fixture = {
  generated_at: "2026-07-31T03:00:00.000Z",
  workspace: { next_milestone: "gate", workflow_progress_percent: 50 },
  projects: [{ name: "System 1.5", progress_percent: 40, phase: "G1" }],
  agents: [], tasks: [], gpus: [], history: [], activity: [], alerts: [],
  system: { memory: {}, disk: {} },
};
const REFUSAL = "읽기 전용이므로";
const PHRASINGS = [
  ["ko  the test's own input", "GPU 0 학습을 중단해줘"],
  ["en  stop the training on GPU 0", "stop the training on GPU 0"],
  ["en  restart the run", "restart the run"],
  ["en  delete the checkpoint", "delete the checkpoint"],
  ["en  deploy to the server", "deploy to the server"],
];
const refused = [];
for (const [label, query] of PHRASINGS) {
  const answer = chat.deterministicAnswer(query, fixture);
  const hit = answer.includes(REFUSAL);
  if (hit) refused.push(label);
  console.log(`    ${hit ? "REFUSED " : "not refused"}  ${label}`);
}
check("  only the Korean phrasing draws the read-only refusal",
  "refused: 1", `refused: ${refused.length} ${JSON.stringify(refused)}`);
console.log("  That is #13's first finding, driven rather than argued. The");
console.log("  test at chat.test.mjs:221 passes either way, because its input");
console.log("  is one the gate already matches. It cannot fail on this defect.");

// ---------------------------------------------------------------- C
console.log("\n########## C. #13 second finding - the test ASSERTS the behaviour ##########");
const chatTest = read("web_tests/chat.test.mjs");
const instructionsAssertion = chatTest
  .split("\n")
  .find((line) => line.includes("captured.instructions"));
console.log(`    chat.test.mjs  ${instructionsAssertion.trim()}`);
check("  the suite asserts snapshot text lands in `instructions`",
  "assert.match(captured.instructions, /최신 EFO 스냅샷 JSON/)",
  instructionsAssertion.trim());
console.log("  #13's second finding is that snapshot text is concatenated into");
console.log("  the model `instructions` block. The suite does not merely miss");
console.log("  that - it REQUIRES it. A fix that moved the snapshot out of");
console.log("  `instructions` would turn this test red.");
console.log("  This is the second instance of the shape #19 showed: the test");
console.log("  encodes the same decision the issue objects to. There the test");
console.log("  EXCLUDED `last_event_hash` from a comparison; here it ASSERTS");
console.log("  the grounding placement. Neither test is wrong on its own terms.");
console.log("  What both mean is that the suite cannot be the thing that");
console.log("  notices - and #13 is about placement, not about whether the");
console.log("  snapshot is sanitized first: `sanitizeSnapshot` at chat.js:235");
console.log("  does run, and the write-up should not be read as saying");
console.log("  otherwise.");

// ---------------------------------------------------------------- D
console.log("\n########## D. #14 - the guard is exact-match, the test picks a listed key ##########");
const { internals: snap } = await import(`${SOURCE}/functions/api/snapshot.js`);
const listed = read("functions/api/snapshot.js")
  .split("const FORBIDDEN_KEYS = new Set([")[1]
  .split("]);")[0]
  .match(/"([a-z]+)"/g)
  .map((s) => s.replaceAll('"', ""));
check("  FORBIDDEN_KEYS entries", "entries: 12", `entries: ${listed.length}`);
console.log(`    ${JSON.stringify(listed)}`);

const sensitiveTest = read("web_tests/snapshot.test.mjs")
  .split("\n")
  .find((line) => line.includes("must-not-pass"));
console.log(`    the only test of it:  ${sensitiveTest.trim()}`);
check("  and the key it injects is IN the set", "password",
  sensitiveTest.trim());

// EXECUTED: the compound names #14 names, through the shipped guard.
const CANDIDATES = [
  ["password", "the test's own key"],
  ["api_key", "#14"],
  ["gpu_uuid", "#14"],
  ["command_line", "#14"],
  ["ssh_key", "#14"],
  ["access_token", "#14 shape"],
  ["env_vars", "#14 shape"],
];
const caught = [];
for (const [key, why] of CANDIDATES) {
  const violation = snap.hasForbiddenKey({ source: { [key]: "x" } }, "$");
  if (violation) caught.push(key);
  console.log(`    ${violation ? "CAUGHT " : "passes "}  ${key.padEnd(14)} ${why}`);
}
check("  of the seven, this many are caught", "caught: 1",
  `caught: ${caught.length} ${JSON.stringify(caught)}`);
console.log("  #14 driven through the shipped guard rather than argued from");
console.log("  the source. This is a RE-CONFIRMATION of an issue already");
console.log("  filed, so it is reported here and NOT filed again.");
console.log("  The point for this pass is the test: it injects `password`, a");
console.log("  key the set contains, so it passes with the defect present.");

// ---------------------------------------------------------------- E
console.log("\n########## E. local-health.test.mjs yielded NOTHING new ##########");
console.log("  Six tests: a reproducible stress-index known answer, signature");
console.log("  validation and fail-closed on extra fields, session-aware");
console.log("  smoothing, view-token protection, and a health endpoint that");
console.log("  reports configuration state without secrets.");
console.log("  `ADDENDUM-chat-refusal-and-grounding.md` already measured");
console.log("  local-health.js as the strongest shape in the repository, and");
console.log("  reading its tests did not change that or add a finding.");
console.log("  Said plainly rather than dressed up as a thorough pass.");
const healthTest = read("web_tests/local-health.test.mjs");
check("  it does contain a genuine known-answer test",
  "stress index has a reproducible known answer", healthTest);

// ---------------------------------------------------------------- F
console.log("\n########## F. what this pass does NOT establish ##########");
console.log("  * It does not run the three files as a SUITE - that is what CI");
console.log("    does, and `ADDENDUM-main-is-red-and-a-push-run-is-not-a-pr-run.md`");
console.log("    reports the current 35/2. This probe calls exported functions");
console.log("    directly, which is a different thing and is labelled as such.");
console.log("  * It does not claim the Node tests are weak. 37 tests and 120");
console.log("    assertions include several this review has cited APPROVINGLY -");
console.log("    the transport-assertion projection tests are why #6's data");
console.log("    contract holds. Nothing here asserts something false.");
console.log("  * #13's OpenAI path is exercised with a stubbed `globalThis.fetch`.");
console.log("    Whether a real model ignores the read-only instruction is");
console.log("    UNMEASURED and unmeasurable here - `network: false`.");
console.log("  * MEASURED: the inventory, the gate's alternatives, all five");
console.log("    phrasings, all seven key candidates, both test inputs.");
console.log("    REASONED: that a test passing on the covered input means it");
console.log("    cannot fail on the uncovered one - which for these two guards");
console.log("    follows from the executed results above, not from inspection.");

console.log(`\n########## ${FAIL} unexpected result(s) ##########`);
console.log("Executed here: exported functions from chat.js and snapshot.js,");
console.log("offline, against literals built in this file. No network, no GPU,");
console.log("no performance measurement - pre-registered permissions unchanged.");
console.log("No issue filed: #13 and #14 already exist and a re-confirmation is");
console.log("a comment, not a new issue.");
console.log("SUBMITTED, not VERIFIED.");
process.exit(0);
