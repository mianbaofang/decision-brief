"""决策记录 CRUD 路由。

- POST   /api/decision        保存（新增/覆盖）
- GET    /api/decision/{id}   查询单条
- PATCH  /api/decision/{id}   部分更新（executed/regret/dialogueHistory）
- DELETE /api/decision/{id}   删除

全部走 SQLite 持久化层（db.py），不再使用内存 _DECISIONS。
"""

from typing import Any, Dict

from fastapi import APIRouter, HTTPException

import db
from models.schemas import DecisionPatch, DecisionSave

router = APIRouter()


@router.post("/api/decision")
def save_decision(body: DecisionSave) -> Dict[str, Any]:
    """保存一条决策记录，自动补齐 id 与 createdAt。返回保存后的 dict。"""
    payload = body.model_dump(exclude_none=True)
    saved = db.save_decision(payload)
    return saved


@router.get("/api/decision/{decision_id}")
def get_decision(decision_id: str) -> Dict[str, Any]:
    """按 id 查询单条决策记录。不存在返回 404。"""
    dec = db.get_decision(decision_id)
    if not dec:
        raise HTTPException(status_code=404, detail="decision not found")
    return dec


@router.patch("/api/decision/{decision_id}")
def update_decision(decision_id: str, body: DecisionPatch) -> Dict[str, Any]:
    """更新 executed/regret/dialogueHistory。返回更新后的 dict。"""
    patches = body.model_dump(exclude_none=True)
    updated = db.update_decision(decision_id, patches)
    if not updated:
        raise HTTPException(status_code=404, detail="decision not found")
    return updated


@router.delete("/api/decision/{decision_id}")
def delete_decision(decision_id: str) -> Dict[str, Any]:
    """删除一条决策记录。不存在返回 404。"""
    ok = db.delete_decision(decision_id)
    if not ok:
        raise HTTPException(status_code=404, detail="decision not found")
    return {"ok": True}
