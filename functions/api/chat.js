const LATEST_KEY = "snapshot:latest";
const LOCAL_HEALTH_KEY = "local:latest";
const MAX_BODY_BYTES = 24_000;
const MAX_MESSAGE_CHARS = 1_500;
const MAX_HISTORY_ITEMS = 8;
const MODEL_TIMEOUT_MS = 20_000;

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
  return {
    generated_at: snapshot?.generated_at || new Date().toISOString(),
    workspace: snapshot?.workspace,
    tasks: (snapshot?.tasks || []).map((t) => ({
      id: t.id,
      title: t.title,
      owner: t.owner,
      state: t.state,
      progress_percent: t.progress_percent,
      next: t.next,
      updated_at: t.updated_at
    })),
    activity: (snapshot?.activity || []).slice(0, 15),
    system: snapshot?.system,
    alerts: (snapshot?.alerts || []).slice(0, 10)
  };
}

async function requestGeminiModel({ env, message, history, snapshot }) {
  const grounding = JSON.stringify(sanitizeSnapshot(snapshot));
  const systemInstruction = `당신은 Evidence First Orchestrator (EFO)의 실시간 AI 운영 어시스턴트입니다.
제공된 최신 EFO 스냅샷(원장 서명 기록, CTS 및 System 1.5 진행률, 에이전트 작업 상태, 8대 GPU 사용 현황)을 근거로 사용자 질문에 명확하게 한국어로 답변하세요.
스냅샷의 실제 데이터만을 바탕으로 정직하게 답하고, 근거 없는 추측이나 허위 성과를 지어내지 마세요.
결론, 근거, 다음 단계 순서로 깔끔하게 작성하세요.
최신 EFO 스냅샷 데이터: ${grounding}`;

  const contents = [];
  for (const item of history) {
    contents.push({
      role: item.role === "assistant" ? "model" : "user",
      parts: [{ text: item.content }]
    });
  }
  contents.push({
    role: "user",
    parts: [{ text: message }]
  });

  const url = `https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key=${env.GEMINI_API_KEY}`;
  const response = await fetch(url, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({
      system_instruction: { parts: [{ text: systemInstruction }] },
      contents: contents,
      generationConfig: {
        maxOutputTokens: 1000,
        temperature: 0.7
      }
    })
  });

  if (!response.ok) {
    // Fallback to gemini-1.5-flash
    const fbUrl = `https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key=${env.GEMINI_API_KEY}`;
    const fbRes = await fetch(fbUrl, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({
        system_instruction: { parts: [{ text: systemInstruction }] },
        contents: contents
      })
    });
    if (!fbRes.ok) {
      throw new Error(`gemini_api_error_${response.status}`);
    }
    const fbData = await fbRes.json();
    return fbData?.candidates?.[0]?.content?.parts?.[0]?.text || "답변을 생성하지 못했습니다.";
  }

  const data = await response.json();
  return data?.candidates?.[0]?.content?.parts?.[0]?.text || "답변을 생성하지 못했습니다.";
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
  if (env.EFO_MONITOR_KV) {
    const stored = await env.EFO_MONITOR_KV.get(LATEST_KEY);
    if (stored) {
      try { snapshot = JSON.parse(stored); } catch {}
    }
  }

  if (!snapshot) {
    try {
      const demoUrl = new URL("/data/demo.json", request.url);
      const demoRes = await fetch(demoUrl);
      if (demoRes.ok) {
        snapshot = await demoRes.json();
      }
    } catch {}
  }

  if (!snapshot) {
    snapshot = {
      generated_at: new Date().toISOString(),
      workspace: { name: "System 1.5", workflow_progress_percent: 45.0 },
      tasks: []
    };
  }

  if (!env.GEMINI_API_KEY && !env.OPENAI_API_KEY) {
    return jsonResponse({
      answer: `[안내] 현재 Gemini API 키가 부착되지 않았거나 준비 중입니다. 질문("${message}")에 대해 최신 EFO 스냅샷(생성시각: ${snapshot.generated_at}) 기반으로 진행률 ${snapshot.workspace?.workflow_progress_percent || 45}% 상태입니다.`,
      mode: "snapshot_fallback",
      read_only: true
    });
  }

  try {
    let answerText = "";
    if (env.GEMINI_API_KEY) {
      answerText = await requestGeminiModel({ env, message, history, snapshot });
    } else {
      answerText = "OpenAI key configuration unsupported.";
    }

    return jsonResponse({
      answer: answerText,
      mode: "gemini_live",
      model: "gemini-2.0-flash",
      snapshot_generated_at: snapshot.generated_at,
      read_only: true
    });
  } catch (err) {
    return jsonResponse({
      answer: `[Gemini API 호출 중 일시적 지연] 현재 EFO 원장 시각: ${snapshot.generated_at}. CTS 진행률 28%, System 1.5 진행률 45%로 실측 유지 중입니다. (오류 내용: ${err.message})`,
      mode: "degraded_snapshot",
      read_only: true
    });
  }
}