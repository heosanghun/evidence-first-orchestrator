import { internals as snapshotInternals } from "./snapshot.js";

const LATEST_KEY = "local:latest";
const MAX_BODY_BYTES = 8_000;
const MAX_CLOCK_SKEW_SECONDS = 300;
const HISTORY_LIMIT = 60;
const EXPECTED_KEYS = new Set([
  "schema_version",
  "generated_at",
  "collection_interval_seconds",
  "device_alias",
  "cpu_percent",
  "memory",
  "disk",
  "uptime_seconds",
  "process_count",
]);
const MEMORY_KEYS = new Set(["used_gib", "total_gib", "percent"]);
const DISK_KEYS = new Set(["free_gib", "total_gib", "percent"]);

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

function bearerToken(request) {
  const authorization = request.headers.get("authorization") || "";
  return authorization.startsWith("Bearer ") ? authorization.slice(7) : "";
}

async function authorizeView(request, env) {
  if (!env.EFO_VIEW_TOKEN) return true;
  return snapshotInternals.constantTimeEqual(
    bearerToken(request),
    env.EFO_VIEW_TOKEN,
  );
}

function exactKeys(value, expected) {
  if (!value || typeof value !== "object" || Array.isArray(value)) return false;
  const keys = Object.keys(value);
  return (
    keys.length === expected.size && keys.every((key) => expected.has(key))
  );
}

function finiteInRange(value, minimum, maximum) {
  return (
    typeof value === "number" &&
    Number.isFinite(value) &&
    value >= minimum &&
    value <= maximum
  );
}

function validatePayload(payload) {
  if (!exactKeys(payload, EXPECTED_KEYS)) return "invalid top-level fields";
  if (payload.schema_version !== "1.0") return "unsupported schema version";
  const generatedAt = Date.parse(payload.generated_at);
  if (!Number.isFinite(generatedAt)) return "invalid generated_at";
  if (Math.abs(Date.now() - generatedAt) > 10 * 60 * 1000) {
    return "generated_at outside allowed window";
  }
  if (
    !Number.isInteger(payload.collection_interval_seconds) ||
    payload.collection_interval_seconds < 30 ||
    payload.collection_interval_seconds > 3600
  ) {
    return "invalid collection interval";
  }
  if (
    typeof payload.device_alias !== "string" ||
    payload.device_alias.trim().length < 1 ||
    payload.device_alias.length > 80
  ) {
    return "invalid device alias";
  }
  if (!finiteInRange(payload.cpu_percent, 0, 100)) {
    return "invalid CPU percent";
  }
  if (!exactKeys(payload.memory, MEMORY_KEYS)) return "invalid memory fields";
  if (!exactKeys(payload.disk, DISK_KEYS)) return "invalid disk fields";
  for (const field of ["used_gib", "total_gib", "percent"]) {
    const maximum = field === "percent" ? 100 : 1_000_000;
    if (!finiteInRange(payload.memory[field], 0, maximum)) {
      return `invalid memory ${field}`;
    }
  }
  for (const field of ["free_gib", "total_gib", "percent"]) {
    const maximum = field === "percent" ? 100 : 1_000_000;
    if (!finiteInRange(payload.disk[field], 0, maximum)) {
      return `invalid disk ${field}`;
    }
  }
  if (payload.memory.used_gib > payload.memory.total_gib) {
    return "memory used exceeds total";
  }
  if (payload.disk.free_gib > payload.disk.total_gib) {
    return "disk free exceeds total";
  }
  if (!finiteInRange(payload.uptime_seconds, 0, 10 * 365 * 86_400)) {
    return "invalid uptime";
  }
  if (
    !Number.isInteger(payload.process_count) ||
    payload.process_count < 0 ||
    payload.process_count > 100_000
  ) {
    return "invalid process count";
  }
  return null;
}

function clamp(value, minimum = 0, maximum = 100) {
  return Math.max(minimum, Math.min(maximum, Number(value) || 0));
}

function rawStressIndex(payload) {
  const diskPressure = clamp(((payload.disk.percent - 70) / 30) * 100);
  const uptimeHours = payload.uptime_seconds / 3600;
  const uptimePressure = clamp(((uptimeHours - 24) / (168 - 24)) * 100);
  return Number(
    (
      payload.cpu_percent * 0.35 +
      payload.memory.percent * 0.4 +
      diskPressure * 0.15 +
      uptimePressure * 0.1
    ).toFixed(1),
  );
}

function stressStatus(value) {
  if (value >= 85) return "critical";
  if (value >= 70) return "high";
  if (value >= 40) return "moderate";
  return "low";
}

function sameRecentSession(previous, payload) {
  if (!previous?.generated_at) return false;
  const previousAt = Date.parse(previous.generated_at);
  const currentAt = Date.parse(payload.generated_at);
  return (
    Number.isFinite(previousAt) &&
    Number.isFinite(currentAt) &&
    currentAt >= previousAt &&
    currentAt - previousAt <= 10 * 60 * 1000 &&
    payload.uptime_seconds >= Number(previous.uptime_seconds || 0)
  );
}

function projectHealth(payload, previous) {
  const raw = rawStressIndex(payload);
  const stressIndex = sameRecentSession(previous, payload)
    ? Number((Number(previous.stress_index) * 0.7 + raw * 0.3).toFixed(1))
    : raw;
  return {
    ...payload,
    stress_index: stressIndex,
    stress_index_raw: raw,
    stress_status: stressStatus(stressIndex),
    interpretation:
      "CPU, memory, disk pressure, and uptime composite; not a medical or hardware-lifespan diagnosis.",
  };
}

export async function onRequestGet(context) {
  const { request, env } = context;
  const url = new URL(request.url);
  if (url.searchParams.get("health") === "1") {
    return jsonResponse({
      ok: Boolean(env.EFO_MONITOR_KV && env.EFO_LOCAL_INGEST_SECRET),
      configured: Boolean(env.EFO_MONITOR_KV && env.EFO_LOCAL_INGEST_SECRET),
      has_snapshot: Boolean(
        env.EFO_MONITOR_KV && (await env.EFO_MONITOR_KV.get(LATEST_KEY)),
      ),
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
    return jsonResponse({ error: "monitor_storage_unconfigured" }, 503);
  }
  const stored = await env.EFO_MONITOR_KV.get(LATEST_KEY);
  if (!stored) return jsonResponse({ error: "local_health_unavailable" }, 503);
  return new Response(stored, {
    headers: {
      "content-type": "application/json; charset=utf-8",
      "cache-control": "no-store, max-age=0",
      "x-content-type-options": "nosniff",
      "referrer-policy": "no-referrer",
    },
  });
}

export async function onRequestPost(context) {
  const { request, env } = context;
  if (!env.EFO_MONITOR_KV || !env.EFO_LOCAL_INGEST_SECRET) {
    return jsonResponse({ error: "local_ingest_unconfigured" }, 503);
  }
  const contentLength = Number(request.headers.get("content-length") || 0);
  if (contentLength > MAX_BODY_BYTES) {
    return jsonResponse({ error: "payload_too_large" }, 413);
  }
  const timestamp = request.headers.get("x-efo-timestamp") || "";
  const timestampNumber = Number(timestamp);
  const nowSeconds = Math.floor(Date.now() / 1000);
  if (
    !Number.isInteger(timestampNumber) ||
    Math.abs(nowSeconds - timestampNumber) > MAX_CLOCK_SKEW_SECONDS
  ) {
    return jsonResponse({ error: "invalid_timestamp" }, 401);
  }

  const rawBody = await request.text();
  if (new TextEncoder().encode(rawBody).byteLength > MAX_BODY_BYTES) {
    return jsonResponse({ error: "payload_too_large" }, 413);
  }
  const providedSignature = (
    request.headers.get("x-efo-signature") || ""
  ).replace(/^sha256=/, "");
  const expectedSignature = await snapshotInternals.hmacHex(
    env.EFO_LOCAL_INGEST_SECRET,
    `${timestamp}.${rawBody}`,
  );
  if (
    !snapshotInternals.constantTimeEqual(
      providedSignature.toLowerCase(),
      expectedSignature,
    )
  ) {
    return jsonResponse({ error: "invalid_signature" }, 401);
  }

  let payload;
  try {
    payload = JSON.parse(rawBody);
  } catch {
    return jsonResponse({ error: "invalid_json" }, 400);
  }
  const validationError = validatePayload(payload);
  if (validationError) {
    return jsonResponse(
      { error: "invalid_local_health", detail: validationError },
      400,
    );
  }

  let previous = null;
  const previousRaw = await env.EFO_MONITOR_KV.get(LATEST_KEY);
  if (previousRaw) {
    try {
      previous = JSON.parse(previousRaw);
    } catch {
      previous = null;
    }
  }
  const projected = projectHealth(payload, previous);
  const history = Array.isArray(previous?.history) ? previous.history : [];
  projected.history = [
    ...history,
    {
      at: projected.generated_at,
      stress_index: projected.stress_index,
      cpu_percent: projected.cpu_percent,
      memory_percent: projected.memory.percent,
      disk_percent: projected.disk.percent,
    },
  ].slice(-HISTORY_LIMIT);

  await env.EFO_MONITOR_KV.put(LATEST_KEY, JSON.stringify(projected), {
    expirationTtl: 604800,
  });
  return jsonResponse({
    ok: true,
    generated_at: projected.generated_at,
    stress_index: projected.stress_index,
    stress_status: projected.stress_status,
  });
}

export const internals = {
  projectHealth,
  rawStressIndex,
  sameRecentSession,
  stressStatus,
  validatePayload,
};
