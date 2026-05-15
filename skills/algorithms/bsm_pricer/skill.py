"""Black-Scholes-Merton option pricing skill."""

import math
from typing import Any

from src.skills.base import BaseSkill, SkillResult, SkillType


def _norm_cdf(x: float) -> float:
    """Standard normal CDF."""
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def _norm_pdf(x: float) -> float:
    """Standard normal PDF."""
    return math.exp(-0.5 * x * x) / math.sqrt(2.0 * math.pi)


class BSMPricerSkill(BaseSkill):
    """Black-Scholes-Merton option pricing with Greeks."""

    @property
    def skill_type(self) -> SkillType:
        return SkillType.ALGORITHM

    @property
    def description(self) -> str:
        return "Black-Scholes-Merton option pricing with full Greeks"

    @property
    def version(self) -> str:
        return "1.0.0"

    def get_required_params(self) -> list[str]:
        return [
            "spot",
            "strike",
            "time_to_expiry",
            "risk_free_rate",
            "volatility",
        ]

    async def execute(self, params: dict[str, Any] | None = None, **kwargs: Any) -> SkillResult:
        payload = dict(params or {})
        payload.update(kwargs)

        try:
            spot = float(payload["spot"])
            strike = float(payload["strike"])
            time_to_expiry = float(payload["time_to_expiry"])
            risk_free_rate = float(payload["risk_free_rate"])
            volatility = float(payload["volatility"])
            option_type = str(payload.get("option_type", "call")).lower()
        except KeyError as exc:
            return SkillResult.error_result(f"Missing required parameter: {exc.args[0]}")
        except (TypeError, ValueError) as exc:
            return SkillResult.error_result(f"Invalid parameter type: {exc}")

        if option_type not in {"call", "put"}:
            return SkillResult.error_result("option_type must be 'call' or 'put'")
        if spot <= 0 or strike <= 0:
            return SkillResult.error_result("spot and strike must be positive")
        if time_to_expiry < 0:
            return SkillResult.error_result("time_to_expiry must be non-negative")
        if volatility < 0:
            return SkillResult.error_result("volatility must be non-negative")

        discounted_strike = strike * math.exp(-risk_free_rate * time_to_expiry)

        if time_to_expiry == 0:
            return SkillResult.success_result(
                self._expiry_boundary(spot, strike, option_type),
                {
                    "method": "expiry_boundary",
                    "option_type": option_type,
                },
            )

        if volatility == 0:
            return SkillResult.success_result(
                self._zero_volatility(spot, strike, time_to_expiry, risk_free_rate, option_type),
                {
                    "method": "zero_volatility",
                    "option_type": option_type,
                },
            )

        sqrt_t = math.sqrt(time_to_expiry)
        sigma_sqrt_t = volatility * sqrt_t

        d1 = (math.log(spot / strike) + (risk_free_rate + 0.5 * volatility * volatility) * time_to_expiry) / sigma_sqrt_t
        d2 = d1 - sigma_sqrt_t

        nd1 = _norm_cdf(d1)
        nd2 = _norm_cdf(d2)
        pdf_d1 = _norm_pdf(d1)

        if option_type == "call":
            price = spot * nd1 - discounted_strike * nd2
            delta = nd1
            theta = (
                -(spot * pdf_d1 * volatility) / (2.0 * sqrt_t)
                - risk_free_rate * discounted_strike * nd2
            ) / 365.0
            rho = (strike * time_to_expiry * math.exp(-risk_free_rate * time_to_expiry) * nd2) / 100.0
            intrinsic_value = max(spot - strike, 0.0)
        else:
            n_minus_d1 = _norm_cdf(-d1)
            n_minus_d2 = _norm_cdf(-d2)
            price = discounted_strike * n_minus_d2 - spot * n_minus_d1
            delta = nd1 - 1.0
            theta = (
                -(spot * pdf_d1 * volatility) / (2.0 * sqrt_t)
                + risk_free_rate * discounted_strike * n_minus_d2
            ) / 365.0
            rho = -(strike * time_to_expiry * math.exp(-risk_free_rate * time_to_expiry) * n_minus_d2) / 100.0
            intrinsic_value = max(strike - spot, 0.0)

        gamma = pdf_d1 / (spot * volatility * sqrt_t)
        vega = (spot * pdf_d1 * sqrt_t) / 100.0
        time_value = max(price - intrinsic_value, 0.0)

        return SkillResult.success_result(
            {
                "price": price,
                "delta": delta,
                "gamma": gamma,
                "theta": theta,
                "vega": vega,
                "rho": rho,
                "intrinsic_value": intrinsic_value,
                "time_value": time_value,
                "d1": d1,
                "d2": d2,
            },
            {
                "method": "black_scholes_merton",
                "option_type": option_type,
            },
        )

    def _expiry_boundary(self, spot: float, strike: float, option_type: str) -> dict[str, float]:
        if option_type == "call":
            intrinsic = max(spot - strike, 0.0)
            delta = 1.0 if spot > strike else 0.0 if spot < strike else 0.5
        else:
            intrinsic = max(strike - spot, 0.0)
            delta = -1.0 if spot < strike else 0.0 if spot > strike else -0.5

        return {
            "price": intrinsic,
            "delta": delta,
            "gamma": 0.0,
            "theta": 0.0,
            "vega": 0.0,
            "rho": 0.0,
            "intrinsic_value": intrinsic,
            "time_value": 0.0,
            "d1": 0.0,
            "d2": 0.0,
        }

    def _zero_volatility(
        self,
        spot: float,
        strike: float,
        time_to_expiry: float,
        risk_free_rate: float,
        option_type: str,
    ) -> dict[str, float]:
        discounted_strike = strike * math.exp(-risk_free_rate * time_to_expiry)

        if option_type == "call":
            price = max(spot - discounted_strike, 0.0)
            delta = 1.0 if spot > discounted_strike else 0.0 if spot < discounted_strike else 0.5
            intrinsic = max(spot - strike, 0.0)
            rho = (time_to_expiry * discounted_strike) / 100.0 if price > 0 else 0.0
        else:
            price = max(discounted_strike - spot, 0.0)
            delta = -1.0 if spot < discounted_strike else 0.0 if spot > discounted_strike else -0.5
            intrinsic = max(strike - spot, 0.0)
            rho = -(time_to_expiry * discounted_strike) / 100.0 if price > 0 else 0.0

        return {
            "price": price,
            "delta": delta,
            "gamma": 0.0,
            "theta": 0.0,
            "vega": 0.0,
            "rho": rho,
            "intrinsic_value": intrinsic,
            "time_value": max(price - intrinsic, 0.0),
            "d1": 0.0,
            "d2": 0.0,
        }
