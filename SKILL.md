---
name: choice-assistant
description: 别纠结决策辅助 - 当用户需要做选择、需要多角度分析、或希望把纠结整理成结构化决策简报时使用
---

# 别纠结决策辅助 (choice-assistant)

> 辅助人做选择，不替代人做决定。

版本：**0.8.0**（前后端分离架构 · 桌面端布局）

本 Skill 通过独立 FastAPI 后端 + 完整前端 UI + CLI 脚本为 AI Agent 与终端用户提供决策辅助能力。当 Agent 检测到用户面临选择困难、需要多角度分析、或希望把纠结整理成结构化决策简报（.brief）时调用本 Skill。

## 何时使用

- 用户提出"我该选 A 还是 B"、"纠结要不要……"等选择类问题
- 用户希望对一件事做多角度分析（理性 / 直觉 / 风水 等）
- 用户要求把模糊的纠结整理成一份结构化决策简报
- 用户希望查看历史决策记录（archive）或统计（stats）

## 参数

| 参数 | 必填 | 说明 |
| --- | --- | --- |
| `--question` / `-q` | 是（`chat` 动作） | 决策问题文本 |
| `--mode` / `-m` | 否 | 决策模式：`auto` / `rational` / `random` / `nature` / `dialogue` / `fengshui`，默认 `auto` |
| `--action` / `-a` | 否 | 执行动作：`chat` / `archive` / `stats` / `decision` / `config-api`，默认 `chat` |
| `--base-url` | 否 | 后端 API 地址，默认 `http://localhost:8000` |
| `--api-key` | 否 | LLM API Key（用户自配，OpenAI 兼容） |
| `--llm-model` | 否 | LLM 模型名，如 `gpt-4o-mini` |
| `--llm-base-url` | 否 | LLM base url（OpenAI 兼容，如 `https://api.openai.com/v1` 或完整 `.../chat/completions`） |
| `--weather-key` | 否 | 高德开放平台 Key（nature 模式用，10 万次/日免费，申请路径 https://lbs.amap.com/dev/key/app） |
| `--weather-appsecret` | 否 | （已弃用，兼容旧版）等价于 `--weather-key` |
| `--weather-city` | 否 | 天气查询城市（默认北京） |
| `--save-config` | 否 | 把本次 CLI 提供的配置持久化到 `~/.choice/config.json` |
| `--id` | 是（`decision` 动作） | 决策记录 id（用于查看或删除单条记录） |
| `--delete` | 否 | `decision` 动作删除单条记录；`config-api` 动作清除 SQLite 中所有 API Key |
| `--list` | 否 | `config-api` 动作查看脱敏配置（默认行为，显式传亦可） |
| `--save-to-db` | 否 | `config-api` 动作把 CLI 提供的配置保存到 SQLite（需配合 `--api-key` 等参数） |

## 调用样例

```bash
# 1. 用自动模式分析一个问题（未配置 API Key 时返回 mock 简报）
python scripts/choice_assistant.py --question "该不该跳槽去新公司" --mode auto

# 2. 用理性模式做决策（短参数形式）
python scripts/choice_assistant.py -q "买电车还是油车" -m rational

# 3. 查看历史决策与统计
python scripts/choice_assistant.py --action archive
python scripts/choice_assistant.py --action stats

# 4. 临时用某个 LLM Key 调用一次（不落盘）
python scripts/choice_assistant.py -q "今晚吃什么" -m auto \
  --api-key sk-xxx --llm-model gpt-4o-mini --llm-base-url https://api.openai.com/v1

# 5. 一次性配置并保存到 ~/.choice/config.json
python scripts/choice_assistant.py -q "测试" --save-config \
  --api-key sk-xxx --llm-model gpt-4o-mini --llm-base-url https://api.openai.com/v1

# 6. 用 config 子命令持久化配置（之后所有调用自动读取）
python scripts/choice_assistant.py config --api-key sk-xxx \
  --llm-model gpt-4o-mini --llm-base-url https://api.openai.com/v1 --save

# 7. 查看当前生效配置
python scripts/choice_assistant.py config

# 8. nature 模式（带天气，需配置天气 Key 才返回真实天气）
python scripts/choice_assistant.py -q "要不要换城市" -m nature \
  --weather-appid xxx --weather-appsecret yyy --weather-city 北京

# 9. 查看单条决策记录（id 来自 chat 返回的 decisionId 或 archive 列表）
python scripts/choice_assistant.py --action decision --id 20260629-abc123

# 10. 删除单条决策记录
python scripts/choice_assistant.py --action decision --id 20260629-abc123 --delete

# 11. 通过后端 /api/config 查看脱敏配置（默认行为，等同 --list）
python scripts/choice_assistant.py --action config-api

# 12. 把 CLI 配置保存到 SQLite（替代 ~/.choice/config.json）
python scripts/choice_assistant.py --action config-api --save-to-db \
  --api-key sk-xxx --llm-model gpt-4o-mini --llm-base-url https://api.openai.com/v1

# 13. 清除 SQLite 中所有 API Key（危险操作）
python scripts/choice_assistant.py --action config-api --delete
```

## 配置管理（三层优先级）

> 与后端 `backend/config.py` 完全对齐：环境变量 > SQLite > config.json。

API Key 按以下优先级从高到低解析（前者覆盖后者）：

1. **请求级覆盖（CLI flag / ChatRequest 字段）**：`--api-key`、`--llm-model`、
   `--llm-base-url`、`--weather-key`（高德 Key）、`--weather-city`，
   每次调用临时传入，不落盘。
2. **环境变量**：`CHOICE_LLM_API_KEY`、`CHOICE_LLM_MODEL`、`CHOICE_LLM_BASE_URL`、
   `CHOICE_WEATHER_KEY`、`CHOICE_WEATHER_CITY`。
   （`CHOICE_WEATHER_APPSECRET` 兼容旧版，自动映射到 `CHOICE_WEATHER_KEY`。）
3. **SQLite 配置表**（`choice.db`，新架构推荐方式）：通过前端设置页或
   `--action config-api --save-to-db` 写入。
4. **配置文件**：`~/.choice/config.json`（兼容旧版，权限 `0600`）。

> 高德 Key 申请：https://lbs.amap.com/dev/key/app（个人开发者每日 10 万次免费）

两套 CLI 配置入口：

- **`config` 子命令**（旧）：写入 `~/.choice/config.json`。
  - `python scripts/choice_assistant.py config --api-key sk-xxx --save`
- **`--action config-api`**（新）：通过后端 `/api/config` 接口管理 SQLite。
  - `--list` / 默认：GET 查看脱敏配置
  - `--save-to-db`：POST 把 CLI 配置写入 SQLite
  - `--delete`：DELETE 清除 SQLite 中所有 API Key

行为约束：

- 未配置任何 LLM Key 时，仍返回结构正确的 **mock 简报**，并附 `source: "mock"` 标识，
  便于无 Key 环境 / CI 中预览。
- 未配置天气 Key 时，nature 模式返回基于关键词的 mock 自然意象简报
  （`source: "模拟自然数据"`，`isReal: false`）。
- **API Key 不可写入日志**；CLI 与后端在回显配置时对 `llm_api_key` / `weather_key` /
  `weather_appsecret` 做 `***已配置***` 脱敏。
- 配置文件权限 `0600`（Windows 上为 best-effort，不报错）。
- ponytail: SQLite 中 API Key 明文存储，升级路径为 AES-256-GCM 加密。

## 输出格式

`--action chat` 返回的 JSON 结构（ChatResponse）：

```json
{
  "brief": {
    "summary": "核心结论",
    "confidence": 72,
    "perspectives": ["角度1", "角度2", "角度3"],
    "nextSteps": ["下一步1", "下一步2"],
    "risks": ["风险1", "风险2"],
    "source": "real"
  },
  "nature": null,
  "mode": "auto",
  "reply": "给用户的自然语言回复",
  "result": { "...": "完整 ModeResult（用于前端渲染和持久化）" },
  "autoRecognized": null,
  "decisionId": "20260629-abc123"
}
```

- `brief.source`：`"real"`（真实 LLM 调用）或 `"mock"`（未配置 / 降级时）。
- nature 模式时 `brief` 为 `null`，改返回 `nature` 自然意象简报：
  `{ type, time, season, weather, sun, wind, source, isReal, signal, poem, suggestion }`。
- `decisionId`：自动落库后的决策记录 id。CLI 在 chat 输出末尾会额外打印
  `已落库决策记录 id：xxx`，便于后续 `--action decision --id xxx` 查看或删除。

各动作返回结构：

- `--action archive` 返回 `{ ok, list, total, page, pageSize }`，CLI 仅打印 `list` 字段
  （每条含 `id` / `question` / `mode` / `brief` / `createdAt`）。
- `--action stats` 返回
  `{ totalDecisions, modeDistribution, avgConfidence, executedRate, regretRate, weekTrend }`：
  - `executedRate`：已执行决策占比
  - `regretRate`：标记后悔的决策占比
  - `weekTrend`：近 7 天每天决策数 `[{date, count}, ...]`
- `--action decision --id xxx` 返回单条决策记录（含 `executed` / `regret` / `dialogueHistory`）。
- `--action decision --id xxx --delete` 返回 `{ ok: true }`，CLI 输出 `已删除决策记录 xxx`。
- `--action config-api` 返回脱敏配置
  `{ llm: { model, baseUrl, hasKey }, weather: { city, hasKey, hasAppsecret }, hasLlm, hasWeather }`。
  （`hasAppsecret` 为兼容旧前端的别名，等价于 `hasKey`。）

## 后端启动

```bash
cd backend
pip install -r requirements.txt
python main.py
# 或热重载：uvicorn main:app --reload --port 8000
```

接口文档见 `http://localhost:8000/docs`，详见 `backend/README.md`。

## 前端 UI

后端启动后会自动挂载 `frontend/` 目录的静态资源（仿 HTML 版完整 UI）。用户可通过浏览器访问：

- **首页（决策面板）**：`http://localhost:8000/`
- **API 文档**：`http://localhost:8000/docs`
- **健康检查**：`http://localhost:8000/api/health`

UI 功能与 CLI 等价（chat / archive / stats / 设置页），所有数据通过同一套后端 API 流转，落库到同一个 SQLite。CLI 与 UI 可混合使用。

仅 CLI-only 模式下（无 `frontend/` 目录）后端跳过静态资源挂载，仅暴露 API。
