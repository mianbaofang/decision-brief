"""服务层测试。

覆盖：
  - mode_recognizer: recognize / explain
  - bazi_engine: year_pillar / parse
  - decision_score: score
  - nature_signal: build
  - llm_service: 无配置时 mock / sanitize_result 补齐
"""

import pytest

from services.bazi_engine import parse, year_pillar
from services.decision_score import score
from services.llm_service import call_llm, sanitize_result
from services.mode_recognizer import explain, recognize
from services.nature_signal import build as build_nature_signal


# ─── mode_recognizer ────────────────────────────────────────


def test_mode_recognizer_lunch_question_returns_random():
    """recognize 对「今天午餐吃什么」返回 random。"""
    assert recognize("今天午餐吃什么") == "random"


def test_mode_recognizer_empty_returns_auto():
    """空文本返回 auto。"""
    assert recognize("") == "auto"
    assert recognize(None) == "auto"  # type: ignore[arg-type]


def test_mode_recognizer_explain_returns_full_shape():
    """explain 返回 {mode, reason, confidence} 三字段，confidence 在合理区间。"""
    result = explain("今天午餐吃什么")
    assert set(result.keys()) >= {"mode", "reason", "confidence"}
    assert result["mode"] == "random"
    assert isinstance(result["reason"], str) and result["reason"]
    assert isinstance(result["confidence"], int)
    assert 0 <= result["confidence"] <= 100


def test_mode_recognizer_explain_unmatched_falls_back_to_rational():
    """未命中任何规则时回落到 rational，confidence=52。"""
    result = explain("hello world")
    assert result["mode"] == "rational"
    assert result["confidence"] == 52


def test_mode_recognizer_fengshui_keywords():
    """八字/风水关键词命中 fengshui。"""
    assert recognize("想算一下八字运势") == "fengshui"
    assert recognize("今年风水如何") == "fengshui"


def test_mode_recognizer_dialogue_keywords():
    """纠结/不敢等关键词命中 dialogue。"""
    assert recognize("我其实不敢说，心里很纠结") == "dialogue"


# ─── bazi_engine ────────────────────────────────────────────


def test_bazi_year_pillar_1990_is_gengwu():
    """1990年6月15日（立春后）年柱为 庚午年。"""
    yp = year_pillar(1990, 6, 15)
    assert "庚午" in yp
    assert yp.endswith("年")


def test_bazi_year_pillar_before_lichun_uses_previous_year():
    """1990年1月15日（立春前）按 1989 年算，年柱为 己巳年。"""
    yp = year_pillar(1990, 1, 15)
    assert "己巳" in yp


def test_bazi_year_pillar_1984_is_jiazi():
    """1984 年是甲子年（基准点）。"""
    assert year_pillar(1984, 6, 15) == "甲子年"


def test_bazi_year_pillar_none_returns_placeholder():
    """year 为 None 返回占位符。"""
    assert year_pillar(None, None, None) == "未知年柱"


def test_bazi_parse_extracts_year_month_day():
    """parse 对「1990年6月15日中午」提取 year/month/day。"""
    info = parse("1990年6月15日中午")
    assert info["year"] == 1990
    assert info["month"] == 6
    assert info["day"] == 15


def test_bazi_parse_extracts_gender_and_hour():
    """parse 提取性别和时辰。"""
    info = parse("男命 1990年6月15日 出生于北京 农历 午时")
    assert info["gender"] == "男"
    assert info["hour"] is not None
    assert info["hour"]["branch"] == "午"
    assert info["calendar"] == "农历"
    assert info["place"] == "北京"


def test_bazi_parse_missing_fields_returns_missing_list():
    """parse 对缺字段文本返回 missing 列表。"""
    info = parse("你好")
    assert info["year"] is None
    assert info["month"] is None
    assert info["day"] is None
    assert "阳历或农历生日" in info["missing"]
    assert "出生时辰" in info["missing"]
    assert "性别" in info["missing"]
    assert "出生地" in info["missing"]


# ─── decision_score ─────────────────────────────────────────


def test_decision_score_returns_six_fields():
    """score() 返回 6 项：benefit/risk/cost/reversibility/valueFit/confidence。"""
    result = score(
        "要不要辞职创业",
        {"pros": ["成长快", "收入高", "自由"], "cons": ["风险大", "压力大"]},
        {"efficiency": 70, "risk": 40, "growth": 80, "relationship": 50},
    )
    assert set(result.keys()) == {
        "benefit", "risk", "cost", "reversibility", "valueFit", "confidence"
    }
    # 所有分数为 0-100 整数
    for v in result.values():
        assert isinstance(v, int)
        assert 0 <= v <= 100


def test_decision_score_high_risk_question():
    """命中高风险词（辞职/创业）时 risk=72。"""
    result = score("要不要辞职创业", {"pros": [], "cons": []}, None)
    assert result["risk"] == 72
    # 辞职创业未命中高可逆词，reversibility=46
    assert result["reversibility"] == 46


def test_decision_score_high_reversibility_question():
    """命中高可逆词（今天/吃）时 reversibility=72。"""
    result = score("今天吃什么", {"pros": [], "cons": []}, None)
    assert result["reversibility"] == 72
    assert result["risk"] == 42  # 未命中高风险词


def test_decision_score_handles_none_inputs():
    """None 入参不崩，使用 fallback。"""
    result = score("", None, None)
    assert result["benefit"] == 48  # 0 + 0 + 0 = 48
    assert result["cost"] == 38


# ─── nature_signal ──────────────────────────────────────────


def test_nature_signal_build_returns_weights_and_summary():
    """build() 返回 {weights, summary}，weights 非空。"""
    weather = {
        "isReal": True,
        "weather": "多云",
        "wind": "东南风 3 级",
        "temperature": 22,
        "humidity": "65%",
        "air": "良",
        "time": "下午",
        "season": "春",
    }
    result = build_nature_signal(weather)
    assert "weights" in result
    assert "summary" in result
    assert isinstance(result["weights"], list) and len(result["weights"]) >= 3
    # 真实天气权重应为 32
    assert result["weights"][0]["name"] == "真实天气"
    assert result["weights"][0]["weight"] == 32
    # summary 含权重表达
    assert "真实天气32%:多云" in result["summary"]


def test_nature_signal_build_handles_none():
    """weather=None 时降级为模拟数据，不崩。"""
    result = build_nature_signal(None)
    assert result["weights"][0]["name"] == "降级天气"
    assert result["weights"][0]["weight"] == 16
    # 时段与季节总是出现
    names = [w["name"] for w in result["weights"]]
    assert "时段" in names
    assert "季节" in names


def test_nature_signal_build_degraded_weather():
    """isReal=False 时降级天气权重为 16。"""
    result = build_nature_signal({"isReal": False, "weather": "模拟阴天"})
    assert result["weights"][0] == {"name": "降级天气", "weight": 16, "value": "模拟阴天"}


# ─── llm_service ────────────────────────────────────────────


def test_llm_service_call_llm_returns_mock_when_no_config(monkeypatch):
    """无 LLM 配置时 call_llm 返回 _source=mock。"""
    # conftest 已隔离 DB，无任何配置；同时清掉环境变量
    for env in ("CHOICE_LLM_API_KEY", "CHOICE_LLM_BASE_URL", "CHOICE_LLM_MODEL"):
        monkeypatch.delenv(env, raising=False)

    result = call_llm("要不要换工作", "rational", config={})
    assert result["_source"] == "mock"
    assert result["type"] == "rational"
    # rational mock 必含 pros/cons/conclusion
    assert "pros" in result and len(result["pros"]) >= 1
    assert "cons" in result and len(result["cons"]) >= 1
    assert "conclusion" in result


def test_llm_service_call_llm_random_returns_six_options(monkeypatch):
    """random 模式 mock 返回 6 个选项。"""
    for env in ("CHOICE_LLM_API_KEY", "CHOICE_LLM_BASE_URL", "CHOICE_LLM_MODEL"):
        monkeypatch.delenv(env, raising=False)

    result = call_llm("今天午餐吃什么", "random", config={})
    assert result["_source"] == "mock"
    assert result["type"] == "random"
    assert len(result["options"]) == 6


def test_llm_service_call_llm_fengshui_returns_need_birth(monkeypatch):
    """fengshui 模式 mock 在缺出生信息时 needBirth=True。"""
    for env in ("CHOICE_LLM_API_KEY", "CHOICE_LLM_BASE_URL", "CHOICE_LLM_MODEL"):
        monkeypatch.delenv(env, raising=False)

    result = call_llm("今年运势", "fengshui", config={})
    assert result["_source"] == "mock"
    assert result["type"] == "fengshui"
    assert result["needBirth"] is True


def test_llm_service_call_llm_rejects_nature_mode():
    """call_llm 对 nature 模式直接抛错（应走 nature_service）。"""
    with pytest.raises(ValueError):
        call_llm("test", "nature", config={})


def test_llm_service_sanitize_result_fills_missing_rational_fields():
    """sanitize_result 对缺失的 pros/cons/conclusion 补齐 fallback。"""
    raw = {"type": "rational"}  # 缺 pros/cons/conclusion
    result = sanitize_result(raw, "rational")
    assert result["type"] == "rational"
    assert result["pros"]  # 补齐后非空
    assert result["cons"]
    assert result["conclusion"]
    # 应该有 schemaWarning
    assert result.get("_schemaWarning")


def test_llm_service_sanitize_result_fills_missing_random_options():
    """sanitize_result 对 random 模式补齐 6 个选项。"""
    raw = {"type": "random"}  # 缺 options
    result = sanitize_result(raw, "random")
    assert result["type"] == "random"
    assert len(result["options"]) == 6


def test_llm_service_sanitize_result_fills_missing_dialogue_fields():
    """sanitize_result 对 dialogue 模式补齐 question 和 3 个 options。"""
    raw = {"type": "dialogue"}
    result = sanitize_result(raw, "dialogue")
    assert result["type"] == "dialogue"
    assert result["question"]
    assert len(result["options"]) >= 3


def test_llm_service_sanitize_result_handles_non_dict():
    """sanitize_result 对非 dict 输入返回带 _schemaWarning 的占位。"""
    result = sanitize_result("not a dict", "rational")  # type: ignore[arg-type]
    assert result["type"] == "rational"
    assert "_schemaWarning" in result
