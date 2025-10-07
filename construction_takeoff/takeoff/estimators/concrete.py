"""Concrete trade estimator implementation."""

from __future__ import annotations

import math
from typing import Dict, Iterable, List

from .base import BaseTradeEstimator, TakeoffLineItem, TakeoffResult
from ..drawings import DrawingElement
from ..human_review import ReviewChecklist


class ConcreteEstimator(BaseTradeEstimator):
    trade_name = "concrete"

    def __init__(self, *, review: ReviewChecklist) -> None:
        super().__init__(review=review)
        # Default pricing/production rates; in production these could be loaded from a DB.
        self.material_prices = {
            "ready_mix_cy": 135.0,  # $/cubic yard
            "rebar_lb": 0.75,
            "formwork_sf": 4.5,
        }
        self.labor_rates = {
            "concrete_crew": 65.0,  # $/labor hour
        }
        self.production_rates = {
            "place_finish_cy_per_hour": 8.0,
            "rebar_lb_per_hour": 120.0,
            "formwork_sf_per_hour": 40.0,
        }

    def estimate(self, elements: Iterable[DrawingElement]) -> TakeoffResult:
        line_items: List[TakeoffLineItem] = []
        summary: Dict[str, float] = {
            "concrete_cy": 0.0,
            "rebar_lb": 0.0,
            "formwork_sf": 0.0,
            "labor_hours": 0.0,
            "material_cost": 0.0,
            "labor_cost": 0.0,
        }

        for element in elements:
            if element.category == "slab":
                cy = self._slab_volume_cy(element)
                formwork = element.geometry.get("area_sqft", 0.0)
                rebar = cy * 250  # lbs per cubic yard (simplified assumption)
                line_items.extend(
                    [
                        self._line_item(
                            description=f"Concrete slab {element.id}",
                            quantity=cy,
                            unit="cy",
                            material_price=self.material_prices["ready_mix_cy"],
                            production_rate=self.production_rates["place_finish_cy_per_hour"],
                        ),
                        self._line_item(
                            description=f"Rebar for slab {element.id}",
                            quantity=rebar,
                            unit="lb",
                            material_price=self.material_prices["rebar_lb"],
                            production_rate=self.production_rates["rebar_lb_per_hour"],
                        ),
                        self._line_item(
                            description=f"Slab formwork {element.id}",
                            quantity=formwork,
                            unit="sf",
                            material_price=self.material_prices["formwork_sf"],
                            production_rate=self.production_rates["formwork_sf_per_hour"],
                        ),
                    ]
                )
                summary["concrete_cy"] += cy
                summary["rebar_lb"] += rebar
                summary["formwork_sf"] += formwork

            elif element.category == "wall":
                cy = self._wall_volume_cy(element)
                formwork = element.geometry.get("length_ft", 0.0) * element.geometry.get("height_ft", 0.0) * 2
                rebar = cy * 180
                line_items.extend(
                    [
                        self._line_item(
                            description=f"Concrete wall {element.id}",
                            quantity=cy,
                            unit="cy",
                            material_price=self.material_prices["ready_mix_cy"],
                            production_rate=self.production_rates["place_finish_cy_per_hour"],
                        ),
                        self._line_item(
                            description=f"Rebar for wall {element.id}",
                            quantity=rebar,
                            unit="lb",
                            material_price=self.material_prices["rebar_lb"],
                            production_rate=self.production_rates["rebar_lb_per_hour"],
                        ),
                        self._line_item(
                            description=f"Wall formwork {element.id}",
                            quantity=formwork,
                            unit="sf",
                            material_price=self.material_prices["formwork_sf"],
                            production_rate=self.production_rates["formwork_sf_per_hour"],
                        ),
                    ]
                )
                summary["concrete_cy"] += cy
                summary["rebar_lb"] += rebar
                summary["formwork_sf"] += formwork

            elif element.category == "pier":
                cy = self._pier_volume_cy(element)
                rebar = cy * 120
                line_items.extend(
                    [
                        self._line_item(
                            description=f"Concrete pier {element.id}",
                            quantity=cy,
                            unit="cy",
                            material_price=self.material_prices["ready_mix_cy"],
                            production_rate=self.production_rates["place_finish_cy_per_hour"],
                        ),
                        self._line_item(
                            description=f"Rebar for pier {element.id}",
                            quantity=rebar,
                            unit="lb",
                            material_price=self.material_prices["rebar_lb"],
                            production_rate=self.production_rates["rebar_lb_per_hour"],
                        ),
                    ]
                )
                summary["concrete_cy"] += cy
                summary["rebar_lb"] += rebar

            else:
                self.review.add(
                    f"Concrete estimator encountered unsupported category '{element.category}' for element {element.id}.",
                    severity="warning",
                )

        for item in line_items:
            summary["material_cost"] += item.material_cost
            summary["labor_hours"] += item.labor_hours
            summary["labor_cost"] += item.labor_cost

        return TakeoffResult(line_items=line_items, summary=summary)

    # --- Helpers -----------------------------------------------------------------

    def _line_item(self, *, description: str, quantity: float, unit: str, material_price: float, production_rate: float) -> TakeoffLineItem:
        labor_rate = self.labor_rates["concrete_crew"]
        labor_hours_per_unit = 1 / production_rate if production_rate else 0.0
        return TakeoffLineItem(
            description=description,
            quantity=quantity,
            unit=unit,
            material_unit_cost=material_price,
            labor_hours_per_unit=labor_hours_per_unit,
            labor_rate_per_hour=labor_rate,
        )

    def _slab_volume_cy(self, element: DrawingElement) -> float:
        area = element.geometry.get("area_sqft", 0.0)
        thickness = element.geometry.get("thickness_in", 0.0)
        return area * thickness / 12 / 27

    def _wall_volume_cy(self, element: DrawingElement) -> float:
        length = element.geometry.get("length_ft", 0.0)
        height = element.geometry.get("height_ft", 0.0)
        thickness = element.geometry.get("thickness_in", 0.0)
        return length * height * thickness / 12 / 27

    def _pier_volume_cy(self, element: DrawingElement) -> float:
        diameter = element.geometry.get("diameter_in", 0.0)
        depth = element.geometry.get("depth_ft", 0.0)
        radius_ft = (diameter / 12) / 2
        return math.pi * radius_ft * radius_ft * depth / 27
