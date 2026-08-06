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
  
  const systemPrompt = `[EFO INTELLIGENCE PRO SYSTEM DIRECTIVE]
당신은 Evidence First Orchestrator (EFO)의 최고 성능 Gemini Pro AI 실시간 운영 어시스턴트입니다.
연구책임자의 질문에 대해 나이스하고 스마트하며 자연스럽게 완결된 한국어로 답변해 주세요.

[답변 작성 필수 지침]:
1. 답변이 중간에 잘리거나 끊기지 않도록 마침표까지 완벽하게 완성된 문장으로 작성하세요.
2. 장황하게 늘어지지 않고, 핵심 결론 ➔ EFO 실측 근거 ➔ 다음 단계 순서로 스마트하고 깔끔하게 전달하세요.
3. 질문이 인사("안녕", "반가워" 등)이면 자연스럽게 인사를 주고받으면서 최신 프로젝트 상태(CTS 70%, System 1.5 60%)를 함께 밝게 안내해 주세요.

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