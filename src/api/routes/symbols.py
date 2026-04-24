"""Symbol-related API routes."""

from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()


class SymbolInfo(BaseModel):
    """Symbol overview information."""
    symbol: str
    name: str
    price: float
    change: float
    changePercent: float
    volume: int
    trend: str
    analysisStatus: str


class SupportResistance(BaseModel):
    """Support or resistance level."""
    level: float
    type: str
    strength: str
    source: str


class VolumeProfile(BaseModel):
    """Volume profile data."""
    poc: float
    vah: float
    val: float
    volumeAtPoc: int


class GexWall(BaseModel):
    """GEX wall data."""
    strike: int
    gamma: float
    type: str
    strength: str


class StrategyRecommendation(BaseModel):
    """Strategy recommendation."""
    id: str
    type: str
    description: str
    riskLevel: str
    expectedReturn: str
    expiration: str | None = None
    strike: str | None = None


class SymbolDetail(BaseModel):
    """Detailed symbol information."""
    symbol: str
    name: str
    price: float
    change: float
    changePercent: float
    volume: int
    avgVolume: int
    marketCap: str
    peRatio: float
    supports: list[SupportResistance]
    resistances: list[SupportResistance]
    volumeProfile: VolumeProfile
    gexWalls: list[GexWall]
    recommendations: list[StrategyRecommendation]


_SYMBOLS: list[dict[str, Any]] = [
    {"symbol": "QQQ", "name": "Invesco QQQ Trust", "price": 438.52, "change": 2.15, "changePercent": 0.49, "volume": 34500000, "trend": "up", "analysisStatus": "completed"},
    {"symbol": "SPY", "name": "SPDR S&P 500 ETF", "price": 582.31, "change": -1.24, "changePercent": -0.21, "volume": 52100000, "trend": "down", "analysisStatus": "completed"},
    {"symbol": "NVDA", "name": "NVIDIA Corp", "price": 138.25, "change": 3.42, "changePercent": 2.54, "volume": 287000000, "trend": "up", "analysisStatus": "completed"},
    {"symbol": "MSFT", "name": "Microsoft Corp", "price": 432.18, "change": 0.85, "changePercent": 0.20, "volume": 18900000, "trend": "up", "analysisStatus": "completed"},
    {"symbol": "AAPL", "name": "Apple Inc", "price": 198.45, "change": -0.72, "changePercent": -0.36, "volume": 45600000, "trend": "down", "analysisStatus": "pending"},
    {"symbol": "KO", "name": "Coca-Cola Co", "price": 68.92, "change": 0.15, "changePercent": 0.22, "volume": 12300000, "trend": "up", "analysisStatus": "completed"},
    {"symbol": "PLTR", "name": "Palantir Technologies", "price": 78.35, "change": 1.92, "changePercent": 2.51, "volume": 67800000, "trend": "up", "analysisStatus": "completed"},
    {"symbol": "NFLX", "name": "Netflix Inc", "price": 885.42, "change": -5.31, "changePercent": -0.60, "volume": 4200000, "trend": "down", "analysisStatus": "completed"},
    {"symbol": "INTC", "name": "Intel Corp", "price": 19.85, "change": -0.42, "changePercent": -2.07, "volume": 89200000, "trend": "down", "analysisStatus": "error"},
    {"symbol": "TSM", "name": "Taiwan Semiconductor", "price": 186.72, "change": 1.18, "changePercent": 0.64, "volume": 15600000, "trend": "up", "analysisStatus": "completed"},
    {"symbol": "TSLA", "name": "Tesla Inc", "price": 342.18, "change": -8.45, "changePercent": -2.41, "volume": 98200000, "trend": "down", "analysisStatus": "completed"},
]


def _get_symbol_detail(symbol: str) -> SymbolDetail | None:
    """Get detailed information for a symbol."""
    info = next((s for s in _SYMBOLS if s["symbol"] == symbol), None)
    if not info:
        return None

    price = info["price"]
    is_up = info["change"] >= 0

    return SymbolDetail(
        symbol=info["symbol"],
        name=info["name"],
        price=price,
        change=info["change"],
        changePercent=info["changePercent"],
        volume=info["volume"],
        avgVolume=round(info["volume"] * (0.8 + hash(info["symbol"]) % 100 / 100)),
        marketCap=f"{(hash(info['symbol']) % 20 + 1) / 10:.2f}T",
        peRatio=round(15 + (hash(info['symbol']) % 400) / 10, 2),
        supports=[
            SupportResistance(level=round(price * 0.95, 2), type="support", strength="strong", source="Volume Profile"),
            SupportResistance(level=round(price * 0.92, 2), type="support", strength="moderate", source="GEX Wall"),
            SupportResistance(level=round(price * 0.88, 2), type="support", strength="weak", source="User Input"),
        ],
        resistances=[
            SupportResistance(level=round(price * 1.05, 2), type="resistance", strength="moderate", source="Volume Profile"),
            SupportResistance(level=round(price * 1.08, 2), type="resistance", strength="strong", source="GEX Wall"),
            SupportResistance(level=round(price * 1.12, 2), type="resistance", strength="weak", source="PE Band"),
        ],
        volumeProfile=VolumeProfile(
            poc=round(price * (0.98 + (hash(info["symbol"]) % 10) / 100), 2),
            vah=round(price * 1.03, 2),
            val=round(price * 0.97, 2),
            volumeAtPoc=round(info["volume"] * (0.15 + (hash(info["symbol"]) % 10) / 100)),
        ),
        gexWalls=[
            GexWall(strike=round(price * 1.05), gamma=0.45 + (hash(info["symbol"]) % 30) / 100, type="call", strength="strong"),
            GexWall(strike=round(price * 0.95), gamma=0.35 + (hash(info["symbol"]) % 25) / 100, type="put", strength="moderate"),
            GexWall(strike=round(price * 1.10), gamma=0.25 + (hash(info["symbol"]) % 20) / 100, type="call", strength="weak"),
        ],
        recommendations=[
            StrategyRecommendation(
                id="1",
                type="LEAPS",
                description=f"Buy {'ITM' if is_up else 'ATM'} {symbol} LEAPS Call, 10+ months out",
                riskLevel="medium",
                expectedReturn="25-40%",
                expiration="Jan 2027",
                strike=f"${round(price * (0.9 if is_up else 1.0))}",
            ),
            StrategyRecommendation(
                id="2",
                type="Bull Spread",
                description=f"{symbol} Bull Call Spread for limited risk exposure",
                riskLevel="low",
                expectedReturn="15-25%",
                expiration="Jul 2026",
                strike=f"${round(price * 0.95)} / ${round(price * 1.05)}",
            ),
            StrategyRecommendation(
                id="3",
                type="Covered Call",
                description=f"Sell {symbol} Covered Call against existing shares",
                riskLevel="low",
                expectedReturn="3-5% monthly",
                expiration="May 2026",
                strike=f"${round(price * 1.08)}",
            ),
        ],
    )


@router.get("/symbols", response_model=list[SymbolInfo])
async def get_symbols() -> list[SymbolInfo]:
    """Get list of all tracked symbols."""
    return [SymbolInfo(**s) for s in _SYMBOLS]


@router.get("/symbols/{symbol}", response_model=SymbolDetail)
async def get_symbol_detail(symbol: str) -> SymbolDetail:
    """Get detailed information for a specific symbol."""
    detail = _get_symbol_detail(symbol.upper())
    if not detail:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail=f"Symbol {symbol} not found")
    return detail


@router.get("/symbols/{symbol}/analysis")
async def get_symbol_analysis(symbol: str) -> dict:
    """Get analysis data for a specific symbol."""
    detail = _get_symbol_detail(symbol.upper())
    if not detail:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail=f"Symbol {symbol} not found")

    return {
        "symbol": detail.symbol,
        "price": detail.price,
        "supports": [s.model_dump() for s in detail.supports],
        "resistances": [r.model_dump() for r in detail.resistances],
        "volumeProfile": detail.volumeProfile.model_dump(),
        "gexWalls": [g.model_dump() for g in detail.gexWalls],
        "recommendations": [r.model_dump() for r in detail.recommendations],
    }
