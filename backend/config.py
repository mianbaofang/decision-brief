"""配置管理（三层优先级）。

按优先级从高到低：
  1. 环境变量：CHOICE_LLM_API_KEY / CHOICE_LLM_MODEL / CHOICE_LLM_BASE_URL
              CHOICE_WEATHER_KEY / CHOICE_WEATHER_CITY
  2. SQLite config 表（UI 设置页写入，落盘到 choice.db）
  3. ~/.choice/config.json（CLI config --save 写入，权限 0600，兼容旧版）

约束：
  - API Key 不可写入日志。
  - 回显配置时对 llm_api_key / weather_key 脱敏为 ***已配置***。
  - ponytail: SQLite 中 API Key 明文存储，升级路径为 AES-256-GCM 加密。

天气服务从 v0.7.0 起从和风天气切换到高德开放平台，配置字段：
  - 主字段：weather_key（高德 Key） + weather_city
  - 兼容字段：weather_appsecret（旧版和风 Key，读取时自动当作 weather_key）
"""

import json
import os
from pathlib import Path
from typing import Any, Dict

# 配置文件路径（与 CLI 共用）
CONFIG_FILE_PATH = Path.home() / ".choice" / "config.json"

# 配置键名
CONFIG_KEYS = (
    "llm_api_key",
    "llm_model",
    "llm_base_url",
    "weather_key",       # 主字段（高德 Key）
    "weather_appsecret", # 兼容字段（旧和风 Key，自动映射到 weather_key）
    "weather_city",
)

# 环境变量映射
ENV_KEY_MAP = {
    "llm_api_key": "CHOICE_LLM_API_KEY",
    "llm_model": "CHOICE_LLM_MODEL",
    "llm_base_url": "CHOICE_LLM_BASE_URL",
    "weather_key": "CHOICE_WEATHER_KEY",
    "weather_appsecret": "CHOICE_WEATHER_APPSECRET",  # 兼容旧变量名
    "weather_city": "CHOICE_WEATHER_CITY",
}

# 敏感键（回显时脱敏）
SENSITIVE_KEYS = ("llm_api_key", "weather_key", "weather_appsecret")

# 内置高德天气 Key（日调用 10 万次免费额度，开箱即用）
BUILTIN_WEATHER_KEY = "9f0126c5a8c28ea743c21d69e3bb35b4"


def _read_config_file() -> Dict[str, Any]:
    """从 ~/.choice/config.json 读取（不存在或解析失败返回空 dict）。"""
    if not CONFIG_FILE_PATH.exists():
        return {}
    try:
        with open(CONFIG_FILE_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except (json.JSONDecodeError, OSError):
        return {}


def _save_config_file(partial: Dict[str, Any]) -> Dict[str, Any]:
    """合并写入 ~/.choice/config.json（权限 0600）。"""
    CONFIG_FILE_PATH.parent.mkdir(parents=True, exist_ok=True)
    merged = dict(_read_config_file())
    for k, v in partial.items():
        if v is not None:
            merged[k] = v
    with open(CONFIG_FILE_PATH, "w", encoding="utf-8") as f:
        json.dump(merged, f, ensure_ascii=False, indent=2)
    try:
        os.chmod(CONFIG_FILE_PATH, 0o600)
    except OSError:
        pass  # Windows best-effort
    return merged


def get_effective_config() -> Dict[str, Any]:
    """返回当前生效的 API Key 配置（环境变量 > SQLite > config.json）。

    注意：返回值含 api_key，调用方不得写入日志。
    """
    # 从 SQLite 读取（延迟导入避免循环依赖）
    from db import get_all_config

    cfg: Dict[str, Any] = {k: "" for k in CONFIG_KEYS}

    # 层 3：config.json
    file_cfg = _read_config_file()
    for k in CONFIG_KEYS:
        if file_cfg.get(k):
            cfg[k] = file_cfg[k]

    # 层 2：SQLite config 表（覆盖 config.json）
    db_cfg = get_all_config()
    for k in CONFIG_KEYS:
        if db_cfg.get(k):
            cfg[k] = db_cfg[k]

    # 层 1：环境变量（最高优先级）
    for k, env in ENV_KEY_MAP.items():
        val = os.environ.get(env)
        if val:
            cfg[k] = val

    # 内置兜底：天气 Key 未配置时使用内置 Key（10 万次/日免费额度）
    if not cfg.get("weather_key"):
        cfg["weather_key"] = BUILTIN_WEATHER_KEY

    return cfg


def get_masked_config() -> Dict[str, Any]:
    """返回脱敏后的配置（用于 UI 显示和 CLI 回显）。"""
    cfg = get_effective_config()
    for k in SENSITIVE_KEYS:
        if cfg.get(k):
            cfg[k] = "***已配置***"
    return cfg


def save_api_keys_to_db(config: Dict[str, Any]) -> Dict[str, Any]:
    """把 API Key 配置保存到 SQLite config 表（UI 设置页用）。

    值为 None 或空字符串的键会被跳过。
    """
    from db import set_config_value

    for k in CONFIG_KEYS:
        val = config.get(k)
        if val:
            set_config_value(k, val)
    return get_masked_config()


def save_api_keys_to_file(config: Dict[str, Any]) -> Dict[str, Any]:
    """把 API Key 配置保存到 ~/.choice/config.json（CLI config --save 用）。"""
    partial = {k: v for k, v in config.items() if k in CONFIG_KEYS and v is not None}
    merged = _save_config_file(partial)
    masked = dict(merged)
    for k in SENSITIVE_KEYS:
        if masked.get(k):
            masked[k] = "***已配置***"
    return masked


def has_llm_config(config: Dict[str, Any] = None) -> bool:
    """判断是否具备真实调用 LLM 的最小条件。"""
    cfg = config or get_effective_config()
    return bool(cfg.get("llm_api_key") and cfg.get("llm_base_url") and cfg.get("llm_model"))


def has_weather_config(config: Dict[str, Any] = None) -> bool:
    """判断是否具备真实调用天气 API 的最小条件。

    高德天气 API 只需 weather_key（city 可选，未配置时默认北京）。
    兼容旧版：weather_appsecret 也会被当作 key 使用。
    """
    cfg = config or get_effective_config()
    return bool(cfg.get("weather_key") or cfg.get("weather_appsecret"))


# ─── 用户偏好（preferences）─────────────────────────────────────

PREF_KEYS = (
    "language",        # 'zh-CN' / 'yue' / 'en' / 'fr' / 'ja' / 'es'
    "default_mode",    # 'auto' / 'rational' / 'random' / 'nature' / 'dialogue' / 'fengshui'
    "theme",           # 'light' / 'dark' / 'auto'
    "logo",            # Logo id
    "auto_speak",      # bool
    "tts_rate",        # float 0.5-1.5
    "tts_pitch",       # float 0.5-1.5
    "tts_voice_uri",   # string
    "values",          # {efficiency, risk, growth, relationship} 0-100
    "demo_mode",       # bool: 无 API Key 时是否使用 mock 演示数据
)

DEFAULT_PREFS: Dict[str, Any] = {
    "language": "zh-CN",
    "default_mode": "auto",
    "theme": "auto",
    "logo": "tree1",
    "auto_speak": True,
    "tts_rate": 0.95,
    "tts_pitch": 1.05,
    "tts_voice_uri": "zh-CN-XiaoxiaoNeural",
    "values": {"efficiency": 60, "risk": 50, "growth": 70, "relationship": 55},
    "demo_mode": False,
}


def get_preferences() -> Dict[str, Any]:
    """读取用户偏好（合并默认值 + SQLite）。空字符串值视为未设置，回退默认。"""
    from db import get_config_value

    prefs = dict(DEFAULT_PREFS)
    stored = get_config_value("preferences", {})
    if isinstance(stored, dict):
        for k, v in stored.items():
            if v == "" and k in DEFAULT_PREFS and DEFAULT_PREFS[k]:
                continue
            prefs[k] = v
    return prefs


def save_preferences(prefs: Dict[str, Any]) -> Dict[str, Any]:
    """保存用户偏用到 SQLite。"""
    from db import set_config_value

    current = get_preferences()
    current.update({k: v for k, v in prefs.items() if k in PREF_KEYS})
    set_config_value("preferences", current)
    return current
