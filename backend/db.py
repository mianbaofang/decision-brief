"""SQLite 持久化层。

替代 HTML 版本的 IndexedDB，提供 decisions 和 config 两张表。
单文件 SQLite，无需服务器，适合本地单机工具。

表结构：
  - decisions: 决策记录（id/question/mode/result/brief/createdAt/executed/regret/dialogueHistory）
  - config: 配置项（key/value），存储 LLM/天气 API Key 和用户偏好
"""

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

# SQLite 数据库文件路径（与 backend/ 同级，gitignore 已忽略 *.db）
DB_PATH = Path(__file__).parent / "choice.db"


def get_conn() -> sqlite3.Connection:
    """获取 SQLite 连接。每次调用创建新连接，避免线程问题。"""
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db() -> None:
    """初始化数据库表。应用启动时调用一次。"""
    with get_conn() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS decisions (
                id TEXT PRIMARY KEY,
                question TEXT NOT NULL,
                mode TEXT NOT NULL,
                result TEXT NOT NULL,
                brief TEXT,
                created_at TEXT NOT NULL,
                executed INTEGER DEFAULT 0,
                regret INTEGER DEFAULT 0,
                dialogue_history TEXT
            );
            CREATE INDEX IF NOT EXISTS idx_decisions_created_at ON decisions(created_at);
            CREATE INDEX IF NOT EXISTS idx_decisions_mode ON decisions(mode);

            CREATE TABLE IF NOT EXISTS config (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );
            """
        )


# ─── decisions 表操作 ───────────────────────────────────────────


def save_decision(dec: dict) -> dict:
    """新增/更新一条决策记录。返回传入的 dec（补齐默认值）。"""
    if not dec.get("id"):
        dec["id"] = f"dec_{datetime.now().strftime('%Y%m%d%H%M%S')}_{_random_suffix()}"
    if not dec.get("createdAt"):
        dec["createdAt"] = datetime.now().isoformat()

    with get_conn() as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO decisions
                (id, question, mode, result, brief, created_at, executed, regret, dialogue_history)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                dec["id"],
                dec["question"],
                dec["mode"],
                json.dumps(dec.get("result", {}), ensure_ascii=False),
                json.dumps(dec.get("brief"), ensure_ascii=False) if dec.get("brief") else None,
                dec["createdAt"],
                1 if dec.get("executed") else 0,
                1 if dec.get("regret") else 0,
                json.dumps(dec.get("dialogueHistory"), ensure_ascii=False) if dec.get("dialogueHistory") else None,
            ),
        )
    return dec


def get_decision(decision_id: str) -> Optional[dict]:
    """按 id 查询单条决策记录。"""
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM decisions WHERE id = ?", (decision_id,)).fetchone()
    return _row_to_decision(row) if row else None


def list_decisions(limit: int = 100, offset: int = 0) -> list[dict]:
    """查询决策历史列表（按 createdAt 降序）。"""
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM decisions ORDER BY created_at DESC LIMIT ? OFFSET ?",
            (limit, offset),
        ).fetchall()
    return [_row_to_decision(r) for r in rows]


def update_decision(decision_id: str, patches: dict) -> Optional[dict]:
    """部分更新决策记录（仅 executed/regret/dialogueHistory 可更新）。"""
    allowed = {"executed", "regret", "dialogueHistory"}
    updates = {k: v for k, v in patches.items() if k in allowed}
    if not updates:
        return get_decision(decision_id)

    sets = []
    vals = []
    if "executed" in updates:
        sets.append("executed = ?")
        vals.append(1 if updates["executed"] else 0)
    if "regret" in updates:
        sets.append("regret = ?")
        vals.append(1 if updates["regret"] else 0)
    if "dialogueHistory" in updates:
        sets.append("dialogue_history = ?")
        vals.append(json.dumps(updates["dialogueHistory"], ensure_ascii=False))

    vals.append(decision_id)
    with get_conn() as conn:
        conn.execute(f"UPDATE decisions SET {', '.join(sets)} WHERE id = ?", vals)
    return get_decision(decision_id)


def delete_decision(decision_id: str) -> bool:
    """删除一条决策记录。返回是否删除成功。"""
    with get_conn() as conn:
        cur = conn.execute("DELETE FROM decisions WHERE id = ?", (decision_id,))
        return cur.rowcount > 0


def count_decisions() -> int:
    """决策总数。"""
    with get_conn() as conn:
        row = conn.execute("SELECT COUNT(*) AS n FROM decisions").fetchone()
    return row["n"]


# ─── config 表操作 ──────────────────────────────────────────────


def get_config_value(key: str, default: Any = None) -> Any:
    """读取单个配置项。"""
    with get_conn() as conn:
        row = conn.execute("SELECT value FROM config WHERE key = ?", (key,)).fetchone()
    if not row:
        return default
    try:
        return json.loads(row["value"])
    except (json.JSONDecodeError, TypeError):
        return default


def set_config_value(key: str, value: Any) -> None:
    """写入单个配置项（upsert）。"""
    with get_conn() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO config (key, value) VALUES (?, ?)",
            (key, json.dumps(value, ensure_ascii=False)),
        )


def get_all_config() -> dict:
    """读取全部配置项，返回 {key: value} 字典。"""
    with get_conn() as conn:
        rows = conn.execute("SELECT key, value FROM config").fetchall()
    out = {}
    for r in rows:
        try:
            out[r["key"]] = json.loads(r["value"])
        except (json.JSONDecodeError, TypeError):
            out[r["key"]] = r["value"]
    return out


def delete_config_value(key: str) -> None:
    """删除单个配置项。"""
    with get_conn() as conn:
        conn.execute("DELETE FROM config WHERE key = ?", (key,))


# ─── 辅助函数 ───────────────────────────────────────────────────


def _row_to_decision(row: sqlite3.Row) -> dict:
    """把数据库行转换为 Decision dict。"""
    out = {
        "id": row["id"],
        "question": row["question"],
        "mode": row["mode"],
        "result": json.loads(row["result"]) if row["result"] else {},
        "createdAt": row["created_at"],
        "executed": bool(row["executed"]),
        "regret": bool(row["regret"]),
    }
    if row["brief"]:
        out["brief"] = json.loads(row["brief"])
    if row["dialogue_history"]:
        out["dialogueHistory"] = json.loads(row["dialogue_history"])
    return out


def _random_suffix() -> str:
    """6 位随机后缀（base36）。"""
    import random
    import string
    return "".join(random.choices(string.ascii_lowercase + string.digits, k=6))
