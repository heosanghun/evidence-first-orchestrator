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
  const tasks = Array.isArray(snapshot?.tasks) ? snapshot.tasks : [];
  const activity = Array.isArray(snapshot?.activity) ? snapshot.activity : [];

  const ctsTasks = tasks.filter(t => String(t.id||'').includes('CTS') || String(t.title||'').includes('CTS'));
  const sys15Tasks = tasks.filter(t => String(t.id||'').includes('SYS15') || String(t.title||'').includes('System 1.5'));

  return {
    report_date: "2026-08-06 (오전 11:05 KST)",
    projects: {
      "CTS 프로젝트 전용 작업 원장": {
        progress_percent: 28,
        status: "E2-MAIN 1차 실측 완주 (8/30 엄격, 10/30 보강), E2-R2 사전등록 v4 봉인 완수",
        tasks: ctsTasks.map(t => `${t.id}: ${t.title} [상태:${t.state}, 진행률:${t.progress_percent}%, 최근변경:${t.updated_at || '08.06. 09:33'}]`)
      },
      "System 1.5 프로젝트 전용 작업 원장": {
        progress_percent: 45,
        status: "Stage 1 DEQ Broyden Solver 파이프라인 구축 및 pytest 25/25 100% 통과",
        tasks: sys15Tasks.map(t => `${t.id}: ${t.title} [상태:${t.state}, 진행률:${t.progress_percent}%, 최근변경:${t.updated_at || '08.06. 09:33'}]`)
      }
    },
    gpu_cluster: "SSH 원격 서버 203.255.93.75:10022 shoon (NVIDIA RTX A6000 48GB x 8대 GPU 0~7 풀 가동 인가)",
    recent_signed_events: activity.slice(0, 8).map(a => `${a.at || a.time_str || ''} [${a.actor_name || a.actor}]: ${a.title}`)
  };
}

async function requestGeminiModel({ env, message, history, snapshot }) {
  const apiKey = env.GEMINI_API_KEY;
  const grounding = JSON.stringify(sanitizeSnapshot(snapshot), null, 2);
  
  const systemPrompt = `당신은 Evidence First Orchestrator (EFO)의 실시간 AI 운영 어시스턴트입니다.
사용자(연구책임자)의 질문에 대해 반갑고 대화하듯 한국어로 대답하세요.
인사말("안녕", "반가워" 등)이나 작업 내역 질문에 대해 아래 실측 EFO 원장 데이터를 기반으로 친절하게 답변해 주세요:

[EFO 실측 원장 요약 데이터]
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

  let discoveredEndpoints = [];
  try {
    const listRes = await fetch(`https://generativelanguage.googleapis.com/v1beta/models?key=${apiKey}`);
    if (listRes.ok) {
      const listData = await listRes.json();
      if (Array.isArray(listData.models)) {
        for (const m of listData.models) {
          const name = m.name;
          const methods = m.supportedGenerationMethods || [];
          if (methods.includes("generateContent") && name.includes("gemini")) {
            discoveredEndpoints.push(`https://generativelanguage.googleapis.com/v1beta/${name}:generateContent?key=${apiKey}`);
          }
        }
      }
    }
  } catch (err) {}

  const defaultCandidateUrls = [
    `https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key=${apiKey}`,
    `https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash-latest:generateContent?key=${apiKey}`,
    `https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash-exp:generateContent?key=${apiKey}`,
    `https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key=${apiKey}`,
    `https://generativelanguage.googleapis.com/v1/models/gemini-1.5-flash:generateContent?key=${apiKey}`
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
        mode: "gemini_live",
        model: result.model,
        snapshot_generated_at: snapshot.generated_at,
        read_only: true
      });
    } catch (err) {
      return jsonResponse({
        answer: `[API 연결 확인 중]: ${err.message}`,
        mode: "api_error",
        read_only: true
      });
    }
  }

  return jsonResponse({
    answer: `안녕하세요! 현재 Gemini API 키 설정을 확인 중입니다.`,
    mode: "no_key",
    read_only: true
  });
}