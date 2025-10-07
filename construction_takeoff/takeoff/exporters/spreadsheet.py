"""Spreadsheet export utilities."""

from __future__ import annotations

import csv
import io
import pathlib
from typing import Any, TextIO

from ..estimators.base import TakeoffResult


class SpreadsheetExporter:
    """Export a takeoff result to CSV compatible with spreadsheets."""

    def __init__(self, output_path: pathlib.Path | TextIO) -> None:
        self.output_path = output_path

    def export(self, result: TakeoffResult) -> None:
        writer, handle = _writer_for_output(self.output_path)
        _write_rows(writer, result)
        if handle is not None:
            handle.close()


def render_csv(result: TakeoffResult) -> str:
    """Return the CSV representation of a takeoff result as a string."""

    buffer = io.StringIO()
    writer = csv.writer(buffer)
    _write_rows(writer, result)
    return buffer.getvalue()


def _writer_for_output(output: pathlib.Path | TextIO) -> tuple[Any, TextIO | None]:
    if isinstance(output, pathlib.Path):
        handle = output.open("w", newline="")
        writer = csv.writer(handle)
        return writer, handle

    writer = csv.writer(output)
    return writer, None


def _write_rows(writer: Any, result: TakeoffResult) -> None:
        header = [
            "Description",
            "Quantity",
            "Unit",
            "Material Unit Cost",
            "Material Cost",
            "Labor Hours",
            "Labor Rate ($/hr)",
            "Labor Cost",
        ]

        writer.writerow(header)
        for item in result.line_items:
            writer.writerow(
                [
                    item.description,
                    round(item.quantity, 4),
                    item.unit,
                    round(item.material_unit_cost, 2),
                    round(item.material_cost, 2),
                    round(item.labor_hours, 2),
                    round(item.labor_rate_per_hour, 2),
                    round(item.labor_cost, 2),
                ]
            )

        writer.writerow([])
        writer.writerow(["Summary", "Value"])
        for key, value in result.summary.items():
            writer.writerow([key, round(value, 2)])
