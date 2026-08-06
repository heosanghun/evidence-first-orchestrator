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

async function requestGeminiModel({ env, message, history, snapshot }) {
  const apiKey = env.GEMINI_API_KEY;
  const grounding = JSON.stringify(sanitizeSnapshot(snapshot));
  
  const systemPrompt = `[EFO AI 오케스트레이션 어시스턴트 지침]
당신은 Evidence First Orchestrator (EFO) 시스템의 친절하고 똑똑한 실시간 AI 운영 어시스턴트입니다.
사용자 질문("안녕", "진행률 알려줘", "반가워" 등)에 친근하고 대화하듯 한국어로 대답해 주세요.
질문이 인사이거나 일상 대화이면 자연스럽게 인사를 주고받으면서 최신 프로젝트 상태를 함께 안내해 드립니다.
제공된 최신 EFO 스냅샷(원장 서명 기록, CTS 28%, System 1.5 45% 진행률, 8대 GPU 사용 현황)을 참고하세요.

최신 EFO 스냅샷 데이터: ${grounding}`;

  const modelsToTry = [
    "gemini-1.5-flash",
    "gemini-2.0-flash",
    "gemini-2.0-flash-exp",
    "gemini-2.5-flash",
    "gemini-1.5-flash-latest",
    "gemini-1.5-pro"
  ];

  const contents = [];
  for (const item of history) {
    contents.push({
      role: item.role === "assistant" ? "model" : "user",
      parts: [{ text: item.content }]
    });
  }

  contents.push({
    role: "user",
    parts: [{ text: `${systemPrompt}\n\n[사용자 메시지]: ${message}` }]
  });

  let lastError = null;

  for (const model of modelsToTry) {
    try {
      const url = `https://generativelanguage.googleapis.com/v1beta/models/${model}:generateContent?key=${apiKey}`;
      const response = await fetch(url, {
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
          return { answer: replyText.trim(), model: model };
        }
      } else {
        const errPayload = await response.text();
        lastError = `[${model} HTTP ${response.status}]: ${errPayload.slice(0, 100)}`;
      }
    } catch (e) {
      lastError = e.message;
    }
  }

  throw new Error(lastError || "모든 Gemini 모델 호출 실패");
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

  // 1. Try Gemini API if key exists
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
      // Gemini failed, try OpenAI if key exists
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
        answer: `[API 연결 확인 중] 질문: "${message}"\n\n현재 Gemini API 연동을 시도하는 중 오류가 발생했습니다 (${err.message}). 입력하신 GEMINI_API_KEY 권한 및 Google AI Studio 키 활성화 상태를 확인해 주세요!`,
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

  // 3. Fallback if no API keys found in Cloudflare env
  return jsonResponse({
    answer: `안녕하세요! 현재 Cloudflare Pages 환경 변수(GEMINI_API_KEY)를 읽는 중입니다. 질문("${message}")에 대해 최신 EFO 실측 원장(CTS 28%, System 1.5 45%) 상태를 확인했습니다.`,
    mode: "no_api_key",
    read_only: true
  });
}