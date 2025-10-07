"""Base classes and utilities for trade estimators."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List

from ..drawings import DrawingElement
from ..human_review import ReviewChecklist


@dataclass
class TakeoffLineItem:
    """Row in the resulting estimate."""

    description: str
    quantity: float
    unit: str
    material_unit_cost: float
    labor_hours_per_unit: float
    labor_rate_per_hour: float

    @property
    def material_cost(self) -> float:
        return self.quantity * self.material_unit_cost

    @property
    def labor_hours(self) -> float:
        return self.quantity * self.labor_hours_per_unit

    @property
    def labor_cost(self) -> float:
        return self.labor_hours * self.labor_rate_per_hour


@dataclass
class TakeoffResult:
    """Complete result of an estimator."""

    line_items: List[TakeoffLineItem]
    summary: Dict[str, float]


class BaseTradeEstimator:
    """Common interface for all trade estimators."""

    trade_name: str

    def __init__(self, *, review: ReviewChecklist) -> None:
        self.review = review

    def filter_elements(self, elements: Iterable[DrawingElement]) -> List[DrawingElement]:
        return [element for element in elements if element.trade == self.trade_name]

    def run(self, elements: Iterable[DrawingElement]) -> TakeoffResult:
        trade_elements = self.filter_elements(elements)
        return self.estimate(trade_elements)

    def estimate(self, elements: Iterable[DrawingElement]) -> TakeoffResult:
        raise NotImplementedError
