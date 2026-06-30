"""POST /api/chat - 接收用户问题 + 模式，返回 AI 回复。

流程：
  1. 合并请求级临时覆盖配置（apiKey/llmModel/... > 环境变量 > SQLite > config.json）
  2. mode == "auto" 时调用 mode_recognizer.explain 识别实际模式
  3. mode == "nature" 时走 nature_service.generate_nature_brief
  4. 其它模式调用 llm_service.call_llm 拿到 ModeResult dict
  5. 自动落库到 SQLite decisions 表
  6. 返回 ChatResponse（brief/nature/mode/reply/result/autoRecognized）
"""

from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException

import db
from config import get_effective_config, get_preferences
from models.schemas import Brief, ChatRequest, ChatResponse
from services.llm_service import NoApiKeyError, call_llm
from services.mode_recognizer import explain as explain_mode
from services.nature_service import generate_nature_brief

router = APIRouter()


def _request_overrides(req: ChatRequest) -> dict:
    """从请求体提取临时覆盖配置（映射到 config 键名）。

    v0.7.0 起 weatherKey（高德 Key）为主字段；
    weatherAppsecret 兼容旧版，自动并入 weather_key。
    """
    weather_key = req.weatherKey or req.weatherAppsecret
    return {
        "llm_api_key": req.apiKey,
        "llm_model": req.llmModel,
        "llm_base_url": req.llmBaseUrl,
        "weather_key": weather_key,
        "weather_appsecret": req.weatherAppsecret,
        "weather_city": req.weatherCity,
    }


def _merge_overrides(base: dict, overrides: dict) -> dict:
    """在 base 之上叠加请求级覆盖（仅覆盖非空字段）。"""
    cfg = dict(base)
    if not overrides:
        return cfg
    for k, v in overrides.items():
        if v:
            cfg[k] = v
    return cfg


def _try_build_brief(result: Dict[str, Any], mode: str = "auto") -> Optional[Brief]:
    """从 ModeResult 构造 Brief。

    优先读取 result 中的 summary/confidence/perspectives/nextSteps/risks；
    缺失时从模式字段推导（conclusion/signal/suggestion/pros/cons），
    confidence 按模式给默认值，确保档案页和统计页有有效数据。
    """
    if not isinstance(result, dict):
        return None

    # 默认值表（与 llm_service._MOCK_BRIEFS 保持一致）
    default_confidence = {
        "rational": 78,
        "random": 55,
        "nature": 65,
        "dialogue": 70,
        "fengshui": 60,
        "auto": 72,
    }.get(mode, 60)

    summary = (
        result.get("summary")
        or result.get("conclusion")
        or result.get("signal")
        or result.get("suggestion")
        or ""
    )
    confidence = result.get("confidence")
    if confidence is None:
        confidence = default_confidence
    try:
        confidence = int(confidence)
    except (TypeError, ValueError):
        confidence = default_confidence

    perspectives = list(result.get("perspectives", []) or [])
    next_steps = list(result.get("nextSteps", []) or [])
    risks = list(result.get("risks", []) or [])

    # 从模式字段推导 perspectives / risks
    if not perspectives:
        pros = result.get("pros") or []
        cons = result.get("cons") or []
        if pros:
            perspectives.append("支持：" + "；".join(str(p) for p in pros[:3]))
        if cons:
            risks.append("风险：" + "；".join(str(c) for c in cons[:3]))
    if not next_steps and result.get("suggestion"):
        next_steps.append(str(result["suggestion"]))

    if not summary:
        return None

    try:
        return Brief(
            summary=summary,
            confidence=confidence,
            perspectives=perspectives,
            nextSteps=next_steps,
            risks=risks,
            source=result.get("source") or result.get("_source"),
        )
    except (TypeError, ValueError):
        return None


@router.post("/api/chat", response_model=ChatResponse)
def chat(req: ChatRequest) -> ChatResponse:
    """接收用户问题 + 模式，返回决策简报与自然语言回复。

    - auto 模式：调用 mode_recognizer.explain 自动识别，并把识别结果写入 autoRecognized
    - nature 模式：走 nature_service，brief 为空
    - 其它模式：调用 call_llm 拿 ModeResult，并尝试从 result 提取 Brief
    - 结果自动落库到 decisions 表
    """
    merged_config = _merge_overrides(get_effective_config(), _request_overrides(req))

    # 用户语言偏好，用于无 Key 时的 mock 数据语言；demo_mode 决定是否允许 mock 降级
    prefs = get_preferences()
    language = prefs.get("language", "zh-CN")
    allow_mock = bool(prefs.get("demo_mode", False))

    # 1. auto 模式识别
    auto_recognized: Optional[Dict[str, Any]] = None
    effective_mode = req.mode
    if effective_mode == "auto":
        auto_recognized = explain_mode(req.question)
        effective_mode = str(auto_recognized.get("mode") or "auto")

    # 2. 分模式处理
    brief: Optional[Brief] = None
    nature: Optional[Dict[str, Any]] = None
    result: Optional[Dict[str, Any]] = None
    reply: str = ""

    try:
        if effective_mode == "nature":
            nature = generate_nature_brief(req.question, config=merged_config,
                                           language=language, allow_mock=allow_mock)
            result = nature
            signal = nature.get("signal", "")
            poem = nature.get("poem", "")
            suggestion = nature.get("suggestion", "")
            reply = (
                f"已用「nature」模式分析你的问题「{req.question}」。\n"
                f"自然信号：{signal}\n"
                f"{poem}\n"
                f"建议：{suggestion}"
            )
        else:
            result = call_llm(req.question, effective_mode, merged_config,
                              language=language, allow_mock=allow_mock,
                              image=req.image)
            brief = _try_build_brief(result, mode=effective_mode)
            summary = result.get("summary") or result.get("conclusion") or ""
            reply = (
                f"已用「{effective_mode}」模式分析你的问题「{req.question}」。\n"
                f"{summary}"
            )
    except NoApiKeyError:
        raise HTTPException(status_code=402, detail="需要配置 LLM API Key 才能使用。可点击「体验 Demo」查看演示效果。")

    # 3. 自动落库
    decision_id: Optional[str] = None
    try:
        saved = db.save_decision({
            "question": req.question,
            "mode": effective_mode,
            "result": result or {},
            "brief": brief.model_dump() if brief else None,
            "executed": False,
            "regret": False,
        })
        decision_id = saved.get("id")
    except Exception as e:
        # 落库失败不阻塞主流程
        print(f"[chat] 落库失败: {type(e).__name__}")

    # 4. 返回
    return ChatResponse(
        brief=brief,
        nature=nature,
        mode=effective_mode,
        reply=reply,
        result=result,
        autoRecognized=auto_recognized,
        decisionId=decision_id,
    )
