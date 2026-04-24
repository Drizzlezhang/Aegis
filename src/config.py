"""Global configuration management."""

from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class DataSourceConfig(BaseModel):
    """Data source configuration."""
    yfinance_enabled: bool = True
    alpha_vantage_enabled: bool = False
    alpha_vantage_api_key: str | None = None
    cache_ttl_seconds: int = 300  # 5 minutes


class LLMConfig(BaseModel):
    """LLM configuration."""
    provider: str = "deepseek"
    reasoning_model: str = "deepseek-v3.2"
    long_context_model: str = "gemini-pro"
    quick_model: str = "minimax-2.7"
    code_model: str = "glm5.1"
    api_base_url: str | None = None
    api_key: str | None = None


class AlgorithmConfig(BaseModel):
    """Algorithm configuration."""
    volume_profile_bins: int = 100
    value_area_percentage: float = 0.7  # 70%
    gex_calculation_method: str = "simplified"  # simplified | black_scholes
    pe_band_percentiles: list[float] = Field(default=[0.1, 0.25, 0.5, 0.75, 0.9])


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


class AgentConfig(BaseModel):
    """Agent configuration."""
    data_harvester_enabled: bool = True
    quant_brain_enabled: bool = True
    strategy_exec_enabled: bool = True
    aegis_memory_enabled: bool = True
    max_concurrent_agents: int = 4


class Config(BaseSettings):
    """Main configuration."""
    model_config = SettingsConfigDict(
        env_prefix="AEGIS_",
        env_nested_delimiter="__",
        case_sensitive=False
    )

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
    agent: AgentConfig = Field(default_factory=AgentConfig)

    # Core symbols
    core_symbols: list[str] = Field(default=[
        "QQQ", "SPY", "NVDA", "MSFT", "AAPL", "KO", "PLTR", "NFLX", "INTC", "TSM", "TSLA"
    ])

    # Strategy
    min_leaps_days_to_expiry: int = 300  # ~10 months
    call_delta_range: list[float] = Field(default=[0.6, 0.8])
    support_distance_threshold: float = 0.02  # 2%

    @field_validator("skill_dirs", "data_dir", "cache_dir", "log_dir", mode="before")
    @classmethod
    def resolve_paths(cls, value: Any) -> Any:
        """Resolve paths to absolute paths."""
        if isinstance(value, list):
            return [Path(str(v)).expanduser().resolve() for v in value]
        return Path(str(value)).expanduser().resolve()

    @field_validator("core_symbols")
    @classmethod
    def validate_symbols(cls, value: Any) -> Any:
        """Validate core symbols."""
        if not value:
            raise ValueError("core_symbols cannot be empty")
        return [s.upper() for s in value]


# Global config instance
_config: Config | None = None


def get_config() -> Config:
    """Get the global configuration instance."""
    global _config
    if _config is None:
        _config = Config()
    return _config


def set_config(config: Config) -> None:
    """Set the global configuration instance."""
    global _config
    _config = config


def reload_config() -> Config:
    """Reload configuration from environment."""
    global _config
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
