import math
import pytest
from skills.algorithms.gex_calculator.skill import GEXCalculatorSkill


def test_bsm_gamma_atm():
    skill = GEXCalculatorSkill()
    # ATM (spot == strike)
    gamma_atm = skill._calculate_bsm_gamma(
        spot=100.0,
        strike=100.0,
        dte_years=0.25,
        risk_free_rate=0.05,
        implied_vol=0.3
    )
    # ATM gamma should be relatively high
    assert gamma_atm > 0.02


def test_bsm_gamma_deep_otm():
    skill = GEXCalculatorSkill()
    # Deep OTM
    gamma_otm = skill._calculate_bsm_gamma(
        spot=100.0,
        strike=150.0,
        dte_years=0.25,
        risk_free_rate=0.05,
        implied_vol=0.3
    )
    # Deep OTM gamma should be close to 0
    assert gamma_otm < 0.005


def test_bsm_gamma_vs_simplified():
    skill = GEXCalculatorSkill()
    gamma_bsm = skill._calculate_bsm_gamma(
        spot=100.0,
        strike=100.0,
        dte_years=0.25,
        risk_free_rate=0.05,
        implied_vol=0.3
    )
    
    # We can't easily test `_calculate_gamma` directly against BSM without a full contract,
    # but we can verify the BSM gamma is positive and within a sane range for standard inputs.
    assert 0.01 < gamma_bsm < 0.1
    
    gamma_otm = skill._calculate_bsm_gamma(100.0, 120.0, 0.25)
    assert gamma_bsm > gamma_otm * 1.5, "ATM gamma should be significantly larger than OTM gamma"