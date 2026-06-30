"""pytest 共享 fixtures。

- 把 backend/ 加入 sys.path（与 main.py 启动脚本一致）
- 每个测试自动隔离 DB_PATH 与 CONFIG_FILE_PATH，避免污染真实 choice.db 与 ~/.choice/config.json
"""

import sys
from pathlib import Path

# 把 backend/ 目录加入 sys.path（与 backend/main.py 第 22 行的做法一致）
BACKEND_DIR = Path(__file__).resolve().parent.parent / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

import pytest  # noqa: E402

import config as config_mod  # noqa: E402
import db  # noqa: E402


@pytest.fixture(autouse=True)
def isolate_paths(tmp_path, monkeypatch):
    """每个测试用独立临时目录的 choice.db 与 config.json，跑前 init_db。"""
    monkeypatch.setattr(db, "DB_PATH", tmp_path / "test_choice.db")
    monkeypatch.setattr(config_mod, "CONFIG_FILE_PATH", tmp_path / "config.json")
    db.init_db()
    yield
