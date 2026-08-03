import assert from "node:assert/strict";
import { webcrypto } from "node:crypto";
import test from "node:test";

if (!globalThis.crypto) {
  Object.defineProperty(globalThis, "crypto", { value: webcrypto });
}

const { internals, onRequestPost } = await import(
  "../functions/api/chat.js"
);

class MemoryKv {
  constructor(snapshot, localHealth = null) {
    this.snapshot = snapshot;
    this.localHealth = localHealth;
  }

  async get(key) {
    if (key === "snapshot:latest" && this.snapshot) {
      return JSON.stringify(this.snapshot);
    }
    if (key === "local:latest" && this.localHealth) {
      return JSON.stringify(this.localHealth);
    }
    return null;
  }
}

function snapshot() {
  return {
    schema_version: "1.0",
    generated_at: "2026-07-31T03:00:00.000Z",
    collection_interval_seconds: 120,
    source: {
      mode: "collector",
      host: "gpu-server",
      collector: "efo-monitor/1.3",
      ledger: { valid: true, event_count: 120 },
    },
    workspace: {
      name: "Research portfolio",
      objective: "Evidence-first research",
      next_milestone: "Thought-Slot trainability gate",
      workflow_progress_percent: 62.5,
    },
    projects: [
      {
        id: "system-1-5",
        name: "System 1.5",
        objective: "Thought-Slot DEQ",
        phase: "G1 trainability",
        next_milestone: "Gradient evidence",
        progress_percent: 40,
        task_count: 5,
        verified_count: 2,
        active_task_count: 1,
        blocked_task_count: 1,
        active_gpu_indexes: [],
      },
      {
        id: "cts",
        name: "CTS",
        objective: "Operator redesign",
        phase: "Evidence audit",
        next_milestone: "Run identity freeze",
        progress_percent: 75,
        task_count: 4,
        verified_count: 3,
        active_task_count: 1,
        blocked_task_count: 0,
        active_gpu_indexes: [0],
      },
    ],
    agents: [
      {
        id: "codex",
        name: "Codex",
        role: "orchestrator",
        state: "working",
        current: "Dashboard chat",
        current_task_id: "EFO-CHAT-1",
        next: "Independent verification",
        progress_percent: 60,
        status_source: "canonical",
        status_badge: "원장",
        updated_at: "2026-07-31T03:00:00Z",
      },
    ],
    tasks: [
      {
        id: "S15-G1",
        title: "Thought-Slot trainability gate",
        owner: "claude",
        state: "blocked",
        canonical_state: "blocked",
        external_phase: "",
        status_source: "canonical",
        status_badge: "원장",
        lease_active: false,
        progress_percent: 45,
        next: "Fix gradient flow",
        updated_at: "2026-07-31T02:59:00Z",
      },
      {
        id: "CTS-P1",
        title: "Freeze run identity",
        owner: "claude-b",
        state: "verified",
        canonical_state: "verified",
        external_phase: "",
        status_source: "canonical",
        status_badge: "원장",
        lease_active: false,
        progress_percent: 100,
        next: "Archive evidence",
        updated_at: "2026-07-31T02:58:00Z",
      },
    ],
    gpus: [
      {
        index: 0,
        name: "NVIDIA RTX A6000",
        utilization_percent: 84,
        memory_used_mib: 24000,
        memory_total_mib: 49140,
        temperature_c: 63,
        power_w: 210,
        projects: [{ name: "CTS", active: true }],
      },
      {
        index: 1,
        name: "NVIDIA RTX A6000",
        utilization_percent: 0,
        memory_used_mib: 20,
        memory_total_mib: 49140,
        temperature_c: 40,
        power_w: 24,
        projects: [],
      },
    ],
    system: {
      hostname: "gpu-server",
      load_1m: 1,
      uptime_seconds: 100,
      memory: { used_gib: 10, total_gib: 100, percent: 10 },
      disk: { used_gib: 90, total_gib: 100, free_gib: 10, percent: 90 },
    },
    history: [],
    activity: [],
    alerts: [],
  };
}

function request(body, token = "") {
  return new Request("https://dashboard.example/api/chat", {
    method: "POST",
    headers: {
      "content-type": "application/json",
      ...(token ? { authorization: `Bearer ${token}` } : {}),
    },
    body: JSON.stringify(body),
  });
}

function localHealth() {
  return {
    schema_version: "1.0",
    generated_at: "2026-07-31T03:00:00.000Z",
    collection_interval_seconds: 120,
    device_alias: "Local workstation",
    cpu_percent: 8,
    memory: { used_gib: 26.2, total_gib: 31.8, percent: 82.4 },
    disk: { free_gib: 26.5, total_gib: 954, percent: 97.2 },
    uptime_seconds: 3000,
    process_count: 458,
    stress_index: 49.4,
    stress_index_raw: 49.4,
    stress_status: "moderate",
    interpretation: "Operational composite",
    history: [],
  };
}

test("snapshot mode answers project progress without an API key", async () => {
  const response = await onRequestPost({
    request: request({ message: "전체 프로젝트 진행률 알려줘" }),
    env: { EFO_MONITOR_KV: new MemoryKv(snapshot()) },
  });
  assert.equal(response.status, 200);
  const body = await response.json();
  assert.equal(body.mode, "snapshot");
  assert.equal(body.read_only, true);
  assert.match(body.answer, /System 1\.5: 40\.0%/);
  assert.match(body.answer, /CTS: 75\.0%/);
  assert.match(body.answer, /워크플로 완료율/);
});

test("GPU answers only report projects explicitly marked active", async () => {
  const body = internals.deterministicAnswer("GPU 상태 알려줘", snapshot());
  assert.match(body, /GPU 0: 사용률 84\.0%/);
  assert.match(body, /CTS/);
  assert.match(body, /GPU 1: 사용률 0\.0%/);
  assert.match(body, /활성 프로젝트 없음/);
});

test("chat includes signed local PC load when available", async () => {
  const response = await onRequestPost({
    request: request({ message: "로컬 PC 피로도와 메모리 상태 알려줘" }),
    env: {
      EFO_MONITOR_KV: new MemoryKv(snapshot(), localHealth()),
    },
  });
  const body = await response.json();
  assert.equal(body.mode, "snapshot");
  assert.match(body.answer, /합성 부하 49\.4%/);
  assert.match(body.answer, /메모리 82\.4%/);
  assert.match(body.answer, /하드웨어 수명 진단이 아닙니다/);
});

test("action requests are refused as read-only", () => {
  const body = internals.deterministicAnswer("GPU 0 학습을 중단해줘", snapshot());
  assert.match(body, /읽기 전용/);
  assert.match(body, /실행하거나 서버를 변경하지 않았습니다/);
});

test("view protection is enforced for chat", async () => {
  const response = await onRequestPost({
    request: request({ message: "상태" }, "wrong"),
    env: {
      EFO_MONITOR_KV: new MemoryKv(snapshot()),
      EFO_VIEW_TOKEN: "correct",
    },
  });
  assert.equal(response.status, 401);
});

test("invalid and empty messages are rejected", async () => {
  const environment = { EFO_MONITOR_KV: new MemoryKv(snapshot()) };
  const invalid = await onRequestPost({
    request: new Request("https://dashboard.example/api/chat", {
      method: "POST",
      body: "{",
    }),
    env: environment,
  });
  assert.equal(invalid.status, 400);

  const empty = await onRequestPost({
    request: request({ message: "   " }),
    env: environment,
  });
  assert.equal(empty.status, 400);
});

test("OpenAI mode requires the API key, explicit enablement, and view protection", () => {
  assert.equal(
    internals.aiEnabled({
      OPENAI_API_KEY: "secret",
      EFO_CHAT_ENABLED: "true",
    }),
    false,
  );
  assert.equal(
    internals.aiEnabled({
      OPENAI_API_KEY: "secret",
      EFO_CHAT_ENABLED: "true",
      EFO_VIEW_TOKEN: "view-secret",
    }),
    true,
  );
});

test("OpenAI mode uses grounded Responses API input", async () => {
  const originalFetch = globalThis.fetch;
  let captured;
  globalThis.fetch = async (_url, options) => {
    captured = JSON.parse(options.body);
    return new Response(
      JSON.stringify({
        output: [
          {
            content: [
              {
                type: "output_text",
                text: "System 1.5는 G1 단계이며 근거 시각은 03:00입니다.",
              },
            ],
          },
        ],
      }),
      { status: 200, headers: { "content-type": "application/json" } },
    );
  };

  try {
    const response = await onRequestPost({
      request: request(
        { message: "맥락을 고려해 요약해줘", history: [] },
        "view-secret",
      ),
      env: {
        EFO_MONITOR_KV: new MemoryKv(snapshot()),
        EFO_VIEW_TOKEN: "view-secret",
        EFO_CHAT_ENABLED: "true",
        OPENAI_API_KEY: "openai-secret",
      },
    });
    assert.equal(response.status, 200);
    const body = await response.json();
    assert.equal(body.mode, "openai");
    assert.equal(body.model, "gpt-5.6-luna");
    assert.match(body.answer, /System 1\.5/);
    assert.equal(captured.store, false);
    assert.equal(captured.reasoning.effort, "low");
    assert.equal(captured.text.verbosity, "low");
    assert.equal(typeof captured.safety_identifier, "string");
    assert.match(captured.instructions, /최신 EFO 스냅샷 JSON/);
    assert.doesNotMatch(JSON.stringify(captured), /openai-secret/);
  } finally {
    globalThis.fetch = originalFetch;
  }
});

test("model failures fall back to the deterministic snapshot answer", async () => {
  const originalFetch = globalThis.fetch;
  globalThis.fetch = async () => {
    throw new Error("network failure");
  };
  try {
    const response = await onRequestPost({
      request: request({ message: "진행률" }, "view-secret"),
      env: {
        EFO_MONITOR_KV: new MemoryKv(snapshot()),
        EFO_VIEW_TOKEN: "view-secret",
        EFO_CHAT_ENABLED: "true",
        OPENAI_API_KEY: "openai-secret",
      },
    });
    const body = await response.json();
    assert.equal(body.mode, "snapshot");
    assert.equal(body.degraded, true);
    assert.match(body.answer, /System 1\.5/);
  } finally {
    globalThis.fetch = originalFetch;
  }
});

test("history normalization is bounded and strips invalid entries", () => {
  const history = Array.from({ length: 12 }, (_, index) => ({
    role: index % 2 ? "assistant" : "user",
    content: `item-${index}`,
  }));
  history.push({ role: "tool", content: "" });
  const normalized = internals.normalizeHistory(history);
  assert.ok(normalized.length <= 8);
  assert.ok(normalized.every((item) => ["user", "assistant"].includes(item.role)));
  assert.ok(normalized.every((item) => item.content));
});
