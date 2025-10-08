"""High-level helpers for running trade takeoffs programmatically."""

from __future__ import annotations

import pathlib
from dataclasses import dataclass
from typing import List

from .drawings import DrawingElement, DrawingLoader, group_elements_by_trade
from .estimators import TRADE_REGISTRY, BaseTradeEstimator
from .estimators.base import TakeoffResult
from .human_review import ReviewChecklist
from .manual import collect_manual_measurements


@dataclass
class TakeoffRun:
    """Container describing the result of a takeoff execution."""

    result: TakeoffResult
    review: ReviewChecklist
    trade: str
    drawing_count: int
    element_count: int
    elements: List[DrawingElement]


def run_trade_takeoff(
    trade: str,
    input_path: pathlib.Path,
    *,
    review: ReviewChecklist | None = None,
) -> TakeoffRun:
    """Execute a trade takeoff and return structured results."""

    trade_key = trade.lower()
    drawings = list(DrawingLoader(input_path, default_trade=trade_key).load())
    grouped = group_elements_by_trade(drawings)

    if trade_key not in TRADE_REGISTRY:
        available = ", ".join(sorted(TRADE_REGISTRY))
        raise ValueError(f"Unsupported trade '{trade}'. Available trades: {available}")

    review = review or ReviewChecklist()

    estimator_cls: type[BaseTradeEstimator] = TRADE_REGISTRY[trade_key]
    estimator = estimator_cls(review=review)

    elements = list(grouped.get(trade_key, []))
    if not elements:
        review.add(
            f"No drawing elements found for trade '{trade}'. Upload a data set that includes {trade_key} items.",
            severity="warning",
        )

    collect_manual_measurements(trade_key, elements, review)

    result = estimator.run(elements)

    return TakeoffRun(
        result=result,
        review=review,
        trade=trade_key,
        drawing_count=len(drawings),
        element_count=len(elements),
        elements=elements,
    )
