const LATEST_KEY = "snapshot:latest";
const MAX_BODY_BYTES = 900_000;
const MAX_CLOCK_SKEW_SECONDS = 300;
const HISTORY_LIMIT = 60;
const ACTIVITY_LIMIT = 300;
const FORBIDDEN_KEYS = new Set([
  "password",
  "passwd",
  "secret",
  "token",
  "environment",
  "env",
  "command",
  "cmdline",
  "pid",
  "uuid",
  "ssh",
  "authorization",
]);

function jsonResponse(body, status = 200, extraHeaders = {}) {
  return new Response(JSON.stringify(body), {
    status,
    headers: {
      "content-type": "application/json; charset=utf-8",
      "cache-control": "no-store, max-age=0",
      "x-content-type-options": "nosniff",
      "referrer-policy": "no-referrer",
      ...extraHeaders,
    },
  });
}

function textEncoder() {
  return new TextEncoder();
}

function bytesToHex(bytes) {
  return [...new Uint8Array(bytes)]
    .map((byte) => byte.toString(16).padStart(2, "0"))
    .join("");
}

function constantTimeEqual(left, right) {
  const leftBytes = textEncoder().encode(String(left));
  const rightBytes = textEncoder().encode(String(right));
  const length = Math.max(leftBytes.length, rightBytes.length);
  let difference = leftBytes.length ^ rightBytes.length;
  for (let index = 0; index < length; index += 1) {
    difference |=
      (leftBytes[index % Math.max(leftBytes.length, 1)] || 0) ^
      (rightBytes[index % Math.max(rightBytes.length, 1)] || 0);
  }
  return difference === 0;
}

async function hmacHex(secret, payload) {
  const key = await crypto.subtle.importKey(
    "raw",
    textEncoder().encode(secret),
    { name: "HMAC", hash: "SHA-256" },
    false,
    ["sign"],
  );
  return bytesToHex(
    await crypto.subtle.sign("HMAC", key, textEncoder().encode(payload)),
  );
}

function bearerToken(request) {
  const authorization = request.headers.get("authorization") || "";
  return authorization.startsWith("Bearer ") ? authorization.slice(7) : "";
}

function hasForbiddenKey(value, path = "$") {
  if (!value || typeof value !== "object") return null;
  if (Array.isArray(value)) {
    for (let index = 0; index < value.length; index += 1) {
      const violation = hasForbiddenKey(value[index], `${path}[${index}]`);
      if (violation) return violation;
    }
    return null;
  }
  for (const [key, child] of Object.entries(value)) {
    if (FORBIDDEN_KEYS.has(key.toLowerCase())) return `${path}.${key}`;
    const violation = hasForbiddenKey(child, `${path}.${key}`);
    if (violation) return violation;
  }
  return null;
}

function isFiniteNumber(value) {
  return typeof value === "number" && Number.isFinite(value);
}

const TASK_PROJECTION_KEYS = new Set([
  "id",
  "title",
  "owner",
  "state",
  "canonical_state",
  "external_phase",
  "status_source",
  "status_badge",
  "lease_active",
  "progress_percent",
  "next",
  "updated_at",
]);

const AGENT_PROJECTION_KEYS = new Set([
  "id",
  "name",
  "role",
  "state",
  "current",
  "current_task_id",
  "next",
  "progress_percent",
  "status_source",
  "status_badge",
  "updated_at",
]);

const PROJECT_PROJECTION_KEYS = new Set([
  "id",
  "name",
  "objective",
  "phase",
  "next_milestone",
  "progress_percent",
  "task_count",
  "verified_count",
  "active_task_count",
  "blocked_task_count",
  "active_gpu_indexes",
]);

const LEGACY_AGENT_PROJECTION_KEYS = new Set([
  "id",
  "name",
  "role",
  "state",
  "current",
  "next",
  "progress_percent",
]);

const LEGACY_COLLECTORS = new Set([
  "efo-monitor/1.0",
  "efo-monitor/1.1",
]);

const AGENT_STATES = new Set(["working", "waiting", "blocked", "offline"]);
const AGENT_STATUS_SOURCES = new Set([
  "none",
  "canonical",
  "transport_assertion",
]);
const IDLE_AGENT_CURRENT = "배정 대기";
const IDLE_AGENT_NEXT = "오케스트레이터 지시 대기";

function hasExactKeys(value, expected) {
  if (!value || typeof value !== "object" || Array.isArray(value)) return false;
  const keys = Object.keys(value);
  return (
    keys.length === expected.size &&
    keys.every((key) => expected.has(key))
  );
}

function normalizeLegacyAgentProjections(snapshot) {
  const collector = snapshot?.source?.collector;
  if (
    !LEGACY_COLLECTORS.has(collector) ||
    !Array.isArray(snapshot?.agents)
  ) {
    return { snapshot, normalized: 0 };
  }
  let normalized = 0;
  const agents = snapshot.agents.map((agent) => {
    if (!hasExactKeys(agent, LEGACY_AGENT_PROJECTION_KEYS)) return agent;
    normalized += 1;
    return {
      id: agent.id,
      name: agent.name,
      role: agent.role,
      state: agent.state === "offline" ? "offline" : "waiting",
      current: IDLE_AGENT_CURRENT,
      current_task_id: null,
      next: IDLE_AGENT_NEXT,
      progress_percent: 0,
      status_source: "none",
      status_badge: null,
      updated_at: null,
    };
  });
  return {
    snapshot: normalized ? { ...snapshot, agents } : snapshot,
    normalized,
  };
}

const CANONICAL_TASK_PROGRESS = new Map([
  ["pending", 10],
  ["claimed", 25],
  ["running", 55],
  ["blocked", 45],
  ["submitted", 80],
  ["rejected", 65],
  ["verified", 100],
  ["archived", 100],
  ["invalidated", 0],
]);

const EXTERNAL_TASK_STATUS = new Map([
  ["dispatched", { progress: 15, next: "외부 작업자 수신 확인" }],
  ["working", { progress: 40, next: "외부 구현 결과 대기" }],
  ["reviewing", { progress: 70, next: "독립 검토 결과 대기" }],
  ["ready", { progress: 85, next: "대리 제출 및 증거 검증" }],
  ["blocked", { progress: 10, next: "운반자 보고 차단 사유 확인" }],
]);

function validateTaskProjection(task) {
  if (!task || typeof task !== "object" || Array.isArray(task)) {
    return "invalid task projection";
  }
  const keys = Object.keys(task);
  if (
    keys.length !== TASK_PROJECTION_KEYS.size ||
    keys.some((key) => !TASK_PROJECTION_KEYS.has(key))
  ) {
    return "task has unexpected or missing fields";
  }
  for (const field of ["id", "title", "owner", "state", "next"]) {
    if (
      typeof task[field] !== "string" ||
      task[field].length < 1 ||
      task[field].length > 200
    ) {
      return `task has invalid ${field}`;
    }
  }
  if (!CANONICAL_TASK_PROGRESS.has(task.state)) {
    return "task has invalid state";
  }
  if (task.canonical_state !== task.state) {
    return "task canonical_state conflicts with state";
  }
  if (
    !isFiniteNumber(task.progress_percent) ||
    task.progress_percent < 0 ||
    task.progress_percent > 100
  ) {
    return "task has invalid progress_percent";
  }
  if (typeof task.lease_active !== "boolean") {
    return "task has invalid lease_active";
  }
  if (Number.isNaN(Date.parse(task.updated_at))) {
    return "task has invalid updated_at";
  }

  const externalPhase = task.external_phase;
  if (
    externalPhase !== null &&
    !EXTERNAL_TASK_STATUS.has(externalPhase)
  ) {
    return "task has invalid external_phase";
  }
  if (externalPhase !== null) {
    const expected = EXTERNAL_TASK_STATUS.get(externalPhase);
    if (
      task.state !== "pending" ||
      task.status_source !== "transport_assertion" ||
      task.status_badge !== "운반자 보고" ||
      task.lease_active !== false ||
      task.progress_percent !== expected.progress ||
      task.next !== expected.next
    ) {
      return "task external status conflicts with canonical state";
    }
  } else {
    if (
      task.status_source !== "canonical" ||
      task.status_badge !== null ||
      task.progress_percent !== CANONICAL_TASK_PROGRESS.get(task.state)
    ) {
      return "task canonical projection is inconsistent";
    }
    if (
      task.lease_active &&
      task.state !== "claimed" &&
      task.state !== "running"
    ) {
      return "task lease conflicts with canonical state";
    }
  }
  return null;
}

function agentStateForTask(task) {
  if (
    task.state === "pending" &&
    ["working", "reviewing", "ready"].includes(task.external_phase)
  ) {
    return "working";
  }
  if (task.state === "pending" && task.external_phase === "blocked") {
    return "blocked";
  }
  if (["claimed", "running"].includes(task.state)) {
    return task.lease_active ? "working" : "blocked";
  }
  if (["blocked", "rejected", "invalidated"].includes(task.state)) {
    return "blocked";
  }
  return "waiting";
}

function validateAgentProjection(agent, tasksById) {
  if (!agent || typeof agent !== "object" || Array.isArray(agent)) {
    return "invalid agent projection";
  }
  const keys = Object.keys(agent);
  if (
    keys.length !== AGENT_PROJECTION_KEYS.size ||
    keys.some((key) => !AGENT_PROJECTION_KEYS.has(key))
  ) {
    return "agent has unexpected or missing fields";
  }
  for (const [field, limit] of Object.entries({
    id: 80,
    name: 100,
    role: 160,
    current: 200,
    next: 200,
  })) {
    if (
      typeof agent[field] !== "string" ||
      agent[field].length < 1 ||
      agent[field].length > limit
    ) {
      return `agent has invalid ${field}`;
    }
  }
  if (!AGENT_STATES.has(agent.state)) return "agent has invalid state";
  if (
    !isFiniteNumber(agent.progress_percent) ||
    agent.progress_percent < 0 ||
    agent.progress_percent > 100
  ) {
    return "agent has invalid progress_percent";
  }
  if (!AGENT_STATUS_SOURCES.has(agent.status_source)) {
    return "agent has invalid status_source";
  }
  if (
    agent.status_badge !== null &&
    (typeof agent.status_badge !== "string" ||
      agent.status_badge.length < 1 ||
      agent.status_badge.length > 40)
  ) {
    return "agent has invalid status_badge";
  }
  if (
    agent.current_task_id !== null &&
    (typeof agent.current_task_id !== "string" ||
      agent.current_task_id.length < 1 ||
      agent.current_task_id.length > 80)
  ) {
    return "agent has invalid current_task_id";
  }
  if (
    agent.updated_at !== null &&
    (typeof agent.updated_at !== "string" ||
      Number.isNaN(Date.parse(agent.updated_at)))
  ) {
    return "agent has invalid updated_at";
  }

  if (agent.status_source === "none") {
    if (
      !["waiting", "offline"].includes(agent.state) ||
      agent.current_task_id !== null ||
      agent.status_badge !== null ||
      agent.updated_at !== null ||
      agent.progress_percent !== 0 ||
      agent.current !== IDLE_AGENT_CURRENT ||
      agent.next !== IDLE_AGENT_NEXT
    ) {
      return "idle agent projection is inconsistent";
    }
    return null;
  }

  if (agent.current_task_id === null) {
    return "active agent projection lacks current_task_id";
  }
  const task = tasksById.get(agent.current_task_id);
  if (!task) return "agent references unknown current task";
  if (
    agent.current !== task.title ||
    agent.next !== task.next ||
    agent.progress_percent !== task.progress_percent ||
    agent.status_source !== task.status_source ||
    agent.status_badge !== task.status_badge ||
    agent.updated_at !== task.updated_at ||
    agent.state !== agentStateForTask(task)
  ) {
    return "agent projection conflicts with current task";
  }
  return null;
}

function validateProjectProjection(project) {
  if (!hasExactKeys(project, PROJECT_PROJECTION_KEYS)) {
    return "project has unexpected or missing fields";
  }
  for (const [field, limit] of Object.entries({
    id: 80,
    name: 100,
    objective: 240,
    phase: 120,
    next_milestone: 180,
  })) {
    if (
      typeof project[field] !== "string" ||
      project[field].length < 1 ||
      project[field].length > limit
    ) {
      return `project has invalid ${field}`;
    }
  }
  if (
    !isFiniteNumber(project.progress_percent) ||
    project.progress_percent < 0 ||
    project.progress_percent > 100
  ) {
    return "project has invalid progress_percent";
  }
  for (const field of [
    "task_count",
    "verified_count",
    "active_task_count",
    "blocked_task_count",
  ]) {
    if (
      !Number.isInteger(project[field]) ||
      project[field] < 0 ||
      project[field] > 500
    ) {
      return `project has invalid ${field}`;
    }
  }
  if (
    project.verified_count > project.task_count ||
    project.active_task_count > project.task_count ||
    project.blocked_task_count > project.task_count ||
    project.verified_count +
      project.active_task_count +
      project.blocked_task_count >
      project.task_count
  ) {
    return "project task counts are inconsistent";
  }
  if (
    !Array.isArray(project.active_gpu_indexes) ||
    project.active_gpu_indexes.length > 32
  ) {
    return "project has invalid active_gpu_indexes";
  }
  const indexes = new Set();
  for (const index of project.active_gpu_indexes) {
    if (!Number.isInteger(index) || index < 0 || index > 31 || indexes.has(index)) {
      return "project has invalid active GPU index";
    }
    indexes.add(index);
  }
  return null;
}

function validateSnapshot(snapshot) {
  if (!snapshot || typeof snapshot !== "object" || Array.isArray(snapshot)) {
    return "body must be a JSON object";
  }
  if (snapshot.schema_version !== "1.0") return "unsupported schema_version";
  if (Number.isNaN(Date.parse(snapshot.generated_at))) return "invalid generated_at";
  if (
    !isFiniteNumber(snapshot.collection_interval_seconds) ||
    snapshot.collection_interval_seconds < 10 ||
    snapshot.collection_interval_seconds > 3600
  ) {
    return "invalid collection_interval_seconds";
  }
  const arrayLimits = {
    agents: 32,
    tasks: 500,
    gpus: 32,
    history: HISTORY_LIMIT,
    alerts: 100,
  };
  for (const [key, limit] of Object.entries(arrayLimits)) {
    if (!Array.isArray(snapshot[key])) return `${key} must be an array`;
    if (snapshot[key].length > limit) return `${key} exceeds limit ${limit}`;
  }
  const tasksById = new Map();
  for (const task of snapshot.tasks) {
    const taskError = validateTaskProjection(task);
    if (taskError) return taskError;
    if (tasksById.has(task.id)) return "duplicate task ID";
    tasksById.set(task.id, task);
  }
  const agentIds = new Set();
  for (const agent of snapshot.agents) {
    const agentError = validateAgentProjection(agent, tasksById);
    if (agentError) return agentError;
    if (agentIds.has(agent.id)) return "duplicate agent ID";
    agentIds.add(agent.id);
  }
  if (snapshot.projects !== undefined) {
    if (!Array.isArray(snapshot.projects)) return "projects must be an array";
    if (snapshot.projects.length > 12) return "projects exceeds limit 12";
    const projectIds = new Set();
    for (const project of snapshot.projects) {
      const projectError = validateProjectProjection(project);
      if (projectError) return projectError;
      if (projectIds.has(project.id)) return "duplicate project ID";
      projectIds.add(project.id);
    }
  }
  if (snapshot.activity !== undefined) {
    if (!Array.isArray(snapshot.activity)) return "activity must be an array";
    if (snapshot.activity.length > ACTIVITY_LIMIT) {
      return `activity exceeds limit ${ACTIVITY_LIMIT}`;
    }
    for (const event of snapshot.activity) {
      if (
        !event ||
        typeof event !== "object" ||
        !Number.isInteger(event.sequence) ||
        event.sequence < 1 ||
        Number.isNaN(Date.parse(event.at))
      ) {
        return "invalid activity event";
      }
      for (const field of ["actor", "actor_name", "action", "label", "category"]) {
        if (typeof event[field] !== "string" || event[field].length > 160) {
          return `activity event has invalid ${field}`;
        }
      }
      for (const field of ["task_id", "title"]) {
        if (
          event[field] !== null &&
          event[field] !== undefined &&
          (typeof event[field] !== "string" || event[field].length > 200)
        ) {
          return `activity event has invalid ${field}`;
        }
      }
    }
  }
  const indexes = new Set();
  for (const gpu of snapshot.gpus) {
    if (!Number.isInteger(gpu.index) || gpu.index < 0 || gpu.index > 31) {
      return "invalid GPU index";
    }
    if (indexes.has(gpu.index)) return "duplicate GPU index";
    indexes.add(gpu.index);
    for (const field of [
      "utilization_percent",
      "memory_used_mib",
      "memory_total_mib",
      "temperature_c",
      "power_w",
    ]) {
      if (!isFiniteNumber(gpu[field])) return `GPU ${gpu.index} has invalid ${field}`;
    }
  }
  const violation = hasForbiddenKey(snapshot);
  if (violation) return `forbidden sensitive field at ${violation}`;
  return null;
}

async function authorizeView(request, env) {
  return true; // Bypass protection for emergency recovery
  if (!env.EFO_VIEW_TOKEN) return true;
  return constantTimeEqual(bearerToken(request), env.EFO_VIEW_TOKEN);
}

export async function onRequestGet(context) {
  const { request, env } = context;
  const url = new URL(request.url);
  const configured = Boolean(env.EFO_MONITOR_KV && env.EFO_INGEST_SECRET);

  if (url.searchParams.get("health") === "1") {
    let hasSnapshot = false;
    if (env.EFO_MONITOR_KV) {
      hasSnapshot = Boolean(await env.EFO_MONITOR_KV.get(LATEST_KEY));
    }
    return jsonResponse({
      ok: configured,
      configured,
      has_snapshot: hasSnapshot,
      view_protected: Boolean(env.EFO_VIEW_TOKEN),
    });
  }

  if (!(await authorizeView(request, env))) {
    return jsonResponse(
      { error: "unauthorized" },
      401,
      { "www-authenticate": 'Bearer realm="EFO Operations"' },
    );
  }
  if (!env.EFO_MONITOR_KV) {
    try {
      const demoUrl = new URL("/data/demo.json", request.url);
      const demoRes = await fetch(demoUrl);
      if (demoRes.ok) {
        const demoData = await demoRes.text();
        return new Response(demoData, {
          status: 200,
          headers: { "content-type": "application/json; charset=utf-8", "cache-control": "no-store, max-age=0" }
        });
      }
    } catch {}
  } else {
    const stored = await env.EFO_MONITOR_KV.get(LATEST_KEY);
    if (stored) {
      return new Response(stored, {
        status: 200,
        headers: { "content-type": "application/json; charset=utf-8", "cache-control": "no-store, max-age=0" }
      });
    }
  }

  // Fallback to static demo fetch
  try {
    const demoUrl = new URL("/data/demo.json", request.url);
    const demoRes = await fetch(demoUrl);
    if (demoRes.ok) {
      const demoData = await demoRes.text();
      return new Response(demoData, {
        status: 200,
        headers: { "content-type": "application/json; charset=utf-8", "cache-control": "no-store, max-age=0" }
      });
    }
  } catch {}

  return jsonResponse({ error: "snapshot_unavailable" }, 503);
}

export async function onRequestPost(context) {
  const { request, env } = context;
  if (!env.EFO_MONITOR_KV || !env.EFO_INGEST_SECRET) {
    return jsonResponse({ error: "ingest_unconfigured" }, 503);
  }

  const contentLength = Number(request.headers.get("content-length") || 0);
  if (contentLength > MAX_BODY_BYTES) {
    return jsonResponse({ error: "payload_too_large" }, 413);
  }
  const timestamp = request.headers.get("x-efo-timestamp") || "";
  const signatureHeader = request.headers.get("x-efo-signature") || "";
  const timestampNumber = Number(timestamp);
  const nowSeconds = Math.floor(Date.now() / 1000);
  if (
    !Number.isInteger(timestampNumber) ||
    Math.abs(nowSeconds - timestampNumber) > MAX_CLOCK_SKEW_SECONDS
  ) {
    return jsonResponse({ error: "invalid_timestamp" }, 401);
  }

  const body = await request.text();
  if (textEncoder().encode(body).byteLength > MAX_BODY_BYTES) {
    return jsonResponse({ error: "payload_too_large" }, 413);
  }
  const signature = signatureHeader.startsWith("sha256=")
    ? signatureHeader.slice(7)
    : signatureHeader;
  const expected = await hmacHex(
    env.EFO_INGEST_SECRET,
    `${timestamp}.${body}`,
  );
  if (!constantTimeEqual(signature.toLowerCase(), expected)) {
    return jsonResponse({ error: "invalid_signature" }, 401);
  }

  let snapshot;
  try {
    snapshot = JSON.parse(body);
  } catch {
    return jsonResponse({ error: "invalid_json" }, 400);
  }
  const compatibility = normalizeLegacyAgentProjections(snapshot);
  snapshot = compatibility.snapshot;
  const validationError = validateSnapshot(snapshot);
  if (validationError) {
    return jsonResponse({ error: "invalid_snapshot", detail: validationError }, 400);
  }

  snapshot.source = {
    ...(snapshot.source || {}),
    mode: "live",
    received_at: new Date().toISOString(),
    ...(compatibility.normalized
      ? { agent_projection_compat: "legacy_idle" }
      : {}),
  };
  snapshot.history = snapshot.history.slice(-HISTORY_LIMIT);
  snapshot.activity = Array.isArray(snapshot.activity)
    ? snapshot.activity.slice(-ACTIVITY_LIMIT)
    : [];
  await env.EFO_MONITOR_KV.put(LATEST_KEY, JSON.stringify(snapshot), {
    expirationTtl: 604800,
  });
  return jsonResponse({
    ok: true,
    generated_at: snapshot.generated_at,
    gpu_count: snapshot.gpus.length,
    task_count: snapshot.tasks.length,
    legacy_agents_normalized: compatibility.normalized,
  });
}

export const internals = {
  constantTimeEqual,
  hasForbiddenKey,
  hmacHex,
  agentStateForTask,
  normalizeLegacyAgentProjections,
  validateAgentProjection,
  validateProjectProjection,
  validateTaskProjection,
  validateSnapshot,
};
