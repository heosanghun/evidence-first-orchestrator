/**
 * EFO `functions/api/snapshot.js` at main (5694ab45): the ingest/publish gate.
 *
 * This is the boundary where a snapshot becomes the public artifact that
 * README.md:359-361 describes:
 *
 *   "Public snapshots omit passwords, secrets, environment variables, command
 *    lines, PIDs, GPU UUIDs, ledger signatures, hashes, and event payloads."
 *
 * `NOTE-collector-redaction-holds.md` already measured that the collector does
 * not PRODUCE those. This measures whether the endpoint would ACCEPT them, via
 * `FORBIDDEN_KEYS` / `hasForbiddenKey` and the per-projection key sets.
 *
 * Handlers run as real exported functions with real Request/Response and a KV
 * double. Section A is the positive control.
 *
 *   node probe_snapshot_ingest.mjs
 */

import {
  internals as snap,
  onRequestGet as snapshotGet,
  onRequestPost as snapshotPost,
} from "/tmp/efo-prov/functions/api/snapshot.js";

let FAIL = 0;
const SECRET = "ingest-secret";

function check(name, expected, observed) {
  const ok = String(observed).includes(expected);
  if (!ok) FAIL += 1;
  console.log(`  [${ok ? "ok" : "!! UNEXPECTED !!"}] ${name}`);
  console.log(`        expected: ${expected}`);
  console.log(`        observed: ${observed}`);
}

function makeKv(initial = {}) {
  const store = new Map(Object.entries(initial));
  const calls = [];
  return {
    calls, store,
    async get(key) { calls.push(`get:${key}`); return store.get(key) ?? null; },
    async put(key, value) { calls.push(`put:${key}`); store.set(key, value); },
  };
}

const task = () => ({
  id: "T1", title: "train the model", owner: "claude", state: "running",
  canonical_state: "running", external_phase: null, status_source: "canonical",
  status_badge: null, lease_active: true, progress_percent: 55,
  next: "제출 준비", updated_at: new Date().toISOString(),
});

const agent = () => ({
  id: "claude", name: "Claude B", role: "구현검증 작업자", state: "working",
  current: "train the model", current_task_id: "T1", next: "제출 준비",
  progress_percent: 55, status_source: "canonical", status_badge: null,
  updated_at: new Date().toISOString(),
});

const baseSnapshot = () => ({
  schema_version: "1.0",
  generated_at: new Date().toISOString(),
  collection_interval_seconds: 120,
  source: { mode: "collector", collector: "efo-monitor/1.2" },
  workspace: { name: "System 1.5", workflow_progress_percent: 45 },
  agents: [agent()],
  tasks: [task()],
  projects: [],
  activity: [],
  gpus: [{
    index: 0, utilization_percent: 91, memory_used_mib: 40960,
    memory_total_mib: 81920, temperature_c: 71, power_w: 310, projects: [],
  }],
  system: { hostname: "gpu-server", load_1m: 0.3, uptime_seconds: 100 },
  history: [],
  alerts: [],
});

async function post(snapshot, { secret = SECRET, skew = 0, kv = makeKv() } = {}) {
  const raw = JSON.stringify(snapshot);
  const timestamp = String(Math.floor(Date.now() / 1000) + skew);
  const signature = await snap.hmacHex(secret, `${timestamp}.${raw}`);
  const request = new Request("https://dash.invalid/api/snapshot", {
    method: "POST",
    headers: {
      "content-type": "application/json",
      "x-efo-timestamp": timestamp,
      "x-efo-signature": `sha256=${signature}`,
    },
    body: raw,
  });
  const response = await snapshotPost({
    request,
    env: { EFO_MONITOR_KV: kv, EFO_INGEST_SECRET: SECRET },
  });
  return { status: response.status, body: await response.json(), kv };
}

// ------------------------------------------------------------------ A
console.log("########## A. POSITIVE CONTROL ##########");
{
  const result = await post(baseSnapshot());
  check("an honest snapshot is accepted", "200 ok=true",
        `${result.status} ok=${result.body.ok}`);
  check("  and stored", "put:snapshot:latest", result.kv.calls.join(","));

  const request = new Request("https://dash.invalid/api/snapshot");
  const response = await snapshotGet({ request, env: { EFO_MONITOR_KV: result.kv } });
  const served = await response.text();
  check("  and served back by GET", "200", String(response.status));
  check("  with the ingest stamp applied", '"mode":"live"',
        served.replaceAll(" ", "").slice(0, 400));
}

// ------------------------------------------------------------------ B
console.log("\n########## B. the transport gates ##########");
{
  const raw = JSON.stringify(baseSnapshot());
  const timestamp = String(Math.floor(Date.now() / 1000));
  const request = new Request("https://dash.invalid/api/snapshot", {
    method: "POST",
    headers: {
      "content-type": "application/json",
      "x-efo-timestamp": timestamp,
      "x-efo-signature": "sha256=" + "0".repeat(64),
    },
    body: raw,
  });
  const response = await snapshotPost({
    request,
    env: { EFO_MONITOR_KV: makeKv(), EFO_INGEST_SECRET: SECRET },
  });
  check("an unsigned snapshot", "401 invalid_signature",
        `${response.status} ${(await response.json()).error}`);

  const wrongKey = await post(baseSnapshot(), { secret: "not-the-secret" });
  check("a snapshot signed with the wrong secret", "401 invalid_signature",
        `${wrongKey.status} ${wrongKey.body.error}`);

  const stale = await post(baseSnapshot(), { skew: -3600 });
  check("a correctly signed hour-old replay", "401 invalid_timestamp",
        `${stale.status} ${stale.body.error}`);

  const future = await post(baseSnapshot(), { skew: 3600 });
  check("a correctly signed hour-in-the-future snapshot", "401 invalid_timestamp",
        `${future.status} ${future.body.error}`);
}

// ------------------------------------------------------------------ C
console.log("\n########## C. per-projection exact key sets ##########");
{
  const extraTask = baseSnapshot();
  extraTask.tasks[0].blocked_reason = "/abs/path/run.sh";
  const r1 = await post(extraTask);
  check("an extra field on a task projection",
        "400 task has unexpected or missing fields",
        `${r1.status} ${r1.body.detail}`);

  const extraAgent = baseSnapshot();
  extraAgent.agents[0].note = "x";
  const r2 = await post(extraAgent);
  check("an extra field on an agent projection",
        "400 agent has unexpected or missing fields",
        `${r2.status} ${r2.body.detail}`);

  const missing = baseSnapshot();
  delete missing.tasks[0].status_badge;
  const r3 = await post(missing);
  check("a missing field on a task projection",
        "400 task has unexpected or missing fields",
        `${r3.status} ${r3.body.detail}`);
}

// ------------------------------------------------------------------ D
console.log("\n########## D. FORBIDDEN_KEYS: exact names only ##########");
console.log("  snapshot.js:6-19 lists: password passwd secret token environment");
console.log("  env command cmdline pid uuid ssh authorization");
console.log("  hasForbiddenKey compares key.toLowerCase() against that set.");
{
  console.log("  caught, at any depth:");
  for (const [label, mutate] of [
    ["gpus[0].uuid", (s) => { s.gpus[0].uuid = "GPU-abc"; }],
    ["system.token", (s) => { s.system.token = "t"; }],
    ["system.nested.secret", (s) => { s.system.nested = { secret: "s" }; }],
    ["alerts[0].pid", (s) => { s.alerts.push({ pid: 1234 }); }],
    ["source.command", (s) => { s.source.command = "python train.py"; }],
    ["system.cmdline", (s) => { s.system.cmdline = "python train.py"; }],
  ]) {
    const snapshot = baseSnapshot();
    mutate(snapshot);
    const result = await post(snapshot);
    check(`  ${label}`, "400 forbidden sensitive field",
          `${result.status} ${result.body.detail}`);
  }

  console.log("  NOT caught - the same idea under a compound name:");
  for (const [label, mutate] of [
    ["system.api_key", (s) => { s.system.api_key = "sk-ant-0123"; }],
    ["system.access_token", (s) => { s.system.access_token = "ghp_0123"; }],
    ["gpus[0].gpu_uuid", (s) => { s.gpus[0].gpu_uuid = "GPU-abc"; }],
    ["gpus[0].process_id", (s) => { s.gpus[0].process_id = 918273645; }],
    ["system.command_line", (s) => { s.system.command_line = "python train.py --key=x"; }],
    ["system.ssh_key", (s) => { s.system.ssh_key = "ssh-ed25519 AAAA"; }],
    ["system.environment_variables", (s) => { s.system.environment_variables = { A: "1" }; }],
  ]) {
    const snapshot = baseSnapshot();
    mutate(snapshot);
    const result = await post(snapshot);
    check(`  ${label}`, "200 ok=true",
          `${result.status} ok=${result.body.ok}${result.body.detail ? " " + result.body.detail : ""}`);
  }

  console.log("  and values are never inspected, only key names:");
  const valueSnapshot = baseSnapshot();
  valueSnapshot.system.note =
    "AKIA1234567890EXAMPLE /home/operator/.ssh/id_ed25519 python train.py";
  const valueResult = await post(valueSnapshot);
  check("  a credential, a private-key path and a command line as a VALUE",
        "200 ok=true", `${valueResult.status} ok=${valueResult.body.ok}`);
  const served = valueResult.kv.store.get("snapshot:latest");
  check("  and it is what GET will serve", "AKIA1234567890EXAMPLE present: true",
        `AKIA1234567890EXAMPLE present: ${served.includes("AKIA1234567890EXAMPLE")}`);
}

// ------------------------------------------------------------------ E
console.log("\n########## E. which containers are shape-checked at all ##########");
{
  const wild = baseSnapshot();
  wild.system = { anything: { at: { all: [1, 2, 3] } } };
  const r1 = await post(wild);
  check("system replaced with an arbitrary object", "200 ok=true",
        `${r1.status} ok=${r1.body.ok}`);

  const wildGpu = baseSnapshot();
  wildGpu.gpus[0].arbitrary = { free: "text" };
  const r2 = await post(wildGpu);
  check("an arbitrary extra field on a GPU entry", "200 ok=true",
        `${r2.status} ok=${r2.body.ok}`);

  const wildAlert = baseSnapshot();
  wildAlert.alerts.push({ whatever: "free text", nested: { deep: "value" } });
  const r3 = await post(wildAlert);
  check("an arbitrary alert object", "200 ok=true",
        `${r3.status} ok=${r3.body.ok}`);

  console.log("  so the shape-checked containers are tasks, agents, projects");
  console.log("  and activity; system, gpus[] extras, alerts[], history[],");
  console.log("  workspace and source rely on FORBIDDEN_KEYS alone.");
}

// ------------------------------------------------------------------ F
console.log("\n########## F. constantTimeEqual ##########");
{
  for (const [left, right, expected] of [
    ["abc", "abc", "true"],
    ["abc", "abd", "false"],
    ["abc", "abcabc", "false"],
    ["", "", "true"],
    ["", "a", "false"],
    ["a", "aa", "false"],
    ["ab", "abab", "false"],
  ]) {
    check(`  equal(${JSON.stringify(left)}, ${JSON.stringify(right)})`,
          `= ${expected}`, `= ${snap.constantTimeEqual(left, right)}`);
  }
  console.log("  The length XOR seeds `difference`, so the cyclic index never");
  console.log("  lets a repeated string match a shorter one.");
}

console.log(`\n########## ${FAIL} unexpected result(s) ##########`);
console.log("SUBMITTED, not VERIFIED.");
