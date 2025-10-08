"""Project orchestration for construction takeoffs."""

from __future__ import annotations

import pathlib
from dataclasses import dataclass

from .human_review import ReviewChecklist
from .exporters.spreadsheet import SpreadsheetExporter
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

        print(self.review.summarize())
        print(f"Estimate exported to {self.config.output_path}")
