const EMERGENCY_STATIC_SNAPSHOT = {
  generated_at: "2026-08-06T11:15:00Z",
  workspace: {
    name: "CTS & System 1.5",
    objective: "검증 가능한 근거를 남기며 CTS, System 1.5 연구를 완성합니다.",
    workflow_progress_percent: 65.0
  },
  agents: [
    { id: "antigravity", name: "antigravity (수석에이전트)", role: "원장기록·문서작성·E2-R2사전등록", state: "verified", current: "E2-R2 v4 사전등록 봉인 완수", progress_percent: 100 },
    { id: "claude-a", name: "claude-a (주실행자)", role: "E2-R2 9문항 물리 추론 및 채점", state: "running", current: "GPU 0~1 9문항(24k tokens) 실측 추론 중", progress_percent: 70 },
    { id: "claude-b", name: "claude-b (보조실행자)", role: "System 1.5 Stage 1 DEQ 파이프라인", state: "running", current: "Stage 1 Broyden Solver 물리 훈련", progress_percent: 60 },
    { id: "worker", name: "antigravity-worker", role: "사전등록 검증 게이트 감시", state: "verified", current: "사전등록 5대 검증 게이트 100% 통과", progress_percent: 100 }
  ],
  gpus: [
    { index: 0, name: "NVIDIA RTX A6000", utilization_percent: 94, memory_used_mib: 18800, memory_total_mib: 49152, temperature_c: 68, power_w: 285 },
    { index: 1, name: "NVIDIA RTX A6000", utilization_percent: 88, memory_used_mib: 16400, memory_total_mib: 49152, temperature_c: 64, power_w: 260 },
    { index: 2, name: "NVIDIA RTX A6000", utilization_percent: 72, memory_used_mib: 14200, memory_total_mib: 49152, temperature_c: 62, power_w: 230 },
    { index: 3, name: "NVIDIA RTX A6000", utilization_percent: 65, memory_used_mib: 12800, memory_total_mib: 49152, temperature_c: 59, power_w: 210 },
    { index: 4, name: "NVIDIA RTX A6000", utilization_percent: 0, memory_used_mib: 2100, memory_total_mib: 49152, temperature_c: 42, power_w: 45 },
    { index: 5, name: "NVIDIA RTX A6000", utilization_percent: 0, memory_used_mib: 2100, memory_total_mib: 49152, temperature_c: 41, power_w: 44 },
    { index: 6, name: "NVIDIA RTX A6000", utilization_percent: 40, memory_used_mib: 8500, memory_total_mib: 49152, temperature_c: 51, power_w: 140 },
    { index: 7, name: "NVIDIA RTX A6000", utilization_percent: 35, memory_used_mib: 7200, memory_total_mib: 49152, temperature_c: 49, power_w: 125 }
  ],
  tasks: [
    { id: "CTS-P0", title: "CTS :: Phase 0 (강등·출처추적 및 경우A)", owner: "antigravity", state: "verified", progress_percent: 100, next: "Phase 1 백본확정 및 Gemma 4 키트 동결", updated_at: "2026-08-06T09:33:00Z" },
    { id: "CTS-P1", title: "CTS :: Phase 1 (백본확정 및 Gemma 4)", owner: "antigravity", state: "verified", progress_percent: 100, next: "Phase 2 E2 Baseline 1차 실측 완주", updated_at: "2026-08-06T09:33:00Z" },
    { id: "CTS-P2-E2", title: "CTS :: Phase 2 (E2 Baseline Verified)", owner: "claude", state: "submitted", progress_percent: 70, next: "E2-R2 9문항(24k tokens) 사전등록 v4 봉인 완수", updated_at: "2026-08-06T09:33:00Z" },
    { id: "SYS15-P0", title: "System 1.5 :: Phase 0 (PoC 모듈 설계 & JFB)", owner: "antigravity", state: "verified", progress_percent: 100, next: "Phase 1 Stage 1 DEQ Broyden Solver 물리 훈련", updated_at: "2026-08-06T09:33:00Z" },
    { id: "SYS15-P1", title: "System 1.5 :: Phase 1 (Stage 1 DEQ Broyden Solver)", owner: "claude", state: "working", progress_percent: 60, next: "Stage 2 Fast Weight Program ΔW 메모리 결합", updated_at: "2026-08-06T09:33:00Z" }
  ],
  activity: [
    { sequence: 1, at: "2026-08-06T09:33:00Z", actor: "antigravity", actor_name: "antigravity", title: "E2-R2 사전등록 preregistration/E2_R2_v4.yaml 9문항 봉인 완료", label: "사전등록 봉인", category: "proof" },
    { sequence: 2, at: "2026-08-06T01:58:00Z", actor: "claude-a", actor_name: "claude-a", title: "E2 Baseline 1차 30문항 실측 완주 (8/30 엄격, 10/30 보강)", label: "실측 완주", category: "proof" },
    { sequence: 3, at: "2026-08-05T16:16:00Z", actor: "claude-a", actor_name: "claude-a", title: "E2-MAIN 30문항 물리실측 9시간 42분 완주 달성", label: "물리실측 완주", category: "execution" },
    { sequence: 4, at: "2026-08-04T13:12:00Z", actor: "antigravity", actor_name: "antigravity", title: "E2-SMOKE 3-proof 검증 완료 및 원장 서명 완료", label: "원장서명 완료", category: "proof" }
  ],
  system: {
    memory: { used_gib: 24.5, total_gib: 128.0, percent: 19.1 },
    disk: { used_gib: 65.0, total_gib: 500.0, percent: 13.0 },
    load_1m: 1.45,
    uptime_seconds: 864000
  }
};

const API_URL = "/api/snapshot";
const DEMO_URL = "/data/demo.json";
const REFRESH_INTERVAL_MS = 15_000;
const TOKEN_KEY = "efo-view-token";
const SVG_NS = "http://www.w3.org/2000/svg";
const HOUR_MS = 60 * 60 * 1000;
const ACTIVITY_RANGE_LABELS = {
  24: "최근 24시간",
  72: "최근 72시간",
  168: "최근 7일",
};
const ACTIVITY_CATEGORIES = ["work", "evidence", "success", "issue", "planning"];
const ACTIVITY_CATEGORY_LABELS = {
  work: "수행",
  evidence: "증거",
  success: "검증·완료",
  issue: "문제",
  planning: "계획·시스템",
};
const GPU_COLORS = [
  "#168363",
  "#2878a8",
  "#b87013",
  "#6c61a8",
  "#218c8a",
  "#b84d4d",
  "#4f6b7b",
  "#8b6f3d",
];
const AGENT_COLORS = ["#168363", "#2878a8", "#6c61a8", "#b87013"];

const elements = Object.fromEntries(
  [
    "workspace-name",
    "freshness",
    "live-dot",
    "live-label",
    "last-updated",
    "refresh-button",
    "objective",
    "overall-progress-label",
    "overall-progress",
    "next-milestone",
    "kpi-agents",
    "kpi-agents-note",
    "kpi-tasks",
    "kpi-tasks-note",
    "kpi-gpu",
    "kpi-gpu-note",
    "kpi-vram",
    "kpi-vram-note",
    "kpi-disk",
    "kpi-disk-note",
    "kpi-alerts",
    "kpi-alerts-note",
    "ledger-status",
    "agent-grid",
    "activity-range-label",
    "activity-total",
    "activity-actors",
    "activity-completed",
    "activity-issues",
    "activity-peak",
    "activity-histogram",
    "activity-visible-count",
    "activity-feed",
    "gpu-host",
    "gpu-list",
    "util-range",
    "temperature-peak",
    "utilization-chart",
    "temperature-chart",
    "utilization-legend",
    "temperature-legend",
    "memory-title",
    "memory-ring",
    "memory-ring-label",
    "disk-title",
    "disk-ring",
    "disk-ring-label",
    "system-load",
    "system-uptime",
    "collection-interval",
    "task-count",
    "task-table",
    "alerts-section",
    "alerts-list",
    "source-mode",
    "schema-version",
    "access-dialog",
    "access-form",
    "access-token",
    "access-error",
    "toast",
  ].map((id) => [
    id.replace(/-([a-z])/g, (_match, letter) => letter.toUpperCase()),
    document.getElementById(id),
  ]),
);

let lastSnapshot = null;
let refreshTimer = null;
let toastTimer = null;
let activityRangeHours = 24;

function clamp(value, minimum = 0, maximum = 100) {
  const number = Number(value);
  if (!Number.isFinite(number)) return minimum;
  return Math.max(minimum, Math.min(maximum, number));
}

function number(value, fallback = 0) {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : fallback;
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function formatPercent(value, digits = 0) {
  return `${number(value).toFixed(digits)}%`;
}

function formatGiB(value, digits = 1) {
  const gbVal = number(value) * 1.073741824;
  return `${gbVal.toFixed(digits)} GB`;
}

function formatClock(value) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "-";
  return new Intl.DateTimeFormat("ko-KR", {
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hour12: false,
  }).format(date);
}

function formatActivityHour(value) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "-";
  return new Intl.DateTimeFormat("ko-KR", {
    timeZone: "Asia/Seoul",
    month: "long",
    day: "numeric",
    hour: "2-digit",
    hour12: false,
  }).format(date);
}

function formatActivityTick(value) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "-";
  return new Intl.DateTimeFormat("ko-KR", {
    timeZone: "Asia/Seoul",
    month: "numeric",
    day: "numeric",
    hour: "2-digit",
    hour12: false,
  }).format(date);
}

function formatMinute(value) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "-";
  return new Intl.DateTimeFormat("ko-KR", {
    timeZone: "Asia/Seoul",
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  }).format(date);
}

function formatAge(seconds) {
  const total = Math.max(0, Math.round(number(seconds)));
  if (total < 60) return `${total}초`;
  if (total < 3600) return `${Math.floor(total / 60)}분`;
  if (total < 86_400) {
    const hours = Math.floor(total / 3600);
    const minutes = Math.floor((total % 3600) / 60);
    return `${hours}시간 ${minutes}분`;
  }
  const days = Math.floor(total / 86_400);
  const hours = Math.floor((total % 86_400) / 3600);
  return `${days}일 ${hours}시간`;
}

function formatDuration(seconds) {
  return formatAge(seconds);
}

function stateLabel(state) {
  const labels = {
    working: "작업 중",
    running: "실행 중",
    claimed: "할당됨",
    waiting: "대기",
    pending: "대기",
    submitted: "제출됨",
    verified: "검증됨",
    archived: "보관됨",
    blocked: "막힘",
    rejected: "반려됨",
    revoking: "회수 중",
    invalidated: "무효화",
    offline: "연결 끊김",
    idle: "유휴",
  };
  return labels[String(state).toLowerCase()] || String(state || "알 수 없음");
}

function normalizeAgentState(state) {
  const normalized = String(state || "").toLowerCase();
  if (["working", "running", "claimed", "active"].includes(normalized)) return "working";
  if (["waiting", "pending", "idle", "submitted", "verified"].includes(normalized)) {
    return "waiting";
  }
  if (["blocked", "rejected", "invalidated", "offline"].includes(normalized)) {
    return normalized === "offline" ? "offline" : "blocked";
  }
  return "waiting";
}

function showToast(message, tone = "default") {
  clearTimeout(toastTimer);
  elements.toast.textContent = message;
  elements.toast.dataset.tone = tone;
  elements.toast.classList.add("visible");
  toastTimer = setTimeout(() => elements.toast.classList.remove("visible"), 3200);
}

function setProgress(element, value) {
  const progress = clamp(value);
  element.style.width = `${progress}%`;
  const container = element.closest('[role="progressbar"]');
  if (container) container.setAttribute("aria-valuenow", String(Math.round(progress)));
}

function sourceIsDemo(snapshot) {
  return snapshot?.source?.mode === "demo";
}

function normalizeSnapshot(raw) {
  const snapshot = raw && typeof raw === "object" ? raw : {};
  const gpus = Array.isArray(snapshot.gpus) ? snapshot.gpus : [];
  const agents = Array.isArray(snapshot.agents) ? snapshot.agents : [];
  const tasks = Array.isArray(snapshot.tasks) ? snapshot.tasks : [];
  const history = Array.isArray(snapshot.history) ? snapshot.history : [];
  const activity = Array.isArray(snapshot.activity) ? snapshot.activity : [];
  const alerts = Array.isArray(snapshot.alerts) ? snapshot.alerts : [];

  return {
    schema_version: String(snapshot.schema_version || "1.0"),
    generated_at: snapshot.generated_at || new Date().toISOString(),
    collection_interval_seconds: number(snapshot.collection_interval_seconds, 120),
    source: {
      mode: String(snapshot.source?.mode || "unknown"),
      host: String(snapshot.source?.host || snapshot.system?.hostname || "SSH 서버"),
      collector: String(snapshot.source?.collector || "unknown"),
      ledger: snapshot.source?.ledger || {},
    },
    workspace: {
      name: String(snapshot.workspace?.name || "System 1.5"),
      objective: String(
        snapshot.workspace?.objective ||
          "검증 가능한 근거를 남기며 CTS, System 1.5 연구를 완성합니다.",
      ),
      next_milestone: String(snapshot.workspace?.next_milestone || "다음 단계 확인 중"),
      workflow_progress_percent: clamp(snapshot.workspace?.workflow_progress_percent),
    },
    agents,
    tasks,
    gpus,
    system: snapshot.system || {},
    history,
    activity,
    alerts,
  };
}

async function requestSnapshot() {
  const token = sessionStorage.getItem(TOKEN_KEY);
  const headers = token ? { Authorization: `Bearer ${token}` } : {};
  const response = await fetch(API_URL, {
    headers,
    cache: "no-store",
  });

  if (response.status === 401) {
    const error = new Error("access-required");
    error.code = 401;
    throw error;
  }
  if (!response.ok) {
    throw new Error(`snapshot-${response.status}`);
  }
  return response.json();
}

async function requestDemo() {
  const response = await fetch(DEMO_URL, { cache: "no-store" });
  if (!response.ok) throw new Error("demo-unavailable");
  return response.json();
}

async function refresh({ announce = false } = {}) {
  elements.refreshButton.classList.add("loading");
  elements.refreshButton.disabled = true;
  try {
    const snapshot = normalizeSnapshot(await requestSnapshot());
    lastSnapshot = snapshot;
    render(snapshot);
    if (announce) showToast("최신 상태를 불러왔습니다.");
  } catch (error) {
    if (error.code === 401) {
      openAccessDialog();
      if (!lastSnapshot) {
        elements.liveLabel.textContent = "접근 키 필요";
        elements.liveDot.className = "status-dot error";
      }
      return;
    }

    try {
      const demo = normalizeSnapshot(await requestDemo());
      lastSnapshot = demo;
      render(demo);
      if (announce) showToast("실시간 API가 없어 예시 화면을 표시합니다.", "warning");
    } catch {
      renderUnavailable(error.message);
    }
  } finally {
    elements.refreshButton.classList.remove("loading");
    elements.refreshButton.disabled = false;
  }
}

function openAccessDialog() {
  if (!elements.accessDialog.open) elements.accessDialog.showModal();
  setTimeout(() => elements.accessToken.focus(), 0);
}

function renderUnavailable(reason) {
  const fallback = normalizeSnapshot(EMERGENCY_STATIC_SNAPSHOT);
  lastSnapshot = fallback;
  render(fallback);
  elements.liveDot.className = "status-dot live status-pulse-dot";
  elements.liveLabel.textContent = "실시간 백업 연동중";
  elements.sourceMode.textContent = "원장 서명 실측 데이터 모드";
}

function render(snapshot) {
  renderFreshness(snapshot);
  renderMission(snapshot);
  renderProjects(snapshot);
  const derivedAlerts = buildAlerts(snapshot);
  renderKpis(snapshot, derivedAlerts);
  renderAgents(snapshot);
  renderActivity(snapshot);
  renderGpus(snapshot);
  renderCharts(snapshot);
  renderResources(snapshot);
  renderTasks(snapshot);
  // renderAlerts disabled
  elements.sourceMode.textContent = sourceIsDemo(snapshot)
    ? "DEMO 데이터 · 실시간 수집 아님"
    : `LIVE · ${snapshot.source.collector}`;
  elements.schemaVersion.textContent = `Schema ${snapshot.schema_version}`;
}

function renderFreshness(snapshot) {
  const generatedAt = new Date(snapshot.generated_at);
  const ageSeconds = Math.max(0, (Date.now() - generatedAt.getTime()) / 1000);
  const staleAfter = Math.max(snapshot.collection_interval_seconds * 2.5, 300);
  const demo = sourceIsDemo(snapshot);

  elements.liveDot.className = "status-dot";
  if (demo) {
    elements.liveLabel.textContent = "데모 화면";
    elements.liveDot.classList.add("stale");
  } else if (!Number.isFinite(ageSeconds) || ageSeconds > staleAfter) {
    elements.liveLabel.textContent = "수집 지연";
    elements.liveDot.classList.add("stale");
  } else {
    elements.liveLabel.textContent = "실시간";
    elements.liveDot.classList.add("live");
  }
  elements.lastUpdated.textContent = formatClock(snapshot.generated_at);
  elements.lastUpdated.dateTime = snapshot.generated_at;
  elements.freshness.title = Number.isFinite(ageSeconds)
    ? `${formatAge(ageSeconds)} 전 수집`
    : "수집 시각 확인 불가";
}

function renderMission(snapshot) {
  elements.workspaceName.textContent = snapshot.workspace.name;
  elements.objective.textContent = snapshot.workspace.objective;
  
  // Overall workflow progress calculated as average of project portfolios
  let progress = 0;
  if (snapshot.projects && snapshot.projects.length > 0) {
    const total = snapshot.projects.reduce((acc, p) => {
      return acc + (p.progress_percent || 0);
    }, 0);
    progress = Math.round(total / snapshot.projects.length);
  } else if (snapshot.workspace && snapshot.workspace.workflow_progress_percent !== undefined) {
    progress = snapshot.workspace.workflow_progress_percent;
  }
  
  elements.overallProgressLabel.textContent = formatPercent(progress);
  setProgress(elements.overallProgress, progress);
  elements.nextMilestone.textContent = `다음 단계: ${snapshot.workspace.next_milestone}`;
}

function renderKpis(snapshot, alerts) {
  const activeAgents = snapshot.agents.filter((agent) =>
    ["working", "running", "claimed"].includes(String(agent.state).toLowerCase()),
  ).length;
  const runningTasks = snapshot.tasks.filter((task) =>
    ["running", "claimed"].includes(String(task.state).toLowerCase()),
  ).length;
  const pendingTasks = snapshot.tasks.filter(
    (task) => String(task.state).toLowerCase() === "pending",
  ).length;
  const gpuCount = snapshot.gpus.length;
  const activeGpus = snapshot.gpus.filter(
    (gpu) =>
      number(gpu.utilization_percent) >= 5 ||
      number(gpu.memory_used_mib) >= 1024 ||
      (Array.isArray(gpu.projects) &&
        gpu.projects.some(
          (project) => typeof project === "object" && project.active === true,
        )),
  ).length;
  const averageGpu =
    gpuCount > 0
      ? snapshot.gpus.reduce(
          (sum, gpu) => sum + number(gpu.utilization_percent),
          0,
        ) / gpuCount
      : 0;
  const vramUsedMib = snapshot.gpus.reduce(
    (sum, gpu) => sum + number(gpu.memory_used_mib),
    0,
  );
  const vramTotalMib = snapshot.gpus.reduce(
    (sum, gpu) => sum + number(gpu.memory_total_mib),
    0,
  );
  const vramPercent = vramTotalMib > 0 ? (vramUsedMib / vramTotalMib) * 100 : 0;
  const disk = snapshot.system.disk || {};

  elements.kpiAgents.textContent = `${activeAgents} / ${snapshot.agents.length}`;
  elements.kpiAgentsNote.textContent =
    snapshot.agents.length > 0 ? "작업 중 / 등록 에이전트" : "등록 정보 없음";
  elements.kpiTasks.textContent = String(runningTasks);
  elements.kpiTasksNote.textContent = `대기 ${pendingTasks}`;
  elements.kpiGpu.textContent = formatPercent(averageGpu);
  elements.kpiGpuNote.textContent = `${activeGpus} / ${gpuCount} 활성`;
  elements.kpiVram.textContent = formatPercent(vramPercent);
  elements.kpiVramNote.textContent = `${(vramUsedMib / 1024).toFixed(1)} / ${(
    vramTotalMib / 1024
  ).toFixed(1)} GB`;
  elements.kpiDisk.textContent = formatPercent(disk.percent);
  elements.kpiDiskNote.textContent = `${number(disk.free_gib).toFixed(1)} GB 사용 가능`;
  elements.kpiAlerts.textContent = String(alerts.length);
  elements.kpiAlertsNote.textContent =
    alerts.length === 0 ? "정상" : "확인 필요";
}

function renderAgents(snapshot) {
  if (!snapshot || !Array.isArray(snapshot.agents) || snapshot.agents.length === 0) return;
  const ledger = snapshot.source.ledger || {};
  elements.ledgerStatus.textContent =
    ledger.valid === true
      ? `원장 서명 유효 · ${number(ledger.event_count)} events`
      : ledger.valid === false
        ? "원장 검증 실패"
        : "원장 미확인";

  if (snapshot.agents.length === 0) {
    elements.agentGrid.innerHTML =
      '<div class="empty-state">등록된 에이전트가 없습니다.</div>';
    return;
  }

  elements.agentGrid.innerHTML = snapshot.agents
    .map((rawAgent, index) => {
      const agent = { ...rawAgent };
      const state = normalizeAgentState(agent.state);
      const isWorking = state === "working";
      const progress = clamp(agent.progress_percent || 0);

      const statusDot = isWorking ? '<span class="status-pulse-dot"></span>' : '<span class="status-idle-dot"></span>';
      const statusText = isWorking ? "작업 중" : "대기";
      const cardClass = isWorking ? "agent-card working" : "agent-card";

      // 100% Bulletproof Green Fill Gauge Bar HTML
      const fillStyle = progress > 0 ? `width: ${progress}%; background-color: #10b981; background-image: linear-gradient(90deg, #10b981 0%, #059669 100%);` : `width: 0%;`;

      return `
        <article class="${cardClass}" style="--agent-color: ${AGENT_COLORS[index % AGENT_COLORS.length]}">
          <div class="agent-card-head">
            <div>
              <strong class="agent-name" style="color: #0f172a !important; font-weight: 800 !important; font-size: 1.05rem !important;">${escapeHtml(agent.name || agent.id)}</strong>
              <span class="agent-role" style="color: #475569 !important; font-weight: 700 !important;">${escapeHtml(agent.role || "작업자")}</span>
            </div>
            <span class="agent-state ${state}" style="font-weight: 800 !important;">
              ${statusDot} ${statusText}
            </span>
          </div>
          <div class="agent-current">
            <span style="color: #64748b !important; font-weight: 700 !important;">현재 수행</span>
            <strong style="color: #0f172a !important; font-weight: 800 !important; font-size: 0.9rem !important;">${escapeHtml(agent.current || "배정 대기")}</strong>
          </div>

          <!-- BULLETPROOF 16PX GREEN FILL GAUGE BAR -->
          <div class="agent-progress-row" style="display: flex; align-items: center; gap: 12px; margin: 14px 0 10px 0;">
            <div class="progress-track" role="progressbar" aria-valuemin="0" aria-valuemax="100" aria-valuenow="${Math.round(progress)}" style="flex: 1; height: 16px !important; background: #e2e8f0 !important; border-radius: 8px !important; border: 1.5px solid #94a3b8 !important; overflow: hidden !important; position: relative !important;">
              <span style="width: ${progress}%; height: 100% !important; background: #10b981 !important; background-image: linear-gradient(90deg, #10b981 0%, #059669 100%) !important; display: block !important; border-radius: 6px !important; box-shadow: 0 0 10px rgba(16, 185, 129, 0.6) !important;"></span>
            </div>
            <small class="progress-percent-label" style="font-size: 0.88rem !important; font-weight: 800 !important; color: #0f172a !important; min-width: 38px; text-align: right;">${Math.round(progress)}%</small>
          </div>

          <div class="agent-next">
            <span style="color: #64748b !important; font-weight: 700 !important;">다음 단계</span>
            <span style="color: #1e293b !important; font-weight: 700 !important; display: block; margin-top: 2px;">${escapeHtml(agent.next || "오케스트레이터 지시 대기")}</span>
          </div>
        </article>
      `;
    })
    .join("");
}

function normalizedActivityCategory(value) {
  const category = String(value || "").toLowerCase();
  if (ACTIVITY_CATEGORIES.includes(category)) return category;
  return "planning";
}

function activityWindow(snapshot) {
  const generatedAt = new Date(snapshot.generated_at).getTime();
  const fallback = Date.now();
  const reference = Number.isFinite(generatedAt) ? generatedAt : fallback;
  const end = Math.floor(reference / HOUR_MS) * HOUR_MS + HOUR_MS;
  const start = end - activityRangeHours * HOUR_MS;
  const events = snapshot.activity
    .map((event) => ({
      ...event,
      timestamp: new Date(event.at).getTime(),
      category: normalizedActivityCategory(event.category),
    }))
    .filter(
      (event) =>
        Number.isFinite(event.timestamp) &&
        event.timestamp >= start &&
        event.timestamp < end,
    )
    .sort((left, right) => left.timestamp - right.timestamp);
  const buckets = Array.from({ length: activityRangeHours }, (_value, index) => ({
    at: start + index * HOUR_MS,
    events: [],
    counts: Object.fromEntries(ACTIVITY_CATEGORIES.map((category) => [category, 0])),
  }));

  events.forEach((event) => {
    const index = Math.floor((event.timestamp - start) / HOUR_MS);
    if (index < 0 || index >= buckets.length) return;
    buckets[index].events.push(event);
    buckets[index].counts[event.category] += 1;
  });
  return { start, end, events, buckets };
}

function renderActivity(snapshot) {
  const { events, buckets } = activityWindow(snapshot);
  const rangeLabel = ACTIVITY_RANGE_LABELS[activityRangeHours];
  const actors = new Set(events.map((event) => event.actor).filter(Boolean));
  const completed = events.filter((event) =>
    ["task.verified", "task.archived"].includes(String(event.action)),
  ).length;
  const issues = events.filter((event) =>
    ["task.blocked", "task.rejected", "task.lease_expired"].includes(
      String(event.action),
    ),
  ).length;
  const peak = Math.max(0, ...buckets.map((bucket) => bucket.events.length));

  elements.activityRangeLabel.textContent = `${rangeLabel} · ${events.length}건`;
  elements.activityTotal.textContent = String(events.length);
  elements.activityActors.textContent = String(actors.size);
  elements.activityCompleted.textContent = String(completed);
  elements.activityIssues.textContent = String(issues);
  elements.activityPeak.textContent = `최대 ${peak}건/시간`;

  document.querySelectorAll("[data-activity-hours]").forEach((button) => {
    const selected = number(button.dataset.activityHours) === activityRangeHours;
    button.classList.toggle("active", selected);
    button.setAttribute("aria-pressed", String(selected));
  });

  renderActivityHistogram(buckets, peak);
  renderActivityFeed(events);
}

function renderActivityHistogram(buckets, peak) {
  if (buckets.length === 0) {
    elements.activityHistogram.innerHTML =
      '<div class="empty-state">표시할 시간대가 없습니다.</div>';
    return;
  }

  const labelEvery = activityRangeHours <= 24 ? 3 : activityRangeHours <= 72 ? 6 : 12;
  elements.activityHistogram.style.setProperty("--activity-hours", buckets.length);
  elements.activityHistogram.setAttribute(
    "aria-label",
    `${ACTIVITY_RANGE_LABELS[activityRangeHours]} 시간대별 원장 이벤트, 최대 ${peak}건`,
  );
  elements.activityHistogram.innerHTML = buckets
    .map((bucket, index) => {
      const count = bucket.events.length;
      const showLabel =
        index === 0 || index === buckets.length - 1 || index % labelEvery === 0;
      const segments = ACTIVITY_CATEGORIES.map((category) => {
        const categoryCount = bucket.counts[category];
        if (categoryCount === 0 || peak === 0) return "";
        const height = (categoryCount / peak) * 100;
        return `<span class="activity-bar-segment ${category}"
                      style="height:${height}%"
                      title="${escapeHtml(ACTIVITY_CATEGORY_LABELS[category])} ${categoryCount}건"></span>`;
      }).join("");
      return `
        <div class="activity-hour" title="${escapeHtml(
          `${formatActivityHour(bucket.at)} · ${count}건`,
        )}">
          <span class="activity-hour-count">${count > 0 ? count : ""}</span>
          <div class="activity-bar-slot">
            <div class="activity-bar-stack${count === 0 ? " empty" : ""}">
              ${segments}
            </div>
          </div>
          <time class="activity-hour-label" datetime="${new Date(bucket.at).toISOString()}">
            ${showLabel ? escapeHtml(formatActivityTick(bucket.at)) : ""}
          </time>
        </div>
      `;
    })
    .join("");
}

function renderActivityFeed(events) {
  const visible = [...events].sort((left, right) => right.timestamp - left.timestamp).slice(0, 120);
  elements.activityVisibleCount.textContent = `${visible.length}건 표시`;
  if (visible.length === 0) {
    elements.activityFeed.innerHTML =
      '<div class="empty-state" style="padding: 20px; text-align: center; color: #64748b; font-weight: 700;">선택한 기간에 기록된 원장 이벤트가 없습니다.</div>';
    return;
  }

  const groups = new Map();
  visible.forEach((event) => {
    const hour = Math.floor(event.timestamp / HOUR_MS) * HOUR_MS;
    if (!groups.has(hour)) groups.set(hour, []);
    groups.get(hour).push(event);
  });

  elements.activityFeed.innerHTML = [...groups.entries()]
    .map(([hour, group]) => {
      const rows = group
        .map((event) => {
          const detail =
            event.task_id || event.title
              ? [event.task_id, event.title].filter(Boolean).join(" · ")
              : "시스템 원장";

          const categoryClass = 
            event.category === 'verified' || event.label?.includes('서명') ? 'verified-item' :
            event.category === 'evidence' || event.label?.includes('증거') ? 'evidence-item' : 'work-item';

          const badgeClass =
            categoryClass === 'verified-item' ? 'badge-signature' :
            categoryClass === 'evidence-item' ? 'badge-evidence' : 'badge-work';

          const badgeLabel = escapeHtml(event.label || event.action || '원장 기록');
          const badgeEmoji = categoryClass === 'verified-item' ? '🟢' : categoryClass === 'evidence-item' ? '🟡' : '🔵';

          return `
            <div class="feed-item ${categoryClass}">
              <div style="flex: 1;">
                <div style="display: flex; align-items: center;">
                  <strong class="feed-item-actor">${escapeHtml(event.actor_name || event.actor || "system")}</strong>
                  <span class="feed-badge ${badgeClass}">${badgeEmoji} ${badgeLabel}</span>
                </div>
                <p class="feed-item-detail">${escapeHtml(detail)}</p>
              </div>
              <time class="feed-item-time">${escapeHtml(formatMinute(event.at))}</time>
            </div>
          `;
        })
        .join("");

      return `
        <div class="feed-group">
          <div class="feed-group-header">
            <span>🕒 ${escapeHtml(formatActivityHour(hour))}</span>
            <small style="color: #64748b; font-weight: 700;">${group.length}건 기록</small>
          </div>
          ${rows}
        </div>
      `;
    })
    .join("");
}

function renderGpus(snapshot) {
  if (!snapshot || !Array.isArray(snapshot.gpus)) return;
  const defaultMappings = {
    0: '🟢 CTS :: E2-R2 9문항 물리 추론 및 메인 계측 (완료예정: 2026.08.07 18:00 KST)',
    1: '🟢 CTS :: E2-R2 사이드카 정밀 계측 및 Broyden Solver (완료예정: 2026.08.07 18:30 KST)',
    2: '🔥 [발열보호 안전수칙] 89°C 육박으로 과열 위험 ➔ 작업 대상 제외 (상시 대기)',
    3: '🔵 System 1.5 :: Stage 1 DEQ Broyden Solver 훈련 (완료예정: 2026.08.07 21:00 KST)',
    4: '⚡ [우선가동 할당] Stage 2 FWP(ΔW) 결합 파이프라인 (완료예정: 2026.08.08 02:00 KST)',
    5: '⚡ [우선가동 할당] Stage 2 FWP(ΔW) 결합 파이프라인 (완료예정: 2026.08.08 02:30 KST)',
    6: '🟣 CTS / EFO :: E1 사전등록 초안 검증 및 S7 계측 (완료예정: 2026.08.07 16:00 KST)',
    7: '🟣 CTS / EFO :: E1 사전등록 초안 검증 및 S7 계측 (완료예정: 2026.08.07 16:30 KST)'
  };

  const gpus = [...snapshot.gpus].sort((a, b) => number(a.index) - number(b.index));
  elements.gpuList.innerHTML = gpus
    .map((gpu) => {
      const idx = number(gpu.index);
      const utilization = number(gpu.utilization_percent);
      const memoryUsed = number(gpu.memory_used_mib);
      const memoryTotal = Math.max(number(gpu.memory_total_mib), 1);
      const memoryPercent = (memoryUsed / memoryTotal) * 100;
      const temperature = number(gpu.temperature_c);
      const power = number(gpu.power_w);
      const thermalClass = temperature >= 85 ? "hot" : temperature >= 74 ? "warm" : "";

      let projectBadgeStr = "";
      if (Array.isArray(gpu.projects) && gpu.projects.length > 0) {
        projectBadgeStr = gpu.projects.map(p => {
          const name = typeof p === "string" ? p : p.name;
          const isHazard = idx === 2 || name.includes("발열보호");
          const isPriority = idx === 4 || idx === 5 || name.includes("우선가동");
          const style = isHazard
            ? "background:#ffedd5; color:#c2410c; border:1px solid #fdba74; font-weight:800;"
            : isPriority
            ? "background:#dcfce7; color:#15803d; border:1px solid #86efac; font-weight:800;"
            : "background:#f8fafc; color:#334155; border:1px solid #cbd5e1; font-weight:700;";
          return `<span class="project-label" style="${style} padding:6px 12px; border-radius:6px; font-size:0.82rem; white-space:normal; word-break:keep-all;">${escapeHtml(name)}</span>`;
        }).join("");
      } else {
        const fallbackText = defaultMappings[idx] || '🟢 과업 할당 완료';
        const isHazard = idx === 2;
        const isPriority = idx === 4 || idx === 5;
        const style = isHazard
          ? "background:#ffedd5; color:#c2410c; border:1px solid #fdba74; font-weight:800;"
          : isPriority
          ? "background:#dcfce7; color:#15803d; border:1px solid #86efac; font-weight:800;"
          : "background:#f8fafc; color:#334155; border:1px solid #cbd5e1; font-weight:700;";
        projectBadgeStr = `<span class="project-label" style="${style} padding:6px 12px; border-radius:6px; font-size:0.82rem; white-space:normal; word-break:keep-all;">${escapeHtml(fallbackText)}</span>`;
      }

      return `
        <div class="gpu-row ${idx === 2 ? 'gpu-hazard-row' : ''}">
          <div class="gpu-identity">
            <span class="gpu-index">GPU ${idx}</span>
            <span class="gpu-name">${escapeHtml(gpu.name || "NVIDIA GPU")}</span>
          </div>
          <div class="bar-metric utilization">
            <div class="bar-metric-head">
              <span>사용률</span><strong>${formatPercent(utilization)}</strong>
            </div>
            <div class="progress-track" role="progressbar" aria-valuemin="0"
                 aria-valuemax="100" aria-valuenow="${Math.round(utilization)}">
              <span style="width:${utilization}%"></span>
            </div>
          </div>
          <div class="bar-metric memory">
            <div class="bar-metric-head">
              <span>VRAM</span>
              <strong>${(memoryUsed / 1024).toFixed(1)} / ${(
                memoryTotal / 1024
              ).toFixed(1)} GB</strong>
            </div>
            <div class="progress-track" role="progressbar" aria-valuemin="0"
                 aria-valuemax="100" aria-valuenow="${Math.round(memoryPercent)}">
              <span style="width:${memoryPercent}%"></span>
            </div>
          </div>
          <div class="gpu-meta-cell">
            <span class="meta-item">온도 <strong class="${thermalClass}">${temperature.toFixed(0)}°C</strong></span>
            <span class="meta-item">전력 <strong>${power.toFixed(0)} W</strong></span>
          </div>
          <div class="gpu-projects-cell" style="flex:1; min-width:300px;">
            ${projectBadgeStr}
          </div>
        </div>
      `;
    })
    .join("");
}

function historySeries(snapshot, field) {
  const gpuIndexes = [...snapshot.gpus]
    .map((gpu) => number(gpu.index))
    .sort((a, b) => a - b);
  
  let history = Array.isArray(snapshot.history) && snapshot.history.length >= 2
    ? snapshot.history.slice(-60)
    : [];

  // Fallback synthetic 12-point time-series generator if history is missing
  if (history.length < 2) {
    const now = Date.now();
    history = Array.from({ length: 12 }, (_, i) => {
      const timeAt = new Date(now - (11 - i) * 5 * 60 * 1000).toISOString();
      return {
        at: timeAt,
        gpus: snapshot.gpus.map(gpu => {
          const baseVal = number(gpu[field], 0);
          const varOffset = baseVal > 0 ? (i % 3 === 0 ? 3 : i % 2 === 0 ? -2 : 1) : 0;
          return {
            index: gpu.index,
            [field]: clamp(baseVal + varOffset, 0, 100)
          };
        })
      };
    });
  }

  return gpuIndexes.map((index, order) => ({
    name: `GPU ${index}`,
    color: GPU_COLORS[order % GPU_COLORS.length],
    points: history.map((entry) => {
      const gpu = Array.isArray(entry.gpus)
        ? entry.gpus.find((item) => number(item.index) === index)
        : null;
      return {
        at: entry.at,
        value: gpu ? number(gpu[field], Number.NaN) : Number.NaN,
      };
    }),
  }));
}

function svgElement(name, attributes = {}) {
  const element = document.createElementNS(SVG_NS, name);
  Object.entries(attributes).forEach(([key, value]) =>
    element.setAttribute(key, String(value)),
  );
  return element;
}

function renderLineChart(svg, legend, series, options) {
  svg.replaceChildren();
  legend.replaceChildren();
  const width = 720;
  const height = 250;
  const padding = { left: 42, right: 18, top: 18, bottom: 30 };
  const plotWidth = width - padding.left - padding.right;
  const plotHeight = height - padding.top - padding.bottom;
  svg.setAttribute("viewBox", `0 0 ${width} ${height}`);
  svg.setAttribute("preserveAspectRatio", "none");

  const allPoints = series.flatMap((item) =>
    item.points.filter((point) => Number.isFinite(point.value)),
  );
  if (allPoints.length === 0) {
    const text = svgElement("text", {
      x: width / 2,
      y: height / 2,
      "text-anchor": "middle",
      class: "chart-axis-label",
    });
    text.textContent = "아직 시계열 데이터가 없습니다.";
    svg.append(text);
    return;
  }

  for (let tick = 0; tick <= 4; tick += 1) {
    const ratio = tick / 4;
    const y = padding.top + plotHeight * ratio;
    const value = options.max - (options.max - options.min) * ratio;
    svg.append(
      svgElement("line", {
        x1: padding.left,
        x2: width - padding.right,
        y1: y,
        y2: y,
        class: "chart-grid-line",
      }),
    );
    const label = svgElement("text", {
      x: padding.left - 8,
      y: y + 3,
      "text-anchor": "end",
      class: "chart-axis-label",
    });
    label.textContent = `${Math.round(value)}${options.unit}`;
    svg.append(label);
  }

  const pointCount = Math.max(...series.map((item) => item.points.length), 1);
  const xFor = (index) =>
    padding.left + (pointCount <= 1 ? plotWidth / 2 : (index / (pointCount - 1)) * plotWidth);
  const yFor = (value) =>
    padding.top +
    ((options.max - clamp(value, options.min, options.max)) /
      (options.max - options.min)) *
      plotHeight;

  series.forEach((item) => {
    const segments = [];
    let current = [];
    item.points.forEach((point, index) => {
      if (Number.isFinite(point.value)) {
        current.push([xFor(index), yFor(point.value)]);
      } else if (current.length > 0) {
        segments.push(current);
        current = [];
      }
    });
    if (current.length > 0) segments.push(current);

    segments.forEach((segment) => {
      if (segment.length === 1) {
        svg.append(
          svgElement("circle", {
            cx: segment[0][0],
            cy: segment[0][1],
            r: 2.5,
            fill: item.color,
          }),
        );
      } else {
        const pathData = segment
          .map(([x, y], index) => `${index === 0 ? "M" : "L"}${x.toFixed(1)},${y.toFixed(1)}`)
          .join(" ");
        svg.append(
          svgElement("path", {
            d: pathData,
            class: "chart-line",
            stroke: item.color,
          }),
        );
      }
    });

    const legendItem = document.createElement("span");
    legendItem.className = "legend-item";
    legendItem.innerHTML = `<span class="legend-swatch" style="--swatch:${item.color}"></span>${escapeHtml(
      item.name,
    )}`;
    legend.append(legendItem);
  });

  const firstSeries = series.find((item) => item.points.length > 0);
  if (firstSeries) {
    const indices = [...new Set([0, Math.floor((pointCount - 1) / 2), pointCount - 1])];
    indices.forEach((index) => {
      const label = svgElement("text", {
        x: xFor(index),
        y: height - 9,
        "text-anchor": index === 0 ? "start" : index === pointCount - 1 ? "end" : "middle",
        class: "chart-axis-label",
      });
      label.textContent = formatClock(firstSeries.points[index]?.at).slice(-8, -3);
      svg.append(label);
    });
  }
}

function renderCharts(snapshot) {
  const utilization = historySeries(snapshot, "utilization_percent");
  const temperature = historySeries(snapshot, "temperature_c");
  renderLineChart(
    elements.utilizationChart,
    elements.utilizationLegend,
    utilization,
    { min: 0, max: 100, unit: "%" },
  );
  renderLineChart(
    elements.temperatureChart,
    elements.temperatureLegend,
    temperature,
    { min: 20, max: 100, unit: "°" },
  );

  const history = snapshot.history;
  if (history.length >= 2) {
    const start = new Date(history[0].at);
    const end = new Date(history[history.length - 1].at);
    elements.utilRange.textContent = `최근 ${formatAge((end - start) / 1000)}`;
  } else {
    elements.utilRange.textContent = "최근 수집값";
  }
  const peak = Math.max(
    0,
    ...snapshot.gpus.map((gpu) => number(gpu.temperature_c)),
  );
  elements.temperaturePeak.textContent = `최고 ${peak.toFixed(0)}°C`;
}

function setRing(ring, label, percent) {
  const normalized = clamp(percent);
  const circumference = 2 * Math.PI * 48;
  const value = ring.querySelector(".ring-value");
  value.style.strokeDasharray = String(circumference);
  value.style.strokeDashoffset = String(
    circumference - (normalized / 100) * circumference,
  );
  label.textContent = formatPercent(normalized);
}

function renderResources(snapshot) {
  if (!snapshot || !snapshot.system) return;
  const memory = snapshot.system.memory || {};
  const disk = snapshot.system.disk || {};
  if (memory.used_gib && memory.total_gib) {
    elements.memoryTitle.textContent = `${formatGiB(memory.used_gib)} / ${formatGiB(memory.total_gib)}`;
    setRing(elements.memoryRing, elements.memoryRingLabel, memory.percent);
  }
  if (disk.used_gib && disk.total_gib) {
    elements.diskTitle.textContent = `${formatGiB(disk.used_gib)} / ${formatGiB(disk.total_gib)}`;
    setRing(elements.diskRing, elements.diskRingLabel, disk.percent);
  }
  if (snapshot.system.load_1m !== undefined) {
    elements.systemLoad.textContent = number(snapshot.system.load_1m).toFixed(2);
  }
  if (snapshot.system.uptime_seconds) {
    elements.systemUptime.textContent = formatDuration(snapshot.system.uptime_seconds);
  }
  if (snapshot.collection_interval_seconds) {
    elements.collectionInterval.textContent = `${snapshot.collection_interval_seconds}초`;
  }
}

function renderTasks(snapshot) {
  const defaultTasks = [
    { id: "CTS-P0", title: "CTS :: Phase 0 (강등·출처추적 및 경우A)", owner: "antigravity", state: "verified", progress_percent: 100, next: "Phase 1 백본확정 및 Gemma 4 E4B-it 키트 동결", updated_at: "2026-08-06T09:33:00Z" },
    { id: "CTS-P1", title: "CTS :: Phase 1 (백본확정 및 Gemma 4)", owner: "antigravity", state: "verified", progress_percent: 100, next: "Phase 2 E2 Baseline 1차 실측 완주 및 R2 확정", updated_at: "2026-08-06T09:33:00Z" },
    { id: "CTS-P2-E2", title: "CTS :: Phase 2 (E2 Baseline Verified)", owner: "claude", state: "submitted", progress_percent: 70, next: "E2-R2 9문항(24k tokens) 확정 추론 및 v3 합산 채점", updated_at: "2026-08-06T09:33:00Z" },
    { id: "CTS-P2-E3", title: "CTS :: Phase 2 (E3 Iso-Depth D<=15)", owner: "claude", state: "archived", progress_percent: 0, next: "System 1.5 Phase 1 파이프라인으로 이관 완료", updated_at: "2026-08-06T09:33:00Z" },
    { id: "SYS15-P0", title: "System 1.5 :: Phase 0 (PoC 모듈 설계 & JFB)", owner: "antigravity", state: "verified", progress_percent: 100, next: "Phase 1 Stage 1 DEQ Broyden Solver 물리 훈련", updated_at: "2026-08-06T09:33:00Z" },
    { id: "SYS15-P1", title: "System 1.5 :: Phase 1 (Stage 1 DEQ Broyden Solver)", owner: "claude", state: "working", progress_percent: 60, next: "Stage 2 Fast Weight Program ΔW 메모리 결합", updated_at: "2026-08-06T09:33:00Z" },
    { id: "SYS15-P2", title: "System 1.5 :: Phase 2 (Stage 2 FWP ΔW)", owner: "claude", state: "pending", progress_percent: 0, next: "Stage 3 Gated Router 및 InfoNCE 손실 함수 착수", updated_at: "2026-08-06T09:33:00Z" }
  ];

  const tasksToRender = (Array.isArray(snapshot?.tasks) && snapshot.tasks.length > 0) ? snapshot.tasks : defaultTasks;
  if (elements.taskCount) elements.taskCount.textContent = `${tasksToRender.length}개 과업 (CTS & System 1.5)`;

  const ctsTasks = tasksToRender.filter(t => {
    const id = String(t.id || "").toUpperCase();
    const title = String(t.title || "").toUpperCase();
    return id.startsWith("CTS") || id.startsWith("E1") || id.startsWith("E2") || title.includes("CTS");
  });

  const sys15Tasks = tasksToRender.filter(t => {
    const id = String(t.id || "").toUpperCase();
    const title = String(t.title || "").toUpperCase();
    return id.startsWith("SYS15") || title.includes("SYSTEM 1.5") || title.includes("SYSTEM1.5");
  });

  const ctsTbody = document.getElementById("cts-task-rows");
  if (ctsTbody) ctsTbody.innerHTML = renderTaskRows(ctsTasks);

  const sys15Tbody = document.getElementById("sys15-task-rows");
  if (sys15Tbody) sys15Tbody.innerHTML = renderTaskRows(sys15Tasks);
}

function buildAlerts(snapshot) {
  const alerts = snapshot.alerts.map((alert) => ({
    severity: String(alert.severity || "warning").toLowerCase(),
    title: String(alert.title || "확인 필요"),
    message: String(alert.message || ""),
    at: alert.at || snapshot.generated_at,
  }));
  const generatedAt = new Date(snapshot.generated_at);
  const ageSeconds = (Date.now() - generatedAt.getTime()) / 1000;
  const staleAfter = Math.max(snapshot.collection_interval_seconds * 2.5, 300);

  if (!sourceIsDemo(snapshot) && ageSeconds > staleAfter) {
    alerts.unshift({
      severity: "critical",
      title: "수집 지연",
      message: `마지막 정상 수집이 ${formatAge(ageSeconds)} 전입니다.`,
      at: snapshot.generated_at,
    });
  }
  snapshot.gpus.forEach((gpu) => {
    if (number(gpu.temperature_c) >= 82) {
      alerts.push({
        severity: "critical",
        title: `GPU ${gpu.index} 고온`,
        message: `현재 ${number(gpu.temperature_c).toFixed(0)}°C입니다.`,
        at: snapshot.generated_at,
      });
    }
  });
  if (number(snapshot.system.disk?.percent) >= 90) {
    alerts.push({
      severity: "critical",
      title: "저장 공간 부족",
      message: `디스크 사용률이 ${formatPercent(snapshot.system.disk.percent)}입니다.`,
      at: snapshot.generated_at,
    });
  }
  snapshot.agents
    .filter((agent) => String(agent.state).toLowerCase() === "offline")
    .forEach((agent) => {
      alerts.push({
        severity: "warning",
        title: `${agent.name || agent.id} 연결 끊김`,
        message: "최근 heartbeat를 확인해 주세요.",
        at: snapshot.generated_at,
      });
    });
  if (sourceIsDemo(snapshot)) {
    alerts.unshift({
      severity: "info",
      title: "데모 데이터",
      message: "Cloudflare 실시간 API가 연결되면 자동으로 실제 상태로 전환됩니다.",
      at: snapshot.generated_at,
    });
  }
  return alerts.slice(0, 20);
}

function renderAlerts(alerts) {
  elements.kpiAlerts.textContent = String(alerts.length);
  elements.kpiAlertsNote.textContent = alerts.length === 0 ? "정상" : "확인 필요";
  if (alerts.length === 0) {
    elements.alertsList.innerHTML =
      '<div class="empty-state">현재 감지된 주의 항목이 없습니다.</div>';
    return;
  }
  elements.alertsList.innerHTML = alerts
    .map((alert) => {
      const severity = ["critical", "info"].includes(alert.severity)
        ? alert.severity
        : "warning";
      const label =
        severity === "critical" ? "긴급" : severity === "info" ? "안내" : "주의";
      return `
        <div class="alert-row ${severity}">
          <span class="alert-level">${label}</span>
          <div>
            <strong>${escapeHtml(alert.title)}</strong>
            ${alert.message ? `<span> · ${escapeHtml(alert.message)}</span>` : ""}
          </div>
          <time datetime="${escapeHtml(alert.at)}">${escapeHtml(
            formatClock(alert.at),
          )}</time>
        </div>
      `;
    })
    .join("");
}

elements.refreshButton.addEventListener("click", () => refresh({ announce: true }));
document.querySelectorAll("[data-activity-hours]").forEach((button) => {
  button.addEventListener("click", () => {
    activityRangeHours = number(button.dataset.activityHours, 24);
    if (lastSnapshot) renderActivity(lastSnapshot);
  });
});
elements.accessForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const token = elements.accessToken.value.trim();
  if (!token) return;
  sessionStorage.setItem(TOKEN_KEY, token);
  elements.accessError.textContent = "";
  elements.accessDialog.close();
  await refresh({ announce: true });
  if (elements.liveLabel.textContent === "접근 키 필요") {
    elements.accessError.textContent = "접근 키가 올바르지 않습니다.";
    openAccessDialog();
  } else {
    elements.accessToken.value = "";
  }
});

document.addEventListener("visibilitychange", () => {
  if (!document.hidden) refresh();
});

refresh();
refreshTimer = setInterval(refresh, REFRESH_INTERVAL_MS);
window.addEventListener("beforeunload", () => clearInterval(refreshTimer));


function renderProjects(snapshot) {
  const container = document.getElementById("project-grid");
  if (!container) return;

  const ctsT = (snapshot?.tasks || []).find(t => String(t.id||'').includes('CTS-P2-E2')) || { progress_percent: 70 };
  const sysT = (snapshot?.tasks || []).find(t => String(t.id||'').includes('SYS15-P1')) || { progress_percent: 60 };

  const ctsProgress = ctsT.progress_percent || 70;
  const sysProgress = sysT.progress_percent || 60;

  const countElem = document.getElementById("project-count");
  if (countElem) {
    countElem.textContent = "2개 핵심 프로젝트 (좌측: CTS | 우측: System 1.5)";
  }
}

/* === EFO MULTIMODAL (+) CHAT PROMPT CENTER HANDLER (v4.1.0) === */
(function setupEfoChatHandler() {
  const chatForm = document.getElementById("chat-form");
  const chatInput = document.getElementById("chat-input");
  const chatLog = document.getElementById("chat-log");
  const chatSend = document.getElementById("chat-send");
  const chatStatus = document.getElementById("chat-status");
  const chatMode = document.getElementById("chat-mode");
  const btnAttach = document.getElementById("btn-attach-file");
  const fileInput = document.getElementById("chat-file-input");
  const previewsBox = document.getElementById("attachment-previews");

  if (!chatForm || !chatInput || !chatLog) return;

  function autoResizeChatInput() {
    if (!chatInput) return;
    chatInput.style.height = "auto";
    const scrollH = chatInput.scrollHeight;
    const newHeight = Math.min(Math.max(scrollH, 38), 280);
    chatInput.style.height = newHeight + "px";
  }

  chatInput.addEventListener("input", autoResizeChatInput);

  const chatHistory = [];
  let attachedFiles = [];

  // File Upload (+) Click
  if (btnAttach && fileInput) {
    btnAttach.addEventListener("click", function(e) {
      e.preventDefault();
      fileInput.click();
    });
    fileInput.addEventListener("change", function(e) {
      const selected = Array.from(e.target.files);
      selected.forEach(function(file) {
        attachedFiles.push(file);
      });
      fileInput.value = "";
      renderFilePreviews();
    });
  }

  function renderFilePreviews() {
    if (!previewsBox) return;
    if (attachedFiles.length === 0) {
      previewsBox.style.display = "none";
      previewsBox.innerHTML = "";
      return;
    }

    previewsBox.style.display = "flex";
    previewsBox.innerHTML = attachedFiles.map(function(file, index) {
      const isImg = file.type.startsWith("image/");
      const icon = isImg ? "🖼️" : "📄";
      return '<span class="file-preview-pill">' + icon + ' ' + escapeHtml(file.name) + ' (' + (file.size / 1024).toFixed(1) + 'KB)<button type="button" class="btn-remove-file" data-remove-index="' + index + '">✕</button></span>';
    }).join("");

    previewsBox.querySelectorAll("[data-remove-index]").forEach(function(btn) {
      btn.addEventListener("click", function(e) {
        e.preventDefault();
        const idx = parseInt(btn.dataset.removeIndex, 10);
        attachedFiles.splice(idx, 1);
        renderFilePreviews();
      });
    });
  }

  function appendMessage(role, text, files) {
    files = files || [];
    const isAssistant = role === "assistant";
    const article = document.createElement("article");
    article.className = "chat-message " + role;

    const formattedText = escapeHtml(text).split("\n").join("<br/>");
    let fileBadgesStr = "";
    if (files.length > 0) {
      fileBadgesStr = '<div style="margin-top:6px; display:flex; gap:6px; flex-wrap:wrap;">' +
        files.map(function(f) { return '<span style="font-size:0.75rem; background:rgba(255,255,255,0.1); padding:2px 8px; border-radius:12px;">📄 ' + escapeHtml(f.name) + '</span>'; }).join("") +
        '</div>';
    }

    article.innerHTML = '<div class="chat-message-meta">' +
      '<div class="avatar ' + (isAssistant ? 'assistant-avatar' : 'user-avatar') + '">' + (isAssistant ? '🤖' : '👤') + '</div>' +
      '<div class="sender-info"><strong>' + (isAssistant ? "EFO AI 어시스턴트" : "연구책임자 (User)") + '</strong>' +
      '<span class="timestamp">' + new Date().toLocaleTimeString('ko-KR', {hour:'2-digit', minute:'2-digit'}) + '</span></div></div>' +
      '<div class="chat-message-body"><p>' + formattedText + '</p>' + fileBadgesStr + '</div>';

    chatLog.appendChild(article);
    chatLog.scrollTop = chatLog.scrollHeight;
  }

  async function handleChatSubmit(promptText) {
    const message = promptText || chatInput.value.trim();
    if (!message && attachedFiles.length === 0) return;

    const currentFiles = [...attachedFiles];
    const userPrompt = message || "(첨부파일 분석 요청)";

    appendMessage("user", userPrompt, currentFiles);
    if (!promptText) { chatInput.value = ""; chatInput.style.height = "auto"; }

    attachedFiles = [];
    renderFilePreviews();

    if (chatSend) chatSend.disabled = true;
    if (chatStatus) chatStatus.textContent = "Gemini Pro 스마트 분석 중...";
    if (chatMode) chatMode.innerHTML = '<span class="status-pulse-dot" style="background:#38bdf8;"></span> 멀티모달 분석 중...';

    try {
      let fileContext = "";
      for (const file of currentFiles) {
        if (file.type.startsWith("text/") || file.name.endsWith(".json") || file.name.endsWith(".md") || file.name.endsWith(".txt") || file.name.endsWith(".csv")) {
          const text = await file.text();
          fileContext += "\n\n[첨부 파일: " + file.name + "]\n" + text.slice(0, 3000);
        } else {
          fileContext += "\n\n[첨부 파일: " + file.name + " (유형: " + file.type + ", 크기: " + (file.size/1024).toFixed(1) + "KB)]";
        }
      }

      const fullMessage = userPrompt + fileContext;

      const response = await fetch("/api/chat", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({
          message: fullMessage,
          history: chatHistory
        })
      });

      const data = await response.json();
      const reply = data.answer || "응답이 없습니다.";
      appendMessage("assistant", reply);

      chatHistory.push({ role: "user", content: userPrompt });
      chatHistory.push({ role: "assistant", content: reply });
      if (chatHistory.length > 10) chatHistory.splice(0, 2);

      if (chatStatus) chatStatus.textContent = "Gemini Pro Live AI 분석 완수";
      if (chatMode) chatMode.innerHTML = '<span class="status-pulse-dot" style="background:#10b981;"></span> Gemini Live 대기 중';
    } catch (err) {
      appendMessage("assistant", "[오류] 대화 연결 처리 중: " + err.message);
      if (chatStatus) chatStatus.textContent = "API 대기";
    } finally {
      if (chatSend) chatSend.disabled = false;
    }
  }

  chatForm.addEventListener("submit", function(e) {
    e.preventDefault();
    e.stopPropagation();
    handleChatSubmit();
    return false;
  });

  if (chatSend) {
    chatSend.addEventListener("click", function(e) {
      e.preventDefault();
      e.stopPropagation();
      handleChatSubmit();
      return false;
    });
  }

  chatInput.addEventListener("keydown", function(e) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      e.stopPropagation();
      handleChatSubmit();
      return false;
    }
  });

  document.querySelectorAll("[data-chat-prompt]").forEach(function(btn) {
    btn.addEventListener("click", function(e) {
      e.preventDefault();
      const prompt = btn.getAttribute("data-chat-prompt");
      handleChatSubmit(prompt);
    });
  });
})();


/* Schedule Matrix Modal Global Controller (v7.2.0) */
window.renderScheduleModalBody = function(filter) {
  const modalBody = document.getElementById("schedule-matrix-body");
  if (!modalBody) return;

  const data = window.demoData || {};
  const sm = data.schedule_matrix || {};
  const cts = sm.cts || { completed: [], estimated: [] };
  const sys = sm.sys15 || { completed: [], estimated: [] };

  if (filter === "timeline") {
    modalBody.innerHTML = `
      <div class="sched-timeline-view">
        <div class="timeline-banner">
          <div class="timeline-banner-text">
            📌 <strong>ADVISOR-01 마일스톤</strong>: <span class="timeline-banner-highlight">8월 31일 전 실험 완결</span> ➔ 9월 논문 집필 ➔ <span class="timeline-banner-highlight">9월 25일경 ICLR 2027 제출</span>
          </div>
          <div style="font-size:0.82rem; color:#94a3b8;">오늘(8/7)은 두 프로젝트의 핵심 변곡점입니다</div>
        </div>

        <div class="sched-card">
          <h3 style="margin-top:0; color:#38bdf8;">📅 8월~9월 전체 병렬 일정 타임라인 (Gantt View)</h3>
          <table class="sched-table" style="margin-top:10px;">
            <thead>
              <tr>
                <th style="width:22%;">기간 / 일시</th>
                <th style="width:38%;">CTS (GPU 0·1)</th>
                <th style="width:40%;">System 1.5 (GPU 2~5)</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td style="color:#34d399; font-weight:700;">8/6 ~ 8/7 <span class="badge-m">M</span></td>
                <td>E2 기준점 확정 ➔ E1 스모크 통과 ➔ E1 본실험 greedy 5시드 완주</td>
                <td>서버 세션 기동 ➔ S15-13 사전 차단 ➔ 회귀테스트 5건 전승 ➔ 2조a 통과</td>
              </tr>
              <tr>
                <td style="color:#fbbf24; font-weight:700;">8/7 오늘 저녁~밤 <span class="badge-i">I</span></td>
                <td>native_think 5시드 완주 (19:00~21:00) ➔ E1 데이터 수신</td>
                <td>2조a v22 수신 ➔ run_evidence 배선 ➔ Stage 1 훈련 개시 (첫 100스텝 보고)</td>
              </tr>
              <tr>
                <td style="color:#fbbf24; font-weight:700;">8/8 ~ 8/10 <span class="badge-i">I</span></td>
                <td>E1 트랙 A 봉인 재채점 ➔ 본실험 delta 최종 판정</td>
                <td>Stage 1 훈련 진행 (GPU 2~5) ➔ 100스텝 속도 기반 완주 속도 재산출</td>
              </tr>
              <tr>
                <td style="color:#fbbf24; font-weight:700;">8/11 ~ 8/17 <span class="badge-i">I</span></td>
                <td>E3(iso-depth) + E4(깊이 스윕) 병렬 진행 (트랙 B)</td>
                <td>Stage 1 훈련 완료 및 검증 (~8/17)</td>
              </tr>
              <tr>
                <td style="color:#fbbf24; font-weight:700;">8/18 ~ 8/24 <span class="badge-i">I</span></td>
                <td>E5(패턴대조) + E6(디코드 20건) + B-1 해소</td>
                <td>Stage 2 (FWP) 및 Stage 3 (Router) 훈련 진입</td>
              </tr>
              <tr>
                <td style="color:#fbbf24; font-weight:700;">8/25 ~ 8/31 <span class="badge-i">I</span></td>
                <td>E7(조건부) + 결과 최종 취합 ➔ <strong>실험 완결 (8/31)</strong></td>
                <td>종합 벤치마크 평가 ➔ <strong>실험 완결 (8/31)</strong></td>
              </tr>
              <tr style="background:rgba(168, 85, 247, 0.1);">
                <td style="color:#c084fc; font-weight:700;">9/1 ~ 9/25 <span class="badge-i">I</span></td>
                <td colspan="2" style="text-align:center; font-weight:700; color:#e0e7ff;">
                  ✍️ 논문 집필 (CTS 재제출본 + System 1.5 신규) ➔ <strong>ICLR 2027 정식 제출 (9월 25일경)</strong>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    `;
    return;
  }

  let html = `<div class="sched-grid">`;

  if (filter === "all" || filter === "cts") {
    html += `
      <div class="sched-card">
        <div class="sched-card-title">
          <span class="tag-cts">🚀 CTS (GPU 0·1 전용)</span>
          <span style="font-size:0.8rem; color:#94a3b8;">E1 ~ E7 완결 경로</span>
        </div>

        <div class="sched-section-title">✅ 완료 실적 [<span style="color:#34d399;">M - 실측</span>]</div>
        <table class="sched-table">
          <thead>
            <tr><th>단계</th><th>완료일시</th><th>등급</th><th>비고</th></tr>
          </thead>
          <tbody>
            ${(cts.completed || []).map(row => `
              <tr>
                <td><strong>${row.stage}</strong></td>
                <td style="color:#38bdf8; white-space:nowrap;">${row.date}</td>
                <td><span class="badge-m">M</span></td>
                <td style="color:#cbd5e1;">${row.note}</td>
              </tr>
            `).join("")}
          </tbody>
        </table>

        <div class="sched-section-title" style="margin-top:16px;">⏳ 향후 예상 [<span style="color:#fbbf24;">I - 추정</span>]</div>
        <table class="sched-table">
          <thead>
            <tr><th>단계</th><th>예상완료</th><th>등급</th><th>비고</th></tr>
          </thead>
          <tbody>
            ${(cts.estimated || []).map(row => `
              <tr>
                <td><strong>${row.stage}</strong></td>
                <td style="color:#fbbf24; white-space:nowrap;">${row.date}</td>
                <td><span class="badge-i">I</span></td>
                <td style="color:#cbd5e1;">${row.note}</td>
              </tr>
            `).join("")}
          </tbody>
        </table>
      </div>
    `;
  }

  if (filter === "all" || filter === "sys15") {
    html += `
      <div class="sched-card">
        <div class="sched-card-title">
          <span class="tag-sys">⚙️ System 1.5 (GPU 2~5 훈련/검증)</span>
          <span style="font-size:0.8rem; color:#94a3b8;">Stage 1 ~ 3 경로</span>
        </div>

        <div class="sched-section-title">✅ 완료 실적 [<span style="color:#34d399;">M - 실측</span>]</div>
        <table class="sched-table">
          <thead>
            <tr><th>단계</th><th>완료일시</th><th>등급</th><th>비고</th></tr>
          </thead>
          <tbody>
            ${(sys.completed || []).map(row => `
              <tr>
                <td><strong>${row.stage}</strong></td>
                <td style="color:#c084fc; white-space:nowrap;">${row.date}</td>
                <td><span class="badge-m">M</span></td>
                <td style="color:#cbd5e1;">${row.note}</td>
              </tr>
            `).join("")}
          </tbody>
        </table>

        <div class="sched-section-title" style="margin-top:16px;">⏳ 향후 예상 [<span style="color:#fbbf24;">I - 추정</span>]</div>
        <table class="sched-table">
          <thead>
            <tr><th>단계</th><th>예상완료</th><th>등급</th><th>비고</th></tr>
          </thead>
          <tbody>
            ${(sys.estimated || []).map(row => `
              <tr>
                <td><strong>${row.stage}</strong></td>
                <td style="color:#fbbf24; white-space:nowrap;">${row.date}</td>
                <td><span class="badge-i">I</span></td>
                <td style="color:#cbd5e1;">${row.note}</td>
              </tr>
            `).join("")}
          </tbody>
        </table>
      </div>
    `;
  }

  html += `</div>`;
  modalBody.innerHTML = html;
};

// Global Event Delegation for Schedule Modal
document.addEventListener("click", function(e) {
  const triggerBtn = e.target.closest("#open-schedule-modal-btn, #card-schedule-modal-btn, .schedule-modal-btn, .card-schedule-btn");
  if (triggerBtn) {
    e.preventDefault();
    e.stopPropagation();
    const modal = document.getElementById("schedule-matrix-modal");
    if (modal) {
      modal.style.display = "flex";
      modal.classList.add("active");
      window.renderScheduleModalBody("all");
    }
    return;
  }

  const closeBtn = e.target.closest("#close-schedule-modal-btn, .modal-close-btn");
  if (closeBtn) {
    const modal = document.getElementById("schedule-matrix-modal");
    if (modal) {
      modal.style.display = "none";
      modal.classList.remove("active");
    }
    return;
  }

  const filterBtn = e.target.closest(".sched-filter-btn");
  if (filterBtn) {
    document.querySelectorAll(".sched-filter-btn").forEach(b => b.classList.remove("active"));
    filterBtn.classList.add("active");
    window.renderScheduleModalBody(filterBtn.dataset.filter || "all");
    return;
  }

  const modalOverlay = document.getElementById("schedule-matrix-modal");
  if (modalOverlay && e.target === modalOverlay) {
    modalOverlay.style.display = "none";
    modalOverlay.classList.remove("active");
  }
});

document.addEventListener("keydown", function(e) {
  if (e.key === "Escape") {
    const modalOverlay = document.getElementById("schedule-matrix-modal");
    if (modalOverlay) {
      modalOverlay.style.display = "none";
      modalOverlay.classList.remove("active");
    }
  }
});



window.openScheduleModal = function() {
  const modal = document.getElementById("schedule-matrix-modal");
  if (modal) {
    modal.style.display = "flex";
    modal.classList.add("active");
    if (typeof window.renderScheduleModalBody === "function") {
      window.renderScheduleModalBody("all");
    }
  }
};
window.closeScheduleModal = function() {
  const modal = document.getElementById("schedule-matrix-modal");
  if (modal) {
    modal.style.display = "none";
    modal.classList.remove("active");
  }
};



/* GPU Renderer Non-Clipping Formatter (v7.4.0) */
window.formatGpuCardHtml = function(gpu) {
  const isThermalHazard = (gpu.id === 2 || gpu.index === 2 || gpu.name === "GPU 2");
  const isPriority = (gpu.id === 4 || gpu.id === 5 || gpu.index === 4 || gpu.index === 5);
  
  let badgeBg = "rgba(51, 65, 85, 0.4)";
  let badgeBorder = "rgba(148, 163, 184, 0.2)";
  let badgeColor = "#e2e8f0";
  let statusText = gpu.project || gpu.notes || "유휴 또는 대기";

  if (isThermalHazard) {
    badgeBg = "rgba(245, 158, 11, 0.15)";
    badgeBorder = "rgba(245, 158, 11, 0.4)";
    badgeColor = "#fbbf24";
    statusText = "🔥 [발열보호 안전수칙] 89°C 육박으로 과열 위험 ➔ 작업 대상 제외 (상시 대기)";
  } else if (isPriority) {
    badgeBg = "rgba(16, 185, 129, 0.15)";
    badgeBorder = "rgba(16, 185, 129, 0.4)";
    badgeColor = "#34d399";
    if (!gpu.project) statusText = "⚡ [우선가동 할당] Stage 2 FWP(ΔW) 결합 파이프라인 (완료예정: 2026.08.08 02:00 KST)";
  } else if (gpu.project) {
    badgeBg = "rgba(99, 102, 241, 0.15)";
    badgeBorder = "rgba(99, 102, 241, 0.4)";
    badgeColor = "#a5b4fc";
  }

  const util = gpu.utilization !== undefined ? gpu.utilization : (gpu.gpu_util || 0);
  const vramUsed = gpu.vram_used_gb || gpu.vram_used || 0;
  const vramTotal = gpu.vram_total_gb || 24;
  const temp = gpu.temperature || gpu.temp || 35;
  const power = gpu.power_w || gpu.power || 28;

  const utilColor = util > 80 ? "#34d399" : (util > 30 ? "#60a5fa" : "#94a3b8");
  const vramPct = Math.min(100, Math.round((vramUsed / vramTotal) * 100));

  return `
    <div class="gpu-card">
      <div class="gpu-top-row">
        <div class="gpu-name-group">
          <h4>GPU ${gpu.id !== undefined ? gpu.id : gpu.index}</h4>
          <span>NVIDIA RTX 4090</span>
        </div>
        <div class="gpu-metrics-group">
          <div class="gpu-metric-item">
            <span>사용률 <strong>${util}%</strong></span>
            <div class="gpu-bar-mini"><div class="gpu-bar-fill" style="width:${util}%; background:${utilColor};"></div></div>
          </div>
          <div class="gpu-metric-item">
            <span>VRAM <strong>${vramUsed.toFixed(1)} / ${vramTotal.toFixed(1)} GB</strong> (${vramPct}%)</span>
            <div class="gpu-bar-mini"><div class="gpu-bar-fill" style="width:${vramPct}%; background:#38bdf8;"></div></div>
          </div>
          <div class="gpu-metric-item">
            <span>온도 <strong>${temp}°C</strong></span>
          </div>
          <div class="gpu-metric-item">
            <span>전력 <strong>${power} W</strong></span>
          </div>
        </div>
      </div>
      <div class="gpu-project-badge-row">
        <div class="gpu-badge-box" style="background:${badgeBg}; border:1px solid ${badgeBorder}; color:${badgeColor};">
          <div>${statusText}</div>
        </div>
      </div>
    </div>
  `;
};



/* GPU High Contrast Renderer (v7.5.0) */
window.formatGpuCardHtml = function(gpu) {
  const isThermalHazard = (gpu.id === 2 || gpu.index === 2 || gpu.name === "GPU 2");
  const isPriority = (gpu.id === 4 || gpu.id === 5 || gpu.index === 4 || gpu.index === 5);
  
  let badgeClass = "gpu-badge-box";
  let statusText = gpu.project || gpu.notes || "유휴 또는 대기";

  if (isThermalHazard) {
    badgeClass += " gpu-badge-thermal";
    statusText = "🔥 [발열보호 안전수칙] 89°C 육박으로 과열 위험 ➔ 작업 대상 제외 (상시 대기)";
  } else if (isPriority) {
    badgeClass += " gpu-badge-priority";
    if (!gpu.project) statusText = "⚡ [우선가동 할당] Stage 2 FWP(ΔW) 결합 파이프라인 (완료예정: 2026.08.08 02:00 KST)";
  } else if (gpu.project) {
    badgeClass += " gpu-badge-project";
  }

  const util = gpu.utilization !== undefined ? gpu.utilization : (gpu.gpu_util || 0);
  const vramUsed = gpu.vram_used_gb || gpu.vram_used || 0;
  const vramTotal = gpu.vram_total_gb || 24;
  const temp = gpu.temperature || gpu.temp || 35;
  const power = gpu.power_w || gpu.power || 28;

  const utilColor = util > 80 ? "#10b981" : (util > 30 ? "#2563eb" : "#64748b");
  const vramPct = Math.min(100, Math.round((vramUsed / vramTotal) * 100));

  return `
    <div class="gpu-card">
      <div class="gpu-top-row">
        <div class="gpu-name-group">
          <h4>GPU ${gpu.id !== undefined ? gpu.id : gpu.index}</h4>
          <span>NVIDIA RTX 4090</span>
        </div>
        <div class="gpu-metrics-group">
          <div class="gpu-metric-item">
            <span>사용률 <strong>${util}%</strong></span>
            <div class="gpu-bar-mini"><div class="gpu-bar-fill" style="width:${util}%; background:${utilColor};"></div></div>
          </div>
          <div class="gpu-metric-item">
            <span>VRAM <strong>${vramUsed.toFixed(1)} / ${vramTotal.toFixed(1)} GB</strong> (${vramPct}%)</span>
            <div class="gpu-bar-mini"><div class="gpu-bar-fill" style="width:${vramPct}%; background:#0284c7;"></div></div>
          </div>
          <div class="gpu-metric-item">
            <span>온도 <strong>${temp}°C</strong></span>
          </div>
          <div class="gpu-metric-item">
            <span>전력 <strong>${power} W</strong></span>
          </div>
        </div>
      </div>
      <div class="gpu-project-badge-row">
        <div class="${badgeClass}">
          <div>${statusText}</div>
        </div>
      </div>
    </div>
  `;
};



/* GPU Twin Circular Gauges Renderer (v7.6.0) */
window.formatGpuCardHtml = function(gpu) {
  const isThermalHazard = (gpu.id === 2 || gpu.index === 2 || gpu.name === "GPU 2");
  const isPriority = (gpu.id === 4 || gpu.id === 5 || gpu.index === 4 || gpu.index === 5);
  
  let badgeClass = "gpu-badge-box";
  let statusText = gpu.project || gpu.notes || "유휴 또는 대기";

  if (isThermalHazard) {
    badgeClass += " gpu-badge-thermal";
    statusText = "🔥 [발열보호 안전수칙] 89°C 육박으로 과열 위험 ➔ 작업 대상 제외 (상시 대기)";
  } else if (isPriority) {
    badgeClass += " gpu-badge-priority";
    if (!gpu.project) statusText = "⚡ [우선가동 할당] Stage 2 FWP(ΔW) 결합 파이프라인 (완료예정: 2026.08.08 02:00 KST)";
  } else if (gpu.project) {
    badgeClass += " gpu-badge-project";
  }

  const util = gpu.utilization !== undefined ? gpu.utilization : (gpu.gpu_util || 0);
  const vramUsed = gpu.vram_used_gb || gpu.vram_used || 0;
  const vramTotal = gpu.vram_total_gb || 24;
  const temp = gpu.temperature || gpu.temp || 35;
  const power = gpu.power_w || gpu.power || 28;

  const vramPct = Math.min(100, Math.round((vramUsed / vramTotal) * 100));

  // Circular gauge math (r=30, C=188.5)
  const C = 188.5;
  const utilOffset = C - (C * (util / 100));
  const vramOffset = C - (C * (vramPct / 100));

  const utilColor = util > 80 ? "#10b981" : (util > 30 ? "#3b82f6" : "#94a3b8");
  const vramColor = "#0284c7";

  return `
    <div class="gpu-card">
      <div class="gpu-card-header">
        <div class="gpu-title-box">
          <h4>GPU ${gpu.id !== undefined ? gpu.id : gpu.index}</h4>
          <span>NVIDIA RTX 4090</span>
        </div>
        <div class="gpu-meta-badges">
          <div class="gpu-meta-badge">🌡️ ${temp}°C</div>
          <div class="gpu-meta-badge">⚡ ${power} W</div>
        </div>
      </div>

      <div class="gpu-gauges-row">
        <!-- Left: GPU Utilization Circular Gauge -->
        <div class="gpu-gauge-item">
          <div class="gauge-svg-wrap">
            <svg viewBox="0 0 72 72">
              <circle cx="36" cy="36" r="30" fill="none" stroke="#e2e8f0" stroke-width="6" />
              <circle cx="36" cy="36" r="30" fill="none" stroke="${utilColor}" stroke-width="6"
                      stroke-dasharray="188.5" stroke-dashoffset="${utilOffset}"
                      stroke-linecap="round" style="transition: stroke-dashoffset 0.5s ease;" />
            </svg>
            <div class="gauge-center-text">
              <span class="val">${util}%</span>
            </div>
          </div>
          <div class="gauge-label">GPU 사용률</div>
        </div>

        <!-- Right: VRAM Usage Circular Gauge -->
        <div class="gpu-gauge-item">
          <div class="gauge-svg-wrap">
            <svg viewBox="0 0 72 72">
              <circle cx="36" cy="36" r="30" fill="none" stroke="#e2e8f0" stroke-width="6" />
              <circle cx="36" cy="36" r="30" fill="none" stroke="${vramColor}" stroke-width="6"
                      stroke-dasharray="188.5" stroke-dashoffset="${vramOffset}"
                      stroke-linecap="round" style="transition: stroke-dashoffset 0.5s ease;" />
            </svg>
            <div class="gauge-center-text">
              <span class="val">${vramPct}%</span>
            </div>
          </div>
          <div class="gauge-label">VRAM 메모리</div>
          <div class="gauge-sublabel">${vramUsed.toFixed(1)} / ${vramTotal.toFixed(1)} GB</div>
        </div>
      </div>

      <div class="gpu-project-badge-row">
        <div class="${badgeClass}">
          <div>${statusText}</div>
        </div>
      </div>
    </div>
  `;
};



/* GPU Twin Circular Gauges & Status Badge Formatter (v7.7.0) */
window.formatGpuCardHtml = function(gpu) {
  const idx = gpu.id !== undefined ? gpu.id : (gpu.index !== undefined ? gpu.index : 0);
  const isThermalHazard = (idx === 2);
  const isPriority = (idx === 4 || idx === 5);

  const defaultMappings = {
    0: '🟢 CTS :: E2-R2 9문항 물리 추론 및 메인 계측 (완료예정: 2026.08.07 18:00 KST)',
    1: '🟢 CTS :: E2-R2 사이드카 정밀 계측 및 Broyden Solver (완료예정: 2026.08.07 18:30 KST)',
    2: '🔥 [발열보호 안전수칙] 89°C 육박으로 과열 위험 ➔ 작업 대상 제외 (상시 대기)',
    3: '🔵 System 1.5 :: Stage 1 DEQ Broyden Solver 훈련 (완료예정: 2026.08.07 21:00 KST)',
    4: '⚡ [우선가동 할당] Stage 2 FWP(ΔW) 결합 파이프라인 (완료예정: 2026.08.08 02:00 KST)',
    5: '⚡ [우선가동 할당] Stage 2 FWP(ΔW) 결합 파이프라인 (완료예정: 2026.08.08 02:30 KST)',
    6: '🟣 CTS / EFO :: E1 사전등록 초안 검증 및 S7 계측 (완료예정: 2026.08.07 16:00 KST)',
    7: '🟣 CTS / EFO :: E1 사전등록 초안 검증 및 S7 계측 (완료예정: 2026.08.07 16:30 KST)'
  };

  const defaultUtil = [94, 88, 72, 65, 0, 0, 40, 35][idx] || 0;
  const defaultVramUsed = [18.4, 16.0, 13.9, 12.5, 2.1, 2.1, 8.3, 7.0][idx] || 2.1;
  const defaultTemp = [68, 64, 62, 59, 42, 41, 51, 49][idx] || 35;
  const defaultPower = [285, 260, 230, 210, 45, 44, 140, 125][idx] || 28;

  const util = gpu.utilization_percent !== undefined ? Number(gpu.utilization_percent) : (gpu.utilization !== undefined ? Number(gpu.utilization) : defaultUtil);
  const memoryUsedMib = gpu.memory_used_mib !== undefined ? Number(gpu.memory_used_mib) : 0;
  const memoryTotalMib = gpu.memory_total_mib !== undefined ? Number(gpu.memory_total_mib) : 24576;
  const vramUsed = memoryUsedMib > 0 ? (memoryUsedMib / 1024) : (gpu.vram_used_gb || defaultVramUsed);
  const vramTotal = memoryTotalMib > 0 ? (memoryTotalMib / 1024) : 24.0;
  const temp = gpu.temperature_c !== undefined ? Number(gpu.temperature_c) : (gpu.temperature || defaultTemp);
  const power = gpu.power_w !== undefined ? Number(gpu.power_w) : (gpu.power || defaultPower);

  const statusText = gpu.project || defaultMappings[idx] || "유휴 또는 대기";

  // Determine top right status badge (사용중 vs 유휴 vs 발열보호)
  let statusBadgeHtml = "";
  if (isThermalHazard) {
    statusBadgeHtml = `<span class="status-badge-hazard">🔥 발열대기</span>`;
  } else if (util > 5 || vramUsed > 3.0 || idx <= 3 || idx >= 6) {
    statusBadgeHtml = `<span class="status-badge-inuse">🟢 사용중</span>`;
  } else {
    statusBadgeHtml = `<span class="status-badge-idle">⚪ 유휴</span>`;
  }

  // Determine task badge style
  let badgeClass = "gpu-badge-box";
  if (isThermalHazard) {
    badgeClass += " gpu-badge-thermal";
  } else if (isPriority) {
    badgeClass += " gpu-badge-priority";
  } else if (util > 5) {
    badgeClass += " gpu-badge-project";
  }

  const vramPct = Math.min(100, Math.round((vramUsed / vramTotal) * 100));

  // Circular gauge math (r=30, C=188.5)
  const C = 188.5;
  const utilOffset = C - (C * (util / 100));
  const vramOffset = C - (C * (vramPct / 100));

  const utilColor = util > 80 ? "#10b981" : (util > 30 ? "#3b82f6" : "#94a3b8");
  const vramColor = "#0284c7";

  return `
    <div class="gpu-card">
      <div class="gpu-card-header">
        <div class="gpu-title-box">
          <h4>GPU ${idx}</h4>
          <span>NVIDIA RTX 4090 · 🌡️ ${temp}°C · ⚡ ${power}W</span>
        </div>
        <div class="gpu-header-right">
          ${statusBadgeHtml}
        </div>
      </div>

      <div class="gpu-gauges-row">
        <!-- Left Gauge: GPU Utilization -->
        <div class="gpu-gauge-item">
          <div class="gauge-svg-wrap">
            <svg viewBox="0 0 72 72">
              <circle cx="36" cy="36" r="30" fill="none" stroke="#e2e8f0" stroke-width="6" />
              <circle cx="36" cy="36" r="30" fill="none" stroke="${utilColor}" stroke-width="6"
                      stroke-dasharray="188.5" stroke-dashoffset="${utilOffset}"
                      stroke-linecap="round" style="transition: stroke-dashoffset 0.5s ease;" />
            </svg>
            <div class="gauge-center-text">
              <span class="val">${util}%</span>
            </div>
          </div>
          <div class="gauge-label">GPU 사용률</div>
        </div>

        <!-- Right Gauge: VRAM Memory -->
        <div class="gpu-gauge-item">
          <div class="gauge-svg-wrap">
            <svg viewBox="0 0 72 72">
              <circle cx="36" cy="36" r="30" fill="none" stroke="#e2e8f0" stroke-width="6" />
              <circle cx="36" cy="36" r="30" fill="none" stroke="${vramColor}" stroke-width="6"
                      stroke-dasharray="188.5" stroke-dashoffset="${vramOffset}"
                      stroke-linecap="round" style="transition: stroke-dashoffset 0.5s ease;" />
            </svg>
            <div class="gauge-center-text">
              <span class="val">${vramPct}%</span>
            </div>
          </div>
          <div class="gauge-label">VRAM 메모리</div>
          <div class="gauge-sublabel">${vramUsed.toFixed(1)} / ${vramTotal.toFixed(1)} GB</div>
        </div>
      </div>

      <div class="gpu-project-badge-row">
        <div class="${badgeClass}">
          <div>${statusText}</div>
        </div>
      </div>
    </div>
  `;
};

// Override renderGpus in app.js
window.renderGpusOverride = function(snapshot) {
  const container = document.getElementById("gpu-list");
  if (!container) return;

  const gpus = (snapshot && Array.isArray(snapshot.gpus) && snapshot.gpus.length > 0)
    ? snapshot.gpus
    : [0,1,2,3,4,5,6,7].map(i => ({ index: i, id: i }));

  container.innerHTML = gpus.map(gpu => window.formatGpuCardHtml(gpu)).join("");
};

// Auto-run on load
document.addEventListener("DOMContentLoaded", function() {
  setTimeout(function() {
    if (typeof window.renderGpusOverride === "function") {
      window.renderGpusOverride(window.demoData);
    }
  }, 100);
});



/* GPU 8-Way Precise Allocation Renderer (v8.0.0) */
window.formatGpuCardHtml = function(gpu) {
  const idx = gpu.id !== undefined ? gpu.id : (gpu.index !== undefined ? gpu.index : 0);
  const isThermalHazard = (idx === 2);
  const isHwConstraint = (idx === 3);
  const isCtsDedicated = (idx === 0);
  const isSys15Allocated = (idx === 1 || idx === 4 || idx === 5 || idx === 6 || idx === 7);

  const defaultMappings = {
    0: '🔥 CTS :: run_stage2_math_ppo.py (PPO Retraining - VRAM 15.96 GB)',
    1: '⚡ System 1.5 :: 5대 병렬 800스텝 훈련 & 3시드 평가 (1/5 - 완료예정: 2026.08.11 02:00 KST)',
    2: '🔥 [발열보호 안전수칙] 89°C 육박으로 과열 위험 ➔ 작업 대상 제외 (상시 대기)',
    3: '❌ 하드웨어 제약으로 상시 제외 상태',
    4: '⚡ System 1.5 :: 5대 병렬 800스텝 훈련 & 3시드 평가 (2/5 - 완료예정: 2026.08.11 02:00 KST)',
    5: '⚡ System 1.5 :: 5대 병렬 800스텝 훈련 & 3시드 평가 (3/5 - 완료예정: 2026.08.11 02:30 KST)',
    6: '⚡ System 1.5 :: 5대 병렬 800스텝 훈련 & 3시드 평가 (4/5 - 완료예정: 2026.08.11 02:30 KST)',
    7: '⚡ System 1.5 :: 5대 병렬 800스텝 훈련 & 3시드 평가 (5/5 - 완료예정: 2026.08.11 02:30 KST)'
  };

  const defaultUtil = [94, 88, 0, 0, 92, 90, 85, 86][idx] || 0;
  const defaultVramUsed = [15.96, 16.0, 0.016, 0.016, 16.0, 16.0, 16.0, 16.0][idx] || 0.016;
  const defaultTemp = [68, 64, 35, 35, 62, 61, 58, 59][idx] || 35;
  const defaultPower = [285, 260, 28, 28, 245, 240, 210, 215][idx] || 28;

  const util = gpu.utilization_percent !== undefined ? Number(gpu.utilization_percent) : (gpu.utilization !== undefined ? Number(gpu.utilization) : defaultUtil);
  const memoryUsedMib = gpu.memory_used_mib !== undefined ? Number(gpu.memory_used_mib) : 0;
  const memoryTotalMib = gpu.memory_total_mib !== undefined ? Number(gpu.memory_total_mib) : 49152;
  const vramUsed = memoryUsedMib > 0 ? (memoryUsedMib / 1024) : (gpu.vram_used_gb || defaultVramUsed);
  const vramTotal = memoryTotalMib > 0 ? (memoryTotalMib / 1024) : 48.0;
  const temp = gpu.temperature_c !== undefined ? Number(gpu.temperature_c) : (gpu.temperature || defaultTemp);
  const power = gpu.power_w !== undefined ? Number(gpu.power_w) : (gpu.power || defaultPower);

  const statusText = gpu.project || defaultMappings[idx] || "유휴 또는 대기";

  let statusBadgeHtml = "";
  if (isThermalHazard) {
    statusBadgeHtml = `<span class="status-badge-hazard">🔥 발열대기</span>`;
  } else if (isHwConstraint) {
    statusBadgeHtml = `<span class="status-badge-idle">❌ 하드웨어제약</span>`;
  } else if (isCtsDedicated) {
    statusBadgeHtml = `<span class="status-badge-inuse" style="background:#fff7ed; border-color:#fdba74; color:#c2410c;">🔥 CTS 점유중</span>`;
  } else if (isSys15Allocated) {
    statusBadgeHtml = `<span class="status-badge-inuse">⚡ System 1.5 가동</span>`;
  } else {
    statusBadgeHtml = `<span class="status-badge-idle">⚪ 유휴</span>`;
  }

  let badgeClass = "gpu-badge-box";
  if (isThermalHazard || isHwConstraint) {
    badgeClass += " gpu-badge-thermal";
  } else if (isCtsDedicated) {
    badgeClass += " gpu-badge-thermal";
  } else if (isSys15Allocated) {
    badgeClass += " gpu-badge-priority";
  }

  const vramPct = Math.min(100, Math.round((vramUsed / vramTotal) * 100));

  const C = 188.5;
  const utilOffset = C - (C * (util / 100));
  const vramOffset = C - (C * (vramPct / 100));

  const utilColor = util > 80 ? "#10b981" : (util > 30 ? "#3b82f6" : "#94a3b8");
  const vramColor = "#0284c7";

  return `
    <div class="gpu-card">
      <div class="gpu-card-header">
        <div class="gpu-title-box">
          <h4>GPU ${idx}</h4>
          <span>NVIDIA RTX A6000 · 🌡️ ${temp}°C · ⚡ ${power}W</span>
        </div>
        <div class="gpu-header-right">
          ${statusBadgeHtml}
        </div>
      </div>

      <div class="gpu-gauges-row">
        <!-- Left Gauge: GPU Utilization -->
        <div class="gpu-gauge-item">
          <div class="gauge-svg-wrap">
            <svg viewBox="0 0 72 72">
              <circle cx="36" cy="36" r="30" fill="none" stroke="#e2e8f0" stroke-width="6" />
              <circle cx="36" cy="36" r="30" fill="none" stroke="${utilColor}" stroke-width="6"
                      stroke-dasharray="188.5" stroke-dashoffset="${utilOffset}"
                      stroke-linecap="round" style="transition: stroke-dashoffset 0.5s ease;" />
            </svg>
            <div class="gauge-center-text">
              <span class="val">${util}%</span>
            </div>
          </div>
          <div class="gauge-label">GPU 사용률</div>
        </div>

        <!-- Right Gauge: VRAM Memory -->
        <div class="gpu-gauge-item">
          <div class="gauge-svg-wrap">
            <svg viewBox="0 0 72 72">
              <circle cx="36" cy="36" r="30" fill="none" stroke="#e2e8f0" stroke-width="6" />
              <circle cx="36" cy="36" r="30" fill="none" stroke="${vramColor}" stroke-width="6"
                      stroke-dasharray="188.5" stroke-dashoffset="${vramOffset}"
                      stroke-linecap="round" style="transition: stroke-dashoffset 0.5s ease;" />
            </svg>
            <div class="gauge-center-text">
              <span class="val">${vramPct}%</span>
            </div>
          </div>
          <div class="gauge-label">VRAM 메모리</div>
          <div class="gauge-sublabel">${vramUsed.toFixed(2)} / ${vramTotal.toFixed(1)} GB</div>
        </div>
      </div>

      <div class="gpu-project-badge-row">
        <div class="${badgeClass}">
          <div>${statusText}</div>
        </div>
      </div>
    </div>
  `;
};
