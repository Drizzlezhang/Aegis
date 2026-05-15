"""Tests for BSM pricer skill."""

import math
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from skills.algorithms.bsm_pricer.skill import BSMPricerSkill


@pytest.mark.asyncio
async def test_atm_call_price() -> None:
    """ATM call theoretical value and Greeks should match known benchmark."""
    skill = BSMPricerSkill()
    result = await skill.execute({
        "spot": 100,
        "strike": 100,
        "time_to_expiry": 1.0,
        "risk_free_rate": 0.05,
        "volatility": 0.2,
        "option_type": "call",
    })

    assert result.success is True
    data = result.data
    assert data is not None

    assert abs(data["price"] - 10.4506) < 0.02
    assert abs(data["delta"] - 0.6368) < 0.02
    assert abs(data["gamma"] - 0.0188) < 0.002
    assert abs(data["theta"] - (-0.0176)) < 0.002
    assert abs(data["vega"] - 0.3752) < 0.01


@pytest.mark.asyncio
async def test_deep_itm_call() -> None:
    """Deep ITM call delta should approach 1."""
    skill = BSMPricerSkill()
    result = await skill.execute({
        "spot": 200,
        "strike": 100,
        "time_to_expiry": 0.5,
        "risk_free_rate": 0.03,
        "volatility": 0.15,
        "option_type": "call",
    })

    assert result.success is True
    data = result.data
    assert data is not None
    assert data["delta"] > 0.98
    assert data["price"] > 100


@pytest.mark.asyncio
async def test_deep_otm_put() -> None:
    """Deep OTM put delta should approach 0."""
    skill = BSMPricerSkill()
    result = await skill.execute({
        "spot": 200,
        "strike": 100,
        "time_to_expiry": 0.5,
        "risk_free_rate": 0.03,
        "volatility": 0.15,
        "option_type": "put",
    })

    assert result.success is True
    data = result.data
    assert data is not None
    assert -0.02 < data["delta"] <= 0.0
    assert data["price"] < 0.05


@pytest.mark.asyncio
async def test_put_call_parity() -> None:
    """Put-call parity should hold under same inputs."""
    skill = BSMPricerSkill()

    call = await skill.execute({
        "spot": 100,
        "strike": 100,
        "time_to_expiry": 1.0,
        "risk_free_rate": 0.05,
        "volatility": 0.2,
        "option_type": "call",
    })
    put = await skill.execute({
        "spot": 100,
        "strike": 100,
        "time_to_expiry": 1.0,
        "risk_free_rate": 0.05,
        "volatility": 0.2,
        "option_type": "put",
    })

    assert call.success is True
    assert put.success is True
    assert call.data is not None
    assert put.data is not None

    lhs = call.data["price"] - put.data["price"]
    rhs = 100 - 100 * math.exp(-0.05 * 1.0)
    assert abs(lhs - rhs) < 0.02


@pytest.mark.asyncio
async def test_greeks_boundary_near_expiry() -> None:
    """Near expiry ATM option should show high gamma and negative theta."""
    skill = BSMPricerSkill()
    result = await skill.execute({
        "spot": 100,
        "strike": 100,
        "time_to_expiry": 1e-4,
        "risk_free_rate": 0.01,
        "volatility": 0.5,
        "option_type": "call",
    })

    assert result.success is True
    data = result.data
    assert data is not None
    assert data["gamma"] > 0.5
    assert data["theta"] < 0


@pytest.mark.asyncio
async def test_zero_volatility() -> None:
    """Zero volatility should reduce to discounted intrinsic expectation."""
    skill = BSMPricerSkill()
    result = await skill.execute({
        "spot": 100,
        "strike": 100,
        "time_to_expiry": 1.0,
        "risk_free_rate": 0.05,
        "volatility": 0.0,
        "option_type": "call",
    })

    assert result.success is True
    data = result.data
    assert data is not None

    expected = max(100 - 100 * math.exp(-0.05), 0.0)
    assert abs(data["price"] - expected) < 1e-9
    assert data["gamma"] == 0.0
    assert data["vega"] == 0.0


@pytest.mark.asyncio
async def test_invalid_option_type() -> None:
    """Invalid option type should return error result."""
    skill = BSMPricerSkill()
    result = await skill.execute({
        "spot": 100,
        "strike": 100,
        "time_to_expiry": 1.0,
        "risk_free_rate": 0.05,
        "volatility": 0.2,
        "option_type": "swap",
    })

    assert result.success is False
    assert result.error == "option_type must be 'call' or 'put'"
