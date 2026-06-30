"""端到端集成测试：6 模式全链路 + 配置流程 + 数据持久化。

直接对运行中的后端（默认 http://localhost:8765）做真实 HTTP 调用，
不走 TestClient，用于验证：
1. 6 模式（auto/rational/random/nature/dialogue/fengshui）的 /api/chat 全链路
2. 配置流程：POST /api/config → GET 脱敏 → DELETE 清除
3. 数据持久化：chat 自动落库 → archive 列表 → decision 查询/更新 → stats 统计
4. preferences GET/POST
"""

import os
import sys
from pathlib import Path

import httpx
import pytest

# 把 backend 加入 sys.path 以便复用 schemas
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

BASE_URL = os.environ.get("CHOICE_TEST_BASE_URL", "http://localhost:8765")


@pytest.fixture(scope="module")
def client():
    """HTTP 客户端。"""
    with httpx.Client(base_url=BASE_URL, timeout=30.0) as c:
        # 先确认服务在跑
        try:
            r = c.get("/api/health")
            r.raise_for_status()
        except Exception as e:
            pytest.skip(f"后端未运行在 {BASE_URL}：{e}")
        yield c


# ============================== 1. 健康检查 ==============================

def test_health(client):
    r = client.get("/api/health")
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "ok"
    assert data["name"]
    assert data["version"]


def test_modes(client):
    r = client.get("/api/modes")
    assert r.status_code == 200
    data = r.json()
    # 后端返回 {modes: [...], quickQuestions: [...]}
    assert "modes" in data
    assert "quickQuestions" in data
    modes = data["modes"]
    assert isinstance(modes, list)
    assert len(modes) == 6
    ids = {m["id"] for m in modes}
    assert ids == {"auto", "rational", "random", "nature", "dialogue", "fengshui"}
    assert isinstance(data["quickQuestions"], list)
    assert len(data["quickQuestions"]) >= 1


# ============================== 2. 6 模式全链路 ==============================

def test_chat_auto(client):
    r = client.post("/api/chat", json={"question": "今天午餐吃什么", "mode": "auto"})
    assert r.status_code == 200
    d = r.json()
    # auto 模式识别后 mode 字段是识别出的子模式（不再是 'auto'）
    assert d["mode"] in {"rational", "random", "nature", "dialogue", "fengshui"}
    assert d["autoRecognized"] is not None
    assert d["autoRecognized"]["mode"] == d["mode"]
    assert d["reply"]
    assert d["result"] is not None
    assert d["decisionId"]


def test_chat_rational(client):
    r = client.post("/api/chat", json={"question": "买电车还是油车", "mode": "rational"})
    assert r.status_code == 200
    d = r.json()
    assert d["mode"] == "rational"
    assert d["reply"]
    assert d["result"] is not None
    # rational 应有 conclusion 或 pros/cons
    res = d["result"]
    assert "conclusion" in res or "pros" in res or "score" in res
    assert d["decisionId"]


def test_chat_random(client):
    r = client.post("/api/chat", json={"question": "今晚看哪部电影", "mode": "random"})
    assert r.status_code == 200
    d = r.json()
    assert d["mode"] == "random"
    assert d["reply"]
    res = d["result"]
    # random 应返回 options 或 wheelResult
    assert "options" in res or "wheelResult" in res
    assert d["decisionId"]


def test_chat_nature(client):
    r = client.post("/api/chat", json={"question": "要不要换城市生活", "mode": "nature"})
    assert r.status_code == 200
    d = r.json()
    assert d["mode"] == "nature"
    assert d["reply"]
    # nature 模式应返回 nature 字段
    assert d["nature"] is not None
    n = d["nature"]
    assert "signal" in n or "suggestion" in n
    assert d["decisionId"]


def test_chat_dialogue(client):
    r = client.post("/api/chat", json={"question": "要不要辞职创业", "mode": "dialogue"})
    assert r.status_code == 200
    d = r.json()
    assert d["mode"] == "dialogue"
    assert d["reply"]
    res = d["result"]
    # dialogue 应有 options（追问选项）或 needBirth/question
    assert "options" in res or "question" in res or "needBirth" in res
    assert d["decisionId"]


def test_chat_fengshui(client):
    r = client.post("/api/chat", json={"question": "新办公室座位朝向", "mode": "fengshui"})
    assert r.status_code == 200
    d = r.json()
    assert d["mode"] == "fengshui"
    assert d["reply"]
    res = d["result"]
    # fengshui 应有 bazi / baziAudit / needBirth
    assert "bazi" in res or "baziAudit" in res or "needBirth" in res
    assert d["decisionId"]


# ============================== 3. 配置流程 ==============================

def test_config_flow(client):
    # 1. 先 GET 当前配置（脱敏）
    r = client.get("/api/config")
    assert r.status_code == 200
    before = r.json()
    assert "llm" in before
    assert "weather" in before
    assert "hasLlm" in before
    assert "hasWeather" in before
    # 脱敏：不应直接返回明文 key
    assert "apiKey" not in before["llm"]
    assert before["llm"].get("hasKey") in (True, False)

    # 2. POST 保存一个测试 model（不动 api_key 以免污染）
    r = client.post("/api/config", json={"llm_model": "test-model-integration"})
    assert r.status_code == 200
    saved = r.json()
    assert saved["llm"]["model"] == "test-model-integration"

    # 3. GET 验证已保存
    r = client.get("/api/config")
    assert r.status_code == 200
    after = r.json()
    assert after["llm"]["model"] == "test-model-integration"

    # 4. POST 一个完整 LLM key（仅用于测试）
    r = client.post("/api/config", json={
        "llm_api_key": "sk-test-integration-key",
        "llm_base_url": "https://api.test.com/v1",
    })
    assert r.status_code == 200
    assert r.json()["llm"]["hasKey"] is True

    # 5. GET 确认 hasKey 为 True，但不应回显明文 key
    r = client.get("/api/config")
    data = r.json()
    assert data["llm"]["hasKey"] is True
    assert "sk-test-integration-key" not in r.text  # 明文不应出现在响应中

    # 6. DELETE 清除
    r = client.delete("/api/config")
    assert r.status_code == 200

    # 7. GET 确认已清除
    r = client.get("/api/config")
    data = r.json()
    assert data["llm"]["hasKey"] is False
    assert data["weather"]["hasAppid"] is False


# ============================== 4. 数据持久化全链路 ==============================

def test_persistence_flow(client):
    # 1. 发起一次 chat，拿到 decisionId
    r = client.post("/api/chat", json={"question": "持久化测试问题", "mode": "random"})
    assert r.status_code == 200
    did = r.json()["decisionId"]
    assert did

    # 2. GET /api/decision/{id} 查询
    r = client.get(f"/api/decision/{did}")
    assert r.status_code == 200
    d = r.json()
    assert d["id"] == did
    assert d["question"] == "持久化测试问题"
    assert d["mode"] == "random"
    assert d["result"] is not None

    # 3. PATCH 标记 executed
    r = client.patch(f"/api/decision/{did}", json={"executed": True})
    assert r.status_code == 200
    assert r.json()["executed"] is True

    # 4. PATCH 标记 regret
    r = client.patch(f"/api/decision/{did}", json={"regret": True})
    assert r.status_code == 200
    assert r.json()["regret"] is True

    # 5. GET /api/archive 验证列表包含该记录
    r = client.get("/api/archive")
    assert r.status_code == 200
    arc = r.json()
    assert arc["ok"] is True
    assert "list" in arc
    assert "total" in arc
    ids = [item["id"] for item in arc["list"]]
    assert did in ids

    # 6. GET /api/stats 验证统计
    r = client.get("/api/stats")
    assert r.status_code == 200
    s = r.json()
    assert s["totalDecisions"] >= 1
    assert "modeDistribution" in s
    assert "executedRate" in s
    assert "regretRate" in s
    assert "weekTrend" in s
    # random 模式至少有 1 条
    assert s["modeDistribution"].get("random", 0) >= 1

    # 7. DELETE /api/decision/{id}
    r = client.delete(f"/api/decision/{did}")
    assert r.status_code == 200

    # 8. GET 已删除应 404
    r = client.get(f"/api/decision/{did}")
    assert r.status_code == 404


# ============================== 5. preferences ==============================

def test_preferences_flow(client):
    # 1. GET 当前（扁平结构）
    r = client.get("/api/preferences")
    assert r.status_code == 200
    before = r.json()
    assert "default_mode" in before or "language" in before  # 扁平结构

    # 2. POST 修改 default_mode / theme / language
    r = client.post("/api/preferences", json={
        "default_mode": "rational",
        "theme": "dark",
        "language": "zh-CN",
    })
    assert r.status_code == 200
    saved = r.json()
    assert saved.get("default_mode") == "rational"
    assert saved.get("theme") == "dark"
    assert saved.get("language") == "zh-CN"

    # 3. GET 验证
    r = client.get("/api/preferences")
    assert r.status_code == 200
    after = r.json()
    assert after.get("default_mode") == "rational"
    assert after.get("theme") == "dark"
    assert after.get("language") == "zh-CN"

    # 4. 恢复（避免污染其它测试）
    client.post("/api/preferences", json={
        "default_mode": before.get("default_mode", "auto"),
        "theme": before.get("theme", "auto"),
        "language": before.get("language", "zh-CN"),
    })


# ============================== 6. archive 分页 ==============================

def test_archive_pagination(client):
    r = client.get("/api/archive?page=1&pageSize=5")
    assert r.status_code == 200
    d = r.json()
    assert d["ok"] is True
    assert d["page"] == 1
    assert d["pageSize"] == 5
    assert isinstance(d["list"], list)
    assert len(d["list"]) <= 5


# ============================== 7. 输入校验 ==============================

def test_chat_missing_question(client):
    r = client.post("/api/chat", json={"mode": "auto"})
    assert r.status_code == 422  # Pydantic 校验失败


def test_chat_invalid_mode(client):
    r = client.post("/api/chat", json={"question": "x", "mode": "invalid"})
    assert r.status_code == 422


def test_decision_not_found(client):
    r = client.get("/api/decision/nonexistent-id-xxx")
    assert r.status_code == 404
