"""TTS 路由：edge-tts 免费神经 TTS。

- GET /api/tts/voices  返回推荐音色列表（前端设置页用）
- GET /api/tts/speak?text=&voice=&rate=&pitch=  流式返回 MP3 音频

rate:  如 '+0%'、'+20%'、'-10%'
pitch: 如 '+0Hz'、'+5Hz'、'-5Hz'

ponytail: 音色列表为手写精选，升级路径：用 edge_tts.list_voices() 动态拉取并按语言过滤。
"""

from typing import Optional

import edge_tts
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse

router = APIRouter()

# 精选常用音色（中文+多语）
VOICES = [
    # 中文（简体）
    {"id": "zh-CN-XiaoxiaoNeural",    "lang": "zh-CN", "name": "晓晓",   "gender": "F", "desc": "温柔女声，新闻/日常"},
    {"id": "zh-CN-YunxiNeural",       "lang": "zh-CN", "name": "云希",   "gender": "M", "desc": "阳光男声，年轻感"},
    {"id": "zh-CN-YunjianNeural",     "lang": "zh-CN", "name": "云健",   "gender": "M", "desc": "低沉男声，故事感"},
    {"id": "zh-CN-YunyangNeural",     "lang": "zh-CN", "name": "云扬",   "gender": "M", "desc": "专业男声，新闻播报"},
    {"id": "zh-CN-XiaoyiNeural",      "lang": "zh-CN", "name": "晓伊",   "gender": "F", "desc": "清甜女声，少女感"},
    {"id": "zh-CN-YunxiaNeural",      "lang": "zh-CN", "name": "云夏",   "gender": "M", "desc": "少年男声，活力感"},
    {"id": "zh-CN-XiaomoNeural",      "lang": "zh-CN", "name": "晓墨",   "gender": "F", "desc": "知性女声，沉稳"},
    {"id": "zh-CN-XiaohanNeural",     "lang": "zh-CN", "name": "晓涵",   "gender": "F", "desc": "温暖女声"},
    {"id": "zh-CN-XiaomengNeural",    "lang": "zh-CN", "name": "晓梦",   "gender": "F", "desc": "萌系少女"},
    {"id": "zh-CN-XiaoshuangNeural",  "lang": "zh-CN", "name": "晓双",   "gender": "F", "desc": "童声"},
    # 粤语
    {"id": "zh-HK-HiuMaanNeural",     "lang": "yue",   "name": "曉曼",   "gender": "F", "desc": "粤语女声"},
    {"id": "zh-HK-WanLungNeural",     "lang": "yue",   "name": "雲龍",   "gender": "M", "desc": "粤语男声"},
    # 英文
    {"id": "en-US-AriaNeural",        "lang": "en",    "name": "Aria",   "gender": "F", "desc": "Female US"},
    {"id": "en-US-GuyNeural",         "lang": "en",    "name": "Guy",    "gender": "M", "desc": "Male US"},
    {"id": "en-US-JennyNeural",       "lang": "en",    "name": "Jenny",  "gender": "F", "desc": "Female US (friendly)"},
    # 日语
    {"id": "ja-JP-NanamiNeural",      "lang": "ja",    "name": "七海",   "gender": "F", "desc": "女声"},
    {"id": "ja-JP-KeitaNeural",       "lang": "ja",    "name": "圭太",   "gender": "M", "desc": "男声"},
    # 法语
    {"id": "fr-FR-DeniseNeural",      "lang": "fr",    "name": "Denise", "gender": "F", "desc": "Female FR"},
    {"id": "fr-FR-HenriNeural",       "lang": "fr",    "name": "Henri",  "gender": "M", "desc": "Male FR"},
    # 西语
    {"id": "es-ES-ElviraNeural",      "lang": "es",    "name": "Elvira", "gender": "F", "desc": "Female ES"},
    {"id": "es-ES-AlvaroNeural",      "lang": "es",    "name": "Alvaro", "gender": "M", "desc": "Male ES"},
]

# 语言到默认音色映射
DEFAULT_VOICE = {
    "zh-CN": "zh-CN-XiaoxiaoNeural",
    "yue":   "zh-HK-HiuMaanNeural",
    "en":    "en-US-AriaNeural",
    "fr":    "fr-FR-DeniseNeural",
    "ja":    "ja-JP-NanamiNeural",
    "es":    "es-ES-ElviraNeural",
}


@router.get("/api/tts/voices")
def list_voices(lang: Optional[str] = None) -> dict:
    """返回可选音色列表，可按 lang 过滤。"""
    items = VOICES
    if lang:
        items = [v for v in VOICES if v["lang"] == lang]
    return {"voices": items, "defaults": DEFAULT_VOICE}


def _normalise_rate(rate: float) -> str:
    """把 0.5~1.5 的倍率转成 edge-tts 百分比字符串。"""
    pct = int(round((float(rate) - 1.0) * 100))
    pct = max(-50, min(100, pct))
    return f"{pct:+d}%"


def _normalise_pitch(pitch: float) -> str:
    """把 0.5~1.5 的倍率转成 edge-tts Hz 字符串。"""
    # 以 0Hz 为基准，倍率 1.05 约等于 +5Hz
    hz = int(round((float(pitch) - 1.0) * 100))
    hz = max(-50, min(50, hz))
    return f"{hz:+d}Hz"


async def _audio_generator(text: str, voice: str, rate: str, pitch: str):
    """异步生成器：把 edge-tts 的 audio chunk 直接流式 yield。"""
    communicate = edge_tts.Communicate(text=text, voice=voice, rate=rate, pitch=pitch)
    async for chunk in communicate.stream():
        if chunk["type"] == "audio":
            yield chunk["data"]


@router.get("/api/tts/speak")
async def speak(
    text: str = Query(..., min_length=1, max_length=5000),
    voice: Optional[str] = None,
    rate: float = Query(0.95, ge=0.5, le=2.0),
    pitch: float = Query(1.05, ge=0.5, le=2.0),
):
    """流式返回 TTS 合成的 MP3 音频。

    voice 不指定时默认晓晓（zh-CN-XiaoxiaoNeural）。
    """
    if not text.strip():
        raise HTTPException(status_code=400, detail="text 不能为空")
    voice_id = voice or DEFAULT_VOICE["zh-CN"]
    # 校验 voice 是否在白名单（edge-tts 自身也会校验，这里加一道防呆）
    if not any(v["id"] == voice_id for v in VOICES):
        voice_id = DEFAULT_VOICE["zh-CN"]
    rate_str = _normalise_rate(rate)
    pitch_str = _normalise_pitch(pitch)

    filename = "tts.mp3"
    return StreamingResponse(
        _audio_generator(text, voice_id, rate_str, pitch_str),
        media_type="audio/mpeg",
        headers={
            "Content-Disposition": f"inline; filename={filename}",
            "Cache-Control": "no-cache",
        },
    )
