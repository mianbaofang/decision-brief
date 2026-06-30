"""AI 模式识别 + 自动可解释性路由。

移植自 HTML 版本的 ModeRecognizer 与 ExplainRouter（行 3319-3345）。
负责把用户输入的自然语言问题，按关键词命中优先级路由到六种决策模式之一。

六种模式：auto / rational / random / nature / dialogue / fengshui
- recognize: 返回 mode id
- explain: 返回 {mode, reason, confidence}，用于前端展示"为什么进入这个模式"
"""

from typing import Dict, List

# 合法的六种模式 id
VALID_MODES: List[str] = ["auto", "rational", "random", "nature", "dialogue", "fengshui"]

# mode id → 中文名（用于 reason 文案）
_MODE_NAMES: Dict[str, str] = {
    "auto": "自动",
    "rational": "理性",
    "random": "随机",
    "nature": "自然",
    "dialogue": "对话",
    "fengshui": "风水",
}

# 路由规则：按优先级排序，先命中先返回。
# 顺序对应 HTML 版本 ModeRecognizer.rules 数组。
RULES: List[Dict[str, object]] = [
    {
        "mode": "random",
        "keywords": ["吃什么", "喝什么", "看什么", "玩什么", "去哪", "午餐", "晚餐", "早餐", "选哪个"],
    },
    {
        "mode": "fengshui",
        "keywords": ["八字", "算命", "运势", "风水", "命理", "玄学", "占卜", "卦", "流年", "大运"],
    },
    {
        "mode": "rational",
        "keywords": ["辞职", "跳槽", "买房", "租房", "创业", "转行", "出国", "考研", "投资", "借钱", "贷款", "买车", "卖房"],
    },
    {
        "mode": "dialogue",
        "keywords": ["不敢", "害怕", "纠结", "犹豫", "放不下", "心里", "其实", "要不要说", "该不该说"],
    },
    {
        "mode": "nature",
        "keywords": ["感情", "恋爱", "喜欢", "表白", "暗恋", "复合", "前任", "婚姻", "情绪", "心烦", "出门", "旅行"],
    },
    {
        "mode": "rational",
        "keywords": ["书", "收拾", "整理", "买", "卖", "换", "留还是", "要不要买", "该不该"],
    },
]


def recognize(text: str) -> str:
    """识别用户问题对应的模式 id。

    空文本返回 'auto'；其余交由 explain() 决定。
    """
    if not text:
        return "auto"
    return explain(text)["mode"]


def explain(text: str) -> Dict[str, object]:
    """返回 {mode, reason, confidence}。

    命中关键词：confidence=76，reason 给出命中的关键词与模式名。
    未命中任何规则：默认进入理性分析，confidence=52。
    """
    input_text = text or ""
    for rule in RULES:
        for keyword in rule["keywords"]:
            if keyword in input_text:
                mode = rule["mode"]
                mode_name = _MODE_NAMES.get(mode, mode)
                return {
                    "mode": mode,
                    "reason": f"命中关键词「{keyword}」，按{mode_name}处理",
                    "confidence": 76,
                }
    return {
        "mode": "rational",
        "reason": "未命中特定场景，默认进入理性分析",
        "confidence": 52,
    }


if __name__ == "__main__":
    # 自测：覆盖每条规则 + 默认分支
    cases = [
        ("今天午餐吃什么", "random", "吃什么"),
        ("想算一下八字运势", "fengshui", "八字"),
        ("该不该辞职跳槽", "rational", "辞职"),
        ("我其实不敢说，心里很纠结", "dialogue", "不敢"),
        ("要不要向前任表白复合", "nature", "表白"),
        ("这本书该不该买", "rational", "书"),
        ("", "auto", None),
        ("hello world", "rational", None),
    ]
    all_ok = True
    for text, expect_mode, expect_kw in cases:
        if not text:
            mode = recognize(text)
            ok = mode == expect_mode
            print(f"[{'OK' if ok else 'FAIL'}] recognize({text!r}) = {mode} (expect {expect_mode})")
            all_ok = all_ok and ok
            continue
        result = explain(text)
        ok = result["mode"] == expect_mode
        if expect_kw:
            ok = ok and expect_kw in result["reason"]
        print(f"[{'OK' if ok else 'FAIL'}] explain({text!r}) = {result} (expect mode={expect_mode}, kw={expect_kw})")
        all_ok = all_ok and ok
    print("\n全部通过" if all_ok else "\n存在失败用例")
