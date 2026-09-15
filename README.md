# 海龟汤 · 举石大冒险 🐢

一个像素风的「海龟汤」（情境推理）小游戏，在经典的是非问答玩法上加了一个**举重**环节：一只原创的小鼹鼠会替你扛石头。

## 玩法

- 读「汤面」，向主持人提**是非问题**推理真相。
- 每提问一轮（消耗一回合），鼹鼠身上就多压一块石头，表情越来越吃力。
- **10 块石头**会把鼹鼠压垮，本局结束。
- 在**5 回合以内**猜中汤底，鼹鼠体型 +1（跨局无限累计）。
- 与谜题无关的问题会被引导回正题，不消耗回合。
- 「看汤底」随时可查看正确答案；「下一题」解题后继续挑战（体型/已解保留）；「新局」彻底重来。

题目由大模型实时生成。**后端无状态**——游戏状态（回合、石头、体型、对话上下文）都在浏览器里，
后端只负责出题、判定、以及把 API key 藏在服务端。汤底经过加密（`sealed`）才发给前端，
浏览器里看不到明文，判定时后端解密对照，玩家无法偷看答案。

## 架构

```
index.html + assets/       ← 静态前端，持有全部游戏状态
functions/                 ← Cloudflare Pages Functions（无状态后端）
  _common.js               ← prompts / 调用大模型 / 汤底 AES-GCM 加解密
  api/new.js   POST /api/new    出题 → {surface, sealed}
  api/ask.js   POST /api/ask    判定 → {type, reply, truth?}
  api/truth.js POST /api/truth  看汤底 → {truth}
server.py                  ← 本地开发用的等价后端（纯标准库，同一套 API）
```

## 部署到 Cloudflare Pages（推荐，免费、不休眠）

1. https://dash.cloudflare.com → Workers & Pages → Create → Pages → Connect to Git，选本仓库。
2. 构建设置：Framework preset = **None**，Build command 留空，Build output directory = `/`。
3. Settings → Environment variables 配置下方 4 个变量。
4. 部署后得到 `https://xxx.pages.dev`；之后每次 `git push` 自动重新部署。

> ⚠️ Cloudflare 边缘在海外，若 `LLM_API_BASE` 用阿里云国内站可能超时。
> 可改用国际站 `https://dashscope-intl.aliyuncs.com/compatible-mode/v1`（需国际站 key），
> 或任一海外可达的 OpenAI 兼容端点——只改环境变量，无需改代码。

## 环境变量

| 变量 | 说明 | 默认 |
|---|---|---|
| `LLM_API_KEY` | 聊天/出题模型的 API key（必填） | — |
| `LLM_API_BASE` | OpenAI 兼容端点 base URL | 阿里云 DashScope |
| `LLM_MODEL` | 模型名 | `qwen-plus` |
| `SEAL_SECRET` | 汤底加密密钥，填一个长随机串 | — |

## 本地开发

**方式一：贴近线上（用 Cloudflare Functions）**

```bash
cp .dev.vars.example .dev.vars   # 填入你的 key
npx wrangler pages dev .
# 打开 http://localhost:8788
```

**方式二：纯 Python（最轻量，本机能连国内百炼）**

```bash
cp .env.example .env             # 填入你的 key
set -a; source .env; set +a
export SEAL_SECRET="任意长随机串"
python3 server.py
# 打开 http://127.0.0.1:8777
```

两种方式跑的是同一个 `index.html`。

## 目录

- `index.html` — 前端：场景渲染 + 会话框 + 石头/体型机制 + 全部游戏状态。
- `functions/` — Cloudflare Pages Functions（线上后端）。
- `server.py` — 本地开发后端（与 Functions 同一套无状态 API）。
- `assets/` — 像素素材（`hero0`–`hero10` 对应 0–10 块石头的鼹鼠）。
- `gen_*.py` — 生成像素素材的脚本（一次性工具，需额外的文生图端点）。

## 素材说明

游戏角色是**原创的小鼹鼠形象**，所有像素素材由文生图模型生成。
