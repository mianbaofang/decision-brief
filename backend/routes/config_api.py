"""配置管理路由（/api/config + /api/preferences）。

- GET  /api/config        读取脱敏后的 LLM/天气配置
- POST /api/config        保存 API Key 配置到 SQLite（空字段跳过）
- DELETE /api/config      清除所有 API Key 配置
- GET  /api/preferences   读取用户偏好
- POST /api/preferences   保存用户偏好

约束：apiKey/weather_key 永不回传明文，仅返回是否已配置。

天气服务从 v0.7.0 起切换到高德开放平台：weather.hasKey 替代 hasAppid/hasAppsecret。
"""

from typing import Any, Dict

from fastapi import APIRouter

import config as config_mod
import db
from models.schemas import ConfigUpdate, PreferencesUpdate

router = APIRouter()


def _to_config_response(masked: Dict[str, Any]) -> Dict[str, Any]:
    """把 get_masked_config() 的扁平结构转为 ConfigResponse 形状。"""
    has_key = bool(masked.get("llm_api_key"))
    # 高德只需一个 weather_key（兼容旧 weather_appsecret）
    has_weather_key = bool(masked.get("weather_key") or masked.get("weather_appsecret"))
    return {
        "llm": {
            "model": masked.get("llm_model", ""),
            "baseUrl": masked.get("llm_base_url", ""),
            "hasKey": has_key,
        },
        "weather": {
            "city": masked.get("weather_city", ""),
            "hasKey": has_weather_key,
            # 兼容字段（旧前端可能仍读 hasAppsecret）
            "hasAppsecret": has_weather_key,
        },
        "hasLlm": config_mod.has_llm_config(masked),
        "hasWeather": config_mod.has_weather_config(masked),
    }


# ─── /api/config ───────────────────────────────────────────────


@router.get("/api/config")
def get_config() -> Dict[str, Any]:
    """返回脱敏后的 LLM/天气配置 + hasLlm/hasWeather。"""
    masked = config_mod.get_masked_config()
    return _to_config_response(masked)


@router.post("/api/config")
def save_config(body: ConfigUpdate) -> Dict[str, Any]:
    """保存 API Key 配置到 SQLite。空字符串或 None 的字段跳过。"""
    payload = body.model_dump(exclude_none=True)
    # 空字符串也跳过（避免覆盖已有值）
    payload = {k: v for k, v in payload.items() if v}
    masked = config_mod.save_api_keys_to_db(payload)
    return _to_config_response(masked)


@router.delete("/api/config")
def clear_config() -> Dict[str, Any]:
    """清除所有 API Key 配置（危险操作）。"""
    for key in config_mod.CONFIG_KEYS:
        db.delete_config_value(key)
    return {"ok": True}


# ─── /api/preferences ─────────────────────────────────────────


@router.get("/api/preferences")
def get_preferences() -> Dict[str, Any]:
    """返回用户偏好（合并默认值 + SQLite），扁平结构便于前端直接消费。"""
    return config_mod.get_preferences()


@router.post("/api/preferences")
def save_preferences(body: PreferencesUpdate) -> Dict[str, Any]:
    """保存用户偏好到 SQLite，返回合并后的完整偏好。"""
    payload = body.model_dump(exclude_none=True)
    return config_mod.save_preferences(payload)
