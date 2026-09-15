// POST /api/ask — judge one player question against the sealed truth.
// Body: { surface, sealed, history: [{role,content}...], question }
// Returns: { type, reply, truth? }  (truth included only when solved)
// Stateless: the browser owns round/stones/size and applies the consequences.
import { judgeSys, callLLM, parseJson, unseal, json } from "../_common.js";

export async function onRequestPost({ request, env }) {
  try {
    const body = await request.json();
    const question = (body?.question || "").trim();
    const surface = body?.surface || "";
    const sealed = body?.sealed || "";
    const history = Array.isArray(body?.history) ? body.history : [];
    if (!question) return json({ error: "empty" }, 400);
    if (!sealed) return json({ error: "missing sealed puzzle" }, 400);

    const truth = await unseal(env, sealed);

    const messages = [
      { role: "system", content: judgeSys(surface, truth) },
      ...history,
      { role: "user", content: question },
    ];
    const raw = await callLLM(env, messages);

    let res;
    try {
      res = parseJson(raw);
    } catch (_) {
      res = { type: "answer", reply: raw.trim().slice(0, 200) };
    }
    const type = res.type || "answer";
    const reply = res.reply || "";

    // Return the raw assistant JSON so the client can append it to history,
    // keeping the model's conversational memory intact across turns.
    const out = { type, reply, raw };
    if (type === "solved") out.truth = truth;
    return json(out);
  } catch (e) {
    return json({ error: String(e.message || e) }, 500);
  }
}
