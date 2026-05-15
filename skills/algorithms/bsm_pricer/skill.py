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
    """Black-Scholes-Merton option pricing with Greeks and IV solver."""

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
        ]

    async def execute(self, params: dict[str, Any] | None = None, **kwargs: Any) -> SkillResult:
        payload = dict(params or {})
        payload.update(kwargs)

        mode = str(payload.get("mode", "price")).lower()
        if mode == "price":
            return self._price_option(payload)
        if mode == "implied_volatility":
            return self._solve_implied_volatility(payload)
        return SkillResult.error_result("mode must be 'price' or 'implied_volatility'")

    def _price_option(self, payload: dict[str, Any]) -> SkillResult:
        try:
            spot = float(payload["spot"])
            strike = float(payload["strike"])
            time_to_expiry = float(payload["time_to_expiry"])
            risk_free_rate = float(payload["risk_free_rate"])
            volatility = float(payload["volatility"])
            dividend_yield = float(payload.get("dividend_yield", 0.0))
            option_type = str(payload.get("option_type", "call")).lower()
        except KeyError as exc:
            return SkillResult.error_result(f"Missing required parameter: {exc.args[0]}")
        except (TypeError, ValueError) as exc:
            return SkillResult.error_result(f"Invalid parameter type: {exc}")

        error = self._validate_inputs(
            spot=spot,
            strike=strike,
            time_to_expiry=time_to_expiry,
            risk_free_rate=risk_free_rate,
            volatility=volatility,
            option_type=option_type,
            dividend_yield=dividend_yield,
        )
        if error:
            return SkillResult.error_result(error)

        metrics = self._bsm_price(
            spot=spot,
            strike=strike,
            time_to_expiry=time_to_expiry,
            risk_free_rate=risk_free_rate,
            volatility=volatility,
            option_type=option_type,
            dividend_yield=dividend_yield,
        )

        return SkillResult.success_result(
            {
                "price": metrics["price"],
                "delta": metrics["delta"],
                "gamma": metrics["gamma"],
                "theta": metrics["theta"],
                "vega": metrics["vega"],
                "rho": metrics["rho"],
                "intrinsic_value": metrics["intrinsic_value"],
                "time_value": metrics["time_value"],
                "d1": metrics["d1"],
                "d2": metrics["d2"],
            },
            {
                "method": "black_scholes_merton",
                "option_type": option_type,
                "mode": "price",
            },
        )

    def _solve_implied_volatility(self, payload: dict[str, Any]) -> SkillResult:
        try:
            spot = float(payload["spot"])
            strike = float(payload["strike"])
            time_to_expiry = float(payload["time_to_expiry"])
            risk_free_rate = float(payload["risk_free_rate"])
            market_price = float(payload["market_price"])
            dividend_yield = float(payload.get("dividend_yield", 0.0))
            option_type = str(payload.get("option_type", "call")).lower()
        except KeyError as exc:
            return SkillResult.error_result(f"Missing required parameter: {exc.args[0]}")
        except (TypeError, ValueError) as exc:
            return SkillResult.error_result(f"Invalid parameter type: {exc}")

        if market_price <= 0:
            return SkillResult.error_result("market_price is required for IV solving")
        if time_to_expiry <= 0:
            return SkillResult.error_result("time_to_expiry must be positive for IV solving")

        error = self._validate_inputs(
            spot=spot,
            strike=strike,
            time_to_expiry=time_to_expiry,
            risk_free_rate=risk_free_rate,
            volatility=0.2,
            option_type=option_type,
            dividend_yield=dividend_yield,
        )
        if error:
            return SkillResult.error_result(error)

        sigma = 0.3
        max_iter = 100
        tolerance = 1e-6

        for i in range(max_iter):
            metrics = self._bsm_price(
                spot=spot,
                strike=strike,
                time_to_expiry=time_to_expiry,
                risk_free_rate=risk_free_rate,
                volatility=sigma,
                option_type=option_type,
                dividend_yield=dividend_yield,
            )
            diff = metrics["price"] - market_price
            if abs(diff) < tolerance:
                return SkillResult.success_result(
                    {
                        "implied_volatility": sigma,
                        "iterations": i + 1,
                        "converged": True,
                    },
                    {
                        "method": "newton_raphson",
                        "mode": "implied_volatility",
                    },
                )

            vega_raw = metrics["vega_raw"]
            if abs(vega_raw) < 1e-10:
                return self._bisection_iv(
                    spot=spot,
                    strike=strike,
                    time_to_expiry=time_to_expiry,
                    risk_free_rate=risk_free_rate,
                    market_price=market_price,
                    option_type=option_type,
                    dividend_yield=dividend_yield,
                )

            sigma -= diff / vega_raw
            sigma = max(0.001, min(sigma, 5.0))

        return SkillResult.success_result(
            {
                "implied_volatility": sigma,
                "iterations": max_iter,
                "converged": False,
            },
            {
                "method": "newton_raphson",
                "mode": "implied_volatility",
                "warning": "did not converge",
            },
        )

    def _bisection_iv(
        self,
        *,
        spot: float,
        strike: float,
        time_to_expiry: float,
        risk_free_rate: float,
        market_price: float,
        option_type: str,
        dividend_yield: float,
    ) -> SkillResult:
        lo, hi = 0.001, 5.0
        tolerance = 1e-6

        for i in range(200):
            mid = (lo + hi) / 2
            price = self._bsm_price(
                spot=spot,
                strike=strike,
                time_to_expiry=time_to_expiry,
                risk_free_rate=risk_free_rate,
                volatility=mid,
                option_type=option_type,
                dividend_yield=dividend_yield,
            )["price"]

            diff = price - market_price
            if abs(diff) < tolerance:
                return SkillResult.success_result(
                    {
                        "implied_volatility": mid,
                        "iterations": i + 1,
                        "converged": True,
                    },
                    {
                        "method": "bisection",
                        "mode": "implied_volatility",
                    },
                )

            if price > market_price:
                hi = mid
            else:
                lo = mid

        return SkillResult.success_result(
            {
                "implied_volatility": (lo + hi) / 2,
                "iterations": 200,
                "converged": False,
            },
            {
                "method": "bisection",
                "mode": "implied_volatility",
                "warning": "did not converge",
            },
        )

    def _bsm_price(
        self,
        *,
        spot: float,
        strike: float,
        time_to_expiry: float,
        risk_free_rate: float,
        volatility: float,
        option_type: str,
        dividend_yield: float,
    ) -> dict[str, float]:
        if time_to_expiry == 0:
            return self._expiry_boundary(spot, strike, option_type)

        if volatility == 0:
            return self._zero_volatility(
                spot=spot,
                strike=strike,
                time_to_expiry=time_to_expiry,
                risk_free_rate=risk_free_rate,
                option_type=option_type,
                dividend_yield=dividend_yield,
            )

        sqrt_t = math.sqrt(time_to_expiry)
        sigma_sqrt_t = volatility * sqrt_t
        discounted_spot = spot * math.exp(-dividend_yield * time_to_expiry)
        discounted_strike = strike * math.exp(-risk_free_rate * time_to_expiry)

        d1 = (
            math.log(spot / strike)
            + (risk_free_rate - dividend_yield + 0.5 * volatility * volatility) * time_to_expiry
        ) / sigma_sqrt_t
        d2 = d1 - sigma_sqrt_t

        nd1 = _norm_cdf(d1)
        nd2 = _norm_cdf(d2)
        pdf_d1 = _norm_pdf(d1)

        if option_type == "call":
            price = discounted_spot * nd1 - discounted_strike * nd2
            delta = math.exp(-dividend_yield * time_to_expiry) * nd1
            theta = (
                -(discounted_spot * pdf_d1 * volatility) / (2.0 * sqrt_t)
                - risk_free_rate * discounted_strike * nd2
                + dividend_yield * discounted_spot * nd1
            ) / 365.0
            rho = (strike * time_to_expiry * math.exp(-risk_free_rate * time_to_expiry) * nd2) / 100.0
            intrinsic_value = max(spot - strike, 0.0)
        else:
            n_minus_d1 = _norm_cdf(-d1)
            n_minus_d2 = _norm_cdf(-d2)
            price = discounted_strike * n_minus_d2 - discounted_spot * n_minus_d1
            delta = math.exp(-dividend_yield * time_to_expiry) * (nd1 - 1.0)
            theta = (
                -(discounted_spot * pdf_d1 * volatility) / (2.0 * sqrt_t)
                + risk_free_rate * discounted_strike * n_minus_d2
                - dividend_yield * discounted_spot * n_minus_d1
            ) / 365.0
            rho = -(strike * time_to_expiry * math.exp(-risk_free_rate * time_to_expiry) * n_minus_d2) / 100.0
            intrinsic_value = max(strike - spot, 0.0)

        gamma = (math.exp(-dividend_yield * time_to_expiry) * pdf_d1) / (spot * volatility * sqrt_t)
        vega_raw = discounted_spot * pdf_d1 * sqrt_t
        vega = vega_raw / 100.0

        return {
            "price": price,
            "delta": delta,
            "gamma": gamma,
            "theta": theta,
            "vega": vega,
            "vega_raw": vega_raw,
            "rho": rho,
            "intrinsic_value": intrinsic_value,
            "time_value": max(price - intrinsic_value, 0.0),
            "d1": d1,
            "d2": d2,
        }

    def _validate_inputs(
        self,
        *,
        spot: float,
        strike: float,
        time_to_expiry: float,
        risk_free_rate: float,
        volatility: float,
        option_type: str,
        dividend_yield: float,
    ) -> str | None:
        del risk_free_rate

        if option_type not in {"call", "put"}:
            return "option_type must be 'call' or 'put'"
        if spot <= 0 or strike <= 0:
            return "spot and strike must be positive"
        if time_to_expiry < 0:
            return "time_to_expiry must be non-negative"
        if volatility < 0:
            return "volatility must be non-negative"
        if dividend_yield < 0:
            return "dividend_yield must be non-negative"
        return None

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
            "vega_raw": 0.0,
            "rho": 0.0,
            "intrinsic_value": intrinsic,
            "time_value": 0.0,
            "d1": 0.0,
            "d2": 0.0,
        }

    def _zero_volatility(
        self,
        *,
        spot: float,
        strike: float,
        time_to_expiry: float,
        risk_free_rate: float,
        option_type: str,
        dividend_yield: float,
    ) -> dict[str, float]:
        discounted_spot = spot * math.exp(-dividend_yield * time_to_expiry)
        discounted_strike = strike * math.exp(-risk_free_rate * time_to_expiry)

        if option_type == "call":
            price = max(discounted_spot - discounted_strike, 0.0)
            delta_scale = math.exp(-dividend_yield * time_to_expiry)
            delta = delta_scale if discounted_spot > discounted_strike else 0.0 if discounted_spot < discounted_strike else 0.5 * delta_scale
            intrinsic = max(spot - strike, 0.0)
            rho = (time_to_expiry * discounted_strike) / 100.0 if price > 0 else 0.0
        else:
            price = max(discounted_strike - discounted_spot, 0.0)
            delta_scale = math.exp(-dividend_yield * time_to_expiry)
            delta = -delta_scale if discounted_spot < discounted_strike else 0.0 if discounted_spot > discounted_strike else -0.5 * delta_scale
            intrinsic = max(strike - spot, 0.0)
            rho = -(time_to_expiry * discounted_strike) / 100.0 if price > 0 else 0.0

        return {
            "price": price,
            "delta": delta,
            "gamma": 0.0,
            "theta": 0.0,
            "vega": 0.0,
            "vega_raw": 0.0,
            "rho": rho,
            "intrinsic_value": intrinsic,
            "time_value": max(price - intrinsic, 0.0),
            "d1": 0.0,
            "d2": 0.0,
        }
