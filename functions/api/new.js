// POST /api/new — generate a fresh puzzle.
// Body (optional): { seen: [recent surfaces] } to avoid repeats.
// Returns: { surface, sealed }  (truth is NOT returned in plaintext)
import { PUZZLE_SYS, callLLM, parseJson, seal, json } from "../_common.js";

export async function onRequestPost({ request, env }) {
  try {
    let seen = [];
    try {
      const body = await request.json();
      if (Array.isArray(body?.seen)) seen = body.seen;
    } catch (_) { /* empty body is fine */ }

    let avoid = "";
    if (seen.length) {
      const recent = seen.slice(-6).map((s) => String(s).slice(0, 40)).join("；");
      avoid = `\n注意：不要与最近出过的这些谜题重复或雷同：${recent}`;
    }

    const raw = await callLLM(env, [
      { role: "system", content: PUZZLE_SYS },
      { role: "user", content: "出一道新的海龟汤谜题。" + avoid },
    ]);
    const p = parseJson(raw);
    const sealed = await seal(env, p.truth);
    return json({ surface: p.surface, sealed });
  } catch (e) {
    return json({ error: String(e.message || e) }, 500);
  }
}
