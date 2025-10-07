"""Utilities for loading and representing drawing data for takeoffs."""

from __future__ import annotations

import json
import pathlib
import zipfile
from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Optional


@dataclass
class DrawingElement:
    """Single element extracted from a drawing set."""

    id: str
    trade: str
    category: str
    geometry: Dict[str, float]
    metadata: Dict[str, str] = field(default_factory=dict)


@dataclass
class Drawing:
    """Represents a single drawing or level within the project."""

    name: str
    level: Optional[str]
    scale: Optional[str]
    elements: List[DrawingElement]


class DrawingLoader:
    """Load drawing data from a directory or zip archive.

    The loader expects each drawing export to be a JSON file following the
    schema illustrated in ``docs/sample_drawing.json``. All numeric values
    should be expressed in imperial units to align with the estimation logic.
    """

    def __init__(self, input_path: pathlib.Path) -> None:
        self.input_path = input_path

    def load(self) -> Iterable[Drawing]:
        if self.input_path.is_dir():
            yield from self._load_from_directory(self.input_path)
        elif zipfile.is_zipfile(self.input_path):
            yield from self._load_from_zip(self.input_path)
        else:
            raise ValueError(
                f"Unsupported drawing input: {self.input_path}. Expected directory or zip archive."
            )

    def _load_from_directory(self, directory: pathlib.Path) -> Iterable[Drawing]:
        for json_path in sorted(directory.glob("*.json")):
            yield self._load_single(json_path.read_text(), source=str(json_path))

    def _load_from_zip(self, archive_path: pathlib.Path) -> Iterable[Drawing]:
        with zipfile.ZipFile(archive_path) as archive:
            for name in sorted(archive.namelist()):
                if name.lower().endswith(".json"):
                    with archive.open(name) as fh:
                        payload = fh.read().decode("utf-8")
                        yield self._load_single(payload, source=f"{archive_path}:{name}")

    def _load_single(self, payload: str, *, source: str) -> Drawing:
        try:
            data = json.loads(payload)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Failed to parse drawing JSON from {source}: {exc}") from exc

        project_info = data.get("project", {})
        elements = [self._parse_element(item, source=source) for item in data.get("elements", [])]
        return Drawing(
            name=project_info.get("name", pathlib.Path(source).stem),
            level=project_info.get("level"),
            scale=project_info.get("scale"),
            elements=elements,
        )

    def _parse_element(self, item: Dict, *, source: str) -> DrawingElement:
        required_fields = {"id", "trade", "category", "geometry"}
        missing = required_fields - item.keys()
        if missing:
            raise ValueError(f"Element missing fields {missing} in {source}")

        geometry = item["geometry"]
        if not isinstance(geometry, dict):
            raise ValueError(f"Element geometry must be a dict in {source}: {item}")

        metadata = {
            key: value
            for key, value in item.items()
            if key not in {"id", "trade", "category", "geometry"}
        }

        return DrawingElement(
            id=str(item["id"]),
            trade=str(item["trade"]).lower(),
            category=str(item["category"]).lower(),
            geometry={k: float(v) for k, v in geometry.items()},
            metadata=metadata,
        )


def group_elements_by_trade(drawings: Iterable[Drawing]) -> Dict[str, List[DrawingElement]]:
    grouped: Dict[str, List[DrawingElement]] = {}
    for drawing in drawings:
        for element in drawing.elements:
            grouped.setdefault(element.trade, []).append(element)
    return grouped
