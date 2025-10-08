"""Utilities for rendering markup overlays on drawing PDFs."""

from __future__ import annotations

import base64
import io
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Tuple

try:  # pragma: no cover - optional dependency for rendering overlays
    from pypdf import PdfReader, PdfWriter  # type: ignore
    from pypdf.generic import (  # type: ignore
        ArrayObject,
        DictionaryObject,
        FloatObject,
        NameObject,
        NumberObject,
        TextStringObject,
    )
except ImportError:  # pragma: no cover - allow environments without pypdf
    PdfReader = None  # type: ignore
    PdfWriter = None  # type: ignore
    ArrayObject = None  # type: ignore
    DictionaryObject = None  # type: ignore
    FloatObject = None  # type: ignore
    NameObject = None  # type: ignore
    NumberObject = None  # type: ignore
    TextStringObject = None  # type: ignore

SUPPORTS_PDF_OVERLAYS = PdfReader is not None and PdfWriter is not None

from .drawings import DrawingElement


@dataclass
class MarkupOverlay:
    """Represents an annotated PDF produced for a set of bounding boxes."""

    source: Path
    filename: str
    payload: bytes

    def as_data_url(self) -> str:
        """Return the PDF payload encoded as a data URL for easy embedding."""

        encoded = base64.b64encode(self.payload).decode("ascii")
        return f"data:application/pdf;base64,{encoded}"


def build_pdf_overlays(elements: Iterable[DrawingElement]) -> List[MarkupOverlay]:
    """Create annotated PDF overlays for elements that include markup bounding boxes."""

    if not SUPPORTS_PDF_OVERLAYS:
        return []

    grouped = _group_elements(elements)
    overlays: List[MarkupOverlay] = []

    for source_path, pages in grouped.items():
        if not source_path.exists():
            continue

        reader = PdfReader(str(source_path))
        writer = PdfWriter()

        for index, page in enumerate(reader.pages):
            annotations = pages.get(index, [])
            if annotations:
                for element, coords in annotations:
                    rect = _normalized_rect(coords, page.mediabox.width, page.mediabox.height)
                    if rect is None:
                        continue
                    annotation = _square_annotation(rect, element)
                    _attach_annotation(page, annotation)
            writer.add_page(page)

        buffer = io.BytesIO()
        writer.write(buffer)
        filename = f"{source_path.stem}.markup.pdf"
        overlays.append(MarkupOverlay(source=source_path, filename=filename, payload=buffer.getvalue()))

    return overlays


def export_pdf_overlays(elements: Iterable[DrawingElement], directory: Path) -> List[Path]:
    """Persist overlay PDFs to ``directory`` and return the generated paths."""

    if not SUPPORTS_PDF_OVERLAYS:
        return []

    directory.mkdir(parents=True, exist_ok=True)
    paths: List[Path] = []
    for overlay in build_pdf_overlays(elements):
        target = directory / overlay.filename
        target.write_bytes(overlay.payload)
        paths.append(target)
    return paths


def _group_elements(
    elements: Iterable[DrawingElement],
) -> Dict[Path, Dict[int, List[Tuple[DrawingElement, Tuple[float, float, float, float]]]]]:
    grouped: Dict[Path, Dict[int, List[Tuple[DrawingElement, Tuple[float, float, float, float]]]]] = {}

    for element in elements:
        bbox_raw = element.metadata.get("markup_bbox")
        source = element.metadata.get("source")
        if not bbox_raw or not source:
            continue

        parsed = _parse_source(source)
        if not parsed:
            continue

        pdf_path, page_index = parsed
        coords = _parse_bbox(bbox_raw)
        if coords is None:
            continue

        grouped.setdefault(pdf_path, {}).setdefault(page_index, []).append((element, coords))

    return grouped


def _parse_source(source: str) -> Tuple[Path, int] | None:
    if "#page" not in source.lower():
        return None

    path_part, _, page_part = source.partition("#page")
    try:
        page_index = int(page_part) - 1
    except ValueError:
        return None
    if page_index < 0:
        return None

    return Path(path_part), page_index


def _parse_bbox(raw: str) -> Tuple[float, float, float, float] | None:
    parts = raw.split(",")
    if len(parts) != 4:
        return None

    try:
        coords = tuple(float(part) for part in parts)  # type: ignore[assignment]
    except ValueError:
        return None

    x1, y1, x2, y2 = coords
    if x1 == x2 or y1 == y2:
        return None

    return coords  # type: ignore[return-value]


def _normalized_rect(
    coords: Tuple[float, float, float, float],
    width: float,
    height: float,
) -> Tuple[float, float, float, float] | None:
    x1, y1, x2, y2 = coords

    if not (0.0 <= x1 <= 1.0 and 0.0 <= x2 <= 1.0 and 0.0 <= y1 <= 1.0 and 0.0 <= y2 <= 1.0):
        return None

    if x2 < x1:
        x1, x2 = x2, x1
    if y2 < y1:
        y1, y2 = y2, y1

    # The markup entry captures coordinates assuming the origin is the top-left
    # corner. Convert to PDF coordinates, whose origin is bottom-left.
    left = max(0.0, min(width, width * x1))
    right = max(0.0, min(width, width * x2))
    bottom = max(0.0, min(height, height * (1 - y2)))
    top = max(0.0, min(height, height * (1 - y1)))

    if left == right or bottom == top:
        return None

    return left, bottom, right, top


def _square_annotation(rect: Tuple[float, float, float, float], element: DrawingElement) -> DictionaryObject:
    if DictionaryObject is None:
        raise RuntimeError("PDF overlay support requires the 'pypdf' package")

    left, bottom, right, top = rect
    annotation = DictionaryObject()
    annotation.update(
        {
            NameObject("/Type"): NameObject("/Annot"),
            NameObject("/Subtype"): NameObject("/Square"),
            NameObject("/Rect"): ArrayObject([
                FloatObject(left),
                FloatObject(bottom),
                FloatObject(right),
                FloatObject(top),
            ]),
            NameObject("/C"): ArrayObject([
                FloatObject(0.95),
                FloatObject(0.45),
                FloatObject(0.1),
            ]),
            NameObject("/CA"): FloatObject(0.2),
            NameObject("/Border"): ArrayObject([
                NumberObject(0),
                NumberObject(0),
                NumberObject(2),
            ]),
            NameObject("/Contents"): TextStringObject(
                f"{element.category.title()} ({element.id})"
            ),
        }
    )
    return annotation


def _attach_annotation(page, annotation: DictionaryObject) -> None:
    if ArrayObject is None or NameObject is None:
        raise RuntimeError("PDF overlay support requires the 'pypdf' package")

    if hasattr(page, "add_annotation"):
        page.add_annotation(annotation)
        return

    annots = page.get(NameObject("/Annots"))
    if annots is None:
        annots = ArrayObject()
        page[NameObject("/Annots")] = annots
    annots.append(annotation)

