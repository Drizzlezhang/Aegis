"""GEX (Gamma Exposure) calculation algorithm skill."""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Any, Tuple
import logging
from datetime import datetime
from enum import Enum

from src.skills.base import BaseSkill, SkillResult, SkillType
from src.models import OptionChain, OptionContract, OptionType, GEXWall
from src.config import get_config


logger = logging.getLogger(__name__)


class GEXCalculationMethod(str, Enum):
    """GEX calculation method."""
    SIMPLIFIED = "simplified"
    BLACK_SCHOLES = "black_scholes"


class GEXCalculatorSkill(BaseSkill):
    """GEX calculation algorithm skill."""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
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

    def get_required_params(self) -> List[str]:
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
            # More accurate GEX calculation (placeholder)
            # In production, use proper Black-Scholes gamma
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
        calculation_method: Optional[str] = None
    ) -> List[GEXWall]:
        """Calculate GEX walls from options chain."""
        calculation_method = calculation_method or self.calculation_method

        spot_price = options_chain.spot_price

        # Combine all contracts
        all_contracts = options_chain.calls + options_chain.puts

        # Group by strike price
        strike_groups: Dict[float, List[OptionContract]] = {}
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
        calculation_method: Optional[str] = None
    ) -> List[GEXWall]:
        """Get top N GEX walls by absolute GEX value."""
        gex_walls = self.calculate_gex_walls(options_chain, calculation_method)
        return gex_walls[:top_n]

    async def execute(self, params: Dict[str, Any]) -> SkillResult:
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
    strikes: List[float],
    call_oi: List[int],
    put_oi: List[int],
    spot_price: float,
    calculation_method: str = "simplified"
) -> List[Dict[str, Any]]:
    """Quick GEX calculation (for testing)."""
    skill = GEXCalculatorSkill({
        "calculation_method": calculation_method
    })

    # Create mock OptionChain
    from src.models import OptionChain, OptionContract, OptionType
    from datetime import datetime, date

    calls = []
    puts = []

    for strike, oi in zip(strikes, call_oi):
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

    for strike, oi in zip(strikes, put_oi):
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