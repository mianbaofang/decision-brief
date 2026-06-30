"""nature 模式专用 LLM 调用。

参考 HTML 版本 Prompts.nature：先取当前天气，再把天气数据注入 prompt，
让 LLM 用自然意象给启示。未配置 LLM 时回退到基于关键词的 mock 自然简报。

输出结构：
  { type, time, season, weather, sun, wind, source, isReal, signal, poem, suggestion }
"""

from typing import Any, Dict, Optional

from config import get_effective_config, has_llm_config
from services.llm_service import NoApiKeyError, call_openai_llm
from services.weather_service import get_current_weather

# ponytail: nature_signal 模块尚未实现，ImportError 时降级为 None。
# 升级路径：实现 services/nature_signal.py 后自动接入 build_signals。
try:
    from services.nature_signal import build as build_signals
except ImportError:
    build_signals = None

_HUMANIZE = (
    "重要：用朋友聊天的口吻说话，不要像AI机器人。"
    "别用\"首先/其次/最后/综上所述\"这种机械连接词，用大白话。"
    "句子长短混搭，加入个人色彩，用具体代替抽象。"
)


def _build_nature_prompt(question: str, w: Dict[str, Any]) -> str:
    source_note = (
        f"数据源：{w['source']}，城市：{w['city']}，更新时间：{w.get('updateTime') or '实时接口返回'}"
        if w.get("isReal")
        else f"数据源：{w['source']}（天气接口未配置或不可用时的降级数据）"
    )
    lines = [
        f"当前时间：{w.get('date','')} {w['time']}".strip(),
        f"季节：{w['season']}",
        f"天气：{w['weather']}",
        f"气温：{w['temperature']}℃" if w.get("temperature") else "",
        f"风向风力：{w['wind']}",
        f"湿度：{w['humidity']}" if w.get("humidity") else "",
        f"空气质量：{w['air']}" if w.get("air") else "",
        f"天光信号：{w['sun']}",
        source_note,
    ]
    weather_line = "，".join(x for x in lines if x)
    return (
        f"{_HUMANIZE}\n\n"
        f"你是自然决策师，像个看惯了山水的朋友。{weather_line}。"
        f"针对问题：\"{question}\"，结合此刻真实或降级的自然条件，用自然意象给点启示。\n"
        "输出严格 JSON：\n"
        '{"type":"nature","time":"' + w['time'] + '","season":"' + w['season'] + '",'
        '"weather":"' + w['weather'] + '","sun":"' + w.get('sun', '') + '",'
        '"wind":"' + w['wind'] + '","source":"' + w['source'] + '",'
        '"isReal":' + ("true" if w.get("isReal") else "false") + ","
        '"signal":"自然信号名","poem":"结合自然条件的诗意解读2-3句，别太文绉绉",'
        '"suggestion":"基于自然逻辑的建议一句话，像朋友会说的话"}'
    )


def _mock_nature_brief(question: str, w: Dict[str, Any], language: str = "zh-CN") -> Dict[str, Any]:
    """基于关键词的 mock 自然简报，结构对齐 HTML 版本。"""
    q = question
    is_en = language == "en"
    time, season, weather, sun, wind = w["time"], w["season"], w["weather"], w.get("sun", "日光和煦"), w["wind"]
    if is_en:
        nature_map = [
            (["eat", "food", "lunch", "dinner", "restaurant"], "Ripe fruit",
             f"In the {season} {weather}, fruit falls when it is ready. Under {sun}, everything has its rhythm.",
             f"Pick the one that moves you right now, as the {wind} points."),
            (["quit", "job", "work", "career", "startup"], "Migrating birds",
             f"{season} days with {wind}, migrating birds set off. Not to betray the old forest, but to follow the season. {sun} shows the way.",
             f"If staying is only out of fear, the {wind} is already urging you to go."),
            (["break", "love", "relationship", "marry", "divorce"], "Two converging streams",
             f"Under the {weather}, streams meet and part. {sun} on the water shows that coming together and apart are both natural.",
             "Ask yourself: with them, do you feel more like yourself or less?"),
            (["buy", "sell", "house", "car", "rent", "money", "invest"], "Deep-rooted and shallow-rooted trees",
             f"In the {wind}, deep-rooted trees stand still while shallow-rooted ones sway. The soil of {season} decides where roots go.",
             f"Count the cost, then listen to the {wind}."),
            (["study", "exam", "read", "book", "major", "graduate"], "Sun-seeking vines",
             f"{sun}, vines climb toward the light without asking how far. {season} is a season of growth.",
             "Choose the path that makes your eyes light up."),
            (["move", "city", "stay", "leave"], "Drifting dandelion seeds",
             f"The {wind} rises and dandelion seeds drift. Under the {weather} sky, wherever they land is home.",
             "Imagine where future-you would regret being."),
            (["should", "whether", "can", "could"], "Ebb and flow of the tide",
             f"At {time}, {weather}, the sea does not rush the tide. Under {sun}, advance and retreat have their own rhythm.",
             "Wait three days; if the answer is still the same, do it."),
            (["choose", "pick", "which", "or"], "Forked river",
             f"In the {season} {weather}, the river reaches a fork. The {wind} pushes the current; every branch has its view.",
             "The moment the coin is in the air, you will know."),
        ]
        default_signal, default_poem, default_suggestion = (
            "Go with the flow",
            f"{weather} at {time}, {wind} brushes everything. If you cling to the answer, you cannot hear nature's whisper.",
            "Let go of the fixation and go with the flow."
        )
    else:
        nature_map = [
            (["吃", "喝", "食物", "餐厅"], "成熟的果实",
             f"{season}的{weather}里，果实不问甜涩，到时便落。{sun}时，万物自有其节奏。",
             f"选那个此刻最让你心头一动的，如同{wind}吹向的方向。"),
            (["辞职", "跳槽", "工作", "离职", "职业"], "迁徙的候鸟",
             f"{season}天{wind}，候鸟启程。不为背叛旧林，只为顺应天时。{sun}指引方向。",
             f"如果留下只是出于恐惧，{wind}已在催你启程。"),
            (["分手", "恋爱", "感情", "爱", "结婚", "离婚"], "两条交汇的溪流",
             f"{weather}之下，溪流交汇又分岔。{sun}映照水面，聚散皆是自然。",
             "问自己：和TA在一起时，你更像自己还是更不像自己？"),
            (["买", "卖", "房", "车", "租", "钱", "投资"], "深根与浅根的树",
             f"{wind}中，深根的树纹丝不动，浅根的树灵活摇摆。{season}的土壤，决定根的走向。",
             f"算清成本，再听{wind}的方向。"),
            (["学", "考", "读", "书", "专业", "考研", "出国"], "向阳的藤蔓",
             f"{sun}，藤蔓不问路有多远，只向着光攀爬。{season}是生长的季节。",
             "选那条让你眼睛发亮的路。"),
            (["搬", "走", "留", "城市", "回"], "随风飘散的蒲公英",
             f"{wind}起，蒲公英乘风向远方。{weather}的天空下，落处即是归处。",
             "想象五年后的自己会在哪里后悔。"),
            (["要不要", "该不该", "行不行", "能不能"], "潮起潮落的海",
             f"{time}，{weather}，海不催促潮水。{sun}下，进退自有节律。",
             "等三天，如果答案没变，就去做。"),
            (["选", "挑", "哪个", "还是"], "分岔的河流",
             f"{season}的{weather}，河流到了分岔处。{wind}推着水流，每条支流都有风景。",
             "抛硬币的瞬间，你就知道答案了。"),
        ]
        default_signal, default_poem, default_suggestion = (
            "顺势而行",
            f"{weather}的{time}，{wind}拂过万物。心若执着答案，便听不见自然的低语。",
            "放下执念，顺势而行。"
        )
    signal, poem, suggestion = default_signal, default_poem, default_suggestion
    for keys, sig, po, sug in nature_map:
        if any(k in q for k in keys):
            signal, poem, suggestion = sig, po, sug
            break
    return {
        "type": "nature",
        "time": time,
        "season": season,
        "weather": weather,
        "sun": sun,
        "wind": wind,
        "source": w["source"],
        "isReal": bool(w.get("isReal")),
        "signal": signal,
        "poem": poem,
        "suggestion": suggestion,
    }


def generate_nature_brief(question: str, config: Optional[Dict[str, Any]] = None,
                         language: str = "zh-CN", allow_mock: bool = False) -> Dict[str, Any]:
    """生成 nature 模式简报：取天气 → 调 LLM（带天气 prompt）→ 失败回退 mock。

    allow_mock=True 时无 Key 或调用失败回退 mock；allow_mock=False 时无 Key 抛 NoApiKeyError。
    """
    if config is None:
        config = get_effective_config()
    weather = get_current_weather(config, language=language)

    if has_llm_config(config):
        try:
            result = call_openai_llm(_build_nature_prompt(question, weather), config)
            # 用天气真实值回填，避免 LLM 编造
            result["source"] = result.get("source") or weather["source"]
            result["isReal"] = bool(result.get("isReal", weather["isReal"]))
            result["weather"] = result.get("weather") or weather["weather"]
            result["wind"] = result.get("wind") or weather["wind"]
            result["time"] = result.get("time") or weather["time"]
            result["season"] = result.get("season") or weather["season"]
            result["sun"] = result.get("sun") or weather.get("sun", "")
            result["type"] = "nature"
            return result
        except Exception as e:
            print(f"[nature] LLM 调用失败: {type(e).__name__}")
            if not allow_mock:
                raise
            print(f"[nature] allow_mock=True，降级 mock")

    if not allow_mock:
        raise NoApiKeyError("未配置 LLM API Key，且未开启 Demo 模式")

    return _mock_nature_brief(question, weather, language=language)
