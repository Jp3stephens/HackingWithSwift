"""Human-in-the-loop helpers for the takeoff workflow."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, List


@dataclass
class ReviewItem:
    """An assumption or decision that should be confirmed by a human."""

    message: str
    severity: str = "info"  # Could be "info", "warning", or "critical".


class ReviewChecklist:
    """Container used to accumulate review items during estimation."""

    def __init__(self) -> None:
        self._items: List[ReviewItem] = []

    def add(self, message: str, severity: str = "info") -> None:
        self._items.append(ReviewItem(message=message, severity=severity))

    def extend(self, items: Iterable[ReviewItem]) -> None:
        for item in items:
            self.add(item.message, item.severity)

    @property
    def items(self) -> List[ReviewItem]:
        return list(self._items)

    def summarize(self) -> str:
        if not self._items:
            return "No human review items."

        lines = ["Human review required for the following items:"]
        for idx, item in enumerate(self._items, start=1):
            lines.append(f"  {idx}. [{item.severity.upper()}] {item.message}")
        return "\n".join(lines)
