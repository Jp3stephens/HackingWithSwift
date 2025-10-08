"""Export markup overlays for reviewed drawing elements."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable, Optional

from .drawings import DrawingElement


def export_markups(elements: Iterable[DrawingElement], output_path: Path) -> Optional[Path]:
    """Persist markup bounding boxes alongside the generated estimate."""

    markups = []
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
        markups.append(
            {
                "element_id": element.id,
                "trade": element.trade,
                "category": element.category,
                "source": element.metadata.get("source"),
                "bounding_box": coords,
            }
        )

    if not markups:
        return None

    markup_path = output_path.with_suffix(output_path.suffix + ".markups.json")
    markup_path.write_text(json.dumps({"markups": markups}, indent=2))
    return markup_path

