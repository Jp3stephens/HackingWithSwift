"""Project orchestration for construction takeoffs."""

from __future__ import annotations

import pathlib
from dataclasses import dataclass

from .human_review import ReviewChecklist
from .exporters.spreadsheet import SpreadsheetExporter
from .markups import export_markups
from .overlays import get_overlay_support_state
from .service import run_trade_takeoff


@dataclass
class TakeoffConfig:
    trade: str
    input_path: pathlib.Path
    output_path: pathlib.Path


class TakeoffProject:
    """High-level interface for executing a takeoff."""

    def __init__(self, config: TakeoffConfig) -> None:
        self.config = config
        self.review = ReviewChecklist()

    def run(self) -> None:
        run = run_trade_takeoff(self.config.trade, self.config.input_path, review=self.review)

        exporter = SpreadsheetExporter(self.config.output_path)
        exporter.export(run.result)

        markup_export = export_markups(run.elements, self.config.output_path)
        overlay_support = get_overlay_support_state()

        print(self.review.summarize())
        print(f"Estimate exported to {self.config.output_path}")
        if markup_export.metadata:
            print(f"Markup metadata exported to {markup_export.metadata}")
            if not markup_export.overlays and not overlay_support.available:
                message = overlay_support.message
                if message:
                    print(message)
        for overlay_path in markup_export.overlays:
            print(f"Markup overlay exported to {overlay_path}")
