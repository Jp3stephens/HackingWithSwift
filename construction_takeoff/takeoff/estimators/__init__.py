"""Trade estimator registry."""

from __future__ import annotations

from typing import Dict, Type

from .base import BaseTradeEstimator
from .concrete import ConcreteEstimator

TRADE_REGISTRY: Dict[str, Type[BaseTradeEstimator]] = {
    ConcreteEstimator.trade_name: ConcreteEstimator,
}

__all__ = ["BaseTradeEstimator", "ConcreteEstimator", "TRADE_REGISTRY"]
