"""GEX (Gamma Exposure) calculation algorithm skill."""

import logging
from datetime import datetime
from enum import StrEnum
from typing import Any

import numpy as np
import pandas as pd

from src.models import GEXWall, OptionChain, OptionContract, OptionType
from src.skills.base import BaseSkill, SkillResult, SkillType

logger = logging.getLogger(__name__)


class GEXCalculationMethod(StrEnum):
    """GEX calculation method."""
    SIMPLIFIED = "simplified"
    BLACK_SCHOLES = "black_scholes"


class GEXCalculatorSkill(BaseSkill):
    """GEX calculation algorithm skill."""

    def __init__(self, config: dict[str, Any] | None = None):
        super().__init__(config)
        self.calculation_method = config.get("calculation_method", "simplified") if config else "simplified"
        self.spot_price_weight = config.get("spot_price_weight", True) if config else True
        self.min_open_interest = config.get("min_open_interest", 100) if config else 100

    @property
    def skill_type(self) -> SkillType:
        return SkillType.ALGORITHM

    @property
    def description(self) -> str:
        return "GEX (Gamma Exposure) calculation algorithm"

    @property
    def version(self) -> str:
        return "0.1.0"

    def get_required_params(self) -> list[str]:
        return ["options_chain"]

    def _calculate_gamma(self, contract: OptionContract, spot_price: float) -> float:
        """Calculate gamma for an option contract.

        Simplified gamma calculation based on distance from strike.
        In a production system, you would use Black-Scholes or a proper options pricing model.
        """
        if contract.gamma is not None:
            return contract.gamma

        # Simplified gamma calculation
        # Gamma is highest when option is at-the-money and decreases as it moves in/out-of-the-money
        moneyness = abs(contract.strike - spot_price) / spot_price

        # Approximate gamma using a normal distribution-like shape
        # Max gamma ~0.4 for at-the-money options
        gamma = 0.4 * np.exp(-moneyness * 10)

        # Adjust for time to expiry (gamma increases as expiry approaches)
        days_to_expiry = contract.days_to_expiry
        if days_to_expiry > 0:
            time_factor = 1.0 / np.sqrt(days_to_expiry / 365.0)
            gamma *= min(time_factor, 2.0)  # Cap at 2x

        return gamma

    def _calculate_bsm_gamma(
        self,
        spot: float,
        strike: float,
        dte_years: float,
        risk_free_rate: float = 0.05,
        implied_vol: float = 0.3,
    ) -> float:
        """Black-Scholes Gamma calculation.
        
        Gamma = N'(d1) / (S * σ * √T)
        where d1 = [ln(S/K) + (r + σ²/2)T] / (σ√T)
        """
        import math
        from scipy.stats import norm
        
        if dte_years <= 0 or implied_vol <= 0:
            return 0.0
        
        sqrt_t = math.sqrt(dte_years)
        d1 = (math.log(spot / strike) + (risk_free_rate + 0.5 * implied_vol**2) * dte_years) / (implied_vol * sqrt_t)
        
        # N'(d1) = standard normal PDF at d1
        n_prime_d1 = norm.pdf(d1)
        
        gamma = n_prime_d1 / (spot * implied_vol * sqrt_t)
        return gamma

    def _calculate_gex_for_contract(
        self,
        contract: OptionContract,
        spot_price: float,
        calculation_method: str
    ) -> float:
        """Calculate GEX for a single contract."""
        if contract.open_interest is None or contract.open_interest < self.min_open_interest:
            return 0.0

        # Calculate gamma
        gamma = self._calculate_gamma(contract, spot_price)

        # Calculate GEX based on method
        if calculation_method == GEXCalculationMethod.SIMPLIFIED:
            # Simplified GEX calculation
            # GEX = Gamma × Open Interest × 100 × Spot² / 100
            gex = gamma * contract.open_interest * 100 * (spot_price ** 2) / 100
        elif calculation_method == GEXCalculationMethod.BLACK_SCHOLES:
            # More accurate GEX calculation using Black-Scholes gamma
            gamma = self._calculate_bsm_gamma(
                spot=spot_price,
                strike=contract.strike,
                dte_years=max(contract.days_to_expiry / 365.0, 0.001),
                implied_vol=getattr(contract, 'implied_vol', 0.3),
            )
            gex = gamma * contract.open_interest * 100 * (spot_price ** 2) / 100
        else:
            raise ValueError(f"Unknown calculation method: {calculation_method}")

        # Adjust sign based on option type
        if contract.option_type == OptionType.PUT:
            gex = -gex

        return gex

    def calculate_gex_walls(
        self,
        options_chain: OptionChain,
        calculation_method: str | None = None
    ) -> list[GEXWall]:
        """Calculate GEX walls from options chain."""
        calculation_method = calculation_method or self.calculation_method

        spot_price = options_chain.spot_price

        # Combine all contracts
        all_contracts = options_chain.calls + options_chain.puts

        # Group by strike price
        strike_groups: dict[float, list[OptionContract]] = {}
        for contract in all_contracts:
            strike = contract.strike
            if strike not in strike_groups:
                strike_groups[strike] = []
            strike_groups[strike].append(contract)

        gex_walls = []

        for strike, contracts in strike_groups.items():
            total_gex = 0.0
            call_gex = 0.0
            put_gex = 0.0
            total_oi = 0

            for contract in contracts:
                gex = self._calculate_gex_for_contract(
                    contract, spot_price, calculation_method
                )

                if contract.option_type == OptionType.CALL:
                    call_gex += gex
                else:
                    put_gex += gex

                total_gex += gex

                if contract.open_interest:
                    total_oi += contract.open_interest

            # Skip strikes with zero GEX (filtered by min OI)
            if abs(total_gex) < 0.001:
                continue

            # Determine wall type
            if total_gex > 0:
                wall_type = "support"  # Positive GEX = support
            else:
                wall_type = "resistance"  # Negative GEX = resistance

            # Create GEXWall object
            gex_wall = GEXWall(
                symbol=options_chain.symbol,
                timestamp=datetime.now(),
                strike=strike,
                net_gex=total_gex,
                wall_type=wall_type,
                call_gex=call_gex,
                put_gex=put_gex,
                open_interest=total_oi
            )

            gex_walls.append(gex_wall)

        # Sort by absolute GEX value (descending)
        gex_walls.sort(key=lambda x: abs(x.net_gex), reverse=True)

        return gex_walls

    def get_top_gex_walls(
        self,
        options_chain: OptionChain,
        top_n: int = 5,
        calculation_method: str | None = None
    ) -> list[GEXWall]:
        """Get top N GEX walls by absolute GEX value."""
        gex_walls = self.calculate_gex_walls(options_chain, calculation_method)
        return gex_walls[:top_n]

    async def execute(self, params: dict[str, Any]) -> SkillResult:
        """Execute the skill."""
        try:
            options_chain = params.get("options_chain")
            calculation_method = params.get("calculation_method", self.calculation_method)
            top_n = params.get("top_n", 5)

            if not options_chain:
                return SkillResult.error_result("options_chain is required")

            if not isinstance(options_chain, OptionChain):
                return SkillResult.error_result("options_chain must be an OptionChain object")

            # Calculate GEX walls
            gex_walls = self.calculate_gex_walls(options_chain, calculation_method)
            top_walls = gex_walls[:top_n]

            # Calculate summary statistics
            total_gex = sum(wall.net_gex for wall in gex_walls)
            support_walls = [wall for wall in gex_walls if wall.wall_type == "support"]
            resistance_walls = [wall for wall in gex_walls if wall.wall_type == "resistance"]

            metadata = {
                "symbol": options_chain.symbol,
                "spot_price": options_chain.spot_price,
                "calculation_method": calculation_method,
                "total_gex": total_gex,
                "num_support_walls": len(support_walls),
                "num_resistance_walls": len(resistance_walls),
                "top_support": [wall.strike for wall in support_walls[:3]],
                "top_resistance": [wall.strike for wall in resistance_walls[:3]],
            }

            return SkillResult.success_result(top_walls, metadata)

        except ValueError as e:
            logger.error(f"Validation error: {e}")
            return SkillResult.error_result(str(e))
        except Exception as e:
            logger.error(f"GEX calculation failed: {e}")
            return SkillResult.error_result(f"GEX calculation failed: {e}")


# Helper function for quick calculation
def calculate_gex_quick(
    strikes: list[float],
    call_oi: list[int],
    put_oi: list[int],
    spot_price: float,
    calculation_method: str = "simplified"
) -> list[dict[str, Any]]:
    """Quick GEX calculation (for testing)."""
    skill = GEXCalculatorSkill({
        "calculation_method": calculation_method
    })

    # Create mock OptionChain
    from datetime import date, datetime

    from src.models import OptionChain, OptionContract, OptionType

    calls = []
    puts = []

    for strike, oi in zip(strikes, call_oi, strict=False):
        if oi > 0:
            contract = OptionContract(
                symbol="TEST",
                underlying="TEST",
                contract_symbol=f"TEST{strike}C",
                strike=strike,
                expiry=date.today() + pd.Timedelta(days=30),
                option_type=OptionType.CALL,
                open_interest=oi
            )
            calls.append(contract)

    for strike, oi in zip(strikes, put_oi, strict=False):
        if oi > 0:
            contract = OptionContract(
                symbol="TEST",
                underlying="TEST",
                contract_symbol=f"TEST{strike}P",
                strike=strike,
                expiry=date.today() + pd.Timedelta(days=30),
                option_type=OptionType.PUT,
                open_interest=oi
            )
            puts.append(contract)

    options_chain = OptionChain(
        symbol="TEST",
        timestamp=datetime.now(),
        spot_price=spot_price,
        calls=calls,
        puts=puts,
        expiry_dates=[date.today() + pd.Timedelta(days=30)]
    )

    gex_walls = skill.calculate_gex_walls(options_chain, calculation_method)

    return [
        {
            "strike": wall.strike,
            "net_gex": wall.net_gex,
            "wall_type": wall.wall_type,
            "call_gex": wall.call_gex,
            "put_gex": wall.put_gex,
            "open_interest": wall.open_interest,
        }
        for wall in gex_walls
    ]
