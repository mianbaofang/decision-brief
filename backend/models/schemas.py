"""别纠结后端 Pydantic 模型。

对齐 HTML 版本的数据结构，支持 6 模式 ModeResult 联合类型、
Decision 完整字段（executed/regret/dialogueHistory）、Stats 增强（executedRate/regretRate/weekTrend）。
"""

from datetime import datetime
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field


# ─── 决策简报 ───────────────────────────────────────────────────


class Brief(BaseModel):
    """决策简报 - AI 返回的结构化决策结果（非 nature 模式）。"""

    summary: str = Field(..., description="核心结论")
    confidence: int = Field(..., ge=0, le=100, description="信心值 0-100")
    perspectives: List[str] = Field(default_factory=list, description="多角度分析")
    nextSteps: List[str] = Field(default_factory=list, description="下一步建议")
    risks: List[str] = Field(default_factory=list, description="风险提示")
    source: Optional[str] = Field(default=None, description="数据来源：real / mock")


# ─── 6 模式 ModeResult ─────────────────────────────────────────


class RationalResult(BaseModel):
    """理性分析模式结果。"""

    type: str = Field(default="rational")
    pros: List[str] = Field(default_factory=list, description="利")
    cons: List[str] = Field(default_factory=list, description="弊")
    conclusion: str = Field(default="", description="结论")
    score: Optional[Dict[str, Any]] = Field(default=None, description="评分")


class RandomResult(BaseModel):
    """天意随机模式结果。"""

    type: str = Field(default="random")
    options: List[str] = Field(default_factory=list, description="6 个候选项")
    wheelResult: Optional[str] = Field(default=None, description="抽中结果")
    reason: Optional[str] = Field(default=None)


class NatureResult(BaseModel):
    """自然启示模式结果。"""

    type: str = Field(default="nature")
    time: str = ""
    season: str = ""
    weather: str = ""
    sun: Optional[str] = ""
    wind: str = ""
    source: str = ""
    isReal: bool = False
    signal: str = ""
    poem: str = ""
    suggestion: str = ""
    city: Optional[str] = ""
    temperature: Optional[str] = ""
    humidity: Optional[str] = ""
    air: Optional[str] = ""
    signals: Optional[Dict[str, Any]] = None


class DialogueResult(BaseModel):
    """对话引导模式结果。"""

    type: str = Field(default="dialogue")
    question: str = ""
    options: List[str] = Field(default_factory=list)


class FengshuiResult(BaseModel):
    """风水玄学模式结果。"""

    type: str = Field(default="fengshui")
    needBirth: bool = False
    question: str = ""
    bazi: str = ""
    wuxing: str = ""
    element: str = ""
    analysis: str = ""
    suggestion: str = ""
    baziAudit: str = ""


# ─── chat 接口 ─────────────────────────────────────────────────


class ChatRequest(BaseModel):
    """/api/chat 入参。

    天气服务从 v0.7.0 起切换到高德开放平台：
      - weatherKey（高德 Key）是主字段
      - weatherAppsecret 兼容旧版（自动当作 weatherKey 处理）
    """

    question: str = Field(..., description="用户的问题或纠结点")
    mode: Literal["auto", "rational", "random", "nature", "dialogue", "fengshui"] = Field(
        default="auto", description="决策模式"
    )
    # LLM/天气配置临时覆盖（可选，优先级高于环境变量和配置文件）
    apiKey: Optional[str] = Field(default=None)
    llmModel: Optional[str] = Field(default=None)
    llmBaseUrl: Optional[str] = Field(default=None)
    weatherKey: Optional[str] = Field(default=None, description="高德 Key（v0.7.0 主字段）")
    weatherAppsecret: Optional[str] = Field(default=None, description="兼容旧版，自动映射到 weatherKey")
    weatherCity: Optional[str] = Field(default=None)
    # 用户价值观（rational 模式用）
    values: Optional[Dict[str, int]] = Field(default=None)
    # 多模态图片（base64 data URL，可选）
    image: Optional[str] = Field(default=None, description="用户上传的图片，base64 data URL")


class ChatResponse(BaseModel):
    """/api/chat 返回。"""

    brief: Optional[Brief] = Field(default=None, description="决策简报（nature 模式为空）")
    nature: Optional[Dict[str, Any]] = Field(default=None, description="nature 模式自然意象简报")
    mode: str = Field(..., description="实际使用的决策模式（auto 已解析）")
    reply: str = Field(..., description="给用户的自然语言回复")
    result: Optional[Dict[str, Any]] = Field(default=None, description="完整 ModeResult（用于前端渲染和持久化）")
    autoRecognized: Optional[Dict[str, Any]] = Field(default=None, description="auto 模式识别结果")
    decisionId: Optional[str] = Field(default=None, description="自动落库后的决策记录 id")


# ─── decision 接口 ─────────────────────────────────────────────


class DecisionSave(BaseModel):
    """POST /api/decision 入参。"""

    id: Optional[str] = None
    question: str
    mode: str
    result: Dict[str, Any] = Field(default_factory=dict)
    brief: Optional[Brief] = None
    executed: bool = False
    regret: bool = False
    dialogueHistory: Optional[List[Dict[str, str]]] = None


class DecisionPatch(BaseModel):
    """PATCH /api/decision/:id 入参。"""

    executed: Optional[bool] = None
    regret: Optional[bool] = None
    dialogueHistory: Optional[List[Dict[str, str]]] = None


# ─── stats 接口 ────────────────────────────────────────────────


class Stats(BaseModel):
    """/api/stats 返回。"""

    totalDecisions: int
    modeDistribution: Dict[str, int] = Field(default_factory=dict)
    avgConfidence: float = 0.0
    executedRate: float = 0.0
    regretRate: float = 0.0
    weekTrend: List[Dict[str, Any]] = Field(default_factory=list)


# ─── 模式元数据 ────────────────────────────────────────────────


class ModeMeta(BaseModel):
    """决策模式元数据。"""

    id: str
    name: str
    icon: str
    color: str
    description: str


# ─── 配置接口 ─────────────────────────────────────────────────


class ConfigResponse(BaseModel):
    """/api/config GET 返回（脱敏）。"""

    llm: Dict[str, Any] = Field(default_factory=dict, description="LLM 配置（脱敏）")
    weather: Dict[str, Any] = Field(default_factory=dict, description="天气配置（脱敏）")
    hasLlm: bool = False
    hasWeather: bool = False


class ConfigUpdate(BaseModel):
    """/api/config POST 入参。

    天气服务从 v0.7.0 起切换到高德开放平台：
      - weather_key（高德 Key）是主字段
      - weather_appsecret 兼容旧版（自动当作 weather_key 处理）
    """

    llm_api_key: Optional[str] = None
    llm_model: Optional[str] = None
    llm_base_url: Optional[str] = None
    weather_key: Optional[str] = None
    weather_appsecret: Optional[str] = None  # 兼容旧版
    weather_city: Optional[str] = None


class PreferencesUpdate(BaseModel):
    """/api/preferences POST 入参。"""

    language: Optional[str] = None
    default_mode: Optional[str] = None
    theme: Optional[str] = None
    logo: Optional[str] = None
    auto_speak: Optional[bool] = None
    tts_rate: Optional[float] = None
    tts_pitch: Optional[float] = None
    tts_voice_uri: Optional[str] = None
    values: Optional[Dict[str, int]] = None
