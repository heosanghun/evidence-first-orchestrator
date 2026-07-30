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
    return jsonResponse({ error: "monitor_storage_unconfigured" }, 503);
  }
  const stored = await env.EFO_MONITOR_KV.get(LATEST_KEY);
  if (!stored) return jsonResponse({ error: "snapshot_unavailable" }, 503);
  return new Response(stored, {
    status: 200,
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
  const validationError = validateSnapshot(snapshot);
  if (validationError) {
    return jsonResponse({ error: "invalid_snapshot", detail: validationError }, 400);
  }

  snapshot.source = {
    ...(snapshot.source || {}),
    mode: "live",
    received_at: new Date().toISOString(),
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
  });
}

export const internals = {
  constantTimeEqual,
  hasForbiddenKey,
  hmacHex,
  validateSnapshot,
};
