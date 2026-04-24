"""Market data models."""

from datetime import datetime
from enum import StrEnum

import pandas as pd
from pydantic import BaseModel


class AssetType(StrEnum):
    """Asset type enumeration."""
    STOCK = "stock"
    ETF = "etf"
    OPTION = "option"
    INDEX = "index"


class OHLCV(BaseModel):
    """OHLCV data model."""
    symbol: str
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: int
    adjusted_close: float | None = None

    class ConfigDict:
        arbitrary_types_allowed = True

    def to_dataframe(self) -> pd.DataFrame:
        """Convert to pandas DataFrame."""
        return pd.DataFrame([self.model_dump()])

    @classmethod
    def from_dataframe(cls, df: pd.DataFrame, symbol: str) -> list["OHLCV"]:
        """Create from pandas DataFrame."""
        ohlcv_list = []
        for _, row in df.iterrows():
            ohlcv = cls(
                symbol=symbol,
                timestamp=row.get("timestamp") or row.get("date") or row.get("Date"),
                open=float(row.get("open") or row.get("Open")),
                high=float(row.get("high") or row.get("High")),
                low=float(row.get("low") or row.get("Low")),
                close=float(row.get("close") or row.get("Close")),
                volume=int(row.get("volume") or row.get("Volume")),
                adjusted_close=float(row.get("adjusted_close") or row.get("Adj Close")) if "adjusted_close" in row or "Adj Close" in row else None
            )
            ohlcv_list.append(ohlcv)
        return ohlcv_list
