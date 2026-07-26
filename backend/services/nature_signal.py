"""自然信号加权引擎。

移植自 HTML 版本的 NatureSignalEngine（行 3364-3377）。
把当前天气数据按权重拆解成多路自然信号，供 nature 模式做"顺势而行"的解读依据。

权重表：
  天气来源、风、气温、湿度、空气质量、预警、趋势、生活建议、
  时段、季节与月相均按数据存在性参与。预警权重最高；降级数据
  保留来源信号，但降低权重。
"""

from typing import Any, Dict, List, Optional


def build(weather: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """根据天气数据构建自然信号权重列表与汇总文案。

    参数：
      weather: 天气 dict，包含基础天气以及可选 alerts / weatherTrend /
               livingAdvice / airDetail / moonPhase / forecast。可为 None。

    返回：{weights: [{name, weight, value}], summary: str}
    """
    w = weather or {}
    weights: List[Dict[str, Any]] = []

    # 真实天气 vs 降级天气（互斥）
    if w.get("isReal"):
        weights.append({"name": "真实天气", "weight": 32, "value": w.get("weather") or "未知"})
    else:
        weights.append({"name": "降级天气", "weight": 16, "value": w.get("weather") or "模拟"})

    alerts = _text_list(w.get("alarms") or w.get("alerts") or w.get("weatherAlerts") or w.get("warnings"))
    if alerts:
        weights.append({"name": "天气预警", "weight": 28, "value": "；".join(alerts[:2])})
    if w.get("wind"):
        weights.append({"name": "风向风力", "weight": 18, "value": w["wind"]})
    if w.get("temperature") not in (None, ""):
        weights.append({"name": "气温", "weight": 14, "value": f"{w['temperature']}℃"})
    if w.get("humidity"):
        weights.append({"name": "湿度", "weight": 10, "value": w["humidity"]})
    air_detail = _air_detail(w)
    if w.get("air") or air_detail:
        weights.append({"name": "空气详情", "weight": 12, "value": air_detail or str(w.get("air") or "")})
    trend = _trend_text(w)
    if trend:
        weights.append({"name": "天气趋势", "weight": 12, "value": trend})
    living = _text_list(w.get("life_indices") or w.get("livingAdvice") or w.get("lifeAdvice") or w.get("tips"))
    if living:
        weights.append({"name": "生活建议", "weight": 10, "value": "；".join(living[:2])})

    weights.append({"name": "时段", "weight": 8, "value": w.get("time") or "此刻"})
    weights.append({"name": "季节", "weight": 8, "value": w.get("season") or "四季"})
    if w.get("moonPhase"):
        weights.append({"name": "月相", "weight": 6, "value": w["moonPhase"]})

    summary = "；".join(f"{x['name']}{x['weight']}%:{x['value']}" for x in weights)
    return {"weights": weights, "summary": summary}


def _text_list(value: Any) -> List[str]:
    if isinstance(value, str):
        return [value.strip()] if value.strip() else []
    if isinstance(value, dict):
        fields = ("name", "level", "desc", "title", "text", "description", "value")
        items = [str(value[key]).strip() for key in fields if str(value.get(key) or "").strip()]
        ids = value.get("ids")
        if isinstance(ids, list):
            for item in ids:
                items.extend(_text_list(item))
        return items
    if isinstance(value, list):
        items: List[str] = []
        for item in value:
            items.extend(_text_list(item))
        return items
    return [str(value).strip()] if value is not None and str(value).strip() else []


def _air_detail(weather: Dict[str, Any]) -> str:
    detail = weather.get("airDetail") or weather.get("air_detail") or weather.get("airQuality")
    if isinstance(detail, dict):
        labels = (("aqi", "AQI"), ("pm25", "PM2.5"), ("pm10", "PM10"))
        readings = [f"{label} {detail[key]}" for key, label in labels if detail.get(key) not in (None, "")]
        if readings:
            return " · ".join(readings)
    items = _text_list(detail)
    if items:
        return "；".join(items[:2])
    aqi = weather.get("aqi")
    return f"{weather.get('air', '')} · AQI {aqi}".strip(" ·") if aqi not in (None, "") else ""


def _trend_text(weather: Dict[str, Any]) -> str:
    direct = _text_list(weather.get("weatherTrend") or weather.get("trend"))
    if direct:
        return "；".join(direct[:2])
    forecast = weather.get("forecast_1h") or weather.get("forecast_24h") or []
    if not isinstance(forecast, list):
        return ""
    texts = []
    for item in forecast[:2]:
        if not isinstance(item, dict):
            continue
        info = item.get("infos") or item.get("info") or {}
        info = info if isinstance(info, dict) else {}
        time = item.get("hour") or item.get("time") or item.get("update_time") or item.get("forecast_time")
        condition = item.get("weather") or info.get("weather") or item.get("text") or info.get("text")
        temperature = item.get("temperature") or info.get("temperature") or item.get("temp") or info.get("temp")
        parts = [time, condition, f"{temperature}℃" if temperature not in (None, "") else ""]
        text = " ".join(str(part).strip() for part in parts if part)
        if text:
            texts.append(text)
    return "；".join(texts)


if __name__ == "__main__":
    # 自测：真实天气完整数据
    w1 = {
        "isReal": True,
        "weather": "多云",
        "wind": "东南风 3 级",
        "temperature": 22,
        "humidity": "65%",
        "air": "良",
        "time": "下午",
        "season": "春",
    }
    r1 = build(w1)
    print("case1（真实天气）:", r1["summary"])
    assert r1["weights"][0] == {"name": "真实天气", "weight": 32, "value": "多云"}
    assert len(r1["weights"]) == 7  # 真实天气 + 风向风力 + 气温 + 湿度 + 空气质量 + 时段 + 季节
    assert "真实天气32%:多云" in r1["summary"]
    assert "气温14%:22℃" in r1["summary"]

    # 自测：降级天气，缺字段
    w2 = {"isReal": False}
    r2 = build(w2)
    print("case2（降级天气）:", r2["summary"])
    assert r2["weights"][0] == {"name": "降级天气", "weight": 16, "value": "模拟"}
    assert len(r2["weights"]) == 3  # 降级天气 + 时段 + 季节
    assert "时段8%:此刻" in r2["summary"]
    assert "季节8%:四季" in r2["summary"]

    # 自测：None 入参不崩
    r3 = build(None)
    print("case3（None）:", r3["summary"])
    assert r3["weights"][0]["name"] == "降级天气"

    print("\n全部通过")
