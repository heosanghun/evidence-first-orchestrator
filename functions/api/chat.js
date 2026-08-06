const LATEST_KEY = "snapshot:latest";
const MAX_BODY_BYTES = 32_000;
const MAX_MESSAGE_CHARS = 2_000;
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
    activity: (snapshot?.activity || []).slice(0, 10),
    system: snapshot?.system
  };
}

// Dynamic Model Discovery & Execution
async function requestGeminiModel({ env, message, history, snapshot }) {
  const apiKey = env.GEMINI_API_KEY;
  const grounding = JSON.stringify(sanitizeSnapshot(snapshot));
  
  const systemPrompt = `[EFO AI 오케스트레이션 어시스턴트]
당신은 Evidence First Orchestrator (EFO) 연구 및 운영 AI 어시스턴트입니다.
사용자의 질문("안녕", "어제 작업내역은?", "진행률 알려줘" 등)에 대해 친근하고 자연스럽게 한국어로 대화해 주세요.
스냅샷 데이터(원장 서명 기록, CTS 28%, System 1.5 45% 진행률, 8대 GPU 사용 현황)를 근거로 정직하고 상용 서비스 어시스턴트처럼 대답해 주세요.

최신 EFO 실측 스냅샷: ${grounding}`;

  const contents = [];
  for (const item of history) {
    contents.push({
      role: item.role === "assistant" ? "model" : "user",
      parts: [{ text: item.content }]
    });
  }

  contents.push({
    role: "user",
    parts: [{ text: `${systemPrompt}\n\n[사용자 질문]: ${message}` }]
  });

  // Step 1: Query API Key's exact supported models dynamically
  let discoveredEndpoints = [];
  try {
    const listRes = await fetch(`https://generativelanguage.googleapis.com/v1beta/models?key=${apiKey}`);
    if (listRes.ok) {
      const listData = await listRes.json();
      if (Array.isArray(listData.models)) {
        for (const m of listData.models) {
          const name = m.name; // e.g. "models/gemini-1.5-flash"
          const methods = m.supportedGenerationMethods || [];
          if (methods.includes("generateContent") && name.includes("gemini")) {
            discoveredEndpoints.push(`https://generativelanguage.googleapis.com/v1beta/${name}:generateContent?key=${apiKey}`);
          }
        }
      }
    }
  } catch (err) {
    // List models fallback
  }

  // Fallback candidate URLs if dynamic discovery returned nothing
  const defaultCandidateUrls = [
    `https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key=${apiKey}`,
    `https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash-latest:generateContent?key=${apiKey}`,
    `https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash-002:generateContent?key=${apiKey}`,
    `https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash-001:generateContent?key=${apiKey}`,
    `https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash-exp:generateContent?key=${apiKey}`,
    `https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key=${apiKey}`,
    `https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-pro-latest:generateContent?key=${apiKey}`,
    `https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-pro-002:generateContent`,
    `https://generativelanguage.googleapis.com/v1/models/gemini-1.5-flash:generateContent?key=${apiKey}`,
    `https://generativelanguage.googleapis.com/v1/models/gemini-1.5-pro:generateContent?key=${apiKey}`,
    `https://generativelanguage.googleapis.com/v1/models/gemini-pro:generateContent?key=${apiKey}`
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
            maxOutputTokens: 1000
          }
        })
      });

      if (response.ok) {
        const data = await response.json();
        const replyText = data?.candidates?.[0]?.content?.parts?.[0]?.text;
        if (replyText && replyText.trim()) {
          const modelName = endpointUrl.split("/models/")[1]?.split(":")[0] || "gemini";
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

async function requestOpenAIModel({ env, message, history, snapshot }) {
  const apiKey = env.OPENAI_API_KEY;
  const grounding = JSON.stringify(sanitizeSnapshot(snapshot));
  const systemPrompt = `당신은 EFO AI 어시스턴트입니다. 한국어로 자연스럽게 대화하세요. 최신 EFO 스냅샷: ${grounding}`;

  const messages = [
    { role: "system", content: systemPrompt },
    ...history.map(h => ({ role: h.role, content: h.content })),
    { role: "user", content: message }
  ];

  const response = await fetch("https://api.openai.com/v1/chat/completions", {
    method: "POST",
    headers: {
      "authorization": `Bearer ${apiKey}`,
      "content-type": "application/json"
    },
    body: JSON.stringify({
      model: "gpt-4o-mini",
      messages: messages,
      max_tokens: 1000
    })
  });

  if (!response.ok) {
    throw new Error(`OpenAI HTTP ${response.status}`);
  }

  const data = await response.json();
  const reply = data?.choices?.[0]?.message?.content;
  return { answer: reply || "OpenAI 응답 생성 실패", model: "gpt-4o-mini" };
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

  // 1. Try Gemini API with Dynamic Model Discovery
  if (env.GEMINI_API_KEY) {
    try {
      const result = await requestGeminiModel({ env, message, history, snapshot });
      return jsonResponse({
        answer: result.answer,
        mode: "gemini_live",
        model: result.model,
        snapshot_generated_at: snapshot.generated_at,
        read_only: true
      });
    } catch (err) {
      if (env.OPENAI_API_KEY) {
        try {
          const oaResult = await requestOpenAIModel({ env, message, history, snapshot });
          return jsonResponse({
            answer: oaResult.answer,
            mode: "openai_live",
            model: oaResult.model,
            snapshot_generated_at: snapshot.generated_at,
            read_only: true
          });
        } catch {}
      }
      return jsonResponse({
        answer: `[API 연동 확인]: ${err.message}`,
        mode: "api_error_detail",
        error_detail: err.message,
        read_only: true
      });
    }
  }

  // 2. Try OpenAI API if key exists
  if (env.OPENAI_API_KEY) {
    try {
      const oaResult = await requestOpenAIModel({ env, message, history, snapshot });
      return jsonResponse({
        answer: oaResult.answer,
        mode: "openai_live",
        model: oaResult.model,
        snapshot_generated_at: snapshot.generated_at,
        read_only: true
      });
    } catch (err) {
      return jsonResponse({
        answer: `[OpenAI API 오류]: ${err.message}`,
        mode: "openai_error",
        read_only: true
      });
    }
  }

  return jsonResponse({
    answer: `안녕하세요! 현재 Cloudflare Pages 환경 변수(GEMINI_API_KEY)를 확인 중입니다. 질문("${message}")에 대해 최신 EFO 실측 원장(CTS 28%, System 1.5 45%) 상태입니다.`,
    mode: "no_api_key",
    read_only: true
  });
}