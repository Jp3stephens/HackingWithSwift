"""Export markup metadata and overlays for reviewed drawing elements."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Optional

from .drawings import DrawingElement
from .overlays import export_markup_previews, export_pdf_overlays


@dataclass
class MarkupExport:
    """Paths to exported markup artifacts."""

    metadata: Optional[Path]
    overlays: List[Path]
    previews: List[Path]


def export_markups(elements: Iterable[DrawingElement], output_path: Path) -> MarkupExport:
    """Persist markup metadata and overlay PDFs alongside the generated estimate."""

    metadata_path = _export_metadata(elements, output_path)
    overlay_paths = export_pdf_overlays(elements, output_path.parent)
    preview_paths = export_markup_previews(elements, output_path.parent)
    return MarkupExport(metadata=metadata_path, overlays=overlay_paths, previews=preview_paths)


def collect_markup_metadata(elements: Iterable[DrawingElement]) -> List[dict]:
    entries: List[dict] = []

    for element in elements:
        bbox_raw = element.metadata.get("markup_bbox")
        if not bbox_raw:
            continue
        try:
            coords = [float(value) for value in bbox_raw.split(",")]
        except ValueError:
            continue
        if len(coords) != 4:
            continue
        entries.append(
            {
                "element_id": element.id,
                "trade": element.trade,
                "category": element.category,
                "source": element.metadata.get("source"),
                "bounding_box": coords,
            }
        )

    return entries


def _export_metadata(elements: Iterable[DrawingElement], output_path: Path) -> Optional[Path]:
    markups = collect_markup_metadata(elements)

    if not markups:
        return None

    markup_path = output_path.with_suffix(output_path.suffix + ".markups.json")
    markup_path.write_text(json.dumps({"markups": markups}, indent=2))
    return markup_path

