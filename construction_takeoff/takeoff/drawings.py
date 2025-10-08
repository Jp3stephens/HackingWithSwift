"""Utilities for loading and representing drawing data for takeoffs."""

from __future__ import annotations

import io
import json
import pathlib
import re
import zipfile
from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Optional

try:  # pragma: no cover - optional dependency for richer PDF parsing
    from pdfminer.high_level import extract_text_to_fp  # type: ignore
    from pdfminer.layout import LAParams  # type: ignore
except ImportError:  # pragma: no cover - fallback when pdfminer isn't installed
    extract_text_to_fp = None  # type: ignore
    LAParams = None  # type: ignore


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
    """Load drawing data from JSON exports, PDF drawing sheets, or archives.

    The loader will attempt to parse drawing metadata and quantity tables from
    the supported formats. Native PDF support relies on lightweight text
    extraction (via ``pdfminer.six``) to locate measurement callouts such as
    ``Slab Area: 1200 SF``. While imperfect, this allows the automated
    estimators to bootstrap material and labor calculations from typical
    commercial plan sets.
    """

    def __init__(self, input_path: pathlib.Path, *, default_trade: Optional[str] = None) -> None:
        self.input_path = input_path
        self.default_trade = (default_trade or "").lower() or None

    def load(self) -> Iterable[Drawing]:
        if self.input_path.is_dir():
            yield from self._load_from_directory(self.input_path)
        elif zipfile.is_zipfile(self.input_path):
            yield from self._load_from_zip(self.input_path)
        elif self.input_path.suffix.lower() == ".pdf":
            yield from self._load_from_pdf(self.input_path)
        else:
            raise ValueError(
                f"Unsupported drawing input: {self.input_path}. Expected directory, PDF, or zip archive."
            )

    def _load_from_directory(self, directory: pathlib.Path) -> Iterable[Drawing]:
        for json_path in sorted(directory.glob("*.json")):
            yield self._load_json(json_path.read_text(), source=str(json_path))

        for pdf_path in sorted(directory.glob("*.pdf")):
            yield from self._load_from_pdf(pdf_path)

    def _load_from_zip(self, archive_path: pathlib.Path) -> Iterable[Drawing]:
        with zipfile.ZipFile(archive_path) as archive:
            for name in sorted(archive.namelist()):
                lowered = name.lower()
                if lowered.endswith(".json"):
                    with archive.open(name) as fh:
                        payload = fh.read().decode("utf-8")
                        yield self._load_json(payload, source=f"{archive_path}:{name}")
                elif lowered.endswith(".pdf"):
                    with archive.open(name) as fh:
                        payload = fh.read()
                        yield from self._load_pdf_bytes(
                            payload,
                            source=f"{archive_path}:{name}",
                            stem=pathlib.Path(name).stem,
                        )

    def _load_json(self, payload: str, *, source: str) -> Drawing:
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

    def _load_from_pdf(self, pdf_path: pathlib.Path) -> Iterable[Drawing]:
        return self._load_pdf_bytes(pdf_path.read_bytes(), source=str(pdf_path), stem=pdf_path.stem)

    def _load_pdf_bytes(self, payload: bytes, *, source: str, stem: Optional[str] = None) -> Iterable[Drawing]:
        pages = _extract_pdf_pages(payload, source=source)
        if not pages:
            pages = [""]

        for index, page_text in enumerate(pages, start=1):
            drawing_name = f"{stem or pathlib.Path(source).stem}-p{index}"
            elements = self._parse_pdf_page(page_text, source=f"{source}#page{index}")
            yield Drawing(name=drawing_name, level=None, scale=None, elements=elements)

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

    def _parse_pdf_page(self, text: str, *, source: str) -> List[DrawingElement]:
        elements: List[DrawingElement] = []
        for idx, match in enumerate(_MEASUREMENT_PATTERN.finditer(text), start=1):
            label = match.group("label").strip()
            value = float(match.group("value"))
            unit = match.group("unit").lower()
            geometry = _geometry_from_unit(unit, value)
            if not geometry:
                continue

            trade = self._infer_trade(label, fallback=self.default_trade)
            element_id = _slugify(label, idx)
            metadata = {
                "source": source,
                "unit": unit,
                "raw_label": label,
            }
            category = _category_from_label(label)

            if category == "slab" and "area_sqft" in geometry and "thickness_in" not in geometry:
                geometry["thickness_in"] = 6.0
                metadata["assumed_thickness_in"] = 6.0

            elements.append(
                DrawingElement(
                    id=element_id,
                    trade=trade,
                    category=category,
                    geometry=geometry,
                    metadata=metadata,
                )
            )

        if not elements and self.default_trade:
            elements.append(
                DrawingElement(
                    id="placeholder-1",
                    trade=self.default_trade,
                    category="unclassified",
                    geometry={},
                    metadata={
                        "source": source,
                        "note": "No measurable callouts detected. Review required.",
                        "placeholder": "true",
                    },
                )
            )

        return elements

    def _infer_trade(self, label: str, *, fallback: Optional[str]) -> str:
        lowered = label.lower()
        for trade, keywords in _TRADE_KEYWORDS.items():
            if any(keyword in lowered for keyword in keywords):
                if fallback and trade != fallback:
                    return fallback
                return trade
        if fallback:
            return fallback
        return "general"


def group_elements_by_trade(drawings: Iterable[Drawing]) -> Dict[str, List[DrawingElement]]:
    grouped: Dict[str, List[DrawingElement]] = {}
    for drawing in drawings:
        for element in drawing.elements:
            grouped.setdefault(element.trade, []).append(element)
    return grouped


def _extract_pdf_pages(payload: bytes, *, source: str) -> List[str]:
    if extract_text_to_fp is None:
        return _extract_pdf_pages_fallback(payload)

    buffer = io.BytesIO(payload)
    output = io.StringIO()
    try:
        extract_text_to_fp(buffer, output, laparams=LAParams(), output_type="text", codec=None)
    except Exception as exc:  # pragma: no cover - pdfminer raises a variety of errors
        raise ValueError(f"Failed to read drawing PDF from {source}: {exc}") from exc
    finally:
        buffer.close()

    text = output.getvalue()
    pages = [page.strip() for page in text.split("\f") if page.strip()]
    if not pages:
        return _extract_pdf_pages_fallback(payload)
    return pages


def _extract_pdf_pages_fallback(payload: bytes) -> List[str]:
    raw = payload.decode("latin1", errors="ignore")
    fragments = re.findall(r"\(([^\)]*)\)\s*TJ?", raw)
    if not fragments:
        return []

    cleaned: List[str] = []
    for fragment in fragments:
        text = fragment.replace("\\r", " ").replace("\\n", " ")
        text = text.replace("\\)", ")").replace("\\(", "(")
        cleaned.append(text.strip())

    if not cleaned:
        return []

    return ["\n".join(cleaned)]


_MEASUREMENT_PATTERN = re.compile(
    r"(?P<label>[A-Za-z0-9#\-/\s]+)\s*(?:[:=]|-\s)\s*(?P<value>\d+(?:\.\d+)?)\s*(?P<unit>sq\.?\s*ft|sf|square feet|cy|cubic yards|cu\.?\s*yd\.?|lf|linear feet|ft|feet|ea|each|hrs?|hours?)",
    re.IGNORECASE,
)


def _geometry_from_unit(unit: str, value: float) -> Dict[str, float]:
    normalized = unit.replace(".", "").strip().lower()
    compact = normalized.replace(" ", "")
    if normalized in {"sq ft", "square feet"} or compact == "sf":
        return {"area_sqft": value}
    if normalized in {"cubic yards", "cu yd"} or compact in {"cy", "cuyd", "cuyds"}:
        return {"volume_cy": value}
    if normalized in {"linear feet", "ft", "feet"} or compact == "lf":
        return {"length_ft": value}
    if normalized == "each" or compact == "ea":
        return {"count": value}
    if normalized in {"hr", "hrs", "hour", "hours"} or compact in {"hr", "hrs"}:
        return {"labor_hours": value}
    return {"quantity": value}


def _slugify(label: str, index: int) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", label.lower()).strip("-")
    if not slug:
        slug = "item"
    return f"{slug}-{index}"


def _category_from_label(label: str) -> str:
    lowered = label.lower()
    if "slab" in lowered:
        return "slab"
    if "footing" in lowered or "foundation" in lowered:
        return "footing"
    if "rebar" in lowered or "reinforcing" in lowered:
        return "rebar"
    if "form" in lowered:
        return "formwork"
    if "labor" in lowered:
        return "labor"
    return lowered.replace(" ", "_")[:40] or "unclassified"


_TRADE_KEYWORDS = {
    "concrete": ["slab", "concrete", "footing", "foundation", "grade beam", "column", "wall"],
    "masonry": ["masonry", "brick", "cmu", "block"],
    "steel": ["steel", "beam", "joist", "girder"],
    "roofing": ["roof", "roofing", "membrane"],
    "framing": ["stud", "framing", "joist", "truss"],
    "waterproofing": ["waterproof", "damp proof", "seal"],
}
