"""Phase attribution analysis — breaks down backtest performance by Wyckoff phase."""

from __future__ import annotations

from typing import Any

from src.models.backtest import PhaseAttributionRow, PipelineBacktestTrade


class PhaseAttribution:
    """Analyze per-phase performance contribution from backtest trades."""

    @staticmethod
    def analyze(
        trades: list[PipelineBacktestTrade],
        daily_decisions: list[dict[str, Any]],
    ) -> list[PhaseAttributionRow]:
        """Break down performance by entry phase.

        Args:
            trades: List of completed trades with phase info.
            daily_decisions: Daily decision records with phase labels.

        Returns:
            List of PhaseAttributionRow, one per phase.
        """
        if not trades:
            return []

        # Group trades by entry phase
        phase_trades: dict[str, list[PipelineBacktestTrade]] = {}
        for t in trades:
            phase = t.entry_phase or "unknown"
            if phase not in phase_trades:
                phase_trades[phase] = []
            phase_trades[phase].append(t)

        total_pnl = sum(t.pnl for t in trades if t.pnl is not None)

        # Count phase occurrences in daily decisions for transition analysis
        phase_sequence: list[str] = [
            d.get("phase", "unknown") for d in daily_decisions if "phase" in d
        ]

        rows: list[PhaseAttributionRow] = []
        for phase, ptrades in sorted(phase_trades.items()):
            count = len(ptrades)
            avg_return = sum(t.pnl_percent for t in ptrades if t.pnl_percent is not None) / count if count > 0 else 0.0
            wins = sum(1 for t in ptrades if t.pnl is not None and t.pnl > 0)
            win_rate = wins / count if count > 0 else 0.0
            phase_pnl = sum(t.pnl for t in ptrades if t.pnl is not None)
            contribution = (phase_pnl / total_pnl * 100) if total_pnl != 0 else 0.0

            # Transition alpha: measure return when transitioning from this phase
            transition_alpha = PhaseAttribution._calculate_transition_alpha(
                phase, phase_sequence, daily_decisions
            )

            rows.append(PhaseAttributionRow(
                phase=phase,
                trades_count=count,
                avg_return=round(avg_return, 2),
                win_rate=round(win_rate * 100, 1),
                contribution_to_total=round(contribution, 1),
                transition_alpha=transition_alpha,
            ))

        return rows

    @staticmethod
    def _calculate_transition_alpha(
        phase: str,
        phase_sequence: list[str],
        daily_decisions: list[dict[str, Any]],
    ) -> float | None:
        """Calculate average return in the bar following a phase transition.

        Returns None if no transitions detected.
        """
        if len(phase_sequence) < 2:
            return None

        transition_returns: list[float] = []
        for i in range(len(phase_sequence) - 1):
            if phase_sequence[i] == phase and phase_sequence[i + 1] != phase:
                # Transition detected: get next bar's return
                if i + 1 < len(daily_decisions):
                    curr_price = daily_decisions[i].get("price", 0)
                    next_price = daily_decisions[i + 1].get("price", 0)
                    if curr_price > 0:
                        ret = (next_price - curr_price) / curr_price * 100
                        transition_returns.append(ret)

        if not transition_returns:
            return None

        return round(sum(transition_returns) / len(transition_returns), 2)
