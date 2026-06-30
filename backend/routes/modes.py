"""GET /api/modes - 返回六种决策模式元数据 + 五条快捷问题。"""

from typing import Any, Dict

from fastapi import APIRouter

from services.modes_data import MODES, QUICK_QUESTIONS

router = APIRouter()


@router.get("/api/modes")
def get_modes() -> Dict[str, Any]:
    """返回六种模式的元数据（id / 名称 / 图标 / 色值 / 说明）+ 五条快捷问题。"""
    return {
        "modes": [m.model_dump() for m in MODES],
        "quickQuestions": QUICK_QUESTIONS,
    }
