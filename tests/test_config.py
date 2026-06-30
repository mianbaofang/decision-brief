"""配置管理（config.py）测试。

覆盖三层优先级（env > db > file）、脱敏、has_llm_config/has_weather_config、
save_api_keys_to_db、preferences。
"""

import os

import config as config_mod
import db


# ─── 三层优先级 ──────────────────────────────────────────────


def test_get_effective_config_layer_priority_env_over_db_over_file(monkeypatch):
    """环境变量 > SQLite > config.json：三层都设值时环境变量胜出。"""
    # 层 3：config.json
    config_mod._save_config_file({"llm_api_key": "from-file", "llm_model": "gpt-file"})

    # 层 2：SQLite
    db.set_config_value("llm_api_key", "from-db")
    db.set_config_value("llm_model", "gpt-db")

    # 层 1：环境变量
    monkeypatch.setenv("CHOICE_LLM_API_KEY", "from-env")

    cfg = config_mod.get_effective_config()
    assert cfg["llm_api_key"] == "from-env"  # 环境变量胜出
    assert cfg["llm_model"] == "gpt-db"  # 数据库覆盖文件


def test_get_effective_config_db_over_file(monkeypatch):
    """无环境变量时，SQLite 覆盖 config.json。"""
    # 清理可能的环境变量
    for env in ("CHOICE_LLM_API_KEY", "CHOICE_LLM_MODEL", "CHOICE_LLM_BASE_URL"):
        monkeypatch.delenv(env, raising=False)

    config_mod._save_config_file({"llm_api_key": "from-file"})
    db.set_config_value("llm_api_key", "from-db")

    cfg = config_mod.get_effective_config()
    assert cfg["llm_api_key"] == "from-db"


def test_get_effective_config_file_fallback(monkeypatch):
    """无环境变量、无 SQLite 时，回落到 config.json。"""
    for env in ("CHOICE_LLM_API_KEY", "CHOICE_LLM_MODEL", "CHOICE_LLM_BASE_URL"):
        monkeypatch.delenv(env, raising=False)

    config_mod._save_config_file({"llm_api_key": "from-file-only"})

    cfg = config_mod.get_effective_config()
    assert cfg["llm_api_key"] == "from-file-only"


def test_get_effective_config_default_empty(monkeypatch):
    """三层都没有时，所有键为空字符串。"""
    for env in list(config_mod.ENV_KEY_MAP.values()):
        monkeypatch.delenv(env, raising=False)

    cfg = config_mod.get_effective_config()
    for key in config_mod.CONFIG_KEYS:
        assert cfg[key] == ""


# ─── 脱敏 ────────────────────────────────────────────────────


def test_get_masked_config_masks_sensitive_fields(monkeypatch):
    """llm_api_key / weather_key / weather_appsecret 脱敏为 ***已配置***，其它字段保留。"""
    for env in list(config_mod.ENV_KEY_MAP.values()):
        monkeypatch.delenv(env, raising=False)

    db.set_config_value("llm_api_key", "sk-real-secret")
    db.set_config_value("weather_key", "amap-real-key")
    db.set_config_value("llm_model", "gpt-4o-mini")
    db.set_config_value("weather_city", "北京")

    masked = config_mod.get_masked_config()
    assert masked["llm_api_key"] == "***已配置***"
    assert masked["weather_key"] == "***已配置***"
    # 非敏感字段不脱敏
    assert masked["llm_model"] == "gpt-4o-mini"
    assert masked["weather_city"] == "北京"


def test_get_masked_config_empty_when_not_set(monkeypatch):
    """未配置的敏感字段保持空字符串（不脱敏为 ***已配置***）。"""
    for env in list(config_mod.ENV_KEY_MAP.values()):
        monkeypatch.delenv(env, raising=False)

    masked = config_mod.get_masked_config()
    assert masked["llm_api_key"] == ""
    assert masked["weather_key"] == ""
    assert masked["weather_appsecret"] == ""


# ─── has_llm_config / has_weather_config ────────────────────


def test_has_llm_config_requires_all_three(monkeypatch):
    """需要 api_key + base_url + model 三个都有才算 True。"""
    for env in list(config_mod.ENV_KEY_MAP.values()):
        monkeypatch.delenv(env, raising=False)

    assert config_mod.has_llm_config() is False

    db.set_config_value("llm_api_key", "sk-1")
    assert config_mod.has_llm_config() is False  # 还缺 base_url 和 model

    db.set_config_value("llm_base_url", "https://api.openai.com/v1")
    assert config_mod.has_llm_config() is False  # 还缺 model

    db.set_config_value("llm_model", "gpt-4o-mini")
    assert config_mod.has_llm_config() is True


def test_has_weather_config_requires_appid_and_appsecret(monkeypatch):
    """需要 appid + appsecret 两个都有才算 True。"""
    for env in list(config_mod.ENV_KEY_MAP.values()):
        monkeypatch.delenv(env, raising=False)

    assert config_mod.has_weather_config() is False

    db.set_config_value("weather_appid", "appid-1")
    assert config_mod.has_weather_config() is False

    db.set_config_value("weather_appsecret", "secret-1")
    assert config_mod.has_weather_config() is True


def test_has_llm_config_env_overrides(monkeypatch):
    """环境变量也参与判定。"""
    for env in list(config_mod.ENV_KEY_MAP.values()):
        monkeypatch.delenv(env, raising=False)
    monkeypatch.setenv("CHOICE_LLM_API_KEY", "env-key")
    monkeypatch.setenv("CHOICE_LLM_BASE_URL", "https://api.openai.com/v1")
    monkeypatch.setenv("CHOICE_LLM_MODEL", "gpt-4o-mini")

    assert config_mod.has_llm_config() is True


# ─── save_api_keys_to_db ────────────────────────────────────


def test_save_api_keys_to_db_persists_to_sqlite(monkeypatch):
    """保存到 SQLite config 表，且空字段跳过，返回脱敏结果。"""
    for env in list(config_mod.ENV_KEY_MAP.values()):
        monkeypatch.delenv(env, raising=False)

    masked = config_mod.save_api_keys_to_db(
        {
            "llm_api_key": "sk-persist",
            "llm_model": "gpt-4o-mini",
            "llm_base_url": "https://api.openai.com/v1",
            "weather_appid": "",  # 空字符串应被跳过
            "weather_appsecret": None,  # None 应被跳过
        }
    )

    # 脱敏返回
    assert masked["llm_api_key"] == "***已配置***"
    assert masked["llm_model"] == "gpt-4o-mini"

    # 实际落库
    assert db.get_config_value("llm_api_key") == "sk-persist"
    assert db.get_config_value("llm_model") == "gpt-4o-mini"
    assert db.get_config_value("llm_base_url") == "https://api.openai.com/v1"
    # 空字段未落库
    assert db.get_config_value("weather_appid", default="<missing>") == "<missing>"


# ─── preferences ────────────────────────────────────────────


def test_get_preferences_returns_defaults_when_empty():
    """未保存过偏好时，返回完整默认值。"""
    prefs = config_mod.get_preferences()
    assert prefs["language"] == "zh-CN"
    assert prefs["default_mode"] == "auto"
    assert prefs["theme"] == "auto"
    assert prefs["auto_speak"] is True
    assert prefs["tts_rate"] == 0.95
    assert prefs["tts_pitch"] == 1.05
    assert prefs["values"]["efficiency"] == 60
    assert prefs["values"]["risk"] == 50


def test_save_preferences_merges_with_defaults():
    """save_preferences 只覆盖传入的字段，其它字段保留默认值。"""
    saved = config_mod.save_preferences({"language": "yue", "theme": "dark"})
    assert saved["language"] == "yue"
    assert saved["theme"] == "dark"
    # 其它字段仍是默认值
    assert saved["default_mode"] == "auto"
    assert saved["auto_speak"] is True

    # 再次 get 应能拿到刚保存的值
    prefs = config_mod.get_preferences()
    assert prefs["language"] == "yue"
    assert prefs["theme"] == "dark"


def test_save_preferences_ignores_unknown_keys():
    """未知键名被忽略，不写入。"""
    saved = config_mod.save_preferences({"language": "en", "unknown_key": "should-be-ignored"})
    assert "unknown_key" not in saved
    assert saved["language"] == "en"
