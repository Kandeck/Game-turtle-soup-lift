#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Local dev server for the pixel-art 海龟汤 (lateral-thinking) game.

Mirrors the stateless Cloudflare Pages Functions API so the SAME index.html runs
both locally (this server) and online (Cloudflare). The browser owns the game
state; this backend only generates puzzles, judges questions, and seals/unseals
the truth so it can round-trip through the client without leaking.

Endpoints (all POST, JSON):
  /api/new    {seen?}                         -> {surface, sealed}
  /api/ask    {surface, sealed, history, question} -> {type, reply, raw, truth?}
  /api/truth  {sealed}                        -> {truth}
"""
import json, os, re, hmac, hashlib, base64, secrets
import urllib.request, http.server, socketserver

API_BASE = os.environ.get("LLM_API_BASE",
                          "https://dashscope.aliyuncs.com/compatible-mode/v1")
CHAT = API_BASE.rstrip("/") + "/chat/completions"
KEY = os.environ.get("LLM_API_KEY", "")
MODEL = os.environ.get("LLM_MODEL", "qwen-plus")
SEAL_SECRET = os.environ.get("SEAL_SECRET", "insecure-default-change-me")
ROOT = os.path.dirname(os.path.abspath(__file__))
PORT = 8777

def llm(messages):
    body = json.dumps({"model": MODEL, "messages": messages}).encode()
    req = urllib.request.Request(CHAT, data=body, method="POST",
        headers={"Authorization": f"Bearer {KEY}",
                 "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=120) as r:
        data = json.load(r)
    return data["choices"][0]["message"]["content"]

def parse_json(text):
    t = (text or "").strip()
    t = re.sub(r"^```(?:json)?", "", t).strip()
    t = re.sub(r"```$", "", t).strip()
    m = re.search(r"\{.*\}", t, re.S)
    if m:
        t = m.group(0)
    return json.loads(t)

# ---- truth sealing (stdlib authenticated cipher: SHA256 keystream + HMAC) ----
# Local dev only; the Cloudflare backend uses AES-GCM. They need not interop.
def _keystream(key, nonce, n):
    out = bytearray()
    ctr = 0
    while len(out) < n:
        out += hashlib.sha256(key + nonce + ctr.to_bytes(4, "big")).digest()
        ctr += 1
    return bytes(out[:n])

def seal(plaintext):
    key = hashlib.sha256(SEAL_SECRET.encode()).digest()
    nonce = secrets.token_bytes(12)
    pt = plaintext.encode("utf-8")
    ct = bytes(a ^ b for a, b in zip(pt, _keystream(key, nonce, len(pt))))
    tag = hmac.new(key, nonce + ct, hashlib.sha256).digest()
    return base64.b64encode(nonce + tag + ct).decode()

def unseal(sealed):
    key = hashlib.sha256(SEAL_SECRET.encode()).digest()
    raw = base64.b64decode(sealed)
    nonce, tag, ct = raw[:12], raw[12:44], raw[44:]
    if not hmac.compare_digest(tag, hmac.new(key, nonce + ct, hashlib.sha256).digest()):
        raise ValueError("bad seal")
    pt = bytes(a ^ b for a, b in zip(ct, _keystream(key, nonce, len(ct))))
    return pt.decode("utf-8")

PUZZLE_SYS = """你是一个「海龟汤」（情境推理）游戏的出题人。
请生成一道逻辑严密、答案唯一、可以通过一系列是非问题推理出来的海龟汤谜题。
要求：
1. 汤面（surface）：一段看似离奇、令人困惑的场景描述，2~4句话，不泄露真相。
2. 汤底（truth）：完整的真相解释，逻辑必须自洽，能合理解释汤面里所有的反常之处，不能有漏洞。
3. 难度适中，成年人靠若干个是非问题能推出来。
只输出严格的 JSON，不要任何多余文字：
{"surface":"...","truth":"..."}"""

def judge_sys(surface, truth):
    return f"""你是「海龟汤」游戏的主持人。当前谜题：
【汤面】{surface}
【汤底】{truth}

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
只输出严格 JSON：{{"type":"answer|solved|offtopic","reply":"..."}}"""

def gen_puzzle(seen):
    avoid = ""
    if seen:
        recent = "；".join(str(s)[:40] for s in seen[-6:])
        avoid = f"\n注意：不要与最近出过的这些谜题重复或雷同：{recent}"
    raw = llm([{"role": "system", "content": PUZZLE_SYS},
               {"role": "user", "content": "出一道新的海龟汤谜题。" + avoid}])
    p = parse_json(raw)
    return p["surface"], p["truth"]

def api_new(payload):
    seen = payload.get("seen") or []
    surface, truth = gen_puzzle(seen)
    return {"surface": surface, "sealed": seal(truth)}

def api_ask(payload):
    question = (payload.get("question") or "").strip()
    surface = payload.get("surface") or ""
    sealed = payload.get("sealed") or ""
    history = payload.get("history") or []
    if not question:
        return {"error": "empty"}, 400
    if not sealed:
        return {"error": "missing sealed puzzle"}, 400
    truth = unseal(sealed)
    messages = [{"role": "system", "content": judge_sys(surface, truth)}]
    messages += history
    messages.append({"role": "user", "content": question})
    raw = llm(messages)
    try:
        res = parse_json(raw)
    except Exception:
        res = {"type": "answer", "reply": raw.strip()[:200]}
    t = res.get("type", "answer")
    out = {"type": t, "reply": res.get("reply", ""), "raw": raw}
    if t == "solved":
        out["truth"] = truth
    return out, 200

def api_truth(payload):
    sealed = payload.get("sealed") or ""
    if not sealed:
        return {"error": "missing sealed puzzle"}, 400
    return {"truth": unseal(sealed)}, 200

class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *a, **k):
        super().__init__(*a, directory=ROOT, **k)

    def log_message(self, *a):
        pass

    def _json(self, obj, code=200):
        b = json.dumps(obj, ensure_ascii=False).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(b)))
        self.end_headers()
        self.wfile.write(b)

    def do_POST(self):
        n = int(self.headers.get("Content-Length", 0))
        try:
            payload = json.loads(self.rfile.read(n) or b"{}")
        except Exception:
            payload = {}
        try:
            if self.path == "/api/new":
                self._json(api_new(payload))
            elif self.path == "/api/ask":
                obj, code = api_ask(payload)
                self._json(obj, code)
            elif self.path == "/api/truth":
                obj, code = api_truth(payload)
                self._json(obj, code)
            else:
                self._json({"error": "not found"}, 404)
        except Exception as e:
            self._json({"error": str(e)}, 500)

    def do_GET(self):
        if self.path in ("/", ""):
            self.path = "/index.html"
        return super().do_GET()

if __name__ == "__main__":
    socketserver.ThreadingTCPServer.allow_reuse_address = True
    with socketserver.ThreadingTCPServer(("127.0.0.1", PORT), Handler) as httpd:
        print(f"海龟汤游戏运行中 → http://127.0.0.1:{PORT}", flush=True)
        httpd.serve_forever()
