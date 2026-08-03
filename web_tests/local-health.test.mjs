import assert from "node:assert/strict";
import { webcrypto } from "node:crypto";
import test from "node:test";

if (!globalThis.crypto) {
  Object.defineProperty(globalThis, "crypto", { value: webcrypto });
}

const { internals, onRequestGet, onRequestPost } = await import(
  "../functions/api/local-health.js"
);
const { internals: snapshotInternals } = await import(
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

function payload(overrides = {}) {
  return {
    schema_version: "1.0",
    generated_at: new Date().toISOString(),
    collection_interval_seconds: 120,
    device_alias: "Local research workstation",
    cpu_percent: 8,
    memory: {
      used_gib: 26.2,
      total_gib: 31.8,
      percent: 82.4,
    },
    disk: {
      free_gib: 26.5,
      total_gib: 954,
      percent: 97.2,
    },
    uptime_seconds: 3000,
    process_count: 458,
    ...overrides,
  };
}

async function signedRequest(value, secret = "x".repeat(40)) {
  const body = JSON.stringify(value);
  const timestamp = Math.floor(Date.now() / 1000).toString();
  const signature = await snapshotInternals.hmacHex(
    secret,
    `${timestamp}.${body}`,
  );
  return new Request("https://dashboard.example/api/local-health", {
    method: "POST",
    headers: {
      "content-type": "application/json",
      "x-efo-timestamp": timestamp,
      "x-efo-signature": `sha256=${signature}`,
    },
    body,
  });
}

test("stress index has a reproducible known answer", () => {
  assert.equal(internals.rawStressIndex(payload()), 49.4);
  assert.equal(internals.stressStatus(49.4), "moderate");
  assert.equal(internals.stressStatus(70), "high");
  assert.equal(internals.stressStatus(85), "critical");
});

test("signed local health is validated, projected, and stored", async () => {
  const kv = new MemoryKv();
  const secret = "s".repeat(40);
  const response = await onRequestPost({
    request: await signedRequest(payload(), secret),
    env: {
      EFO_MONITOR_KV: kv,
      EFO_LOCAL_INGEST_SECRET: secret,
    },
  });
  assert.equal(response.status, 200);
  const result = await response.json();
  assert.equal(result.stress_index, 49.4);
  assert.equal(result.stress_status, "moderate");

  const stored = JSON.parse(await kv.get("local:latest"));
  assert.equal(stored.device_alias, "Local research workstation");
  assert.equal(stored.history.length, 1);
  assert.equal(stored.history[0].memory_percent, 82.4);
  assert.doesNotMatch(JSON.stringify(stored), /secret|hostname|command|processes/);
});

test("invalid signature and extra fields fail closed", async () => {
  const environment = {
    EFO_MONITOR_KV: new MemoryKv(),
    EFO_LOCAL_INGEST_SECRET: "s".repeat(40),
  };
  const invalidSignature = await onRequestPost({
    request: await signedRequest(payload(), "wrong".repeat(10)),
    env: environment,
  });
  assert.equal(invalidSignature.status, 401);

  const withExtraField = await onRequestPost({
    request: await signedRequest(
      { ...payload(), hostname: "private-host" },
      environment.EFO_LOCAL_INGEST_SECRET,
    ),
    env: environment,
  });
  assert.equal(withExtraField.status, 400);
  const body = await withExtraField.json();
  assert.match(body.detail, /top-level fields/);
});

test("recent same-session samples are smoothed but reboot samples are not", () => {
  const current = payload({
    cpu_percent: 100,
    memory: { used_gib: 31.8, total_gib: 31.8, percent: 100 },
    disk: { free_gib: 0, total_gib: 954, percent: 100 },
    uptime_seconds: 4000,
  });
  const previous = {
    generated_at: new Date(Date.now() - 120_000).toISOString(),
    uptime_seconds: 3880,
    stress_index: 50,
  };
  const smoothed = internals.projectHealth(current, previous);
  assert.ok(smoothed.stress_index < smoothed.stress_index_raw);

  const rebooted = internals.projectHealth(
    { ...current, uptime_seconds: 30 },
    previous,
  );
  assert.equal(rebooted.stress_index, rebooted.stress_index_raw);
});

test("view token protects local health reads", async () => {
  const kv = new MemoryKv();
  await kv.put("local:latest", JSON.stringify({ ok: true }));
  const unauthorized = await onRequestGet({
    request: new Request("https://dashboard.example/api/local-health"),
    env: { EFO_MONITOR_KV: kv, EFO_VIEW_TOKEN: "correct" },
  });
  assert.equal(unauthorized.status, 401);

  const authorized = await onRequestGet({
    request: new Request("https://dashboard.example/api/local-health", {
      headers: { authorization: "Bearer correct" },
    }),
    env: { EFO_MONITOR_KV: kv, EFO_VIEW_TOKEN: "correct" },
  });
  assert.equal(authorized.status, 200);
});

test("health check reveals configuration state without secrets", async () => {
  const response = await onRequestGet({
    request: new Request(
      "https://dashboard.example/api/local-health?health=1",
    ),
    env: {
      EFO_MONITOR_KV: new MemoryKv(),
      EFO_LOCAL_INGEST_SECRET: "hidden",
    },
  });
  const body = await response.json();
  assert.equal(body.configured, true);
  assert.equal(body.has_snapshot, false);
  assert.doesNotMatch(JSON.stringify(body), /hidden/);
});
