#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Local server for the pixel-art 海龟汤 (lateral-thinking) weightlifting game.
Keeps the API key server-side, holds the LLM conversation as puzzle memory,
and owns the authoritative game state (rounds / stones / size)."""
import json, os, re, urllib.request, http.server, socketserver, threading

CHAT = "http://ai-service.tal.com/openai-compatible/v1/chat/completions"
KEY = os.environ.get("TAL_IMAGE_API_KEY", "")  # set via env, never commit the real key
MODEL = "gpt-5.5"
ROOT = os.path.dirname(os.path.abspath(__file__))
PORT = 8777
MAX_ROUND = 10
GROW_WITHIN = 5

def llm(messages, temperature=None):
    payload = {"model": MODEL, "messages": messages}
    if temperature is not None:
        payload["temperature"] = temperature
    body = json.dumps(payload).encode()
    req = urllib.request.Request(CHAT, data=body, method="POST",
        headers={"api-key": KEY, "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=120) as r:
        data = json.load(r)
    return data["choices"][0]["message"]["content"]

def parse_json(text):
    t = text.strip()
    t = re.sub(r"^```(?:json)?", "", t).strip()
    t = re.sub(r"```$", "", t).strip()
    m = re.search(r"\{.*\}", t, re.S)
    if m:
        t = m.group(0)
    return json.loads(t)

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

class Game:
    def __init__(self):
        self.lock = threading.Lock()
        self.pcache_lock = threading.Lock()
        self.next_cache = None       # (surface, truth) pre-generated in background
        self.pregen_busy = False
        self.seen = []               # recent surfaces, to avoid repeats
        self.reset()

    def reset(self):
        self.size = 0
        self.solved_count = 0
        self.new_puzzle()

    def _gen_puzzle(self):
        avoid = ""
        if self.seen:
            recent = "；".join(s[:40] for s in self.seen[-6:])
            avoid = f"\n注意：不要与最近出过的这些谜题重复或雷同：{recent}"
        raw = llm([{"role": "system", "content": PUZZLE_SYS},
                   {"role": "user", "content": "出一道新的海龟汤谜题。" + avoid}])
        p = parse_json(raw)
        return p["surface"], p["truth"]

    def _start_pregen(self):
        with self.pcache_lock:
            if self.pregen_busy or self.next_cache is not None:
                return
            self.pregen_busy = True
        def work():
            try:
                s, t = self._gen_puzzle()
                with self.pcache_lock:
                    self.next_cache = (s, t)
            except Exception:
                pass
            finally:
                with self.pcache_lock:
                    self.pregen_busy = False
        threading.Thread(target=work, daemon=True).start()

    def new_puzzle(self):
        self.round = 0
        self.stones = 0
        self.status = "playing"
        with self.pcache_lock:
            cached = self.next_cache
            self.next_cache = None
        if cached:
            self.surface, self.truth = cached
        else:
            self.surface, self.truth = self._gen_puzzle()
        self.seen.append(self.surface)
        # conversation memory for this puzzle
        self.history = [{"role": "system",
                         "content": judge_sys(self.surface, self.truth)}]
        # prepare the following puzzle in the background so solving stays instant
        self._start_pregen()

    def state(self):
        return {"round": self.round, "maxRound": MAX_ROUND,
                "stones": self.stones, "size": self.size,
                "solvedCount": self.solved_count, "status": self.status,
                "surface": self.surface}

    def advance(self):
        # move to the next puzzle WITHOUT resetting size / solved count
        with self.lock:
            self.new_puzzle()
            return self.state()

    def ask(self, question):
        with self.lock:
            if self.status != "playing":
                return {"type": "over", "reply": "本局已结束，请开始新游戏。",
                        "state": self.state()}
            self.history.append({"role": "user", "content": question})
            raw = llm(self.history)
            try:
                res = parse_json(raw)
            except Exception:
                res = {"type": "answer", "reply": raw.strip()[:200]}
            self.history.append({"role": "assistant", "content": raw})
            t = res.get("type", "answer")
            reply = res.get("reply", "")
            grew = False
            if t == "solved":
                if self.round <= GROW_WITHIN:
                    self.size += 1
                    grew = True
                self.solved_count += 1
                out = {"type": "solved", "reply": reply, "grew": grew,
                       "solvedRound": self.round, "truth": self.truth}
                # do NOT advance automatically — wait for the player to press
                # 「下一题」. Just mark solved and pre-generate the next puzzle.
                self.status = "solved"
                self._start_pregen()
                out["state"] = self.state()
                return out
            elif t == "offtopic":
                return {"type": "offtopic", "reply": reply, "state": self.state()}
            else:  # answer -> costs a round + a stone
                self.round += 1
                self.stones += 1
                if self.round >= MAX_ROUND:
                    self.status = "crushed"
                    reveal = f"{reply}\n\n💀 石头太多，角色被压倒了！汤底揭晓：{self.truth}"
                    return {"type": "crushed", "reply": reveal,
                            "state": self.state()}
                return {"type": "answer", "reply": reply, "state": self.state()}

GAME = Game()

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
        payload = json.loads(self.rfile.read(n) or b"{}")
        try:
            if self.path == "/api/new":
                GAME.reset()
                self._json({"reply": "新游戏开始！", "state": GAME.state()})
            elif self.path == "/api/next":
                self._json({"reply": "下一题！", "state": GAME.advance()})
            elif self.path == "/api/ask":
                q = (payload.get("question") or "").strip()
                if not q:
                    self._json({"error": "empty"}, 400); return
                self._json(GAME.ask(q))
            elif self.path == "/api/truth":
                self._json({"truth": GAME.truth})
            else:
                self._json({"error": "not found"}, 404)
        except Exception as e:
            self._json({"error": str(e)}, 500)

    def do_GET(self):
        if self.path == "/" or self.path == "":
            self.path = "/index.html"
        return super().do_GET()

if __name__ == "__main__":
    socketserver.ThreadingTCPServer.allow_reuse_address = True
    with socketserver.ThreadingTCPServer(("127.0.0.1", PORT), Handler) as httpd:
        print(f"海龟汤游戏运行中 → http://127.0.0.1:{PORT}", flush=True)
        httpd.serve_forever()
