"""天气服务（高德开放平台）。

使用高德天气查询 API：
  - 接口：由用户配置 weather_base_url
  - 文档：https://lbs.amap.com/api/webservice/guide/api/weatherinfo
  - 配额：个人开发者每日 10 万次免费
  - 鉴权：用户自配的高德 Key（weather_key）

未配置 weather_key 或调用失败时返回 mock 自然数据，与之前和风版本一致。
返回结构保持不变，便于上层无感切换：
  { isReal, source, city, weather, temperature, humidity, wind,
    air, time, season, sun, moonPhase, updateTime, forecast_24h }
"""

import random
from datetime import datetime
from typing import Any, Dict, Optional

import httpx

from config import get_effective_config, has_weather_config

_TIMEOUT = 8.0


def _get_period(now: datetime) -> str:
    h = now.hour
    if h < 6:
        return "黎明前"
    if h < 11:
        return "上午"
    if h < 13:
        return "正午"
    if h < 17:
        return "午后"
    if h < 19:
        return "黄昏"
    return "夜晚"


def _get_season(now: datetime) -> str:
    m = now.month
    if m < 3 or m == 12:
        return "冬"
    if m < 6:
        return "春"
    if m < 9:
        return "夏"
    return "秋"


def _get_sun(now: datetime, weather: str) -> str:
    h = now.hour
    if "雨" in weather:
        return "雨幕遮日"
    if "阴" in weather:
        return "天光暗淡"
    if "云" in weather:
        return "日光朦胧" if 6 <= h < 18 else "月隐云后"
    if 6 <= h < 18:
        if h < 12:
            return "太阳东升渐高"
        if h < 15:
            return "烈日当空"
        return "夕阳西斜"
    return "月明星稀"


def _get_moon_phase(now: datetime) -> str:
    """根据朔望月周期估算当前月相。"""
    reference = datetime(2000, 1, 6, 18, 14)
    day_in_cycle = ((now - reference).total_seconds() / 86400) % 29.53058867
    if day_in_cycle < 1:
        return "新月"
    if day_in_cycle < 7:
        return "娥眉月"
    if day_in_cycle < 10:
        return "上弦月"
    if day_in_cycle < 14:
        return "盈凸月"
    if day_in_cycle < 17:
        return "满月"
    if day_in_cycle < 21:
        return "亏凸月"
    if day_in_cycle < 24:
        return "下弦月"
    return "残月"


def _base_context(now: datetime) -> Dict[str, Any]:
    return {
        "date": now.strftime("%Y-%m-%d"),
        "time": _get_period(now),
        "season": _get_season(now),
        "moonPhase": _get_moon_phase(now),
    }


def _coalesce(*vals):
    for v in vals:
        if v not in (None, "", []):
            return v
    return ""


def _parse_amap_response(data: Any) -> Optional[Dict[str, Any]]:
    """解析高德天气响应。

    高德返回结构：
      {
        "status": "1",
        "count": "1",
        "lives": [{
          "province": "北京", "city": "北京市",
          "weather": "晴", "temperature": "23",
          "winddirection": "西北", "windpower": "3",
          "humidity": "45", "reporttime": "2026-06-29 14:32:18",
          "temperature_float": "23.0", "humidity_float": "45.0"
        }]
      }
    """
    if not isinstance(data, dict):
        return None
    # status=0 表示失败
    if str(data.get("status", "0")) != "1":
        return None
    lives = data.get("lives") or []
    if not lives or not isinstance(lives, list):
        return None
    live = lives[0]
    if not isinstance(live, dict):
        return None
    city = _coalesce(live.get("city"), live.get("province"))
    weather = _coalesce(live.get("weather"))
    temperature = _coalesce(live.get("temperature"), live.get("temperature_float"))
    humidity = _coalesce(live.get("humidity"), live.get("humidity_float"))
    wind_dir = _coalesce(live.get("winddirection"))
    wind_power = _coalesce(live.get("windpower"))
    # 高德风力单位是级
    wind = f"{wind_dir}风 {wind_power}级" if (wind_dir or wind_power) else "风向未知"
    update_time = _coalesce(live.get("reporttime"), live.get("updatetime"))
    return {
        "city": city or "当前位置",
        "weather": weather or "未知",
        "temperature": str(temperature) if temperature != "" else "",
        "humidity": str(humidity) if humidity != "" else "",
        "air": "",  # 高德实况接口不返回 AQI
        "wind": wind,
        "updateTime": str(update_time) if update_time != "" else "",
    }


def _parse_amap_forecast(data: Any) -> list[Dict[str, str]]:
    """把高德未来天气转换成自然模式可直接展示的短列表。"""
    if not isinstance(data, dict) or str(data.get("status", "0")) != "1":
        return []
    forecasts = data.get("forecasts") or []
    if not forecasts or not isinstance(forecasts, list):
        return []
    casts = forecasts[0].get("casts") or [] if isinstance(forecasts[0], dict) else []
    items = []
    for cast in casts[:3]:
        if not isinstance(cast, dict):
            continue
        day_weather = str(cast.get("dayweather") or "")
        night_weather = str(cast.get("nightweather") or "")
        weather = day_weather if not night_weather or day_weather == night_weather else f"{day_weather}转{night_weather}"
        items.append({
            "time": str(cast.get("date") or ""),
            "weather": weather,
            "temperature": str(cast.get("daytemp") or cast.get("nighttemp") or ""),
        })
    return items


def _weather_trend(forecast: list[Dict[str, str]]) -> str:
    return "；".join(
        " · ".join(part for part in (item.get("time", ""), item.get("weather", ""),
                                      f"{item.get('temperature')}℃" if item.get("temperature") else "") if part)
        for item in forecast[:2]
    )


def _mock_weather(now: datetime, language: str = "zh-CN") -> Dict[str, Any]:
    """未配置或调用失败时的降级自然数据。"""
    if language == "en":
        conditions = [
            {"weather": "Sunny", "wind": random.choice(["light southeast breeze", "gentle south wind", "cool west wind", "fresh north wind"])},
            {"weather": "Cloudy", "wind": random.choice(["light east wind", "soft south wind", "mild west wind", "thin north wind"])},
            {"weather": "Overcast", "wind": random.choice(["still", "cool east wind", "soft south wind", "chilly west wind"])},
            {"weather": "Drizzle", "wind": random.choice(["damp east wind", "cool south wind", "cold west wind", "wintry north wind"])},
        ]
        source, city = "Simulated nature data", "City not set"
    else:
        conditions = [
            {"weather": "晴朗", "wind": random.choice(["微风东南", "和风南来", "清风西拂", "凉风北至"])},
            {"weather": "多云", "wind": random.choice(["轻风东来", "徐风南至", "柔风西过", "细风北临"])},
            {"weather": "阴", "wind": random.choice(["静风无向", "微凉东风", "轻柔南风", "萧瑟西风"])},
            {"weather": "细雨", "wind": random.choice(["湿润东风", "凉意南风", "清冷西风", "寒意北风"])},
        ]
        source, city = "模拟自然数据", "未配置城市"
    c = random.choice(conditions)
    return {
        "isReal": False,
        "source": source,
        "city": city,
        "weather": c["weather"],
        "temperature": "",
        "humidity": "",
        "wind": c["wind"],
        "air": "",
        "time": _get_period(now),
        "season": _get_season(now),
        "sun": _get_sun(now, c["weather"]),
        "moonPhase": _get_moon_phase(now),
        "updateTime": "",
        "weatherStatus": "not_configured",
        "weatherStatusText": "未配置天气 Key" if language != "en" else "Weather key not configured",
        "alarms": [],
        "forecast_1h": [],
        "forecast_24h": [],
        "weatherTrend": "",
        "life_indices": {},
    }


def get_current_weather(config: Optional[Dict[str, Any]] = None,
                        language: str = "zh-CN") -> Dict[str, Any]:
    """获取当前天气。配置齐全且调用成功返回真实数据，否则返回 mock。

    config 为 None 时从 get_effective_config() 读取。
    """
    if config is None:
        config = get_effective_config()
    now = datetime.now()
    base = _base_context(now)

    if has_weather_config(config):
        # 高德 Key
        key = config.get("weather_key") or config.get("weather_appsecret")
        endpoint = config.get("weather_base_url")
        city = config.get("weather_city") or "北京"
        params = {
            "key": key,
            "city": city,
            "extensions": "base",  # base=实况, all=预报
        }
        try:
            forecast = []
            with httpx.Client(timeout=_TIMEOUT) as client:
                resp = client.get(endpoint, params=params)
                resp.raise_for_status()
                parsed = _parse_amap_response(resp.json())
                if parsed:
                    try:
                        forecast_resp = client.get(endpoint, params={**params, "extensions": "all"})
                        forecast_resp.raise_for_status()
                        forecast = _parse_amap_forecast(forecast_resp.json())
                    except Exception as forecast_error:
                        print(f"[weather] 高德预报调用失败: {type(forecast_error).__name__}")
            if parsed:
                weather_str = parsed["weather"]
                return {
                    "isReal": True,
                    "source": "amap",
                    "city": parsed["city"],
                    "weather": weather_str,
                    "temperature": parsed["temperature"],
                    "humidity": parsed["humidity"],
                    "wind": parsed["wind"],
                    "air": parsed["air"],
                    "time": base["time"],
                    "season": base["season"],
                    "date": base["date"],
                    "sun": _get_sun(now, weather_str),
                    "moonPhase": base["moonPhase"],
                    "updateTime": parsed["updateTime"],
                    "weatherStatus": "ok",
                    "weatherStatusText": "实时天气已更新",
                    "alarms": [],
                    "forecast_1h": [],
                    "forecast_24h": forecast,
                    "weatherTrend": _weather_trend(forecast),
                    "life_indices": {},
                }
        except Exception as e:
            # 不打印 Key；仅记录降级原因
            print(f"[weather] 高德接口调用失败，降级 mock: {type(e).__name__}")

    return {**_mock_weather(now, language=language), "date": base["date"]}
