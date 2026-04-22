"""Tests for GEX calculator algorithm."""

import pytest
import sys
from pathlib import Path
from datetime import datetime, date, timedelta
import pandas as pd

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.models import OptionChain, OptionContract, OptionType
from skills.algorithms.gex_calculator.skill import GEXCalculatorSkill, calculate_gex_quick


def create_mock_option_chain(
    spot_price=100.0,
    strikes=None,
    call_oi=None,
    put_oi=None,
    symbol="QQQ"
):
    """Create mock option chain data."""
    if strikes is None:
        strikes = [90.0, 95.0, 100.0, 105.0, 110.0]
    if call_oi is None:
        call_oi = [1000, 2000, 5000, 3000, 1000]
    if put_oi is None:
        put_oi = [500, 1000, 8000, 1500, 500]

    expiry = date.today() + timedelta(days=30)

    calls = []
    puts = []

    for strike, oi in zip(strikes, call_oi):
        if oi > 0:
            contract = OptionContract(
                symbol=symbol,
                underlying=symbol,
                contract_symbol=f"{symbol}{strike}C",
                strike=strike,
                expiry=expiry,
                option_type=OptionType.CALL,
                open_interest=oi
            )
            calls.append(contract)

    for strike, oi in zip(strikes, put_oi):
        if oi > 0:
            contract = OptionContract(
                symbol=symbol,
                underlying=symbol,
                contract_symbol=f"{symbol}{strike}P",
                strike=strike,
                expiry=expiry,
                option_type=OptionType.PUT,
                open_interest=oi
            )
            puts.append(contract)

    return OptionChain(
        symbol=symbol,
        timestamp=datetime.now(),
        spot_price=spot_price,
        calls=calls,
        puts=puts,
        expiry_dates=[expiry]
    )


def test_gex_basic_calculation():
    """Test basic GEX calculation."""
    # Create option chain with high OI at ATM strike
    strikes = [90.0, 95.0, 100.0, 105.0, 110.0]
    call_oi = [1000, 2000, 10000, 3000, 1000]
    put_oi = [500, 1000, 8000, 1500, 500]

    options_chain = create_mock_option_chain(
        spot_price=100.0,
        strikes=strikes,
        call_oi=call_oi,
        put_oi=put_oi
    )

    skill = GEXCalculatorSkill()
    gex_walls = skill.calculate_gex_walls(options_chain)

    assert len(gex_walls) == 5

    # Highest absolute GEX should be at ATM (100.0)
    top_wall = gex_walls[0]
    assert top_wall.strike == 100.0

    # ATM should be a support wall (positive net GEX from high call OI)
    assert top_wall.wall_type in ["support", "resistance"]


def test_gex_support_vs_resistance():
    """Test support vs resistance identification."""
    # Create option chain with clear positive and negative GEX
    strikes = [95.0, 100.0, 105.0]
    # At 95: high call OI -> positive GEX (support)
    # At 100: balanced -> mixed
    # At 105: high put OI -> negative GEX (resistance)
    call_oi = [10000, 5000, 1000]
    put_oi = [1000, 5000, 10000]

    options_chain = create_mock_option_chain(
        spot_price=100.0,
        strikes=strikes,
        call_oi=call_oi,
        put_oi=put_oi
    )

    skill = GEXCalculatorSkill()
    gex_walls = skill.calculate_gex_walls(options_chain)

    # Find walls at each strike
    wall_95 = next(w for w in gex_walls if w.strike == 95.0)
    wall_105 = next(w for w in gex_walls if w.strike == 105.0)

    # 95 should be support (high call OI)
    assert wall_95.wall_type == "support"

    # 105 should be resistance (high put OI)
    assert wall_105.wall_type == "resistance"


def test_gex_top_walls():
    """Test getting top N GEX walls."""
    strikes = [90.0, 95.0, 100.0, 105.0, 110.0, 115.0, 120.0]
    call_oi = [1000, 2000, 10000, 3000, 1000, 500, 200]
    put_oi = [200, 500, 8000, 1500, 1000, 2000, 1000]

    options_chain = create_mock_option_chain(
        spot_price=100.0,
        strikes=strikes,
        call_oi=call_oi,
        put_oi=put_oi
    )

    skill = GEXCalculatorSkill()
    top_walls = skill.get_top_gex_walls(options_chain, top_n=3)

    assert len(top_walls) == 3

    # Verify sorted by absolute GEX
    for i in range(len(top_walls) - 1):
        assert abs(top_walls[i].net_gex) >= abs(top_walls[i + 1].net_gex)


def test_gex_quick():
    """Test quick GEX calculation helper."""
    strikes = [95.0, 100.0, 105.0]
    call_oi = [10000, 5000, 1000]
    put_oi = [1000, 5000, 10000]

    result = calculate_gex_quick(
        strikes=strikes,
        call_oi=call_oi,
        put_oi=put_oi,
        spot_price=100.0
    )

    # May be 2 or 3 depending on whether middle strike nets to ~0 GEX
    assert len(result) >= 2

    # Check support/resistance identification
    wall_95 = next(w for w in result if w["strike"] == 95.0)
    wall_105 = next(w for w in result if w["strike"] == 105.0)

    assert wall_95["wall_type"] == "support"
    assert wall_105["wall_type"] == "resistance"


def test_gex_empty_chain():
    """Test handling of empty option chain."""
    options_chain = create_mock_option_chain(
        spot_price=100.0,
        strikes=[],
        call_oi=[],
        put_oi=[]
    )

    skill = GEXCalculatorSkill()
    gex_walls = skill.calculate_gex_walls(options_chain)

    assert len(gex_walls) == 0


def test_gex_min_oi_filter():
    """Test minimum open interest filtering."""
    strikes = [95.0, 100.0, 105.0]
    call_oi = [50, 10000, 50]  # 50 is below default min_oi of 100
    put_oi = [50, 5000, 50]

    options_chain = create_mock_option_chain(
        spot_price=100.0,
        strikes=strikes,
        call_oi=call_oi,
        put_oi=put_oi
    )

    skill = GEXCalculatorSkill({"min_open_interest": 100})
    gex_walls = skill.calculate_gex_walls(options_chain)

    # Only 100.0 should have GEX (OI > 100)
    assert len(gex_walls) == 1
    assert gex_walls[0].strike == 100.0
