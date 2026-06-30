"""天气服务（高德开放平台）。

使用高德天气查询 API：
  - 接口：https://restapi.amap.com/v3/weather/weatherInfo
  - 文档：https://lbs.amap.com/api/webservice/guide/api/weatherinfo
  - 配额：个人开发者每日 10 万次免费
  - 鉴权：用户自配的高德 Key（weather_key）

未配置 weather_key 或调用失败时返回 mock 自然数据，与之前和风版本一致。
返回结构保持不变，便于上层无感切换：
  { isReal, source, city, weather, temperature, humidity, wind,
    air, time, season, sun, updateTime }
"""

import random
from datetime import datetime
from typing import Any, Dict, Optional

import httpx

from config import get_effective_config, has_weather_config

# 高德天气查询 API
AMAP_WEATHER_ENDPOINT = "https://restapi.amap.com/v3/weather/weatherInfo"

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


def _base_context(now: datetime) -> Dict[str, Any]:
    return {
        "date": now.strftime("%Y-%m-%d"),
        "time": _get_period(now),
        "season": _get_season(now),
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
        "updateTime": "",
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
        city = config.get("weather_city") or "北京"
        params = {
            "key": key,
            "city": city,
            "extensions": "base",  # base=实况, all=预报
        }
        try:
            with httpx.Client(timeout=_TIMEOUT) as client:
                resp = client.get(AMAP_WEATHER_ENDPOINT, params=params)
                resp.raise_for_status()
            parsed = _parse_amap_response(resp.json())
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
                    "sun": _get_sun(now, weather_str),
                    "updateTime": parsed["updateTime"],
                }
        except Exception as e:
            # 不打印 Key；仅记录降级原因
            print(f"[weather] 高德接口调用失败，降级 mock: {type(e).__name__}")

    return {**_mock_weather(now, language=language), "date": base["date"]}
