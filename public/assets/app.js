const API_URL = "/api/snapshot";
const DEMO_URL = "/data/demo.json";
const REFRESH_INTERVAL_MS = 15_000;
const TOKEN_KEY = "efo-view-token";
const SVG_NS = "http://www.w3.org/2000/svg";
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
  return `${number(value).toFixed(digits)} GiB`;
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
  if (["working", "running", "claimed"].includes(normalized)) return "working";
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
  elements.sourceMode.textContent = `연결 오류: ${reason}`;
}

function render(snapshot) {
  renderFreshness(snapshot);
  renderMission(snapshot);
  const derivedAlerts = buildAlerts(snapshot);
  renderKpis(snapshot, derivedAlerts);
  renderAgents(snapshot);
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
  const progress = snapshot.workspace.workflow_progress_percent;
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
      (Array.isArray(gpu.projects) && gpu.projects.length > 0),
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
  ).toFixed(1)} GiB`;
  elements.kpiDisk.textContent = formatPercent(disk.percent);
  elements.kpiDiskNote.textContent = `${number(disk.free_gib).toFixed(1)} GiB 사용 가능`;
  elements.kpiAlerts.textContent = String(alerts.length);
  elements.kpiAlertsNote.textContent =
    alerts.length === 0 ? "정상" : "확인 필요";
}

function renderAgents(snapshot) {
  const ledger = snapshot.source.ledger || {};
  elements.ledgerStatus.textContent =
    ledger.valid === true
      ? `원장 서명 유효 · ${number(ledger.event_count)} events`
      : ledger.valid === false
        ? "원장 검증 실패"
        : "원장 상태 미수집";

  if (snapshot.agents.length === 0) {
    elements.agentGrid.innerHTML =
      '<div class="empty-state">등록된 에이전트가 없습니다.</div>';
    return;
  }

  elements.agentGrid.innerHTML = snapshot.agents
    .map((agent, index) => {
      const state = normalizeAgentState(agent.state);
      const progress = clamp(agent.progress_percent);
      return `
        <article class="agent-card" style="--agent-color: ${
          AGENT_COLORS[index % AGENT_COLORS.length]
        }">
          <div class="agent-card-head">
            <div>
              <strong class="agent-name">${escapeHtml(agent.name || agent.id)}</strong>
              <span class="agent-role">${escapeHtml(agent.role || "작업자")}</span>
            </div>
            <span class="agent-state ${state}">${escapeHtml(
              stateLabel(agent.state),
            )}</span>
          </div>
          <div class="agent-current">
            <span>현재 수행</span>
            <strong>${escapeHtml(agent.current || "배정 대기")}</strong>
          </div>
          <div class="agent-progress-row">
            <div class="progress-track" role="progressbar" aria-valuemin="0"
                 aria-valuemax="100" aria-valuenow="${Math.round(progress)}">
              <span style="width:${progress}%"></span>
            </div>
            <small>${Math.round(progress)}%</small>
          </div>
          <div class="agent-next">
            <span>다음 단계</span>
            ${escapeHtml(agent.next || "오케스트레이터 지시 대기")}
          </div>
        </article>
      `;
    })
    .join("");
}

function renderGpus(snapshot) {
  elements.gpuHost.textContent = `${snapshot.source.host} · GPU ${snapshot.gpus.length}장`;
  if (snapshot.gpus.length === 0) {
    elements.gpuList.innerHTML =
      '<div class="empty-state">GPU 상태가 수집되지 않았습니다.</div>';
    return;
  }

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
                return `<span class="project-label" title="${escapeHtml(
                  `${name}${progress}${eta}`,
                )}">${escapeHtml(`${name}${progress}`)}</span>`;
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
              ).toFixed(1)} GiB</strong>
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
  const memory = snapshot.system.memory || {};
  const disk = snapshot.system.disk || {};
  elements.memoryTitle.textContent = `${formatGiB(memory.used_gib)} / ${formatGiB(
    memory.total_gib,
  )}`;
  elements.diskTitle.textContent = `${formatGiB(disk.used_gib)} / ${formatGiB(
    disk.total_gib,
  )}`;
  setRing(elements.memoryRing, elements.memoryRingLabel, memory.percent);
  setRing(elements.diskRing, elements.diskRingLabel, disk.percent);
  elements.systemLoad.textContent = number(snapshot.system.load_1m).toFixed(2);
  elements.systemUptime.textContent = formatDuration(snapshot.system.uptime_seconds);
  elements.collectionInterval.textContent = `${snapshot.collection_interval_seconds}초`;
}

function renderTasks(snapshot) {
  elements.taskCount.textContent = `${snapshot.tasks.length}개 작업`;
  if (snapshot.tasks.length === 0) {
    elements.taskTable.innerHTML =
      '<tr><td colspan="6"><div class="empty-state">현재 원장 작업이 없습니다.</div></td></tr>';
    return;
  }

  elements.taskTable.innerHTML = snapshot.tasks
    .map((task) => {
      const progress = clamp(task.progress_percent);
      const state = String(task.state || "pending").toLowerCase();
      return `
        <tr>
          <td>
            <span class="task-title">${escapeHtml(task.title || task.id)}</span>
            <span class="task-id">${escapeHtml(task.id || "-")}</span>
          </td>
          <td>${escapeHtml(task.owner || "미지정")}</td>
          <td><span class="state-label ${escapeHtml(state)}">${escapeHtml(
            stateLabel(state),
          )}</span></td>
          <td>
            <div class="table-progress">
              <div class="progress-track" role="progressbar" aria-valuemin="0"
                   aria-valuemax="100" aria-valuenow="${Math.round(progress)}">
                <span style="width:${progress}%"></span>
              </div>
              <small>${Math.round(progress)}%</small>
            </div>
          </td>
          <td>${escapeHtml(task.next || "-")}</td>
          <td>${escapeHtml(formatClock(task.updated_at))}</td>
        </tr>
      `;
    })
    .join("");
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
