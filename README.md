# 海龟汤 · 举石大冒险 🐢

一个像素风的「海龟汤」（情境推理）小游戏，在经典的是非问答玩法上加了一个**举重**环节：一只原创的小鼹鼠会替你扛石头。

## 玩法

- 读「汤面」，向主持人提**是非问题**推理真相。
- 每提问一轮（消耗一回合），鼹鼠身上就多压一块石头，表情越来越吃力。
- **10 块石头**会把鼹鼠压垮，本局结束。
- 在**5 回合以内**猜中汤底，鼹鼠体型 +1（跨局无限累计）。
- 与谜题无关的问题会被引导回正题，不消耗回合。
- 「看汤底」随时可查看正确答案；「下一题」解题后继续挑战（体型/已解保留）；「新局」彻底重来。

题目由大模型实时生成，对话上下文即记忆。

## 运行

需要 Python 3（若要重新生成素材还需 Pillow）。

1. 配置你自己的模型 key（任意 OpenAI 兼容端点即可）：

```bash
cp .env.example .env
# 编辑 .env，填入 LLM_API_KEY（以及可选的 base / model）
```

2. 加载环境变量并启动：

```bash
set -a; source .env; set +a
python3 server.py
# 打开 http://127.0.0.1:8777
```

## 配置

所有密钥和端点都通过**环境变量**提供，源码中不含任何密钥：

| 变量 | 说明 | 默认 |
|---|---|---|
| `LLM_API_KEY` | 聊天/出题模型的 API key（必填） | — |
| `LLM_API_BASE` | OpenAI 兼容端点 base URL | 阿里云 DashScope |
| `LLM_MODEL` | 模型名 | `qwen-plus` |

默认指向[阿里云 DashScope](https://help.aliyun.com/zh/model-studio/developer-reference/compatibility-of-openai-with-dashscope)，
换成 OpenAI、DeepSeek 等任意 OpenAI 兼容服务只需改这三个变量。

重新生成像素素材（可选）需额外的文生图端点，见 `.env.example` 里的 `IMAGE_API_*`。

## 目录

- `server.py` — 本地服务器：出题、判定、游戏状态、静态资源。
- `index.html` — 前端：场景渲染 + 会话框 + 石头/体型机制。
- `assets/` — 像素素材（`hero0`–`hero10` 对应 0–10 块石头的鼹鼠）。
- `gen_*.py` — 生成像素素材的脚本（一次性工具）。

## 素材说明

游戏角色是**原创的小鼹鼠形象**，所有像素素材由文生图模型生成。
