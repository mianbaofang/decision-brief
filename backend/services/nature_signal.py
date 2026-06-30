"""自然信号加权引擎。

移植自 HTML 版本的 NatureSignalEngine（行 3364-3377）。
把当前天气数据按权重拆解成多路自然信号，供 nature 模式做"顺势而行"的解读依据。

权重表（与 HTML 版本一致）：
  真实天气 32 / 降级天气 16（二选一）
  风向风力 18 / 气温 14 / 湿度 10 / 空气质量 10（按存在性触发）
  时段 8 / 季节 8（总是出现）
"""

from typing import Any, Dict, List, Optional


def build(weather: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """根据天气数据构建自然信号权重列表与汇总文案。

    参数：
      weather: 天气 dict，字段包括 isReal / weather / wind / temperature /
               humidity / air / time / season。可为 None。

    返回：{weights: [{name, weight, value}], summary: str}
    """
    w = weather or {}
    weights: List[Dict[str, Any]] = []

    # 真实天气 vs 降级天气（互斥）
    if w.get("isReal"):
        weights.append({"name": "真实天气", "weight": 32, "value": w.get("weather") or "未知"})
    else:
        weights.append({"name": "降级天气", "weight": 16, "value": w.get("weather") or "模拟"})

    # 可选信号：按存在性触发
    if w.get("wind"):
        weights.append({"name": "风向风力", "weight": 18, "value": w["wind"]})
    if w.get("temperature"):
        weights.append({"name": "气温", "weight": 14, "value": f"{w['temperature']}℃"})
    if w.get("humidity"):
        weights.append({"name": "湿度", "weight": 10, "value": w["humidity"]})
    if w.get("air"):
        weights.append({"name": "空气质量", "weight": 10, "value": w["air"]})

    # 总是出现的信号
    weights.append({"name": "时段", "weight": 8, "value": w.get("time") or "此刻"})
    weights.append({"name": "季节", "weight": 8, "value": w.get("season") or "四季"})

    summary = "；".join(f"{x['name']}{x['weight']}%:{x['value']}" for x in weights)
    return {"weights": weights, "summary": summary}


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
