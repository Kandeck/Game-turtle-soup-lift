// Shared helpers for the 海龟汤 (lateral-thinking) game's Cloudflare Pages Functions.
// Underscore-prefixed filename => not routed; imported by the api/* routes.
// The backend is stateless: game state lives in the browser; the truth is
// sealed (AES-GCM) so it can round-trip through the client without leaking.

export const MAX_ROUND = 10;
export const GROW_WITHIN = 5;

export const PUZZLE_SYS = `你是一个「海龟汤」（情境推理）游戏的出题人。
请生成一道逻辑严密、答案唯一、可以通过一系列是非问题推理出来的海龟汤谜题。
要求：
1. 汤面（surface）：一段看似离奇、令人困惑的场景描述，2~4句话，不泄露真相。
2. 汤底（truth）：完整的真相解释，逻辑必须自洽，能合理解释汤面里所有的反常之处，不能有漏洞。
3. 难度适中，成年人靠若干个是非问题能推出来。
只输出严格的 JSON，不要任何多余文字：
{"surface":"...","truth":"..."}`;

export function judgeSys(surface, truth) {
  return `你是「海龟汤」游戏的主持人。当前谜题：
【汤面】${surface}
【汤底】${truth}

玩家会针对这道谜题提问。你必须严格对照【汤底】来判断每一个问题，规则如下：
- 只要是能用是非判断、且与本谜题相关的问题（包括「你说的是某人物吗」这类身份确认）：type 记为 "answer"。判断方法：
  · 如果这个问题描述的情况**符合汤底**（汤底里确实是这样、或能由汤底推出为真）→ 回答「是」。
  · 如果这个问题描述的情况**与汤底矛盾**（汤底里并非如此）→ 回答「不是」。
  · 如果问题在汤底里既有对也有不对的成分 → 回答「是也不是」。
  · 如果汤底里没有涉及、对推理真相无关紧要 → 回答「不重要」。
  注意：不需要玩家完整说出汤底才回答「是」，只要单个问题贴合汤底就答「是」。回答只能是这四种之一加极简语气词，绝对不能透露汤底细节或给提示。
- 玩家已经说出/猜中了汤底的核心真相（意思对即可，不需逐字一致，覆盖到关键反转点即可）：type 记为 "solved"，reply 里揭晓完整汤底并简短祝贺。
- 玩家问与本谜题无关的问题、闲聊、或试图让你直接给答案/提示：type 记为 "offtopic"，reply 用一句话礼貌地把玩家引导回这道题，不要给任何提示。
严禁给玩家任何提示或线索。
只输出严格 JSON：{"type":"answer|solved|offtopic","reply":"..."}`;
}

// Strip code fences and pull out the first {...} block, then JSON.parse.
export function parseJson(text) {
  let t = (text || "").trim();
  t = t.replace(/^```(?:json)?/i, "").trim();
  t = t.replace(/```$/i, "").trim();
  const m = t.match(/\{[\s\S]*\}/);
  if (m) t = m[0];
  return JSON.parse(t);
}

// Call an OpenAI-compatible chat endpoint. All config comes from env.
export async function callLLM(env, messages) {
  const base = (env.LLM_API_BASE ||
    "https://dashscope.aliyuncs.com/compatible-mode/v1").replace(/\/$/, "");
  const resp = await fetch(base + "/chat/completions", {
    method: "POST",
    headers: {
      "Authorization": `Bearer ${env.LLM_API_KEY || ""}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      model: env.LLM_MODEL || "qwen-plus",
      messages,
    }),
  });
  if (!resp.ok) {
    const detail = await resp.text().catch(() => "");
    throw new Error(`LLM ${resp.status}: ${detail.slice(0, 300)}`);
  }
  const data = await resp.json();
  return data.choices[0].message.content;
}

// ---- truth sealing (AES-GCM, key = SHA-256(SEAL_SECRET)) ----

async function aesKey(env) {
  const secret = env.SEAL_SECRET || "insecure-default-change-me";
  const raw = await crypto.subtle.digest("SHA-256",
    new TextEncoder().encode(secret));
  return crypto.subtle.importKey("raw", raw, { name: "AES-GCM" },
    false, ["encrypt", "decrypt"]);
}

function b64encode(bytes) {
  let s = "";
  for (const b of bytes) s += String.fromCharCode(b);
  return btoa(s);
}
function b64decode(str) {
  const bin = atob(str);
  const out = new Uint8Array(bin.length);
  for (let i = 0; i < bin.length; i++) out[i] = bin.charCodeAt(i);
  return out;
}

export async function seal(env, plaintext) {
  const key = await aesKey(env);
  const iv = crypto.getRandomValues(new Uint8Array(12));
  const ct = new Uint8Array(await crypto.subtle.encrypt(
    { name: "AES-GCM", iv }, key, new TextEncoder().encode(plaintext)));
  const packed = new Uint8Array(iv.length + ct.length);
  packed.set(iv, 0);
  packed.set(ct, iv.length);
  return b64encode(packed);
}

export async function unseal(env, sealed) {
  const key = await aesKey(env);
  const packed = b64decode(sealed);
  const iv = packed.slice(0, 12);
  const ct = packed.slice(12);
  const pt = await crypto.subtle.decrypt({ name: "AES-GCM", iv }, key, ct);
  return new TextDecoder().decode(pt);
}

export function json(obj, status = 200) {
  return new Response(JSON.stringify(obj), {
    status,
    headers: { "Content-Type": "application/json; charset=utf-8" },
  });
}
