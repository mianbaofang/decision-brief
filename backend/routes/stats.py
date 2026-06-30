"""GET /api/stats - 返回统计数据。

字段：
  - totalDecisions: 决策总数
  - modeDistribution: 每个模式各有多少条
  - avgConfidence: brief.confidence 的平均值（brief 为 None 的跳过）
  - executedRate: executed=True 的比例
  - regretRate: regret=True 的比例
  - weekTrend: 最近 7 天每天的决策数量 [{date, count}, ...]

无记录时返回全 0 的 Stats（不返回 mock 数据）。
"""

from collections import defaultdict
from datetime import date, datetime, timedelta
from typing import Any, Dict, List

from fastapi import APIRouter

import db
from models.schemas import Stats
from services.modes_data import MODES

router = APIRouter()

# 单次最多扫描的记录数（ ponytail: 简单粗暴，本地工具的量级足够）
_MAX_SCAN = 100_000


@router.get("/api/stats", response_model=Stats)
def get_stats() -> Stats:
    """返回决策总数、模式分布、平均信心值、执行率、后悔率、近 7 天趋势。"""
    total = db.count_decisions()
    if total == 0:
        return Stats(
            totalDecisions=0,
            modeDistribution={m.id: 0 for m in MODES},
            avgConfidence=0.0,
            executedRate=0.0,
            regretRate=0.0,
            weekTrend=_empty_week_trend(),
        )

    decisions = db.list_decisions(limit=_MAX_SCAN, offset=0)

    # 模式分布
    distribution: Dict[str, int] = {m.id: 0 for m in MODES}
    for d in decisions:
        mode = d.get("mode") or "auto"
        distribution[mode] = distribution.get(mode, 0) + 1

    # 平均信心值（brief 为 None 跳过）
    confidences: List[int] = []
    for d in decisions:
        brief = d.get("brief")
        if isinstance(brief, dict):
            try:
                confidences.append(int(brief.get("confidence", 0)))
            except (TypeError, ValueError):
                pass
    avg_confidence = round(sum(confidences) / len(confidences), 2) if confidences else 0.0

    # 执行率 / 后悔率
    executed_n = sum(1 for d in decisions if d.get("executed"))
    regret_n = sum(1 for d in decisions if d.get("regret"))
    executed_rate = round(executed_n / total, 4) if total else 0.0
    regret_rate = round(regret_n / total, 4) if total else 0.0

    # 近 7 天趋势（含今天，oldest → newest）
    today = date.today()
    counts_by_date: Dict[str, int] = defaultdict(int)
    for d in decisions:
        created = d.get("createdAt")
        if not created:
            continue
        try:
            day = datetime.fromisoformat(created).date().isoformat()
        except (ValueError, TypeError):
            continue
        counts_by_date[day] += 1
    week_trend = [
        {"date": (today - timedelta(days=i)).isoformat(),
         "count": counts_by_date.get((today - timedelta(days=i)).isoformat(), 0)}
        for i in range(6, -1, -1)
    ]

    return Stats(
        totalDecisions=total,
        modeDistribution=distribution,
        avgConfidence=avg_confidence,
        executedRate=executed_rate,
        regretRate=regret_rate,
        weekTrend=week_trend,
    )


def _empty_week_trend() -> List[Dict[str, Any]]:
    """空数据时的近 7 天骨架（count 全 0）。"""
    today = date.today()
    return [
        {"date": (today - timedelta(days=i)).isoformat(), "count": 0}
        for i in range(6, -1, -1)
    ]
