"""Utilities for rendering markup overlays on drawing PDFs."""

from __future__ import annotations

import base64
import importlib
import io
import logging
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

from .drawings import DrawingElement

logger = logging.getLogger(__name__)


@dataclass
class OverlaySupportState:
    """Represents the current overlay capability state."""

    available: bool
    auto_install_attempted: bool = False
    auto_install_error: Optional[str] = None

    @property
    def message(self) -> Optional[str]:
        """Return a human-friendly status message when overlays are unavailable."""

        if self.available:
            return None

        if self.auto_install_attempted and self.auto_install_error:
            return (
                "Automatic installation of the 'pypdf' dependency failed. "
                f"Install 'pypdf>=3.9' manually and retry. ({self.auto_install_error})"
            )

        return (
            "Install the optional 'pypdf' dependency to generate PDF markup "
            "overlays during takeoff runs."
        )


def _load_pypdf():  # pragma: no cover - exercised via integration flow
    """Attempt to import ``pypdf`` and return the relevant classes."""

    try:
        module = importlib.import_module("pypdf")
    except ImportError:
        return None

    try:
        reader = module.PdfReader
        writer = module.PdfWriter
        generic = module.generic
    except AttributeError:
        return None

    return (
        reader,
        writer,
        generic.ArrayObject,
        generic.DictionaryObject,
        generic.FloatObject,
        generic.NameObject,
        generic.NumberObject,
        generic.TextStringObject,
    )


def _set_pdf_api(api) -> None:
    """Assign the pypdf classes to module globals."""

    global PdfReader, PdfWriter, ArrayObject, DictionaryObject, FloatObject
    global NameObject, NumberObject, TextStringObject, SUPPORTS_PDF_OVERLAYS

    (
        PdfReader,
        PdfWriter,
        ArrayObject,
        DictionaryObject,
        FloatObject,
        NameObject,
        NumberObject,
        TextStringObject,
    ) = api

    _overlay_support_state.available = True
    _overlay_support_state.auto_install_error = None
    SUPPORTS_PDF_OVERLAYS = True


def _install_pypdf() -> bool:  # pragma: no cover - depends on environment
    """Attempt to install ``pypdf`` using ``pip`` at runtime."""

    if _overlay_support_state.auto_install_attempted:
        return False

    _overlay_support_state.auto_install_attempted = True

    command = [sys.executable or "python", "-m", "pip", "install", "pypdf>=3.9"]
    try:
        result = subprocess.run(
            command,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
    except Exception as exc:  # pragma: no cover - defensive path
        _overlay_support_state.auto_install_error = str(exc)
        logger.debug("Automatic pypdf installation failed", exc_info=True)
        return False

    logger.info("Installed 'pypdf' to enable markup overlay exports: %s", result.stdout.strip())
    _overlay_support_state.auto_install_error = None
    return True


def _ensure_overlay_support() -> bool:
    """Ensure pypdf is available, attempting a runtime install if required."""

    global SUPPORTS_PDF_OVERLAYS

    if SUPPORTS_PDF_OVERLAYS:
        return True

    api = _load_pypdf()
    if api is not None:
        _set_pdf_api(api)
        return True

    if _install_pypdf():
        api = _load_pypdf()
        if api is not None:
            _set_pdf_api(api)
            return True
        if _overlay_support_state.auto_install_error is None:
            _overlay_support_state.auto_install_error = "pypdf installation succeeded but the module could not be imported."

    SUPPORTS_PDF_OVERLAYS = False
    return False


PdfReader = None  # type: ignore[assignment]
PdfWriter = None  # type: ignore[assignment]
ArrayObject = None  # type: ignore[assignment]
DictionaryObject = None  # type: ignore[assignment]
FloatObject = None  # type: ignore[assignment]
NameObject = None  # type: ignore[assignment]
NumberObject = None  # type: ignore[assignment]
TextStringObject = None  # type: ignore[assignment]

_overlay_support_state = OverlaySupportState(available=False)

initial_api = _load_pypdf()
if initial_api is not None:
    _set_pdf_api(initial_api)

SUPPORTS_PDF_OVERLAYS = _overlay_support_state.available


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

    grouped = _group_elements(elements)
    overlays: List[MarkupOverlay] = []

    if not grouped:
        return overlays

    if not _ensure_overlay_support():
        return overlays

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

    overlays = build_pdf_overlays(elements)
    if not overlays:
        return []

    directory.mkdir(parents=True, exist_ok=True)
    paths: List[Path] = []
    for overlay in overlays:
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


def get_overlay_support_state() -> OverlaySupportState:
    """Return a snapshot of the current overlay capability state."""

    return OverlaySupportState(
        available=_overlay_support_state.available,
        auto_install_attempted=_overlay_support_state.auto_install_attempted,
        auto_install_error=_overlay_support_state.auto_install_error,
    )

