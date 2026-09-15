// POST /api/truth — reveal the sealed truth (for the 「看汤底」 button).
// Body: { sealed }
// Returns: { truth }
import { unseal, json } from "../_common.js";

export async function onRequestPost({ request, env }) {
  try {
    const body = await request.json();
    const sealed = body?.sealed || "";
    if (!sealed) return json({ error: "missing sealed puzzle" }, 400);
    const truth = await unseal(env, sealed);
    return json({ truth });
  } catch (e) {
    return json({ error: String(e.message || e) }, 500);
  }
}
