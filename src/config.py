"""Global configuration management."""

import os
import threading
import warnings
from enum import StrEnum
from pathlib import Path
from typing import Any, Self

from pydantic import BaseModel, Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class ConfigProfile(StrEnum):
    """Environment profile."""
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"


class DataSourceConfig(BaseModel):
    """Data source configuration."""
    yfinance_enabled: bool = True
    alpha_vantage_enabled: bool = False
    alpha_vantage_api_key: str | None = None
    longbridge_enabled: bool = False
    futu_enabled: bool = False
    tiger_enabled: bool = False
    cache_ttl_seconds: int = 300  # 5 minutes
    circuit_breaker_threshold: int = 3
    cross_validation_threshold: float = 0.005  # B1: 0.5% max close deviation
    gap_threshold_bars: int = 1                # B3: min gap bars to flag
    historical_cache_max_mb: int = 500         # B4: max cache size in MB
    health_score_window_size: int = 100        # B5: sliding window for health scoring


class ProviderCredential(BaseModel):
    """单个 LLM Provider 的凭证。"""
    api_key: str | None = None
    api_base_url: str | None = None
    enabled: bool = True


class LLMConfig(BaseModel):
    """LLM configuration."""
    provider: str = "deepseek"
    reasoning_model: str = "deepseek-v3.2"
    long_context_model: str = "gemini-pro"
    quick_model: str = "minimax-2.7"
    code_model: str = "glm5.1"
    api_base_url: str | None = None
    api_key: str | None = None
    model: str | None = None
    providers: dict[str, ProviderCredential] = Field(default_factory=dict)
    max_retries: int = 3
    retry_base_delay: float = 1.0
    enable_request_logging: bool = False


class PhaseThresholds(BaseModel):
    """Phase 判定阈值。"""
    markup_threshold: float = Field(default=70.0, description="Composite score above this + volume confirm → Markup")
    markdown_threshold: float = Field(default=30.0, description="Composite score below this + volume confirm → Markdown")
    bullish_boundary: float = Field(default=60.0, description="Composite score above this → Re-Accumulation (if volume not confirmed)")
    bearish_boundary: float = Field(default=40.0, description="Composite score below this → Re-Distribution (if volume not confirmed)")
    volume_confirm_threshold: float = Field(default=60.0, description="Volume score above this confirms Markup/Markdown")


class PhaseConfig(BaseModel):
    """Phase Predictor 配置。"""
    enabled: bool = Field(default=True, description="Enable/disable PhasePredictor")
    weights: dict[str, float] = Field(
        default_factory=lambda: {
            "trend_momentum": 0.20,
            "velocity": 0.15,
            "acceleration": 0.12,
            "volume": 0.18,
            "mean_reversion": 0.15,
            "macro": 0.10,
            "valuation": 0.10,
        },
        description="Dimension weights (must sum to ~1.0)",
    )
    low_volatility_threshold: float = Field(
        default=0.005,
        description="ATR(14)/close below this triggers neutral override",
    )
    low_volatility_neutral_score: float = Field(
        default=50.0,
        description="Composite score when low volatility is detected",
    )
    min_ohlcv_bars: int = Field(
        default=50,
        description="Minimum OHLCV bars required for PhasePredictor",
    )
    thresholds: PhaseThresholds = Field(default_factory=PhaseThresholds)

    # Scoring sensitivity multipliers
    velocity_sensitivity: float = Field(
        default=2000.0, gt=0,
        description="Multiplier for velocity EMA normalization",
    )
    acceleration_sensitivity: float = Field(
        default=500.0, gt=0,
        description="Multiplier for acceleration slope normalization",
    )
    rsi_change_sensitivity: float = Field(
        default=1.667, gt=0,
        description="Multiplier for RSI change normalization (default: 50/30)",
    )

    # Phase transition cooldown
    phase_transition_cooldown_bars: int = Field(
        default=3, ge=1, le=20,
        description="Minimum bars between phase transitions to avoid whipsaw signals",
    )

    # Composite score smoothing
    composite_smoothing_alpha: float = Field(
        default=0.3, ge=0, le=1,
        description="EMA smoothing alpha for composite_score. 0=disabled (keep raw), 1=no smoothing",
    )

    # Technical indicator periods
    adx_period: int = Field(default=14, ge=7, le=30, description="ADX calculation period")
    rsi_period: int = Field(default=14, ge=7, le=30, description="RSI calculation period")

    @model_validator(mode="after")
    def enforce_weight_normalization(self) -> Self:
        """Validate that dimension weights sum to 1.0 (±0.01)."""
        total = sum(self.weights.values())
        if abs(total - 1.0) > 0.01:
            raise ValueError(
                f"weights must sum to 1.0 (±0.01), got {total:.4f}. "
                f"Weights: {self.weights}"
            )
        return self

    def validate_weights(self) -> bool:
        """验证权重之和 ≈ 1.0。

        .. deprecated::
            Use the built-in @model_validator instead.
            This method is kept for backward compatibility.
        """
        warnings.warn(
            "validate_weights() is deprecated; weight validation is now enforced "
            "automatically via @model_validator.",
            DeprecationWarning,
            stacklevel=2,
        )
        return abs(sum(self.weights.values()) - 1.0) < 0.01


class AlgorithmConfig(BaseModel):
    """Algorithm configuration."""
    volume_profile_bins: int = 100
    value_area_percentage: float = 0.7  # 70%
    gex_calculation_method: str = "simplified"  # simplified | black_scholes
    pe_band_percentiles: list[float] = Field(default=[0.1, 0.25, 0.5, 0.75, 0.9])
    phase: PhaseConfig = Field(default_factory=PhaseConfig)


class MemoryConfig(BaseModel):
    """Memory configuration."""
    storage_type: str = "sqlite"  # sqlite | postgres | chroma
    sqlite_path: str = "~/.aegis-trader/memory.db"
    vector_dimension: int = 384
    max_memory_entries: int = 10000


class WebConfig(BaseModel):
    """Web interface configuration."""
    enabled: bool = True
    host: str = "0.0.0.0"
    port: int = 3000
    api_port: int = 8000


class AuthConfig(BaseModel):
    """Authentication configuration."""
    enabled: bool = False
    jwt_secret: str = ""
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60
    api_key_header: str = "X-API-Key"
    api_keys: list[str] = []
    cors_origins: list[str] = ["http://localhost:3000"]


class DatabaseConfig(BaseModel):
    """Database configuration."""
    url: str = "sqlite:///~/.aegis-trader/aegis.db"
    pool_size: int = 5
    max_overflow: int = 10
    echo: bool = False


class AgentConfig(BaseModel):
    """Agent configuration."""
    data_harvester_enabled: bool = True
    quant_brain_enabled: bool = True
    strategy_exec_enabled: bool = True
    aegis_memory_enabled: bool = True
    max_concurrent_agents: int = 4


class DebateConfig(BaseModel):
    """辩论系统配置。"""
    max_rounds: int = 1
    quick_think_timeout: int = 30
    deep_think_timeout: int = 120
    bull_bear_enabled: bool = True
    risk_debate_enabled: bool = True
    min_confidence_threshold: float = 0.6


class PositionConfig(BaseModel):
    """持仓管理配置。"""
    max_positions: int = 10
    max_sector_concentration: float = 0.4
    stop_loss_default: float = 0.5
    profit_target_pct: float = 1.0
    monitor_interval_minutes: int = 60
    reflection_delay_days: int = 30
    dte_warning_days: int = 30
    iv_alert_threshold: float = 0.3


class RealtimeConfig(BaseModel):
    """实时数据配置。"""
    enabled: bool = False
    poll_interval_seconds: float = 5.0
    stale_threshold_seconds: float = 60.0
    max_subscribers: int = 50
    symbols: list[str] = Field(default_factory=list)
    subscriber_queue_size: int = 1000
    backpressure_strategy: str = "drop_oldest"  # drop_oldest | throttle | block
    heartbeat_interval_seconds: float = 30.0
    heartbeat_timeout_seconds: float = 10.0
    max_reconnect_attempts: int = 5
    reconnect_base_delay: float = 1.0
    reconnect_max_delay: float = 60.0


class WatchlistConfig(BaseModel):
    """Watchlist configuration."""
    max_symbols: int = 30
    storage_path: str = "~/.aegis-trader/watchlist.json"


class SchedulerConfig(BaseModel):
    """Scheduler configuration."""
    enabled: bool = True
    daily_run_time: str = "09:30"
    timezone: str = "America/New_York"
    max_concurrent_analyses: int = 3
    retry_on_failure: bool = True
    max_retries: int = 2
    persistent_jobstore: bool = True
    history_retention_days: int = 30


class TelegramConfig(BaseModel):
    """Telegram notification configuration."""
    enabled: bool = False
    bot_token: str = ""
    chat_id: str = ""
    silent_hours: tuple[int, int] = (23, 7)
    notify_on_high_confidence: bool = True
    notify_on_completion: bool = True
    notify_on_error: bool = True
    confidence_threshold: float = 0.7


class ConfigValidationError(Exception):
    """Raised when strict config validation fails."""

    def __init__(self, issues: list[str]):
        self.issues = issues
        super().__init__(f"Config validation failed: {len(issues)} issue(s)")


class Config(BaseSettings):
    """Main configuration."""
    model_config = SettingsConfigDict(
        env_prefix="AEGIS_",
        env_nested_delimiter="__",
        case_sensitive=False,
        env_file=".env",
        env_file_encoding="utf-8",
    )

    # Profile
    profile: ConfigProfile = ConfigProfile.DEVELOPMENT

    # Project
    project_name: str = "Aegis-Trader"
    version: str = "0.1.0"
    environment: str = "development"
    debug: bool = False
    log_level: str = "INFO"

    # Paths
    base_dir: Path = Path(__file__).parent.parent
    skill_dirs: list[Path] = Field(default=[Path("skills")])
    data_dir: Path = Field(default=Path("~/.aegis-trader/data"))
    cache_dir: Path = Field(default=Path("~/.aegis-trader/cache"))
    log_dir: Path = Field(default=Path("~/.aegis-trader/logs"))

    # Sub-configurations
    data_source: DataSourceConfig = Field(default_factory=DataSourceConfig)
    llm: LLMConfig = Field(default_factory=LLMConfig)
    algorithm: AlgorithmConfig = Field(default_factory=AlgorithmConfig)
    memory: MemoryConfig = Field(default_factory=MemoryConfig)
    web: WebConfig = Field(default_factory=WebConfig)
    auth: AuthConfig = Field(default_factory=AuthConfig)
    database: DatabaseConfig = Field(default_factory=DatabaseConfig)
    agent: AgentConfig = Field(default_factory=AgentConfig)
    debate: DebateConfig = Field(default_factory=DebateConfig)
    position: PositionConfig = Field(default_factory=PositionConfig)
    realtime: RealtimeConfig = Field(default_factory=RealtimeConfig)
    watchlist: WatchlistConfig = Field(default_factory=WatchlistConfig)
    scheduler: SchedulerConfig = Field(default_factory=SchedulerConfig)
    telegram: TelegramConfig = Field(default_factory=TelegramConfig)

    # Core symbols
    core_symbols: list[str] = Field(default=[
        "QQQ", "SPY", "NVDA", "MSFT", "AAPL", "KO", "PLTR", "NFLX", "INTC", "TSM", "TSLA"
    ])

    # Strategy
    min_leaps_days_to_expiry: int = 300  # ~10 months
    call_delta_range: list[float] = Field(default=[0.6, 0.8])
    support_distance_threshold: float = 0.02  # 2%

    # Validation
    strict_validation: bool = False

    @field_validator("skill_dirs", "data_dir", "cache_dir", "log_dir", mode="before")
    @classmethod
    def resolve_paths(cls, value: Any) -> Any:
        """Resolve paths to absolute paths."""
        base = Path(__file__).parent.parent

        def _resolve(p: Path) -> Path:
            p = Path(str(p)).expanduser()
            if not p.is_absolute():
                p = base / p
            return p.resolve()

        if isinstance(value, list):
            return [_resolve(Path(str(v))) for v in value]
        return _resolve(Path(str(value)))

    @field_validator("core_symbols")
    @classmethod
    def validate_symbols(cls, value: Any) -> Any:
        """Validate core symbols."""
        if not value:
            raise ValueError("core_symbols cannot be empty")
        return [s.upper() for s in value]

    @model_validator(mode="after")
    def apply_profile(self) -> "Config":
        """Apply profile-specific defaults."""
        if self.profile == ConfigProfile.PRODUCTION:
            if not os.environ.get("AEGIS_LLM__MAX_RETRIES"):
                self.llm.max_retries = 5
            if not os.environ.get("AEGIS_LLM__RETRY_BASE_DELAY"):
                self.llm.retry_base_delay = 2.0
            if not os.environ.get("AEGIS_DATA_SOURCE__CIRCUIT_BREAKER_THRESHOLD"):
                self.data_source.circuit_breaker_threshold = 5
            if not os.environ.get("AEGIS_LLM__ENABLE_REQUEST_LOGGING"):
                self.llm.enable_request_logging = True
        return self

    @model_validator(mode="after")
    def validate_required_secrets(self) -> "Config":
        """Validate that critical secrets are configured."""
        issues: list[str] = []

        # JWT secret must be set and non-trivial
        if not self.auth.jwt_secret or len(self.auth.jwt_secret) < 16:
            issues.append(
                "AUTH_JWT_SECRET must be set (min 16 chars). "
                "Generate one: python -c \"import secrets; print(secrets.token_hex(32))\""
            )

        # At least one LLM provider must have an API key
        has_llm_key = bool(self.llm.api_key)
        if not has_llm_key:
            for cred in self.llm.providers.values():
                if cred.api_key:
                    has_llm_key = True
                    break
        if not has_llm_key:
            issues.append(
                "At least one LLM API key must be set: "
                "LLM_API_KEY or a provider in LLM__PROVIDERS"
            )

        object.__setattr__(self, "_validation_warnings", issues)

        if issues and self.strict_validation:
            raise ConfigValidationError(issues)

        return self

    @property
    def validation_warnings(self) -> list[str]:
        """Return any startup validation warnings."""
        return getattr(self, "_validation_warnings", [])

    @property
    def is_production_ready(self) -> bool:
        """Check if all production requirements are met."""
        return len(self.validation_warnings) == 0


# Global config instance
_config: Config | None = None
_config_lock = threading.Lock()


def get_config() -> Config:
    """Get the global configuration instance."""
    global _config
    if _config is None:
        with _config_lock:
            # Double-check after acquiring lock
            if _config is None:
                _config = Config()
    return _config


def set_config(config: Config) -> None:
    """Set the global configuration instance."""
    global _config
    with _config_lock:
        _config = config


def reload_config() -> Config:
    """Reload configuration from environment."""
    global _config
    with _config_lock:
        _config = Config()
        return _config


def get_config_dict() -> dict[str, Any]:
    """Get configuration as dictionary."""
    config = get_config()
    return config.model_dump()


# Initialize paths on import
config = get_config()
for path in [config.data_dir, config.cache_dir, config.log_dir]:
    path.mkdir(parents=True, exist_ok=True)
