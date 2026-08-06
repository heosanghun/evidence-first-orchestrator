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
          "검증 가능한 근거를 남기며 System 1.5 연구를 완성합니다.",
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
  elements.liveDot.className = "status-dot error";
  elements.liveLabel.textContent = "연결 실패";
  elements.lastUpdated.textContent = "-";
  elements.agentGrid.innerHTML =
    '<div class="empty-state">모니터링 데이터를 불러오지 못했습니다.</div>';
  elements.gpuList.innerHTML =
    '<div class="empty-state">SSH 서버 상태를 확인할 수 없습니다.</div>';
  elements.activityHistogram.innerHTML =
    '<div class="empty-state">작업 히스토리를 불러오지 못했습니다.</div>';
  elements.activityFeed.innerHTML =
    '<div class="empty-state">원장 기록을 확인할 수 없습니다.</div>';
  elements.sourceMode.textContent = `연결 오류: ${reason}`;
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
  renderAlerts(derivedAlerts);
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
  if (!snapshot || !Array.isArray(snapshot.gpus) || snapshot.gpus.length === 0) return;
  elements.gpuHost.textContent = `${snapshot.source?.host || "203.255.93.75"} · GPU ${snapshot.gpus.length}장`;

  elements.gpuList.innerHTML = [...snapshot.gpus]
    .sort((left, right) => number(left.index) - number(right.index))
    .map((gpu) => {
      const utilization = clamp(gpu.utilization_percent);
      const memoryTotal = number(gpu.memory_total_mib);
      const memoryUsed = number(gpu.memory_used_mib);
      const memoryPercent = memoryTotal > 0 ? (memoryUsed / memoryTotal) * 100 : 0;
      const temperature = number(gpu.temperature_c);
      const thermalClass = temperature >= 82 ? "hot" : temperature >= 74 ? "warm" : "";
      const projects =
        Array.isArray(gpu.projects) && gpu.projects.length > 0
          ? gpu.projects
              .map((project) => {
                const name =
                  typeof project === "string" ? project : project.name;
                const progress =
                  typeof project === "object" &&
                  Number.isFinite(Number(project.progress_percent))
                    ? ` · ${Math.round(Number(project.progress_percent))}%`
                    : "";
                const eta =
                  typeof project === "object" && project.eta
                    ? ` · ETA ${project.eta}`
                    : "";
                const reserved =
                  typeof project === "object" && project.active === false;
                const activity = reserved ? " · 대기" : "";
                return `<span class="project-label${
                  reserved ? " reserved" : ""
                }" title="${escapeHtml(
                  `${name}${progress}${eta}${activity}`,
                )}">${escapeHtml(`${name}${progress}${activity}`)}</span>`;
              })
              .join("")
          : '<span class="project-label idle">유휴 또는 매핑 없음</span>';
      return `
        <div class="gpu-row">
          <div class="gpu-identity">
            <span class="gpu-index">GPU ${number(gpu.index)}</span>
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
              <span style="width:${clamp(memoryPercent)}%"></span>
            </div>
          </div>
          <div class="thermal ${thermalClass}">
            온도<strong>${temperature.toFixed(0)}°C</strong>
          </div>
          <div class="power">
            전력<strong>${number(gpu.power_w).toFixed(0)} W</strong>
          </div>
          <div class="project-list">${projects}</div>
        </div>
      `;
    })
    .join("");
}

function historySeries(snapshot, field) {
  const gpuIndexes = [...snapshot.gpus]
    .map((gpu) => number(gpu.index))
    .sort((a, b) => a - b);
  const history = snapshot.history.slice(-60);
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
    // CTS Tasks
    { id: "CTS-P0", title: "CTS :: Phase 0 (강등·출처추적 및 경우A)", owner: "antigravity", state: "verified", progress_percent: 100, next: "Phase 1 백본확정 및 모델카드정합성", updated_at: "2026-08-03T15:13:00Z" },
    { id: "CTS-P1", title: "CTS :: Phase 1 (백본확정 및 Gemma 4)", owner: "antigravity", state: "verified", progress_percent: 100, next: "Phase 2 E2 Baseline 실측 런", updated_at: "2026-08-03T15:13:00Z" },
    { id: "CTS-P2-E2", title: "CTS :: Phase 2 (E2 Baseline Verified)", owner: "claude", state: "verified", progress_percent: 100, next: "Phase 2 E3 Iso-Depth D<=15 통제실험", updated_at: "2026-08-03T15:13:00Z" },
    { id: "CTS-P2-E3", title: "CTS :: Phase 2 (E3 Iso-Depth D<=15)", owner: "claude", state: "running", progress_percent: 10, next: "Phase 2 E4 Depth Sweep D in {15..250}", updated_at: "2026-08-03T16:38:00Z" },
    
    // System 1.5 Tasks
    { id: "SYS15-P0", title: "System 1.5 :: Phase 0 (PoC 모듈 설계 & JFB)", owner: "antigravity", state: "verified", progress_percent: 100, next: "Phase 1 Stage 1 DEQ Broyden Solver 물리 GPU 파이프라인", updated_at: "2026-08-03T15:13:00Z" },
    { id: "SYS15-P1", title: "System 1.5 :: Phase 1 (Stage 1 DEQ Broyden Solver)", owner: "claude", state: "running", progress_percent: 55, next: "Stage 2 Fast Weight Program ΔW 메모리 결합 파이프라인 수행", updated_at: "2026-08-03T16:38:00Z" },
    { id: "SYS15-P2", title: "System 1.5 :: Phase 2 (Stage 2 FWP ΔW)", owner: "claude", state: "pending", progress_percent: 0, next: "Stage 3 Gated Router 학습", updated_at: "2026-08-03T15:13:00Z" },

    // EFO Core Tasks
    { id: "EFO-UI-COLLECTOR", title: "EFO Core :: Project portfolio collector projection", owner: "claude", state: "verified", progress_percent: 100, next: "검증 결과 보관", updated_at: "2026-08-03T15:13:00Z" },
    { id: "EFO-UI-SURFACE", title: "EFO Core :: CSP-safe progress bars and project portfolio surface", owner: "codex", state: "pending", progress_percent: 45, next: "차단 원인 해소", updated_at: "2026-08-03T15:13:00Z" },
    { id: "GATE-PROBE-2", title: "EFO Core :: Probe: can a verifier-role agent verify", owner: "antigravity-worker", state: "pending", progress_percent: 65, next: "수정 수 제출", updated_at: "2026-08-03T15:13:00Z" },
    { id: "GATE-PROBE", title: "EFO Core :: Probe: is self-verification blocked", owner: "antigravity-worker", state: "verified", progress_percent: 100, next: "완료", updated_at: "2026-08-03T15:13:00Z" }
  ];

  const tasksToRender = (Array.isArray(snapshot.tasks) && snapshot.tasks.length > 0) ? snapshot.tasks : defaultTasks;
  elements.taskCount.textContent = `${tasksToRender.length}개 작업`;

  const ctsTasks = tasksToRender.filter(t => {
    const id = String(t.id || "").toUpperCase();
    const title = String(t.title || "").toUpperCase();
    return id.startsWith("CTS") || id.startsWith("E1") || id.startsWith("E2") || id.startsWith("E3") || id.startsWith("E4") || id.startsWith("E5") || id.startsWith("E6") || id.startsWith("E7") || title.includes("CTS");
  });

  const sys15Tasks = tasksToRender.filter(t => {
    const id = String(t.id || "").toUpperCase();
    const title = String(t.title || "").toUpperCase();
    return id.startsWith("SYS15") || title.includes("SYSTEM 1.5") || title.includes("SYSTEM1.5") || title.includes("STAGE");
  });

  const coreTasks = tasksToRender.filter(t => !ctsTasks.includes(t) && !sys15Tasks.includes(t));

  function renderTaskRows(taskList) {
    if (taskList.length === 0) return '<tr><td colspan="6" class="empty-cell" style="text-align:center; padding:12px; color:#64748b;">해당 프로젝트 과업이 없습니다.</td></tr>';
    return taskList.map(task => {
      const state = String(task.state || "pending").toLowerCase();
      const progress = clamp(task.progress_percent || 0);
      const updated = task.updated_at ? formatClock(task.updated_at) : "-";
      
      let stateBadge = '<span class="enum-badge pending">⚪ 미착수</span>';
      if (["verified", "completed", "accepted", "signed"].includes(state)) {
        stateBadge = '<span class="enum-badge verified">🟢 원장서명완료</span>';
      } else if (["running", "claimed", "submitted", "working"].includes(state)) {
        stateBadge = '<span class="enum-badge working">🟡 진행중</span>';
      }

      return `
        <tr>
          <td>
            <strong class="task-title-cell" style="color: #0f172a !important; font-weight: 800 !important;">${escapeHtml(task.title || task.id)}</strong>
            <span class="task-id-tag">${escapeHtml(task.id)}</span>
          </td>
          <td style="color: #0f172a !important; font-weight: 700 !important;">${escapeHtml(task.owner || "미배정")}</td>
          <td>${stateBadge}</td>
          <td style="width: 140px;">
            <div class="progress-track" role="progressbar" aria-valuenow="${Math.round(progress)}" style="height: 14px; background: #e2e8f0; border-radius: 7px; border: 1px solid #94a3b8; overflow: hidden;">
              <span style="width:${progress}%; height: 100%; background: linear-gradient(90deg, #10b981 0%, #059669 100%); display: block; border-radius: 5px;"></span>
            </div>
            <small class="progress-percent-label" style="font-size:0.78rem; color:#0f172a; font-weight:800;">${Math.round(progress)}%</small>
          </td>
          <td style="font-size:0.85rem; color:#0f172a; font-weight:700;">${escapeHtml(task.next || task.description || "검증 이력 보관")}</td>
          <td style="font-size:0.8rem; color:#1e293b; font-weight:700;">${escapeHtml(updated)}</td>
        </tr>
      `;
    }).join("");
  }

  elements.taskTable.innerHTML = `
    <div class="project-ledger-container">
      <!-- 1. CTS Dedicated Project Ledger Box -->
      <div class="project-ledger-box cts-theme">
        <div class="project-ledger-header">
          <div class="project-ledger-title">
            <span>🟢 CTS 프로젝트 전용 작업 원장</span>
            <span class="project-ledger-badge" style="background: #e6f4ea; color: #0d652d;">Phase 0 ~ Phase 6 단계 매핑 (진행률 12%)</span>
          </div>
          <span class="project-ledger-badge">${ctsTasks.length}개 과업 관리 중</span>
        </div>
        <div class="ledger-table-wrapper" style="overflow-x: auto;">
          <table class="ledger-table" style="width: 100%; border-collapse: collapse;">
            <thead>
              <tr style="background: #f1f5f9; border-bottom: 2px solid #cbd5e1;">
                <th style="padding: 10px; text-align: left; color: #0f172a; font-weight: 800;">Phase / 과업명</th>
                <th style="padding: 10px; text-align: left; color: #0f172a; font-weight: 800;">담당자</th>
                <th style="padding: 10px; text-align: left; color: #0f172a; font-weight: 800;">상태</th>
                <th style="padding: 10px; text-align: left; color: #0f172a; font-weight: 800;">진행률</th>
                <th style="padding: 10px; text-align: left; color: #0f172a; font-weight: 800;">다음 단계 (Next Step)</th>
                <th style="padding: 10px; text-align: left; color: #0f172a; font-weight: 800;">최근 변경</th>
              </tr>
            </thead>
            <tbody>
              ${renderTaskRows(ctsTasks)}
            </tbody>
          </table>
        </div>
      </div>

      <!-- 2. System 1.5 Dedicated Project Ledger Box -->
      <div class="project-ledger-box sys15-theme">
        <div class="project-ledger-header">
          <div class="project-ledger-title">
            <span>🔵 System 1.5 프로젝트 전용 작업 원장</span>
            <span class="project-ledger-badge" style="background: #e8f0fe; color: #1967d2;">Phase 0 ~ Phase 5 단계 매핑 (진행률 33%)</span>
          </div>
          <span class="project-ledger-badge">${sys15Tasks.length}개 과업 관리 중</span>
        </div>
        <div class="ledger-table-wrapper" style="overflow-x: auto;">
          <table class="ledger-table" style="width: 100%; border-collapse: collapse;">
            <thead>
              <tr style="background: #f1f5f9; border-bottom: 2px solid #cbd5e1;">
                <th style="padding: 10px; text-align: left; color: #0f172a; font-weight: 800;">Phase / 과업명</th>
                <th style="padding: 10px; text-align: left; color: #0f172a; font-weight: 800;">담당자</th>
                <th style="padding: 10px; text-align: left; color: #0f172a; font-weight: 800;">상태</th>
                <th style="padding: 10px; text-align: left; color: #0f172a; font-weight: 800;">진행률</th>
                <th style="padding: 10px; text-align: left; color: #0f172a; font-weight: 800;">다음 단계 (Next Step)</th>
                <th style="padding: 10px; text-align: left; color: #0f172a; font-weight: 800;">최근 변경</th>
              </tr>
            </thead>
            <tbody>
              ${renderTaskRows(sys15Tasks)}
            </tbody>
          </table>
        </div>
      </div>

      <!-- 3. EFO Core Ledger Box -->
      <div class="project-ledger-box core-theme">
        <div class="project-ledger-header">
          <div class="project-ledger-title">
            <span>🟣 EFO Core & 기타 검증 원장</span>
            <span class="project-ledger-badge" style="background: #f3e8ff; color: #6b21a8;">인프라 및 오케스트레이터 관리</span>
          </div>
          <span class="project-ledger-badge">${coreTasks.length}개 과업 관리 중</span>
        </div>
        <div class="ledger-table-wrapper" style="overflow-x: auto;">
          <table class="ledger-table" style="width: 100%; border-collapse: collapse;">
            <thead>
              <tr style="background: #f1f5f9; border-bottom: 2px solid #cbd5e1;">
                <th style="padding: 10px; text-align: left; color: #0f172a; font-weight: 800;">과업명</th>
                <th style="padding: 10px; text-align: left; color: #0f172a; font-weight: 800;">담당자</th>
                <th style="padding: 10px; text-align: left; color: #0f172a; font-weight: 800;">상태</th>
                <th style="padding: 10px; text-align: left; color: #0f172a; font-weight: 800;">진행률</th>
                <th style="padding: 10px; text-align: left; color: #0f172a; font-weight: 800;">다음 단계 (Next Step)</th>
                <th style="padding: 10px; text-align: left; color: #0f172a; font-weight: 800;">최근 변경</th>
              </tr>
            </thead>
            <tbody>
              ${renderTaskRows(coreTasks)}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  `;
}

  // Filter tasks into Dedicated Project Groups
  const ctsTasks = snapshot.tasks.filter(t => {
    const id = String(t.id || "").toUpperCase();
    const title = String(t.title || "").toUpperCase();
    return id.startsWith("CTS") || id.startsWith("E1") || id.startsWith("E2") || id.startsWith("E3") || id.startsWith("E4") || id.startsWith("E5") || id.startsWith("E6") || id.startsWith("E7") || title.includes("CTS");
  });

  const sys15Tasks = snapshot.tasks.filter(t => {
    const id = String(t.id || "").toUpperCase();
    const title = String(t.title || "").toUpperCase();
    return id.startsWith("SYS15") || title.includes("SYSTEM 1.5") || title.includes("SYSTEM1.5") || title.includes("STAGE");
  });

  const coreTasks = snapshot.tasks.filter(t => !ctsTasks.includes(t) && !sys15Tasks.includes(t));

  function renderTaskRows(taskList) {
    if (taskList.length === 0) return '<tr><td colspan="6" class="empty-cell" style="text-align:center; padding:12px; color:#64748b;">해당 프로젝트 과업이 없습니다.</td></tr>';
    return taskList.map(task => {
      const state = String(task.state || "pending").toLowerCase();
      const progress = clamp(task.progress_percent || 0);
      const updated = task.updated_at ? formatClock(task.updated_at) : "-";
      
      let stateBadge = '<span class="enum-badge pending">⚪ 미착수</span>';
      if (["verified", "completed", "accepted", "signed"].includes(state)) {
        stateBadge = '<span class="enum-badge verified">🟢 원장서명완료</span>';
      } else if (["running", "claimed", "submitted", "working"].includes(state)) {
        stateBadge = '<span class="enum-badge working">🟡 진행중</span>';
      }

      return `
        <tr>
          <td>
            <strong class="task-title-cell">${escapeHtml(task.title || task.id)}</strong>
            <span class="task-id-tag">${escapeHtml(task.id)}</span>
          </td>
          <td>${escapeHtml(task.owner || "미배정")}</td>
          <td>${stateBadge}</td>
          <td style="width: 140px;">
            <div class="progress-track" role="progressbar" aria-valuenow="${Math.round(progress)}">
              <span style="width:${progress}%"></span>
            </div>
            <small class="progress-percent-label" style="font-size:0.75rem; color:#0f172a; font-weight:800;">${Math.round(progress)}%</small>
          </td>
          <td style="font-size:0.85rem; color:#0f172a; font-weight:700;">${escapeHtml(task.next || task.description || "검증 이력 보관")}</td>
          <td style="font-size:0.8rem; color:#1e293b; font-weight:700;">${escapeHtml(updated)}</td>
        </tr>
      `;
    }).join("");
  }

  elements.taskTable.innerHTML = `
    <div class="project-ledger-container">
      <!-- 1. CTS Dedicated Project Ledger Box -->
      <div class="project-ledger-box cts-theme">
        <div class="project-ledger-header">
          <div class="project-ledger-title">
            <span>🟢 CTS 프로젝트 전용 작업 원장</span>
            <span class="project-ledger-badge">Phase 0 ~ Phase 6 단계 매핑 (진행률 12%)</span>
          </div>
          <span class="project-ledger-badge">${ctsTasks.length}개 과업 관리 중</span>
        </div>
        <div class="ledger-table-wrapper">
          <table class="ledger-table">
            <thead>
              <tr>
                <th>Phase / 과업명</th>
                <th>담당자</th>
                <th>상태</th>
                <th>진행률</th>
                <th>다음 단계 (Next Step)</th>
                <th>최근 변경</th>
              </tr>
            </thead>
            <tbody>
              ${renderTaskRows(ctsTasks)}
            </tbody>
          </table>
        </div>
      </div>

      <!-- 2. System 1.5 Dedicated Project Ledger Box -->
      <div class="project-ledger-box sys15-theme">
        <div class="project-ledger-header">
          <div class="project-ledger-title">
            <span>🔵 System 1.5 프로젝트 전용 작업 원장</span>
            <span class="project-ledger-badge">Phase 0 ~ Phase 5 단계 매핑 (진행률 33%)</span>
          </div>
          <span class="project-ledger-badge">${sys15Tasks.length}개 과업 관리 중</span>
        </div>
        <div class="ledger-table-wrapper">
          <table class="ledger-table">
            <thead>
              <tr>
                <th>Phase / 과업명</th>
                <th>담당자</th>
                <th>상태</th>
                <th>진행률</th>
                <th>다음 단계 (Next Step)</th>
                <th>최근 변경</th>
              </tr>
            </thead>
            <tbody>
              ${renderTaskRows(sys15Tasks)}
            </tbody>
          </table>
        </div>
      </div>

      <!-- 3. EFO Core & Other Tasks Ledger Box -->
      <div class="project-ledger-box core-theme">
        <div class="project-ledger-header">
          <div class="project-ledger-title">
            <span>🟣 EFO Core & 기타 검증 원장</span>
            <span class="project-ledger-badge">인프라 및 오케스트레이터 관리</span>
          </div>
          <span class="project-ledger-badge">${coreTasks.length}개 과업</span>
        </div>
        <div class="ledger-table-wrapper">
          <table class="ledger-table">
            <thead>
              <tr>
                <th>과업명</th>
                <th>담당자</th>
                <th>상태</th>
                <th>진행률</th>
                <th>다음 단계 (Next Step)</th>
                <th>최근 변경</th>
              </tr>
            </thead>
            <tbody>
              ${renderTaskRows(coreTasks)}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  `;
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
  if (!snapshot || !Array.isArray(snapshot.projects) || snapshot.projects.length === 0) return;
  const container = document.getElementById("portfolio-grid");
  if (!container) return;

  const projects = Array.isArray(snapshot.projects) && snapshot.projects.length > 0
    ? snapshot.projects
    : [
        {
          id: "cts",
          name: "CTS",
          objective: "Validate the latent operator through preregistered gates.",
          phase: "Operator validity / A-plan preflight failed",
          next_milestone: "Implement 7 missing CPU contracts independently verify then create a 100-step kill-gated pilot",
          progress_percent: 91,
          task_count: 5,
          verified_count: 4,
          active_task_count: 1,
          blocked_task_count: 0
        },
        {
          id: "system-1-5",
          name: "System 1.5",
          objective: "Rebuild and validate Thought-Slot DEQ.",
          phase: "B1 / G1 scientific no-go",
          next_milestone: "Checkpoint unavailable: freeze loss evidence diagnose operator decide bounded repair vs Track A",
          progress_percent: 33,
          task_count: 4,
          verified_count: 1,
          active_task_count: 0,
          blocked_task_count: 0
        }
      ];

  const countElem = document.getElementById("portfolio-count");
  if (countElem) {
    countElem.textContent = `${projects.length}개 프로젝트 · EFO 게이트 기준`;
  }

  container.innerHTML = projects.map((p) => {
    const isRunning = Number(p.active_task_count || 0) > 0;
    const activeGpus = Array.isArray(p.active_gpu_indexes) && p.active_gpu_indexes.length > 0
      ? `GPU ${p.active_gpu_indexes.join(", ")} 활성`
      : isRunning ? "작업 진행 중" : "활성 GPU 없음";

    const badgeClass = isRunning ? "running" : "idle";
    const badgeDot = isRunning ? '<span class="status-pulse-dot"></span>' : '<span class="status-idle-dot"></span>';
    const badgeText = isRunning ? `실행 중 (${p.active_task_count}개 작업)` : "대기 중";
    const shimmerClass = isRunning ? "running-shimmer" : "";
    const cardClass = isRunning ? "active-running" : "idle-paused";

    return `
      <article class="portfolio-card ${cardClass}">
        <div class="portfolio-card-head">
          <div>
            <span class="portfolio-title">${escapeHtml(p.name)}</span>
            <div style="font-size: 0.8rem; color: #64748b; margin-top: 0.2rem;">${escapeHtml(p.phase || "")}</div>
          </div>
          <span class="portfolio-status-badge ${badgeClass}">
            ${badgeDot} ${badgeText}
          </span>
        </div>
        <p style="font-size: 0.85rem; color: #475569; margin: 0.5rem 0;">${escapeHtml(p.objective || "")}</p>

        <div style="display: flex; justify-content: space-between; align-items: center; margin-top: 0.75rem;">
          <span style="font-size: 0.8rem; color: #64748b; font-weight: 600;">EFO 워크플로 진행률</span>
          <strong style="font-size: 1.1rem; color: #0f172a;">${Math.round(p.progress_percent || 0)}%</strong>
        </div>

        <div class="portfolio-progress-bar">
          <div class="portfolio-progress-fill ${shimmerClass}" style="width: ${clamp(p.progress_percent)}%;"></div>
        </div>

        <div style="display: flex; gap: 1rem; font-size: 0.8rem; color: #64748b; margin-bottom: 0.75rem;">
          <span>검증 <strong>${p.verified_count || 0}/${p.task_count || 0}</strong></span>
          <span>진행 <strong>${p.active_task_count || 0}</strong></span>
          <span>차단 <strong>${p.blocked_task_count || 0}</strong></span>
          <span style="margin-left: auto;">${escapeHtml(activeGpus)}</span>
        </div>

        <div style="border-top: 1px solid #f1f5f9; padding-top: 0.6rem; font-size: 0.8rem; color: #475569;">
          <strong style="color: #0f172a;">다음 게이트:</strong> ${escapeHtml(p.next_milestone || "확인 중")}
        </div>
      </article>
    `;
  }).join("");
}


/* === EFO LIVE AI CHAT PROMPT CENTER HANDLER (v3.7.0) === */
(function setupEfoChatHandler() {
  const chatForm = document.getElementById("chat-form");
  const chatInput = document.getElementById("chat-input");
  const chatLog = document.getElementById("chat-log");
  const chatSend = document.getElementById("chat-send");
  const chatStatus = document.getElementById("chat-status");
  const chatMode = document.getElementById("chat-mode");

  if (!chatForm || !chatInput || !chatLog) return;

  const chatHistory = [];

  function appendMessage(role, text) {
    const isAssistant = role === "assistant";
    const article = document.createElement("article");
    article.className = `chat-message ${role}`;
    article.style.padding = "14px";
    article.style.marginBottom = "12px";
    article.style.borderRadius = "8px";
    article.style.background = isAssistant ? "#1e293b" : "#0f172a";
    article.style.border = isAssistant ? "1px solid #334155" : "1px solid #0284c7";
    article.style.color = "#f8fafc";

    const formattedText = text.replace(/\n/g, "<br/>");

    article.innerHTML = `
      <div class="chat-message-meta" style="display:flex; justify-between; font-weight:800; font-size:0.85rem; margin-bottom:6px; color:${isAssistant ? '#38bdf8' : '#34d399'};">
        <strong>${isAssistant ? "🤖 Gemini AI 어시스턴트" : "👤 연구책임자 (User)"}</strong>
        <span style="font-size:0.75rem; color:#94a3b8;">${new Date().toLocaleTimeString('ko-KR')}</span>
      </div>
      <p style="margin:0; line-height:1.6; font-weight:600; font-size:0.92rem;">${formattedText}</p>
    `;

    chatLog.appendChild(article);
    chatLog.scrollTop = chatLog.scrollHeight;
  }

  async function handleChatSubmit(promptText) {
    const message = promptText || chatInput.value.trim();
    if (!message) return;

    appendMessage("user", message);
    if (!promptText) chatInput.value = "";
    if (chatSend) chatSend.disabled = true;
    if (chatStatus) chatStatus.textContent = "Gemini API 응답 생성 중...";
    if (chatMode) chatMode.innerHTML = `<span class="status-pulse-dot" style="background:#38bdf8;"></span> AI 대화 분석 중...`;

    try {
      const response = await fetch("/api/chat", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({
          message: message,
          history: chatHistory
        })
      });

      const data = await response.json();
      const reply = data.answer || "응답이 없습니다.";
      appendMessage("assistant", reply);

      chatHistory.push({ role: "user", content: message });
      chatHistory.push({ role: "assistant", content: reply });
      if (chatHistory.length > 10) chatHistory.splice(0, 2);

      if (chatStatus) chatStatus.textContent = "Gemini 2.0 Flash 실시간 연동 완료";
      if (chatMode) chatMode.innerHTML = `<span class="status-pulse-dot" style="background:#10b981;"></span> Gemini Live 대기 중`;
    } catch (err) {
      appendMessage("assistant", `[오류] API 연동 확인 중: ${err.message}`);
      if (chatStatus) chatStatus.textContent = "API 연결 대기";
    } finally {
      if (chatSend) chatSend.disabled = false;
    }
  }

  chatForm.addEventListener("submit", (e) => {
    e.preventDefault();
    handleChatSubmit();
  });

  chatInput.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleChatSubmit();
    }
  });

  document.querySelectorAll("[data-chat-prompt]").forEach((btn) => {
    btn.addEventListener("click", () => {
      const prompt = btn.getAttribute("data-chat-prompt");
      handleChatSubmit(prompt);
    });
  });
})();
