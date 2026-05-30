"""Broker implementations for strategy execution.

This directory is allowed to contain only paper / sim / backtest brokers.
Real broker adapters belong in src/integrations/brokers_external/.
"""

from .base import BrokerBase

__all__ = ["BrokerBase"]
