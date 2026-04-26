"""Symbol-related API routes."""

from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel

from skills.algorithms.gex_calculator.skill import GEXCalculatorSkill
from skills.algorithms.volume_profile.skill import VolumeProfileSkill
from skills.data_sources.yfinance_skill.skill import YFinanceSkill
from src.agents.quant_brain.core import create_support_resistance_levels

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


def _format_market_cap(market_cap_value: Any, fallback: str) -> str:
    """Format market cap string."""
    if isinstance(market_cap_value, (int, float)):
        if market_cap_value >= 1e12:
            return f"${market_cap_value / 1e12:.2f}T"
        if market_cap_value >= 1e9:
            return f"${market_cap_value / 1e9:.2f}B"
        return f"${market_cap_value / 1e6:.2f}M"
    return fallback


def _confidence_to_strength(confidence: float) -> str:
    """Map confidence score to API strength label."""
    if confidence >= 0.75:
        return "strong"
    if confidence >= 0.55:
        return "moderate"
    return "weak"


def _source_label(source: str) -> str:
    """Map internal source labels to API labels."""
    labels = {
        "volume_profile": "Volume Profile",
        "gex": "GEX Wall",
        "prior": "User Input",
        "technical": "Technical",
    }
    return labels.get(source, source.replace("_", " ").title())


def _build_analysis_levels(price: float, ohlcv: list[Any] | None) -> tuple[list[SupportResistance], list[SupportResistance], VolumeProfile]:
    """Build support/resistance and volume profile from real OHLCV when available."""
    fallback_volume_profile = VolumeProfile(
        poc=round(price * 0.98, 2),
        vah=round(price * 1.03, 2),
        val=round(price * 0.97, 2),
        volumeAtPoc=0,
    )
    fallback_supports = [
        SupportResistance(level=round(price * 0.95, 2), type="support", strength="strong", source="Volume Profile"),
        SupportResistance(level=round(price * 0.92, 2), type="support", strength="moderate", source="User Input"),
    ]
    fallback_resistances = [
        SupportResistance(level=round(price * 1.05, 2), type="resistance", strength="moderate", source="Volume Profile"),
        SupportResistance(level=round(price * 1.08, 2), type="resistance", strength="strong", source="GEX Wall"),
    ]

    if not ohlcv:
        return fallback_supports, fallback_resistances, fallback_volume_profile

    try:
        volume_profile = VolumeProfileSkill().calculate_volume_profile(ohlcv)
        support_levels, resistance_levels = create_support_resistance_levels(volume_profile, gex_walls=None)

        supports = [
            SupportResistance(
                level=round(level.price, 2),
                type="support",
                strength=_confidence_to_strength(level.confidence),
                source=_source_label(level.source),
            )
            for level in support_levels
        ]
        resistances = [
            SupportResistance(
                level=round(level.price, 2),
                type="resistance",
                strength=_confidence_to_strength(level.confidence),
                source=_source_label(level.source),
            )
            for level in resistance_levels
        ]
        profile = VolumeProfile(
            poc=round(volume_profile.poc_price, 2),
            vah=round(volume_profile.vah_price, 2),
            val=round(volume_profile.val_price, 2),
            volumeAtPoc=int(volume_profile.total_volume),
        )
        return supports, resistances, profile
    except Exception:
        return fallback_supports, fallback_resistances, fallback_volume_profile


def _gex_strength(net_gex: float) -> str:
    """Map GEX magnitude to API strength."""
    abs_gex = abs(net_gex)
    if abs_gex >= 1_000_000:
        return "strong"
    if abs_gex >= 500_000:
        return "moderate"
    return "weak"


def _build_gex_walls(price: float, options_chain: Any | None) -> list[GexWall]:
    """Build GEX wall payload from real options data when available."""
    fallback = [
        GexWall(strike=round(price * 1.05), gamma=0.45, type="call", strength="strong"),
        GexWall(strike=round(price * 0.95), gamma=0.35, type="put", strength="moderate"),
        GexWall(strike=round(price * 1.10), gamma=0.25, type="call", strength="weak"),
    ]

    if not options_chain:
        return fallback

    try:
        walls = GEXCalculatorSkill().calculate_gex_walls(options_chain)
        if not walls:
            return fallback

        return [
            GexWall(
                strike=round(wall.strike),
                gamma=wall.net_gex,
                type="call" if wall.wall_type == "resistance" else "put",
                strength=_gex_strength(wall.net_gex),
            )
            for wall in walls[:3]
        ]
    except Exception:
        return fallback


def _build_recommendations(
    symbol: str,
    price: float,
    supports: list[SupportResistance],
    resistances: list[SupportResistance],
    gex_walls: list[GexWall],
) -> list[StrategyRecommendation]:
    """Build dynamic strategy recommendations from analysis outputs."""
    nearest_support = min(supports, key=lambda level: abs(level.level - price)) if supports else None
    nearest_resistance = min(resistances, key=lambda level: abs(level.level - price)) if resistances else None
    strongest_gex = next((wall for wall in gex_walls if wall.strength == "strong"), gex_walls[0] if gex_walls else None)

    support_level = round(nearest_support.level) if nearest_support else round(price)
    resistance_level = round(nearest_resistance.level) if nearest_resistance else round(price * 1.05)
    upside = max(((resistance_level - price) / price) * 100, 0.0) if price else 0.0
    gex_strike = round(strongest_gex.strike) if strongest_gex else resistance_level

    return [
        StrategyRecommendation(
            id="support-leaps",
            type="LEAPS",
            description=f"Buy {symbol} LEAPS Call near ${support_level} support with upside to ${resistance_level} resistance",
            riskLevel="medium",
            expectedReturn=f"{upside:.1f}% to resistance",
            expiration="Jan 2027",
            strike=f"${support_level}",
        ),
        StrategyRecommendation(
            id="resistance-bull-spread",
            type="Bull Spread",
            description=f"Structure {symbol} bull call spread from ${support_level} support toward ${resistance_level} resistance",
            riskLevel="low",
            expectedReturn="Defined-risk upside into resistance",
            expiration="Jul 2026",
            strike=f"${support_level} / ${resistance_level}",
        ),
        StrategyRecommendation(
            id="gex-covered-call",
            type="Covered Call",
            description=f"Sell {symbol} covered call into GEX resistance at ${gex_strike}",
            riskLevel="low",
            expectedReturn="Income at key resistance",
            expiration="May 2026",
            strike=f"${gex_strike}",
        ),
    ]


async def _get_latest_snapshot(symbol: str) -> dict[str, Any] | None:
    """Get latest price and fundamentals snapshot for a symbol."""
    skill = YFinanceSkill()

    try:
        ohlcv = await skill.get_ohlcv(symbol, period="5d", interval="1d")
        fundamentals = await skill.get_fundamentals(symbol)
        if not ohlcv:
            return None

        latest = ohlcv[-1]
        prev_close = ohlcv[-2].close if len(ohlcv) > 1 else latest.open
        change = float(latest.close - prev_close)
        change_percent = (change / prev_close * 100) if prev_close else 0.0

        options_chain = None
        try:
            options_chain = await skill.get_options_chain(symbol)
        except Exception:
            options_chain = None

        return {
            "price": round(float(latest.close), 2),
            "change": round(change, 2),
            "changePercent": round(change_percent, 2),
            "volume": int(fundamentals.get("volume") or latest.volume or 0),
            "avgVolume": int(fundamentals.get("average_volume") or latest.volume or 0),
            "marketCapValue": fundamentals.get("market_cap"),
            "peRatio": float(fundamentals.get("pe_ratio") or 0.0),
            "ohlcv": ohlcv,
            "optionsChain": options_chain,
        }
    except Exception:
        return None


async def _get_latest_symbol_info() -> list[SymbolInfo]:
    """Get latest symbol snapshot data from yfinance, falling back to seeded values."""
    skill = YFinanceSkill()
    results: list[SymbolInfo] = []

    for info in _SYMBOLS:
        price = float(info["price"])
        change = float(info["change"])
        change_percent = float(info["changePercent"])
        volume = int(info["volume"])

        try:
            ohlcv = await skill.get_ohlcv(info["symbol"], period="5d", interval="1d")
            fundamentals = await skill.get_fundamentals(info["symbol"])

            if ohlcv:
                latest = ohlcv[-1]
                prev_close = ohlcv[-2].close if len(ohlcv) > 1 else latest.open
                price = round(float(latest.close), 2)
                change = round(float(latest.close - prev_close), 2)
                change_percent = round((change / prev_close * 100), 2) if prev_close else 0.0
                volume = int(fundamentals.get("volume") or latest.volume or volume)

            avg_volume = fundamentals.get("average_volume")
            analysis_status = info["analysisStatus"]
            trend = "up" if change > 0 else "down" if change < 0 else "neutral"

            results.append(
                SymbolInfo(
                    symbol=info["symbol"],
                    name=info["name"],
                    price=price,
                    change=change,
                    changePercent=change_percent,
                    volume=volume,
                    trend=trend,
                    analysisStatus=analysis_status,
                )
            )
            continue
        except Exception:
            pass

        results.append(SymbolInfo(**info))

    return results


async def _get_symbol_detail(symbol: str) -> SymbolDetail | None:
    """Get detailed information for a symbol."""
    info = next((s for s in _SYMBOLS if s["symbol"] == symbol), None)
    if not info:
        return None

    price = info["price"]
    change = info["change"]
    change_percent = info["changePercent"]
    volume = info["volume"]
    avg_volume = round(info["volume"] * (0.8 + hash(info["symbol"]) % 100 / 100))
    market_cap = f"{(hash(info['symbol']) % 20 + 1) / 10:.2f}T"
    pe_ratio = round(15 + (hash(info['symbol']) % 400) / 10, 2)
    latest_ohlcv = None
    latest_options_chain = None

    latest = await _get_latest_snapshot(symbol)
    if latest:
        price = latest["price"]
        change = latest["change"]
        change_percent = latest["changePercent"]
        volume = latest["volume"]
        avg_volume = latest["avgVolume"]
        pe_ratio = latest["peRatio"] or pe_ratio
        market_cap = _format_market_cap(latest["marketCapValue"], market_cap)
        latest_ohlcv = latest.get("ohlcv")
        latest_options_chain = latest.get("optionsChain")

    supports, resistances, volume_profile = _build_analysis_levels(price, latest_ohlcv)
    gex_walls = _build_gex_walls(price, latest_options_chain)
    recommendations = _build_recommendations(symbol, price, supports, resistances, gex_walls)

    return SymbolDetail(
        symbol=info["symbol"],
        name=info["name"],
        price=price,
        change=change,
        changePercent=change_percent,
        volume=volume,
        avgVolume=avg_volume,
        marketCap=market_cap,
        peRatio=pe_ratio,
        supports=supports,
        resistances=resistances,
        volumeProfile=volume_profile,
        gexWalls=gex_walls,
        recommendations=recommendations,
    )


@router.get("/symbols", response_model=list[SymbolInfo])
async def get_symbols() -> list[SymbolInfo]:
    """Get list of all tracked symbols."""
    return await _get_latest_symbol_info()


@router.get("/symbols/{symbol}", response_model=SymbolDetail)
async def get_symbol_detail(symbol: str) -> SymbolDetail:
    """Get detailed information for a specific symbol."""
    detail = await _get_symbol_detail(symbol.upper())
    if not detail:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail=f"Symbol {symbol} not found")
    return detail


@router.get("/symbols/{symbol}/analysis")
async def get_symbol_analysis(symbol: str) -> dict:
    """Get analysis data for a specific symbol."""
    detail = await _get_symbol_detail(symbol.upper())
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
