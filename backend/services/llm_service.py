"""LLM 服务封装。

支持两种模式：
  - 真实调用：config 中含 llm_api_key + llm_base_url + llm_model 时，
    用 httpx 调用 OpenAI 兼容协议（/chat/completions）。
  - mock 降级：未配置或调用失败时返回结构正确的 ModeResult，附 _source='mock'。

6 模式差异化：
  - auto: 均衡综合（Brief 风格）
  - rational: 利弊清单 + 结论
  - random: 6 候选项（按问题内容选池：吃/看/买）
  - nature: 走 nature_service，不在本模块
  - dialogue: 反问 + 3 选项
  - fengshui: 调用 bazi_engine.analyze，缺字段返回 needBirth=true

约束：API Key 不可写入日志。
"""

import json
import re
from typing import Any, Dict, Optional

import httpx

from config import get_effective_config, has_llm_config
from models.schemas import Brief

_LLM_TIMEOUT = 15.0

# 旧 Brief mock 模板（generate_brief 兼容用）
_HUMANIZE = (
    "重要：用朋友聊天的口吻说话，不要像AI机器人。"
    "别用\"首先/其次/最后/综上所述\"这种机械连接词，用大白话。"
    "句子长短混搭，加入个人色彩，用具体代替抽象。"
)

# random mock 选项池（按问题内容选择）
_RANDOM_POOLS = {
    "zh-CN": {
        "eat": ["麻辣烫", "便利店寿司", "清淡沙拉", "兰州拉面", "黄焖鸡饭", "煎饼果子"],
        "watch": ["爽片放松", "纪录片", "喜剧乐呵", "悬疑烧脑", "动画回忆", "综艺下饭"],
        "buy": ["先等三天", "找平替", "二手淘", "等大促", "咬牙拿下", "果断放弃"],
        "default": ["先这样试试", "换个思路", "再想想", "问朋友", "睡一觉再说", "抛硬币决定"],
    },
    "en": {
        "eat": ["Malatang", "Sushi", "Salad", "Lanzhou noodles", "Braised chicken", "Jianbing"],
        "watch": ["Action movie", "Documentary", "Comedy", "Thriller", "Animation", "Variety show"],
        "buy": ["Wait 3 days", "Find a cheaper alternative", "Buy second-hand", "Wait for sale", "Just buy it", "Skip it"],
        "default": ["Try this first", "Think differently", "Sleep on it", "Ask a friend", "Take a small step", "Flip a coin"],
    },
}
# random 不足 6 项时的补齐池
_RANDOM_FALLBACK = {
    "zh-CN": ["先暂停", "换个角度", "问问朋友", "明天再定", "做最小尝试", "保留原状"],
    "en": ["Pause", "Change angle", "Ask a friend", "Decide tomorrow", "Take a tiny step", "Keep the status quo"],
}

# dialogue 不足 3 项时的补齐池
_DIALOGUE_FALLBACK = {
    "zh-CN": ["害怕损失", "想要改变", "需要更多信息"],
    "en": ["Fear of loss", "Want change", "Need more info"],
}


def _build_endpoint(base_url: str) -> str:
    """根据 base_url 拼出 chat completions 全路径。

    兼容两种写法：完整 endpoint（含 /chat/completions）或 base（如 .../v1）。
    """
    if base_url.endswith("/chat/completions"):
        return base_url
    if base_url.endswith("/"):
        return base_url + "chat/completions"
    return base_url.rstrip("/") + "/chat/completions"


def _parse_json_content(text: str) -> Any:
    """从 LLM 输出中提取 JSON（处理 ```json 代码块包裹与多余文本）。"""
    if not text:
        return None
    cleaned = text.strip()
    fence = re.search(r"```(?:json)?\s*(\{.*?\}|\[.*?\])\s*```", cleaned, re.DOTALL)
    if fence:
        cleaned = fence.group(1)
    else:
        m = re.search(r"\{.*\}", cleaned, re.DOTALL)
        if m:
            cleaned = m.group(0)
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        return None


def call_openai_llm(prompt: str, config: Dict[str, Any], image: Optional[str] = None) -> Dict[str, Any]:
    """调用 OpenAI 兼容接口，返回解析后的 JSON dict。失败抛异常。

    注意：config 含 api_key，调用方不得将其写入日志。
    image 为可选的 base64 data URL（如 "data:image/png;base64,..."），传入时启用多模态格式。
    """
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {config['llm_api_key']}",
    }
    if image and isinstance(image, str) and image.startswith("data:"):
        user_content = [
            {"type": "text", "text": prompt},
            {"type": "image_url", "image_url": {"url": image}},
        ]
    else:
        user_content = prompt
    body = {
        "model": config["llm_model"],
        "messages": [{"role": "user", "content": user_content}],
        "temperature": 0.7,
    }
    url = _build_endpoint(config["llm_base_url"])
    with httpx.Client(timeout=_LLM_TIMEOUT) as client:
        resp = client.post(url, headers=headers, json=body)
        resp.raise_for_status()
    data = resp.json()
    choices = data.get("choices") or [{}]
    content = (choices[0].get("message") or {}).get("content", "")
    parsed = _parse_json_content(content)
    if not isinstance(parsed, dict):
        raise ValueError("LLM 返回内容无法解析为 JSON")
    return parsed


# ─── Brief 兼容（旧 API）──────────────────────────────────────


def _build_brief_prompt(question: str, mode: str, has_image: bool = False) -> str:
    image_hint = "\n\n（用户同时上传了一张图片，请结合图片内容分析用户的问题。）" if has_image else ""
    return (
        f"{_HUMANIZE}\n\n"
        f"你是决策助手，针对问题：\"{question}\"，用「{mode}」模式分析。"
        f"{image_hint}"
        "输出严格 JSON：\n"
        '{"summary":"核心结论一句话","confidence":0-100整数,'
        '"perspectives":["角度1","角度2","角度3"],"nextSteps":["下一步1","下一步2"],'
        '"risks":["风险1","风险2"]}'
    )


# 各模式 Brief mock 模板（summary 用 {question}/{mode} 占位）
_MOCK_BRIEFS_I18N: Dict[str, Dict[str, Dict[str, Any]]] = {
    "auto": {
        "zh-CN": {
            "summary": "针对「{question}」，在「{mode}」模式下综合多维度评估后给出折中建议。",
            "confidence": 72,
            "perspectives": [
                "综合视角：把理性、情感与随机性都纳入考量，避免任一维度主导。",
                "长期视角：评估该选择对 1 年后状态的综合影响。",
                "均衡视角：寻找折中路径，而非追求单点最优。",
            ],
            "nextSteps": [
                "列出该决策最关心的 2-3 个维度并赋予权重。",
                "用 auto 模式跑一次综合评估作为基线。",
                "选定后设定 24 小时复核窗口再最终确认。",
            ],
            "risks": [
                "维度过多可能导致结论模糊、难以下定。",
                "权重设置偏离实际需求会让综合结果失真。",
            ],
        },
        "en": {
            "summary": "A balanced recommendation for 「{question}」 under the {mode} mode.",
            "confidence": 72,
            "perspectives": [
                "Holistic view: weigh reason, emotion, and chance together.",
                "Long-term view: assess the impact one year from now.",
                "Balanced view: look for a compromise rather than a single optimum.",
            ],
            "nextSteps": [
                "List the 2-3 dimensions you care about most and weight them.",
                "Run an auto-mode evaluation as a baseline.",
                "Set a 24-hour review window before finalizing.",
            ],
            "risks": [
                "Too many dimensions can make the conclusion fuzzy.",
                "Biased weights can distort the combined result.",
            ],
        },
    },
    "rational": {
        "zh-CN": {
            "summary": "针对「{question}」，在「{mode}」模式下按利弊加权计算，建议选得分更高项。",
            "confidence": 78,
            "perspectives": [
                "利弊分析：为每个选项列出 3 条利与 3 条弊。",
                "概率视角：估算每条利弊发生的概率（高/中/低）。",
                "成本视角：量化时间、金钱与机会成本的取舍。",
            ],
            "nextSteps": [
                "为每条利弊打分（1-5）并乘以概率权重。",
                "汇总正负总分，选总分更高者。",
                "若得分接近，引入敏感性分析核对结论稳定性。",
            ],
            "risks": [
                "未量化的情感因素被低估。",
                "概率估算的主观偏差可能让结论失真。",
            ],
        },
        "en": {
            "summary": "For 「{question}」, the {mode} mode scores pros and cons to pick the higher-scoring option.",
            "confidence": 78,
            "perspectives": [
                "Pros/cons: list 3 pros and 3 cons for each option.",
                "Probability: estimate how likely each pro/con is.",
                "Cost view: quantify time, money, and opportunity cost.",
            ],
            "nextSteps": [
                "Score each pro/con 1-5 and multiply by probability weight.",
                "Sum positive and negative scores, pick the higher total.",
                "If scores are close, run a sensitivity check.",
            ],
            "risks": [
                "Emotional factors that are hard to quantify may be undervalued.",
                "Subjective probability estimates can skew the result.",
            ],
        },
    },
    "random": {
        "zh-CN": {
            "summary": "针对「{question}」，在「{mode}」模式下交给随机性打破僵局，并附意外提示。",
            "confidence": 55,
            "perspectives": [
                "硬币视角：抛硬币瞬间的本能倾向很能说明问题。",
                "意外视角：随机结果可能暴露你潜意识的真实倾向。",
                "概率视角：估算每个选项的胜算比并标注不确定性。",
            ],
            "nextSteps": [
                "抛一次硬币，记录抛之前你期望的结果。",
                "若结果与期望相反，再抛一次作为三局两胜。",
                "把「为什么不服」写下来作为决策依据。",
            ],
            "risks": [
                "把随机当真，忽略必要的理性分析。",
                "用随机掩盖本应承担的判断责任。",
            ],
        },
        "en": {
            "summary": "For 「{question}」, the {mode} mode breaks the deadlock with randomness.",
            "confidence": 55,
            "perspectives": [
                "Coin-flip view: the instinct before the toss reveals a lot.",
                "Surprise view: a random result may expose your hidden lean.",
                "Odds view: estimate each option's chance and note uncertainty.",
            ],
            "nextSteps": [
                "Flip a coin and record which side you hoped for before it lands.",
                "If the result feels wrong, flip again as best-of-three.",
                "Write down why you disagree with the outcome.",
            ],
            "risks": [
                "Taking randomness too seriously and skipping rational analysis.",
                "Using randomness to avoid owning the decision.",
            ],
        },
    },
    "dialogue": {
        "zh-CN": {
            "summary": "针对「{question}」，在「{mode}」模式下通过自我对话厘清真实需求。",
            "confidence": 70,
            "perspectives": [
                "自我对话视角：把「支持」和「反对」双方请上台。",
                "他人视角：想象 5 年后的自己怎么看这个决定。",
                "提问视角：问「选 A 我会失去什么？选 B 呢？」。",
            ],
            "nextSteps": [
                "用 5 个为什么追问到底，挖出真实动机。",
                "把内心冲突写成一问一答的对话稿。",
                "请一位朋友扮演反对者与你辩论。",
            ],
            "risks": [
                "对话无限延宕，迟迟不下决定。",
                "扮演者立场偏颇，导致结论失衡。",
            ],
        },
        "en": {
            "summary": "For 「{question}」, the {mode} mode clarifies what you really want through self-dialogue.",
            "confidence": 70,
            "perspectives": [
                "Inner dialogue: let the 'for' and 'against' sides speak.",
                "Future self view: imagine how you'll see this decision in 5 years.",
                "Questioning view: ask 'what do I lose if I pick A? And B?'",
            ],
            "nextSteps": [
                "Ask 'why' five times to dig out the real motive.",
                "Write the internal conflict as a Q&A script.",
                "Ask a friend to play devil's advocate and debate.",
            ],
            "risks": [
                "The dialogue can drag on forever without a decision.",
                "A biased devil's advocate can unbalance the conclusion.",
            ],
        },
    },
    "fengshui": {
        "zh-CN": {
            "summary": "针对「{question}」，在「{mode}」模式下结合方位、五行与时辰给出格局建议。",
            "confidence": 60,
            "perspectives": [
                "方位视角：本命卦象对应的吉方宜行。",
                "五行视角：当前时辰五行生克与该选择的契合度。",
                "时辰视角：选吉时启动该决策，避开冲煞。",
            ],
            "nextSteps": [
                "查询今日宜忌与个人本命方位。",
                "在吉时吉方做出正式决断。",
                "决策后布置空间格局以稳固结果。",
            ],
            "risks": [
                "方位与时辰计算误差，需核对节气。",
                "过度依赖风水，忽略现实条件约束。",
            ],
        },
        "en": {
            "summary": "For 「{question}」, the {mode} mode gives a directional reading based on bearing, elements, and hour.",
            "confidence": 60,
            "perspectives": [
                "Direction view: the auspicious bearing for your birth chart.",
                "Element view: how the current hour's elements interact with the choice.",
                "Hour view: pick a favorable hour and avoid clashes.",
            ],
            "nextSteps": [
                "Check today's dos/don'ts and your personal favorable direction.",
                "Make the formal decision at a favorable hour and bearing.",
                "Arrange the space afterward to stabilize the result.",
            ],
            "risks": [
                "Bearing and hour calculations can be off; verify solar terms.",
                "Over-relying on fengshui while ignoring real-world constraints.",
            ],
        },
    },
}


def _mock_brief(question: str, mode: str, language: str = "zh-CN") -> Dict[str, Any]:
    """Brief mock，按模式和语言差异化生成，附 source='mock'。"""
    templates = _MOCK_BRIEFS_I18N.get(mode, _MOCK_BRIEFS_I18N["auto"])
    template = templates.get(language, templates["zh-CN"])
    return {
        "summary": template["summary"].format(question=question, mode=mode),
        "confidence": template["confidence"],
        "perspectives": list(template["perspectives"]),
        "nextSteps": list(template["nextSteps"]),
        "risks": list(template["risks"]),
        "source": "mock",
    }


# ─── ModeResult（新 API）──────────────────────────────────────


def _get_values() -> Dict[str, int]:
    """从 preferences 读取用户价值观（rational 模式注入用）。"""
    try:
        from config import get_preferences

        prefs = get_preferences()
        values = prefs.get("values")
        if isinstance(values, dict):
            return values
    except Exception:
        pass
    return {}


def _build_mode_prompt(question: str, mode: str, has_image: bool = False) -> str:
    """根据模式构建 prompt（使用 prompts.py 模板）。auto 用 brief prompt 降级。"""
    from services.prompts import (
        rational as rational_prompt,
        random as random_prompt,
        dialogue as dialogue_prompt,
        fengshui as fengshui_prompt,
    )

    image_hint = "\n\n（用户同时上传了一张图片，请结合图片内容分析用户的问题。）" if has_image else ""

    if mode == "rational":
        return rational_prompt(question, _get_values()) + image_hint
    if mode == "random":
        return random_prompt(question) + image_hint
    if mode == "dialogue":
        return dialogue_prompt(question) + image_hint
    if mode == "fengshui":
        return fengshui_prompt(question) + image_hint
    # auto 或未知：用 brief prompt（均衡综合）
    return _build_brief_prompt(question, mode) + image_hint


def _mock_random(question: str, language: str = "zh-CN") -> Dict[str, Any]:
    """random mock：按问题内容选池，不足 6 项用 fallback 补齐。"""
    pools = _RANDOM_POOLS.get(language, _RANDOM_POOLS["zh-CN"])
    if language == "zh-CN":
        if "吃" in question:
            opts = list(pools["eat"])
        elif "看" in question:
            opts = list(pools["watch"])
        elif "买" in question:
            opts = list(pools["buy"])
        else:
            opts = list(pools["default"])
    else:
        q = question.lower()
        if any(w in q for w in ("eat", "food", "lunch", "dinner", "restaurant")):
            opts = list(pools["eat"])
        elif any(w in q for w in ("watch", "movie", "film", "show")):
            opts = list(pools["watch"])
        elif any(w in q for w in ("buy", "purchase", "shop")):
            opts = list(pools["buy"])
        else:
            opts = list(pools["default"])
    fallback = _RANDOM_FALLBACK.get(language, _RANDOM_FALLBACK["zh-CN"])
    # 不足 6 项补齐
    for d in fallback:
        if len(opts) >= 6:
            break
        if d not in opts:
            opts.append(d)
    return {"type": "random", "options": opts[:6], "_source": "mock"}


def _mock_fengshui(question: str, language: str = "zh-CN") -> Dict[str, Any]:
    """fengshui mock：调用 bazi_engine.analyze，缺字段返回 needBirth=true。

    ponytail: bazi_engine 模块尚未实现，ImportError 时直接 needBirth=true。
    升级路径：实现 services/bazi_engine.py 后自动接入。
    """
    is_en = language == "en"
    try:
        from services.bazi_engine import analyze

        bazi = analyze(question)
    except ImportError:
        return {
            "type": "fengshui",
            "needBirth": True,
            "question": (
                "Please provide birth date, time, gender, and birthplace for a complete BaZi chart."
                if is_en else
                "要按 bazi-skill 完整排盘，请补充出生年月日时、性别、出生地，阳历/农历也请说明。"
            ),
            "bazi": "",
            "wuxing": "",
            "element": "",
            "analysis": "",
            "suggestion": "",
            "baziAudit": "",
            "_source": "mock",
        }

    if not bazi.get("complete"):
        missing = bazi.get("missing", [])
        return {
            "type": "fengshui",
            "needBirth": True,
            "question": (
                f"Missing: {', '.join(missing)}. Please provide birth date, time, gender, and birthplace."
                if is_en else
                f"要按 bazi-skill 完整排盘，还缺：{'、'.join(missing)}。请补充出生年月日时、性别、出生地，阳历/农历也请说明。"
            ),
            "bazi": "",
            "wuxing": "",
            "element": "",
            "analysis": "",
            "suggestion": "",
            "baziAudit": bazi.get("audit", ""),
            "_source": "mock",
        }
    pillars = bazi.get("pillars", {})
    return {
        "type": "fengshui",
        "needBirth": False,
        "question": "",
        "bazi": f"{pillars.get('year','')} / {pillars.get('month','')} / {pillars.get('day','')} / {pillars.get('hour','')}",
        "wuxing": bazi.get("wuxing", ""),
        "element": bazi.get("element", ""),
        "analysis": (
            "Basic chart verification only. Full BaZi analysis requires the complete bazi-skill pipeline."
            if is_en else
            "当前只完成基础排盘校验，不能凭空判断日主强弱、大运流年或完整喜用神。要做完整玄学决策，需要接入 bazi-skill 的四柱、十神、格局、大运流年分析。"
        ),
        "suggestion": (
            "Treat this as cultural reference only; for a real BaZi decision, complete the chart first."
            if is_en else
            "可以先把这条作为传统文化参考；真正要按八字做决策，请先补齐 bazi-skill 完整排盘。"
        ),
        "baziAudit": bazi.get("audit", ""),
        "_source": "mock",
    }


def _mock_mode_result(question: str, mode: str, language: str = "zh-CN") -> Dict[str, Any]:
    """mock ModeResult，按模式和语言差异化生成，附 _source='mock'。

    nature 模式不在本函数处理（应走 nature_service）。
    """
    is_en = language == "en"
    if mode == "rational":
        return {
            "type": "rational",
            "pros": [
                "It stops you from overthinking this later" if is_en else "说白了，能让你以后少纠结这事",
                "You get more used to making your own calls" if is_en else "自己拿主意的次数多了，人也更干脆",
                "No more carrying it around in your head" if is_en else "省得老惦记着，心里踏实",
            ],
            "cons": [
                "Some short-term pressure and discomfort" if is_en else "短期内得扛点压力，不舒服",
                "People around you might have opinions" if is_en else "搞不好身边人会念叨两句",
            ],
            "conclusion": (
                "Take two small steps first, keep an exit open."
                if is_en else
                "依我看，分两步走，先动起来再说，给自己留个退路就行。"
            ),
            "_source": "mock",
        }
    if mode == "random":
        return _mock_random(question, language=language)
    if mode == "dialogue":
        return {
            "type": "dialogue",
            "question": (
                "Honestly, what would the person you care about most say if they saw you this stuck?"
                if is_en else
                "说真的，你最在意的那个人，要是知道你这么纠结，他会怎么说？"
            ),
            "options": list(_DIALOGUE_FALLBACK.get(language, _DIALOGUE_FALLBACK["zh-CN"])),
            "_source": "mock",
        }
    if mode == "fengshui":
        return _mock_fengshui(question, language=language)
    if mode == "nature":
        raise ValueError("nature 模式请使用 nature_service.generate_nature_brief，不在 llm_service 中")
    # auto 或未知：均衡综合（Brief 风格 + type=auto）
    template = _mock_brief(question, mode, language=language)
    return {
        "type": "auto",
        "summary": template["summary"],
        "confidence": template["confidence"],
        "perspectives": list(template["perspectives"]),
        "nextSteps": list(template["nextSteps"]),
        "risks": list(template["risks"]),
        "_source": "mock",
    }


def _text(value: Any, max_len: int = 240) -> str:
    """清洗文本：去控制字符 + 截断。"""
    return str(value if value is not None else "").replace("\x00", "").strip()[:max_len]


def _array(value: Any, max_items: int = 8, max_text: int = 120) -> list:
    """清洗数组：每项清洗 + 截断 + 去空。"""
    if not isinstance(value, list):
        return []
    arr = [_text(v, max_text) for v in value[:max_items]]
    return [a for a in arr if a]


def sanitize_result(raw: Dict[str, Any], mode: str) -> Dict[str, Any]:
    """schema 校验，参考 HTML 版本 AI._sanitize。

    Args:
        raw: LLM 返回的 dict（已解析）。
        mode: 期望的模式。

    Returns:
        校验后的 dict，缺失字段用 fallback 补齐，附 _source 与可能的 _schemaWarning。
    """
    if not isinstance(raw, dict):
        return {"type": mode, "_source": "real", "_schemaWarning": "返回非 dict"}

    valid_types = {"rational", "random", "nature", "dialogue", "fengshui"}
    type_ = raw.get("type") if raw.get("type") in valid_types else mode

    warnings: list = []
    base = {"type": type_, "_source": raw.get("_source", "real")}

    def ensure_text(value: Any, fallback: str, max_len: int = 240) -> str:
        text = _text(value, max_len)
        if not text:
            warnings.append(fallback)
        return text or fallback

    def ensure_array(value: Any, fallback: list, min_items: int = 1,
                     max_items: int = 8, max_text: int = 120) -> list:
        arr = _array(value, max_items, max_text)
        if len(arr) < min_items:
            warnings.append(" / ".join(fallback))
        return arr if len(arr) >= min_items else list(fallback)

    def done(data: Dict[str, Any]) -> Dict[str, Any]:
        if warnings:
            data["_schemaWarning"] = "；".join(warnings[:4])
        return data

    if type_ == "rational":
        return done({**base,
                     "pros": ensure_array(raw.get("pros"), ["优势信息不足"], 1, 6),
                     "cons": ensure_array(raw.get("cons"), ["风险信息不足"], 1, 6),
                     "conclusion": ensure_text(raw.get("conclusion"), "先缓一步，补齐信息后再决定", 220)})
    if type_ == "random":
        return done({**base,
                     "options": ensure_array(raw.get("options"), list(_RANDOM_FALLBACK["zh-CN"]), 6, 8, 50),
                     "reason": _text(raw.get("reason"), 160)})
    if type_ == "nature":
        return done({**base,
                     "time": ensure_text(raw.get("time"), "此刻", 30),
                     "season": ensure_text(raw.get("season"), "当前季节", 20),
                     "weather": ensure_text(raw.get("weather"), "未知天气", 40),
                     "sun": _text(raw.get("sun"), 60),
                     "wind": _text(raw.get("wind"), 60),
                     "source": ensure_text(raw.get("source"), "自然信号", 80),
                     "isReal": bool(raw.get("isReal")),
                     "signal": ensure_text(raw.get("signal"), "顺势而行", 80),
                     "poem": ensure_text(raw.get("poem"), "当前自然信号不足，先降低动作幅度。", 260),
                     "suggestion": ensure_text(raw.get("suggestion"), "先做一个低风险的小动作", 180)})
    if type_ == "dialogue":
        return done({**base,
                     "question": ensure_text(raw.get("question"), "你真正担心失去的是什么？", 180),
                     "options": ensure_array(raw.get("options"), list(_DIALOGUE_FALLBACK["zh-CN"]), 3, 4, 80)})
    if type_ == "fengshui":
        need_birth = bool(raw.get("needBirth"))
        return done({**base,
                     "needBirth": need_birth,
                     "question": _text(raw.get("question"), 240),
                     "bazi": ensure_text(raw.get("bazi"), "" if need_birth else "八字排盘信息不足", 200),
                     "wuxing": _text(raw.get("wuxing"), 240),
                     "element": _text(raw.get("element"), 120),
                     "analysis": ensure_text(raw.get("analysis"),
                                             "需要补齐出生信息后再排盘。" if need_birth else "命理分析信息不足。", 360),
                     "suggestion": ensure_text(raw.get("suggestion"), "先补齐信息，再做判断", 200),
                     "baziAudit": _text(raw.get("baziAudit"), 260)})
    # auto 或其它：透传字段
    return done({**base, **{k: v for k, v in raw.items() if k != "type"}})


class NoApiKeyError(Exception):
    """未配置 API Key 且未开启 demo_mode 时抛出。"""
    pass


def call_llm(question: str, mode: str, config: Optional[Dict[str, Any]] = None,
             language: str = "zh-CN", allow_mock: bool = False,
             image: Optional[str] = None) -> Dict[str, Any]:
    """调用 LLM 生成完整 ModeResult。

    config 为 None 时从 get_effective_config() 读取。
    allow_mock=True 时：配置齐全则真实调用，失败/无配置则回退 mock（附 _source='mock'）。
    allow_mock=False 时：无配置直接抛 NoApiKeyError，真实调用失败抛原始异常。
    image 为可选的 base64 data URL，传入时启用多模态格式。

    nature 模式不在本函数处理，应走 nature_service。
    """
    if mode == "nature":
        raise ValueError("nature 模式请使用 nature_service.generate_nature_brief，不在 llm_service 中")

    if config is None:
        config = get_effective_config()

    has_image = bool(image and isinstance(image, str) and image.startswith("data:"))

    if has_llm_config(config):
        try:
            prompt = _build_mode_prompt(question, mode, has_image=has_image)
            raw = call_openai_llm(prompt, config, image=(image if has_image else None))
            raw["_source"] = "real"
            return sanitize_result(raw, mode)
        except Exception as e:
            # 不打印 api_key；仅记录异常类型
            print(f"[llm] 真实调用失败: {type(e).__name__}")
            if not allow_mock:
                raise
            print(f"[llm] allow_mock=True，降级 mock")

    if not allow_mock:
        raise NoApiKeyError("未配置 LLM API Key，且未开启 Demo 模式")

    return _mock_mode_result(question, mode, language=language)


# ─── 旧 API 兼容 ─────────────────────────────────────────────


def generate_brief(question: str, mode: str, config: Optional[Dict[str, Any]] = None) -> Brief:
    """根据问题和模式生成决策简报（兼容旧 API）。

    内部使用 Brief 专用 prompt + Brief mock，不经过 call_llm 的 ModeResult 流程。
    """
    if config is None:
        config = get_effective_config()

    if has_llm_config(config):
        try:
            data = call_openai_llm(_build_brief_prompt(question, mode), config)
            data["source"] = "real"
        except Exception as e:
            print(f"[llm] 真实调用失败，降级 mock: {type(e).__name__}")
            data = _mock_brief(question, mode)
    else:
        data = _mock_brief(question, mode)

    fields = Brief.model_fields if hasattr(Brief, "model_fields") else Brief.__fields__
    return Brief(**{k: v for k, v in data.items() if k in fields})


def generate_reply(question: str, mode: str, brief: Brief) -> str:
    """生成给用户的自然语言回复。"""
    return (
        f"已用「{mode}」模式分析你的问题「{question}」。\n"
        f"核心结论：{brief.summary}\n"
        f"信心值：{brief.confidence}/100。建议参考下方的多角度分析后再做最终决定。"
    )
