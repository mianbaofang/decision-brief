# 别纠结后端 (FastAPI)

独立 FastAPI 后端，为 `choice-assistant` Skill 提供聊天、档案、统计和设置等 REST 接口。

## 依赖

- fastapi
- uvicorn
- httpx
- pydantic

## 启动

在 `backend/` 目录下执行：

```bash
pip install -r requirements.txt

# 方式一：直接运行
python main.py

# 方式二：uvicorn 热重载
uvicorn main:app --reload --host 127.0.0.1 --port 8010
```

启动后：

- 服务地址：http://127.0.0.1:8010
- API 文档：http://127.0.0.1:8010/docs
- 健康检查：http://127.0.0.1:8010/

## 接口

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| POST | /api/chat | 接收问题 + 模式，返回 AI 回复（含决策简报 .brief） |
| GET | /api/modes | 返回六种模式元数据 |
| POST | /api/decision | 保存一条决策记录 |
| GET | /api/archive | 获取决策历史列表 |
| GET | /api/stats | 获取统计数据 |

## 目录

```
backend/
├── main.py              # 应用入口，注册路由，监听 8010
├── requirements.txt
├── routes/              # 路由（chat/modes/decision/archive/stats）
├── services/            # 业务服务（llm_service / modes_data）
└── models/              # Pydantic 模型（schemas.py）
```

## 说明

- LLM 使用 OpenAI 兼容接口，由用户配置 Key、模型和 Base URL。
- 未配置 LLM Key 时，`/api/chat` 返回 402；只有用户主动开启 Demo 才会返回示例数据。
- 天气使用高德开放平台，Key、Base URL 和城市由用户配置；缺少 Key 或 Base URL 时，自然模式使用明确标注的模拟天气。
- 决策记录和设置保存在本机 SQLite，服务重启后仍在。

## Agent 集成

本后端为 `choice-assistant` Skill 提供 API 服务，Agent 通过 CLI 脚本调用：

1. 先启动后端（见上方「启动」章节）
2. Agent 加载 `SKILL.md` 中的 Skill 定义
3. Agent 通过 `python scripts/choice_assistant.py --question "..." --mode auto` 调用
4. CLI 脚本会向本后端的 `/api/chat` 发送 POST 请求，返回结构化决策简报

详细参数和调用样例见项目根目录的 `SKILL.md`。
