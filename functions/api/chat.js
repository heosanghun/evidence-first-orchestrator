import { internals as snapshotInternals } from "./snapshot.js";

const LATEST_KEY = "snapshot:latest";
const LOCAL_HEALTH_KEY = "local:latest";
const MAX_BODY_BYTES = 24_000;
const MAX_MESSAGE_CHARS = 1_500;
const MAX_HISTORY_ITEMS = 8;
const MODEL_TIMEOUT_MS = 20_000;
const DEFAULT_MODEL = "gpt-5.6-luna";

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

function cleanText(value, maximum = MAX_MESSAGE_CHARS) {
  if (typeof value !== "string") return "";
  return value.replaceAll("\u0000", "").trim().slice(0, maximum);
}

function normalizeHistory(value) {
  if (!Array.isArray(value)) return [];
  return value
    .slice(-MAX_HISTORY_ITEMS)
    .map((item) => ({
      role: item?.role === "assistant" ? "assistant" : "user",
      content: cleanText(item?.content, MAX_MESSAGE_CHARS),
    }))
    .filter((item) => item.content);
}

function percent(value) {
  const number = Number(value);
  return `${Number.isFinite(number) ? number.toFixed(1) : "0.0"}%`;
}

function stateLabel(value) {
  const labels = {
    pending: "대기",
    claimed: "할당됨",
    running: "실행 중",
    submitted: "제출됨",
    verified: "검증됨",
    archived: "보관됨",
    blocked: "막힘",
    rejected: "반려됨",
    invalidated: "무효화",
    working: "작업 중",
    waiting: "대기",
    offline: "연결 끊김",
  };
  const state = String(value || "").toLowerCase();
  return labels[state] || state || "알 수 없음";
}

function snapshotAgeSeconds(snapshot) {
  const generatedAt = new Date(snapshot?.generated_at).getTime();
  if (!Number.isFinite(generatedAt)) return null;
  return Math.max(0, Math.round((Date.now() - generatedAt) / 1000));
}

function formatAge(seconds) {
  if (!Number.isFinite(seconds)) return "시각 확인 불가";
  if (seconds < 60) return `${seconds}초 전`;
  if (seconds < 3600) return `${Math.floor(seconds / 60)}분 전`;
  const hours = Math.floor(seconds / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);
  return `${hours}시간 ${minutes}분 전`;
}

function projectLines(snapshot) {
  const projects = Array.isArray(snapshot?.projects) ? snapshot.projects : [];
  if (projects.length === 0) {
    return [
      `- ${snapshot?.workspace?.name || "EFO"}: ${percent(
        snapshot?.workspace?.workflow_progress_percent,
      )} · 다음: ${snapshot?.workspace?.next_milestone || "확인 중"}`,
    ];
  }
  return projects.map((project) => {
    const activeGpu =
      Array.isArray(project.active_gpu_indexes) &&
      project.active_gpu_indexes.length > 0
        ? ` · 활성 GPU ${project.active_gpu_indexes.join(", ")}`
        : "";
    return `- ${project.name}: ${percent(project.progress_percent)} · ${project.phase} · 검증 ${project.verified_count}/${project.task_count} · 활성 ${project.active_task_count} · 막힘 ${project.blocked_task_count}${activeGpu} · 다음: ${project.next_milestone}`;
  });
}

function agentLines(snapshot) {
  const agents = Array.isArray(snapshot?.agents) ? snapshot.agents : [];
  if (agents.length === 0) return ["- 에이전트 투영 정보 없음"];
  return agents.map(
    (agent) =>
      `- ${agent.name}: ${stateLabel(agent.state)} · ${agent.current || "배정 대기"} · 다음: ${agent.next || "확인 중"}`,
  );
}

function issueLines(snapshot) {
  const tasks = Array.isArray(snapshot?.tasks) ? snapshot.tasks : [];
  const issues = tasks.filter((task) =>
    ["blocked", "rejected", "invalidated"].includes(
      String(task.state || "").toLowerCase(),
    ),
  );
  if (issues.length === 0) return ["- 현재 원장에 막힘·반려·무효화 작업 없음"];
  return issues.slice(0, 12).map(
    (task) =>
      `- ${task.id} ${task.title}: ${stateLabel(task.state)} · 담당 ${task.owner} · 다음: ${task.next || "원인 확인"}`,
  );
}

function gpuLines(snapshot) {
  const gpus = Array.isArray(snapshot?.gpus) ? snapshot.gpus : [];
  if (gpus.length === 0) return ["- GPU 측정 정보 없음"];
  return gpus.map((gpu) => {
    const projects = Array.isArray(gpu.projects)
      ? gpu.projects
          .filter((project) => project.active === true)
          .map((project) => project.name)
      : [];
    const projectText =
      projects.length > 0 ? projects.join(", ") : "활성 프로젝트 없음";
    const total = Number(gpu.memory_total_mib) || 0;
    const memory = total > 0 ? (Number(gpu.memory_used_mib) / total) * 100 : 0;
    return `- GPU ${gpu.index}: 사용률 ${percent(gpu.utilization_percent)} · VRAM ${percent(memory)} · ${gpu.temperature_c}°C · ${projectText}`;
  });
}

function localPcLines(snapshot) {
  const local = snapshot?.local_pc;
  if (!local) return ["- 로컬 PC 수집기 연결 대기"];
  return [
    `- ${local.device_alias}: 합성 부하 ${percent(local.stress_index)} (${local.stress_status})`,
    `- CPU ${percent(local.cpu_percent)} · 메모리 ${percent(
      local.memory?.percent,
    )} · C: 디스크 ${percent(local.disk?.percent)} · 여유 ${Number(
      local.disk?.free_gib || 0,
    ).toFixed(1)} GiB`,
    `- 가동 ${Math.round(Number(local.uptime_seconds || 0) / 3600)}시간 · 프로세스 ${local.process_count}개 · 측정 ${local.generated_at}`,
    "- 운영용 합성 지표이며 의료적 스트레스나 하드웨어 수명 진단이 아닙니다.",
  ];
}

function fullSnapshotAnswer(snapshot) {
  const age = snapshotAgeSeconds(snapshot);
  const taskCount = Array.isArray(snapshot?.tasks) ? snapshot.tasks.length : 0;
  const verifiedCount = Array.isArray(snapshot?.tasks)
    ? snapshot.tasks.filter((task) =>
        ["verified", "archived"].includes(
          String(task.state || "").toLowerCase(),
        ),
      ).length
    : 0;
  return [
    `현재 EFO 전체 워크플로 진행률은 ${percent(snapshot?.workspace?.workflow_progress_percent)}입니다.`,
    `스냅샷: ${snapshot?.generated_at || "시각 없음"} (${formatAge(age)})`,
    `원장 작업: 총 ${taskCount}개, 검증·보관 ${verifiedCount}개`,
    "",
    "프로젝트",
    ...projectLines(snapshot),
    "",
    "에이전트",
    ...agentLines(snapshot),
    "",
    "막힌 항목",
    ...issueLines(snapshot),
    "",
    "GPU",
    ...gpuLines(snapshot),
    "",
    "로컬 PC",
    ...localPcLines(snapshot),
    "",
    `전체 다음 단계: ${snapshot?.workspace?.next_milestone || "확인 중"}`,
    "주의: 위 진행률은 EFO 검증 워크플로 완료율이며 모델 정확도가 아닙니다.",
  ].join("\n");
}

function deterministicAnswer(message, snapshot) {
  const query = message.toLowerCase();
  const requestsAction =
    /실행|시작|중단|정지|재시작|삭제|수정|배포|학습해|돌려|할당/.test(query);
  const wantsGpu = /gpu|그래픽|브이램|vram|온도/.test(query);
  const wantsLocal =
    /로컬|pc|컴퓨터|피로|스트레스|메모리 부족|디스크|저장공간/.test(query);
  const wantsAgent = /에이전트|codex|claude|클로드|안티|담당/.test(query);
  const wantsIssue = /막|차단|반려|실패|문제|위험/.test(query);
  const wantsProject = /프로젝트|진행|진척|다음|목표|cts|system/.test(query);
  const sections = [];

  if (wantsProject) sections.push("프로젝트", ...projectLines(snapshot));
  if (wantsAgent) sections.push("에이전트", ...agentLines(snapshot));
  if (wantsIssue) sections.push("막힌 항목", ...issueLines(snapshot));
  if (wantsGpu) sections.push("GPU", ...gpuLines(snapshot));
  if (wantsLocal) sections.push("로컬 PC", ...localPcLines(snapshot));

  const answer =
    sections.length === 0
      ? fullSnapshotAnswer(snapshot)
      : [
    `스냅샷 ${snapshot?.generated_at || "시각 없음"} 기준입니다.`,
    ...sections,
    "",
    `전체 워크플로 진행률: ${percent(snapshot?.workspace?.workflow_progress_percent)}`,
    `다음 단계: ${snapshot?.workspace?.next_milestone || "확인 중"}`,
    "진행률은 모델 정확도가 아니라 EFO 검증 워크플로 완료율입니다.",
        ].join("\n");
  return requestsAction
    ? `이 대화창은 읽기 전용이므로 요청한 작업을 실행하거나 서버를 변경하지 않았습니다.\n\n${answer}`
    : answer;
}

function sanitizeSnapshot(snapshot) {
  return {
    generated_at: snapshot.generated_at,
    workspace: snapshot.workspace,
    projects: snapshot.projects || [],
    agents: (snapshot.agents || []).slice(0, 12),
    tasks: (snapshot.tasks || []).slice(0, 80),
    gpus: (snapshot.gpus || []).map((gpu) => ({
      index: gpu.index,
      utilization_percent: gpu.utilization_percent,
      memory_used_mib: gpu.memory_used_mib,
      memory_total_mib: gpu.memory_total_mib,
      temperature_c: gpu.temperature_c,
      power_w: gpu.power_w,
      projects: (gpu.projects || [])
        .filter((project) => project.active === true)
        .map((project) => project.name),
    })),
    system: snapshot.system,
    local_pc: snapshot.local_pc || null,
    alerts: (snapshot.alerts || []).slice(0, 20),
  };
}

function outputText(response) {
  if (typeof response?.output_text === "string" && response.output_text.trim()) {
    return response.output_text.trim();
  }
  for (const item of response?.output || []) {
    for (const content of item?.content || []) {
      if (
        content?.type === "output_text" &&
        typeof content.text === "string" &&
        content.text.trim()
      ) {
        return content.text.trim();
      }
    }
  }
  return "";
}

async function safetyIdentifier(request) {
  const source =
    request.headers.get("cf-connecting-ip") ||
    request.headers.get("user-agent") ||
    "anonymous";
  const digest = await crypto.subtle.digest(
    "SHA-256",
    new TextEncoder().encode(source),
  );
  return [...new Uint8Array(digest)]
    .slice(0, 16)
    .map((byte) => byte.toString(16).padStart(2, "0"))
    .join("");
}

function aiEnabled(env) {
  return Boolean(
    env.OPENAI_API_KEY &&
      env.EFO_CHAT_ENABLED === "true" &&
      env.EFO_VIEW_TOKEN,
  );
}

async function requestModel({ request, env, message, history, snapshot }) {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), MODEL_TIMEOUT_MS);
  const grounding = JSON.stringify(sanitizeSnapshot(snapshot));
  try {
    const response = await fetch("https://api.openai.com/v1/responses", {
      method: "POST",
      headers: {
        authorization: `Bearer ${env.OPENAI_API_KEY}`,
        "content-type": "application/json",
      },
      signal: controller.signal,
      body: JSON.stringify({
        model: env.EFO_CHAT_MODEL || DEFAULT_MODEL,
        instructions: [
          "당신은 Evidence First Orchestrator의 읽기 전용 Codex 운영 어시스턴트입니다.",
          "오직 제공된 최신 EFO 스냅샷과 대화 문맥만 근거로 한국어로 답하세요.",
          "측정되지 않은 성과, 실행 중이지 않은 학습, ETA를 만들어내지 마세요.",
          "스냅샷 시각과 오래된 데이터 여부를 분명히 밝히세요.",
          "진행률은 모델 정확도가 아니라 EFO 검증 워크플로 완료율이라고 구분하세요.",
          "사용자가 작업 실행, 중단, 변경을 요청하면 이 창은 읽기 전용이라고 설명하고 실제 실행을 주장하지 마세요.",
          "결론, 근거, 다음 단계 순서로 간결하게 답하세요.",
          `최신 EFO 스냅샷 JSON: ${grounding}`,
        ].join("\n"),
        input: [
          ...history.map((item) => ({
            role: item.role,
            content: item.content,
          })),
          { role: "user", content: message },
        ],
        reasoning: { effort: "low" },
        text: { verbosity: "low" },
        max_output_tokens: 900,
        store: false,
        safety_identifier: await safetyIdentifier(request),
      }),
    });
    if (!response.ok) throw new Error(`openai_${response.status}`);
    const payload = await response.json();
    const answer = outputText(payload);
    if (!answer) throw new Error("openai_empty_output");
    return {
      answer,
      model: env.EFO_CHAT_MODEL || DEFAULT_MODEL,
    };
  } finally {
    clearTimeout(timeout);
  }
}

export async function onRequestPost(context) {
  const { request, env } = context;
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

  const contentLength = Number(request.headers.get("content-length") || 0);
  if (contentLength > MAX_BODY_BYTES) {
    return jsonResponse({ error: "payload_too_large" }, 413);
  }

  let body;
  try {
    const rawBody = await request.text();
    if (new TextEncoder().encode(rawBody).byteLength > MAX_BODY_BYTES) {
      return jsonResponse({ error: "payload_too_large" }, 413);
    }
    body = JSON.parse(rawBody);
  } catch {
    return jsonResponse({ error: "invalid_json" }, 400);
  }

  const message = cleanText(body?.message);
  if (!message) return jsonResponse({ error: "message_required" }, 400);
  const history = normalizeHistory(body?.history);
  const stored = await env.EFO_MONITOR_KV.get(LATEST_KEY);
  if (!stored) return jsonResponse({ error: "snapshot_unavailable" }, 503);

  let snapshot;
  try {
    snapshot = JSON.parse(stored);
  } catch {
    return jsonResponse({ error: "snapshot_invalid" }, 503);
  }
  const localRaw = await env.EFO_MONITOR_KV.get(LOCAL_HEALTH_KEY);
  if (localRaw) {
    try {
      snapshot.local_pc = JSON.parse(localRaw);
    } catch {
      snapshot.local_pc = null;
    }
  }

  const fallbackAnswer = deterministicAnswer(message, snapshot);
  if (!aiEnabled(env)) {
    return jsonResponse({
      answer: fallbackAnswer,
      mode: "snapshot",
      snapshot_generated_at: snapshot.generated_at,
      read_only: true,
    });
  }

  try {
    const modelReply = await requestModel({
      request,
      env,
      message,
      history,
      snapshot,
    });
    return jsonResponse({
      answer: modelReply.answer,
      mode: "openai",
      model: modelReply.model,
      snapshot_generated_at: snapshot.generated_at,
      read_only: true,
    });
  } catch {
    return jsonResponse({
      answer: fallbackAnswer,
      mode: "snapshot",
      degraded: true,
      snapshot_generated_at: snapshot.generated_at,
      read_only: true,
    });
  }
}

export const internals = {
  aiEnabled,
  deterministicAnswer,
  fullSnapshotAnswer,
  localPcLines,
  normalizeHistory,
  outputText,
  sanitizeSnapshot,
};
