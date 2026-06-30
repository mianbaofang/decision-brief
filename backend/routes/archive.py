"""GET /api/archive - 分页查询决策历史列表。

参数：page=1&pageSize=20
返回：{ ok, list, total, page, pageSize }
"""

from typing import Any, Dict

from fastapi import APIRouter

import db

router = APIRouter()


@router.get("/api/archive")
def get_archive(page: int = 1, pageSize: int = 20) -> Dict[str, Any]:
    """分页查询决策历史（按 createdAt 降序）。

    - page 从 1 开始；pageSize 默认 20
    - 无记录时返回空列表（不返回 mock 示例数据）
    """
    if page < 1:
        page = 1
    if pageSize < 1:
        pageSize = 20
    offset = (page - 1) * pageSize
    items = db.list_decisions(limit=pageSize, offset=offset)
    total = db.count_decisions()
    return {
        "ok": True,
        "list": items,
        "total": total,
        "page": page,
        "pageSize": pageSize,
    }
