"""API 路由测试（FastAPI TestClient）。

环境隔离由 conftest.py 的 isolate_paths fixture 负责：
  - DB_PATH 指向临时文件
  - CONFIG_FILE_PATH 指向临时文件
  - 未配置 LLM/天气 → /api/chat 走 mock 分支，不发起网络请求
"""

import pytest
from fastapi.testclient import TestClient

import main


@pytest.fixture
def client():
    """每个测试用全新 TestClient。DB 路径已由 conftest.isolate_paths 隔离。"""
    with TestClient(main.app) as c:
        yield c


# ─── 基础 ────────────────────────────────────────────────────


def test_health(client):
    """GET /api/health 返回 200 和 ok 状态。"""
    resp = client.get("/api/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["name"] == "别纠结 API"
    assert "version" in body


def test_get_modes(client):
    """GET /api/modes 返回 6 模式 + 5 快捷问题。"""
    resp = client.get("/api/modes")
    assert resp.status_code == 200
    body = resp.json()
    assert len(body["modes"]) == 6
    mode_ids = {m["id"] for m in body["modes"]}
    assert mode_ids == {"auto", "rational", "random", "nature", "dialogue", "fengshui"}
    # 每个模式必有 name/icon/color/description
    for m in body["modes"]:
        assert m["name"]
        assert m["icon"]
        assert m["color"]
        assert m["description"]
    assert len(body["quickQuestions"]) == 5


# ─── 配置 ────────────────────────────────────────────────────


def test_get_config_returns_masked(client):
    """GET /api/config 返回脱敏配置（无配置时 hasKey=False）。

    v0.7.0 起 weather 用 hasKey（高德单 Key）；hasAppsecret 为兼容旧前端的别名。
    """
    resp = client.get("/api/config")
    assert resp.status_code == 200
    body = resp.json()
    assert body["llm"]["hasKey"] is False
    assert body["weather"]["hasKey"] is False
    assert body["weather"]["hasAppsecret"] is False  # 兼容别名，等价于 hasKey
    assert body["hasLlm"] is False
    assert body["hasWeather"] is False


def test_post_config_then_get_shows_has_key(client):
    """POST /api/config 保存配置后 GET 能看到 hasKey=true。"""
    payload = {
        "llm_api_key": "sk-test-xxx",
        "llm_model": "gpt-4o-mini",
        "llm_base_url": "https://api.openai.com/v1",
    }
    resp = client.post("/api/config", json=payload)
    assert resp.status_code == 200
    assert resp.json()["llm"]["hasKey"] is True

    # GET 验证落库
    resp = client.get("/api/config")
    body = resp.json()
    assert body["llm"]["hasKey"] is True
    assert body["llm"]["model"] == "gpt-4o-mini"
    assert body["llm"]["baseUrl"] == "https://api.openai.com/v1"
    # apiKey 永不回传明文
    assert "sk-test-xxx" not in resp.text


# ─── /api/chat ──────────────────────────────────────────────


def test_chat_auto_recognizes_random_mode(client):
    """POST /api/chat {mode:auto} 对「今天午餐吃什么」识别为 random。"""
    resp = client.post("/api/chat", json={"question": "今天午餐吃什么", "mode": "auto"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["mode"] == "random"
    assert body["autoRecognized"] is not None
    assert body["autoRecognized"]["mode"] == "random"
    assert "reason" in body["autoRecognized"]
    assert "confidence" in body["autoRecognized"]
    # mock 数据源
    assert body["result"]["_source"] == "mock"
    # 已落库
    assert body["decisionId"]


def test_chat_random_returns_six_options(client):
    """POST /api/chat {mode:random} 返回 result.options 6 项。"""
    resp = client.post("/api/chat", json={"question": "今天午餐吃什么", "mode": "random"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["mode"] == "random"
    result = body["result"]
    assert result["type"] == "random"
    assert len(result["options"]) == 6
    assert all(isinstance(o, str) and o for o in result["options"])


def test_chat_rational_returns_pros_and_cons(client):
    """POST /api/chat {mode:rational} 返回 result.pros/cons 非空。

    rational mock 的 result 用 conclusion 而非 summary，所以 brief 为 None 是预期行为
    （_try_build_brief 要求 result 含 summary 或 confidence 字段）。
    """
    resp = client.post("/api/chat", json={"question": "要不要辞职跳槽", "mode": "rational"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["mode"] == "rational"
    result = body["result"]
    assert result["type"] == "rational"
    assert isinstance(result["pros"], list) and len(result["pros"]) >= 1
    assert isinstance(result["cons"], list) and len(result["cons"]) >= 1
    # rational mock 含 conclusion 字段
    assert result.get("conclusion")
    # 已落库
    assert body["decisionId"]


def test_chat_nature_returns_nature_brief(client):
    """POST /api/chat {mode:nature} 返回 nature 字段非 null。"""
    resp = client.post("/api/chat", json={"question": "要不要向前任表白", "mode": "nature"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["mode"] == "nature"
    assert body["nature"] is not None
    # nature 字段必须有 signal/poem/suggestion
    assert body["nature"]["signal"]
    assert body["nature"]["poem"]
    assert body["nature"]["suggestion"]
    # nature 模式 brief 应为 null
    assert body["brief"] is None


def test_chat_fengshui_returns_need_birth(client):
    """POST /api/chat {mode:fengshui} 缺出生信息时返回 result.needBirth=true。"""
    resp = client.post("/api/chat", json={"question": "今年运势如何", "mode": "fengshui"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["mode"] == "fengshui"
    result = body["result"]
    assert result["type"] == "fengshui"
    assert result["needBirth"] is True


# ─── /api/decision CRUD ─────────────────────────────────────


def test_decision_crud_full_cycle(client):
    """POST 创建 → GET 查询 → PATCH 更新 → DELETE 删除 全闭环。"""
    # 1. 创建
    payload = {
        "question": "测试决策",
        "mode": "rational",
        "result": {"type": "rational", "pros": ["a"], "cons": ["b"]},
    }
    resp = client.post("/api/decision", json=payload)
    assert resp.status_code == 200
    created = resp.json()
    assert created["id"]
    assert created["createdAt"]
    decision_id = created["id"]

    # 2. 查询
    resp = client.get(f"/api/decision/{decision_id}")
    assert resp.status_code == 200
    assert resp.json()["question"] == "测试决策"

    # 3. 更新
    resp = client.patch(
        f"/api/decision/{decision_id}",
        json={"executed": True, "regret": False, "dialogueHistory": [{"role": "user", "text": "done"}]},
    )
    assert resp.status_code == 200
    updated = resp.json()
    assert updated["executed"] is True
    assert updated["regret"] is False
    assert updated["dialogueHistory"] == [{"role": "user", "text": "done"}]

    # 4. 删除
    resp = client.delete(f"/api/decision/{decision_id}")
    assert resp.status_code == 200
    assert resp.json()["ok"] is True

    # 5. 删除后再 GET 应 404
    resp = client.get(f"/api/decision/{decision_id}")
    assert resp.status_code == 404


def test_decision_get_returns_404_for_missing(client):
    """查询不存在的 id 返回 404。"""
    resp = client.get("/api/decision/not_exists_xxx")
    assert resp.status_code == 404


def test_decision_patch_returns_404_for_missing(client):
    """更新不存在的 id 返回 404。"""
    resp = client.patch("/api/decision/not_exists_xxx", json={"executed": True})
    assert resp.status_code == 404


def test_decision_delete_returns_404_for_missing(client):
    """删除不存在的 id 返回 404。"""
    resp = client.delete("/api/decision/not_exists_xxx")
    assert resp.status_code == 404


# ─── /api/archive ───────────────────────────────────────────


def test_archive_lists_chat_history(client):
    """POST /api/chat 后 GET /api/archive 能看到记录。"""
    # 先发起一次 chat（自动落库）
    resp = client.post("/api/chat", json={"question": "今天午餐吃什么", "mode": "random"})
    assert resp.status_code == 200
    chat_decision_id = resp.json()["decisionId"]
    assert chat_decision_id

    # 查 archive
    resp = client.get("/api/archive")
    assert resp.status_code == 200
    body = resp.json()
    assert body["ok"] is True
    assert body["total"] >= 1
    assert any(item["id"] == chat_decision_id for item in body["list"])


def test_archive_empty_when_no_decisions(client):
    """无决策记录时 archive 返回空列表与 total=0。"""
    resp = client.get("/api/archive")
    assert resp.status_code == 200
    body = resp.json()
    assert body["list"] == []
    assert body["total"] == 0


# ─── /api/stats ─────────────────────────────────────────────


def test_stats_returns_full_shape(client):
    """GET /api/stats 返回 totalDecisions/modeDistribution/avgConfidence/executedRate/regretRate/weekTrend。"""
    # 先创建若干条决策以保证 total > 0
    client.post("/api/chat", json={"question": "今天午餐吃什么", "mode": "random"})
    client.post("/api/chat", json={"question": "要不要换工作", "mode": "rational"})

    resp = client.get("/api/stats")
    assert resp.status_code == 200
    body = resp.json()
    assert body["totalDecisions"] >= 2
    # 模式分布应包含全部 6 个模式
    assert set(body["modeDistribution"].keys()) == {
        "auto", "rational", "random", "nature", "dialogue", "fengshui"
    }
    # 至少有一条是 random 模式
    assert body["modeDistribution"]["random"] >= 1
    assert isinstance(body["avgConfidence"], (int, float))
    assert 0.0 <= body["executedRate"] <= 1.0
    assert 0.0 <= body["regretRate"] <= 1.0
    # weekTrend 是近 7 天的列表
    assert len(body["weekTrend"]) == 7
    for item in body["weekTrend"]:
        assert "date" in item and "count" in item


def test_stats_empty_returns_zeros(client):
    """无决策记录时 stats 返回全 0。"""
    resp = client.get("/api/stats")
    assert resp.status_code == 200
    body = resp.json()
    assert body["totalDecisions"] == 0
    assert body["avgConfidence"] == 0.0
    assert body["executedRate"] == 0.0
    assert body["regretRate"] == 0.0
    assert len(body["weekTrend"]) == 7
    assert all(item["count"] == 0 for item in body["weekTrend"])


# ─── /api/preferences ───────────────────────────────────────


def test_preferences_get_returns_defaults(client):
    """GET /api/preferences 返回默认偏好（扁平结构）。"""
    resp = client.get("/api/preferences")
    assert resp.status_code == 200
    prefs = resp.json()
    assert prefs["language"] == "zh-CN"
    assert prefs["default_mode"] == "auto"


def test_preferences_post_persists(client):
    """POST /api/preferences 保存后 GET 能读到。"""
    resp = client.post("/api/preferences", json={"language": "yue", "theme": "dark"})
    assert resp.status_code == 200
    saved = resp.json()
    assert saved["language"] == "yue"
    assert saved["theme"] == "dark"

    # GET 验证持久化
    resp = client.get("/api/preferences")
    prefs = resp.json()
    assert prefs["language"] == "yue"
    assert prefs["theme"] == "dark"
