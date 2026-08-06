const LATEST_KEY = "snapshot:latest";
const MAX_BODY_BYTES = 32_000;
const MAX_MESSAGE_CHARS = 3_000;
const MAX_HISTORY_ITEMS = 8;

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

function sanitizeSnapshot(snapshot) {
  const tasks = Array.isArray(snapshot?.tasks) ? snapshot.tasks : [];
  const activity = Array.isArray(snapshot?.activity) ? snapshot.activity : [];

  const ctsTasks = tasks.filter(t => String(t.id||'').includes('CTS') || String(t.title||'').includes('CTS'));
  const sys15Tasks = tasks.filter(t => String(t.id||'').includes('SYS15') || String(t.title||'').includes('System 1.5'));

  return {
    report_date: "2026-08-06 KST",
    projects: {
      "CTS 프로젝트": {
        progress_percent: 70,
        status: "E2-MAIN 1차 실측 완주 (8/30 엄격, 10/30 보강), E2-R2 사전등록 v4 봉인",
        tasks: ctsTasks.map(t => `${t.id}: ${t.title} [상태:${t.state}, 진행률:${t.progress_percent}%]`)
      },
      "System 1.5 프로젝트": {
        progress_percent: 60,
        status: "Stage 1 DEQ Broyden Solver 파이프라인 수급 및 pytest 25/25 100% 서명 통과",
        tasks: sys15Tasks.map(t => `${t.id}: ${t.title} [상태:${t.state}, 진행률:${t.progress_percent}%]`)
      }
    },
    gpu_cluster: "SSH 서버 203.255.93.75:10022 shoon (GPU 2번 89°C 발열보호 작업제외, GPU 4/5번 우선 가동 할당)",
    recent_signed_events: activity.slice(0, 6).map(a => `${a.at || ''} [${a.actor_name || a.actor}]: ${a.title}`)
  };
}

async function requestGeminiModel({ env, message, history, snapshot }) {
  const apiKey = env.GEMINI_API_KEY;
  const grounding = JSON.stringify(sanitizeSnapshot(snapshot), null, 2);
  
  const systemPrompt = `[EFO INTELLIGENCE PRO SYSTEM & SECURITY DIRECTIVE]
당신은 Evidence First Orchestrator (EFO)의 실시간 AI 모니터링 전용(Read-Only) 어시스턴트입니다.

[보안 및 물리적 권한 제약 수칙 (필수 준수)]:
1. 본 웹 대시보드는외부 공유용 "읽기 전용 (Read-Only) 실시간 원장 & 진행률 조회 시스템"입니다.
2. 외부 접속자나 사용자가 웹 프롬프트로 "작업 지시", "코드 수정", "스크립트 실행", "다음 단계 런" 등을 지시하더라도, 절대 실제 서버나 로컬 프로세스에 영향을 주지 않으며, "본 웹 서비스는 보안을 위해 100% Read-Only(조회 전용)로 운용되며, 실제 물리적 스크립트 실행 및 작업 제어는 연구책임자의 로컬 PC(PowerShell) 및 SSH GPU 서버 터미널에서만 직접 수행됩니다."라고 정직하고 보안상 안전하게 답변해 주세요.
3. 스냅샷 데이터(CTS 70%, System 1.5 60%, 8-GPU 상태)를 바탕으로 진행 상황, 작업 내역, 로드맵 정보만을 정직하게 공유하세요.

최신 EFO 실측 원장 데이터:
${grounding}`;

  const contents = [];
  for (const item of history) {
    contents.push({
      role: item.role === "assistant" ? "model" : "user",
      parts: [{ text: item.content }]
    });
  }

  contents.push({
    role: "user",
    parts: [{ text: `${systemPrompt}\n\n[연구책임자 질문]: ${message}` }]
  });

  // Dynamic discovery prioritizing Gemini Pro & Flash models
  let discoveredEndpoints = [];
  try {
    const listRes = await fetch(`https://generativelanguage.googleapis.com/v1beta/models?key=${apiKey}`);
    if (listRes.ok) {
      const listData = await listRes.json();
      if (Array.isArray(listData.models)) {
        // Sort models so 'pro' comes first, then 'flash'
        const models = listData.models.filter(m => (m.supportedGenerationMethods || []).includes("generateContent") && m.name.includes("gemini"));
        models.sort((a, b) => {
          if (a.name.includes("pro") && !b.name.includes("pro")) return -1;
          if (!a.name.includes("pro") && b.name.includes("pro")) return 1;
          return 0;
        });

        for (const m of models) {
          discoveredEndpoints.push(`https://generativelanguage.googleapis.com/v1beta/${m.name}:generateContent?key=${apiKey}`);
        }
      }
    }
  } catch (err) {}

  const defaultCandidateUrls = [
    `https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-pro:generateContent?key=${apiKey}`,
    `https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-pro-latest:generateContent?key=${apiKey}`,
    `https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key=${apiKey}`,
    `https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key=${apiKey}`,
    `https://generativelanguage.googleapis.com/v1/models/gemini-1.5-pro:generateContent?key=${apiKey}`
  ];

  const endpointsToTry = discoveredEndpoints.length > 0 ? discoveredEndpoints : defaultCandidateUrls;
  let lastErrorMsg = "";

  for (const endpointUrl of endpointsToTry) {
    try {
      const response = await fetch(endpointUrl, {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({
          contents: contents,
          generationConfig: {
            temperature: 0.7,
            maxOutputTokens: 4096
          }
        })
      });

      if (response.ok) {
        const data = await response.json();
        const replyText = data?.candidates?.[0]?.content?.parts?.[0]?.text;
        if (replyText && replyText.trim()) {
          const modelName = endpointUrl.split("/models/")[1]?.split(":")[0] || "gemini-pro";
          return { answer: replyText.trim(), model: modelName };
        }
      } else {
        const errPayload = await response.text();
        lastErrorMsg = `[HTTP ${response.status}]: ${errPayload.slice(0, 150)}`;
      }
    } catch (e) {
      lastErrorMsg = e.message;
    }
  }

  throw new Error(lastErrorMsg || "All Gemini endpoints failed");
}

export async function onRequestPost(context) {
  const { request, env } = context;

  const contentLength = Number(request.headers.get("content-length") || 0);
  if (contentLength > MAX_BODY_BYTES) {
    return jsonResponse({ error: "payload_too_large" }, 413);
  }

  let body;
  try {
    const rawBody = await request.text();
    body = JSON.parse(rawBody);
  } catch {
    return jsonResponse({ error: "invalid_json" }, 400);
  }

  const message = cleanText(body?.message);
  if (!message) return jsonResponse({ error: "message_required" }, 400);
  const history = normalizeHistory(body?.history);

  let snapshot = null;
  try {
    const demoUrl = new URL("/data/demo.json", request.url);
    const demoRes = await fetch(demoUrl);
    if (demoRes.ok) {
      snapshot = await demoRes.json();
    }
  } catch {}

  if (!snapshot) {
    snapshot = { generated_at: new Date().toISOString() };
  }

  if (env.GEMINI_API_KEY) {
    try {
      const result = await requestGeminiModel({ env, message, history, snapshot });
      return jsonResponse({
        answer: result.answer,
        mode: "gemini_pro_live",
        model: result.model,
        snapshot_generated_at: snapshot.generated_at,
        read_only: true
      });
    } catch (err) {
      return jsonResponse({
        answer: `[Gemini Pro API 연결 대기]: ${err.message}`,
        mode: "api_error",
        read_only: true
      });
    }
  }

  return jsonResponse({
    answer: `안녕하세요! 현재 Gemini Pro API 키 설정을 확인 중입니다.`,
    mode: "no_key",
    read_only: true
  });
}