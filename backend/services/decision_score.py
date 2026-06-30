"""理性评分引擎。

移植自 HTML 版本的 DecisionScoreEngine（行 3347-3362）。
给定问题、rational 模式的 pros/cons 结果、用户价值观四元组，
计算出 benefit / risk / cost / reversibility / valueFit / confidence 六项分数。

所有分数为 0-100 整数（confidence 受 clamp 保护）。
"""

from typing import Any, Dict, List, Optional

# 触发"高风险"判定的关键词
RISK_WORDS: List[str] = ["辞职", "买房", "投资", "分手", "离婚", "创业", "借钱"]

# 触发"高可逆"判定的关键词
REVERSIBLE_WORDS: List[str] = ["吃", "看", "买小", "今天", "周末"]


def _clamp(low: int, high: int, value: float) -> int:
    """把 value 限制在 [low, high] 区间并取整。"""
    return max(low, min(high, round(value)))


def score(
    question: str,
    result: Optional[Dict[str, Any]],
    values: Optional[Dict[str, int]],
) -> Dict[str, int]:
    """计算理性评分。

    参数：
      question: 用户原始问题
      result:   rational 模式产出的 {pros: [...], cons: [...]}（可为 None）
      values:   价值观四元组 {efficiency, risk, growth, relationship}，0-100 整数

    返回：{benefit, risk, cost, reversibility, valueFit, confidence}
    """
    q = question or ""
    pros: List[str] = (result or {}).get("pros") or []
    cons: List[str] = (result or {}).get("cons") or []
    v = values or {}

    # risk：命中高风险词 → 72，否则 42
    risk = 72 if any(w in q for w in RISK_WORDS) else 42

    # reversibility：命中高可逆词 → 72，否则 46
    reversibility = 72 if any(w in q for w in REVERSIBLE_WORDS) else 46

    # benefit：pros 越多、且重视成长 → 越高，上限 90
    benefit = min(90, 48 + len(pros) * 10 + (6 if v.get("growth", 0) > 60 else 0))

    # cost：cons 越多、且厌恶风险 → 越高，上限 90
    cost = min(90, 38 + len(cons) * 12 + (8 if v.get("risk", 0) > 60 else 0))

    # valueFit：效率 + 成长 + (100 - risk) 三项均值
    value_fit = round(
        (
            v.get("efficiency", 50)
            + v.get("growth", 50)
            + (100 - min(100, risk))
        )
        / 3
    )

    # confidence：四项均值，clamp 到 [35, 88]
    confidence = _clamp(35, 88, (benefit + reversibility + value_fit + (100 - cost)) / 4)

    return {
        "benefit": benefit,
        "risk": risk,
        "cost": cost,
        "reversibility": reversibility,
        "valueFit": value_fit,
        "confidence": confidence,
    }


if __name__ == "__main__":
    # 自测：高风险 + 高可逆 + 成长导向
    r1 = score(
        "要不要辞职创业",
        {"pros": ["成长快", "收入高", "自由"], "cons": ["风险大", "压力大"]},
        {"efficiency": 70, "risk": 40, "growth": 80, "relationship": 50},
    )
    print("case1（辞职创业）:", r1)
    assert r1["risk"] == 72, f"risk 应为 72，实际 {r1['risk']}"
    assert r1["reversibility"] == 46, f"reversibility 应为 46，实际 {r1['reversibility']}"
    # benefit = min(90, 48 + 3*10 + 6) = min(90, 84) = 84
    assert r1["benefit"] == 84, f"benefit 应为 84，实际 {r1['benefit']}"
    # cost = min(90, 38 + 2*12 + 0) = min(90, 62) = 62（risk=40 不 >60）
    assert r1["cost"] == 62, f"cost 应为 62，实际 {r1['cost']}"
    # valueFit = round((70 + 80 + (100-72)) / 3) = round(178/3) = 59
    assert r1["valueFit"] == 59, f"valueFit 应为 59，实际 {r1['valueFit']}"
    # confidence = clamp(35, 88, round((84 + 46 + 59 + 38)/4)) = round(227/4) = 57
    assert r1["confidence"] == 57, f"confidence 应为 57，实际 {r1['confidence']}"

    # 自测：低风险 + 高可逆
    r2 = score(
        "今天吃什么",
        {"pros": [], "cons": []},
        {"efficiency": 50, "risk": 50, "growth": 50, "relationship": 50},
    )
    print("case2（今天吃什么）:", r2)
    assert r2["risk"] == 42
    assert r2["reversibility"] == 72  # 命中"今天"和"吃"

    # 自测：None 入参不崩
    r3 = score("", None, None)
    print("case3（空入参）:", r3)
    assert r3["benefit"] == 48
    assert r3["cost"] == 38

    print("\n全部通过")
