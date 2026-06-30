"""六种决策模式的静态元数据 + 快捷问题。

色值与图标按产品规范定义，供 GET /api/modes 与其它逻辑复用。
"""

from typing import List, Optional

from models.schemas import ModeMeta

# 六种决策模式
MODES: List[ModeMeta] = [
    ModeMeta(id="auto", name="自动", icon="自", color="#317d78",
             description="自动选择最合适的决策模式"),
    ModeMeta(id="rational", name="理性", icon="理", color="#365385",
             description="基于理性分析、利弊权衡做决策"),
    ModeMeta(id="random", name="随机", icon="随", color="#9b7636",
             description="用随机方式打破决策僵局"),
    ModeMeta(id="nature", name="自然", icon="然", color="#486a55",
             description="顺应直觉与自然倾向做选择"),
    ModeMeta(id="dialogue", name="对话", icon="问", color="#69526f",
             description="通过对话提问厘清真实需求"),
    ModeMeta(id="fengshui", name="风水", icon="局", color="#b45a42",
             description="以风水格局视角辅助决策"),
]

# 五条快捷问题（首页快捷入口）
QUICK_QUESTIONS: List[str] = [
    "该不该接受这份新工作？",
    "要不要换城市生活？",
    "继续读书还是开始工作？",
    "要不要主动联系他/她？",
    "该不该接受这个合作邀请？",
]


def get_mode(mode_id: str) -> Optional[ModeMeta]:
    """根据 id 查找模式，找不到返回 None。"""
    for m in MODES:
        if m.id == mode_id:
            return m
    return None
