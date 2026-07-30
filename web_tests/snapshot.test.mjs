import assert from "node:assert/strict";
import { webcrypto } from "node:crypto";
import test from "node:test";

if (!globalThis.crypto) {
  Object.defineProperty(globalThis, "crypto", { value: webcrypto });
}

const { internals, onRequestGet, onRequestPost } = await import(
  "../functions/api/snapshot.js"
);

class MemoryKv {
  constructor() {
    this.values = new Map();
  }

  async get(key) {
    return this.values.get(key) ?? null;
  }

  async put(key, value) {
    this.values.set(key, value);
  }
}

function validSnapshot() {
  return {
    schema_version: "1.0",
    generated_at: new Date().toISOString(),
    collection_interval_seconds: 120,
    source: {
      mode: "collector",
      host: "gpu-server",
      collector: "efo-monitor/1.0",
      ledger: { valid: true, event_count: 18 },
    },
    workspace: {
      name: "System 1.5",
      objective: "Evidence first",
      next_milestone: "Independent verification",
      workflow_progress_percent: 50,
    },
    agents: [],
    tasks: [],
    gpus: [
      {
        index: 0,
        name: "NVIDIA RTX A6000",
        utilization_percent: 75,
        memory_used_mib: 1024,
        memory_total_mib: 49140,
        temperature_c: 65,
        power_w: 220,
        projects: [{ name: "System1.5" }],
      },
    ],
    system: {
      hostname: "gpu-server",
      load_1m: 1,
      uptime_seconds: 100,
      memory: { used_gib: 1, total_gib: 2, percent: 50 },
      disk: { used_gib: 2, total_gib: 10, free_gib: 8, percent: 20 },
    },
    history: [],
    activity: [
      {
        sequence: 18,
        at: new Date().toISOString(),
        actor: "codex",
        actor_name: "Codex",
        action: "task.verified",
        label: "검증 통과",
        category: "success",
        task_id: "P1b-2",
        title: "Cluster-aware significance tests",
      },
    ],
    alerts: [],
  };
}

async function signedRequest(snapshot, secret = "test-secret") {
  const timestamp = String(Math.floor(Date.now() / 1000));
  const body = JSON.stringify(snapshot);
  const signature = await internals.hmacHex(secret, `${timestamp}.${body}`);
  return new Request("https://example.test/api/snapshot", {
    method: "POST",
    headers: {
      "content-type": "application/json",
      "x-efo-timestamp": timestamp,
      "x-efo-signature": `sha256=${signature}`,
    },
    body,
  });
}

test("health reports missing configuration without exposing secrets", async () => {
  const response = await onRequestGet({
    request: new Request("https://example.test/api/snapshot?health=1"),
    env: {},
  });
  assert.equal(response.status, 200);
  assert.deepEqual(await response.json(), {
    ok: false,
    configured: false,
    has_snapshot: false,
    view_protected: false,
  });
});

test("signed snapshot is validated, stored, and served", async () => {
  const kv = new MemoryKv();
  const env = {
    EFO_MONITOR_KV: kv,
    EFO_INGEST_SECRET: "test-secret",
  };
  const request = await signedRequest(validSnapshot());
  const postResponse = await onRequestPost({ request, env });
  assert.equal(postResponse.status, 200);
  assert.equal((await postResponse.json()).gpu_count, 1);

  const getResponse = await onRequestGet({
    request: new Request("https://example.test/api/snapshot"),
    env,
  });
  assert.equal(getResponse.status, 200);
  const stored = await getResponse.json();
  assert.equal(stored.source.mode, "live");
  assert.match(stored.source.received_at, /^\d{4}-\d{2}-\d{2}T/);
  assert.equal(stored.gpus[0].index, 0);
  assert.equal(stored.activity[0].label, "검증 통과");
});

test("malformed activity history is rejected", async () => {
  const snapshot = validSnapshot();
  snapshot.activity[0].sequence = "18";
  const env = {
    EFO_MONITOR_KV: new MemoryKv(),
    EFO_INGEST_SECRET: "test-secret",
  };
  const response = await onRequestPost({
    request: await signedRequest(snapshot),
    env,
  });
  assert.equal(response.status, 400);
  assert.match((await response.json()).detail, /invalid activity event/);
});

test("transport-attested pending task is accepted without becoming running", async () => {
  const snapshot = validSnapshot();
  snapshot.tasks.push({
    id: "P1b-8",
    title: "Freeze run identity",
    owner: "claude",
    state: "pending",
    canonical_state: "pending",
    external_phase: "working",
    status_source: "transport_assertion",
    status_badge: "운반자 보고",
    lease_active: false,
    progress_percent: 40,
    next: "외부 구현 결과 대기",
    updated_at: new Date().toISOString(),
  });
  const env = {
    EFO_MONITOR_KV: new MemoryKv(),
    EFO_INGEST_SECRET: "test-secret",
  };
  const response = await onRequestPost({
    request: await signedRequest(snapshot),
    env,
  });
  assert.equal(response.status, 200);
  const stored = JSON.parse(await env.EFO_MONITOR_KV.get("snapshot:latest"));
  assert.equal(stored.tasks[0].state, "pending");
  assert.equal(stored.tasks[0].external_phase, "working");
  assert.equal(stored.tasks[0].status_source, "transport_assertion");
});

test("transport assertion cannot contradict canonical task state", async () => {
  const snapshot = validSnapshot();
  snapshot.tasks.push({
    id: "P1b-8",
    title: "Freeze run identity",
    owner: "claude",
    state: "running",
    canonical_state: "running",
    external_phase: "working",
    status_source: "transport_assertion",
    status_badge: "운반자 보고",
    lease_active: false,
    progress_percent: 40,
    next: "외부 구현 결과 대기",
    updated_at: new Date().toISOString(),
  });
  const env = {
    EFO_MONITOR_KV: new MemoryKv(),
    EFO_INGEST_SECRET: "test-secret",
  };
  const response = await onRequestPost({
    request: await signedRequest(snapshot),
    env,
  });
  assert.equal(response.status, 400);
  assert.match(
    (await response.json()).detail,
    /external status conflicts with canonical state/,
  );
});

test("invalid signature is rejected before parsing", async () => {
  const env = {
    EFO_MONITOR_KV: new MemoryKv(),
    EFO_INGEST_SECRET: "different-secret",
  };
  const response = await onRequestPost({
    request: await signedRequest(validSnapshot()),
    env,
  });
  assert.equal(response.status, 401);
  assert.equal((await response.json()).error, "invalid_signature");
});

test("sensitive fields are rejected even with a valid signature", async () => {
  const snapshot = validSnapshot();
  snapshot.source.password = "must-not-pass";
  const env = {
    EFO_MONITOR_KV: new MemoryKv(),
    EFO_INGEST_SECRET: "test-secret",
  };
  const response = await onRequestPost({
    request: await signedRequest(snapshot),
    env,
  });
  assert.equal(response.status, 400);
  const payload = await response.json();
  assert.equal(payload.error, "invalid_snapshot");
  assert.match(payload.detail, /forbidden sensitive field/);
});

test("view token protects reads but not health status", async () => {
  const kv = new MemoryKv();
  await kv.put("snapshot:latest", JSON.stringify(validSnapshot()));
  const env = {
    EFO_MONITOR_KV: kv,
    EFO_INGEST_SECRET: "test-secret",
    EFO_VIEW_TOKEN: "viewer-key",
  };
  const denied = await onRequestGet({
    request: new Request("https://example.test/api/snapshot"),
    env,
  });
  assert.equal(denied.status, 401);

  const allowed = await onRequestGet({
    request: new Request("https://example.test/api/snapshot", {
      headers: { authorization: "Bearer viewer-key" },
    }),
    env,
  });
  assert.equal(allowed.status, 200);
});
