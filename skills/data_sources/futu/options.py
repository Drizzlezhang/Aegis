"""Futu options chain conversion utilities."""

import logging
from datetime import date, datetime
from typing import Any

from src.models import OptionChain, OptionContract, OptionType

logger = logging.getLogger(__name__)


def _to_date(strike_time: Any) -> date:
    """Convert Futu strike_time to date."""
    if isinstance(strike_time, str):
        return datetime.strptime(strike_time, "%Y-%m-%d").date()
    if isinstance(strike_time, datetime):
        return strike_time.date()
    if isinstance(strike_time, date):
        return strike_time
    raise ValueError(f"Unsupported strike_time type: {type(strike_time)}")


def _safe_float(value: Any) -> float | None:
    """Safely convert to float, returning None on failure."""
    try:
        if value is None:
            return None
        return float(value)
    except (ValueError, TypeError):
        return None


def _safe_int(value: Any) -> int | None:
    """Safely convert to int, returning None on failure."""
    try:
        if value is None:
            return None
        return int(value)
    except (ValueError, TypeError):
        return None


def _futu_row_to_contract(symbol: str, row: Any) -> OptionContract | None:
    """Convert a single Futu option chain row to OptionContract."""
    try:
        strike_time = row.get("strike_time") if hasattr(row, "get") else getattr(row, "strike_time", None)
        expiry = _to_date(strike_time)

        option_type_str = row.get("option_type") if hasattr(row, "get") else getattr(row, "option_type", "")
        option_type = OptionType.CALL if str(option_type_str).upper() == "CALL" else OptionType.PUT

        strike = _safe_float(row.get("strike_price") if hasattr(row, "get") else getattr(row, "strike_price", 0))
        if strike is None or strike <= 0:
            return None

        contract_symbol = row.get("code") if hasattr(row, "get") else getattr(row, "code", "")

        return OptionContract(
            symbol=contract_symbol or f"{symbol}_{expiry}_{option_type.value}_{strike}",
            underlying=symbol,
            contract_symbol=contract_symbol or "",
            strike=strike,
            expiry=expiry,
            option_type=option_type,
            last_price=_safe_float(row.get("last_price") if hasattr(row, "get") else getattr(row, "last_price", None)),
            bid=_safe_float(row.get("bid_price") if hasattr(row, "get") else getattr(row, "bid_price", None)),
            ask=_safe_float(row.get("ask_price") if hasattr(row, "get") else getattr(row, "ask_price", None)),
            volume=_safe_int(row.get("volume") if hasattr(row, "get") else getattr(row, "volume", None)),
            open_interest=_safe_int(row.get("open_interest") if hasattr(row, "get") else getattr(row, "open_interest", None)),
            implied_volatility=_safe_float(row.get("implied_volatility") if hasattr(row, "get") else getattr(row, "implied_volatility", None)),
            delta=_safe_float(row.get("delta") if hasattr(row, "get") else getattr(row, "delta", None)),
            gamma=_safe_float(row.get("gamma") if hasattr(row, "get") else getattr(row, "gamma", None)),
            theta=_safe_float(row.get("theta") if hasattr(row, "get") else getattr(row, "theta", None)),
            vega=_safe_float(row.get("vega") if hasattr(row, "get") else getattr(row, "vega", None)),
            rho=_safe_float(row.get("rho") if hasattr(row, "get") else getattr(row, "rho", None)),
        )
    except Exception as e:
        logger.warning(f"Failed to convert Futu option row: {e}")
        return None


def futu_df_to_option_chain(symbol: str, df: Any, spot_price: float) -> OptionChain | None:
    """Convert Futu option chain DataFrame to OptionChain model."""
    try:
        calls = []
        puts = []
        expiry_dates: set[date] = set()

        for _, row in df.iterrows():
            contract = _futu_row_to_contract(symbol, row)
            if not contract:
                continue
            expiry_dates.add(contract.expiry)
            if contract.option_type == OptionType.CALL:
                calls.append(contract)
            else:
                puts.append(contract)

        if not calls and not puts:
            logger.warning(f"No valid options parsed from Futu data for {symbol}")
            return None

        return OptionChain(
            symbol=symbol,
            timestamp=datetime.now(),
            spot_price=spot_price,
            calls=calls,
            puts=puts,
            expiry_dates=sorted(expiry_dates),
        )
    except Exception as e:
        logger.error(f"Failed to convert Futu option chain for {symbol}: {e}")
        return None
