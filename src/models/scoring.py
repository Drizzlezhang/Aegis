"""技术评分模型定义。"""

from pydantic import AliasChoices, BaseModel, Field


class TechnicalScoreBreakdown(BaseModel):
    """100 分制技术评分细项。"""

    trend_score: float = Field(0.0, ge=0, le=25, validation_alias=AliasChoices("trend_score", "trend"), description="趋势得分 (0-25)")
    deviation_score: float = Field(0.0, ge=0, le=15, validation_alias=AliasChoices("deviation_score", "deviation"), description="乖离率得分 (0-15)")
    volume_score: float = Field(0.0, ge=0, le=12, validation_alias=AliasChoices("volume_score", "volume"), description="量能得分 (0-12)")
    support_score: float = Field(0.0, ge=0, le=10, validation_alias=AliasChoices("support_score", "support"), description="支撑位得分 (0-10)")
    macd_score: float = Field(0.0, ge=0, le=13, validation_alias=AliasChoices("macd_score", "macd"), description="MACD 得分 (0-13)")
    rsi_score: float = Field(0.0, ge=0, le=10, validation_alias=AliasChoices("rsi_score", "rsi"), description="RSI 得分 (0-10)")
    adx_score: float = Field(0.0, ge=0, le=8, validation_alias=AliasChoices("adx_score", "adx"), description="ADX 得分 (0-8)")
    obv_score: float = Field(0.0, ge=0, le=7, validation_alias=AliasChoices("obv_score", "obv"), description="OBV 得分 (0-7)")

    @property
    def total(self) -> float:
        return (
            self.trend_score
            + self.deviation_score
            + self.volume_score
            + self.support_score
            + self.macd_score
            + self.rsi_score
            + self.adx_score
            + self.obv_score
        )

    @property
    def grade(self) -> str:
        """A/B/C/D/F 评级。"""
        t = self.total
        if t >= 80:
            return "A"
        if t >= 65:
            return "B"
        if t >= 50:
            return "C"
        if t >= 35:
            return "D"
        return "F"


class MacroRegime(BaseModel):
    """宏观 Regime 判断结果。"""

    regime: str = Field(..., description="risk_on | risk_off | neutral")
    confidence: float = Field(0.0, ge=0, le=1)
    vix_signal: str = Field("neutral", description="low | normal | elevated | extreme")
    market_trend: str = Field("neutral", description="bullish | neutral | bearish")
    sector_rotation: str = Field("neutral", description="growth | defensive | balanced")
    safe_haven_pressure: float = Field(0.0, ge=0, le=1, description="避险压力 0-1")
    credit_spread: str = Field("normal", description="tight | normal | wide | extreme")
    factors: dict[str, float] = Field(default_factory=dict, description="各因子得分")
