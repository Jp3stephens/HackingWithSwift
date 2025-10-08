"""Interactive helpers for collecting manual takeoff inputs."""

from __future__ import annotations

import sys
from typing import Dict, Iterable, List, Tuple

from .drawings import DrawingElement
from .human_review import ReviewChecklist


_CATEGORY_FIELDS: Dict[str, List[Tuple[str, str]]] = {
    "slab": [
        ("area_sqft", "Enter slab area in square feet"),
        ("thickness_in", "Enter slab thickness in inches"),
    ],
    "wall": [
        ("length_ft", "Enter wall length in feet"),
        ("height_ft", "Enter wall height in feet"),
        ("thickness_in", "Enter wall thickness in inches"),
    ],
    "pier": [
        ("diameter_in", "Enter pier diameter in inches"),
        ("depth_ft", "Enter pier depth in feet"),
    ],
    "footing": [
        ("volume_cy", "Enter footing volume in cubic yards"),
        ("area_sqft", "Optional: enter footing formwork area in square feet"),
    ],
}


_SUPPORTED_CATEGORIES = sorted(_CATEGORY_FIELDS)


def collect_manual_measurements(
    trade: str, elements: Iterable[DrawingElement], review: ReviewChecklist
) -> None:
    """Prompt the user for missing geometry when running in an interactive shell."""

    pending = [element for element in elements if _needs_geometry(trade, element)]
    if not pending:
        return

    if not sys.stdin.isatty():
        for element in pending:
            review.add(
                _manual_entry_message(element),
                severity="warning",
            )
        return

    print("\nManual takeoff inputs required for the following elements:")
    print("Provide numeric values or press Enter to skip an item.")

    for element in pending:
        print("\n---")
        print(_manual_entry_message(element))

        category = element.category
        if category not in _CATEGORY_FIELDS:
            category = _prompt_category(default=category)
            if not category:
                review.add(_manual_entry_message(element), severity="warning")
                continue
            element.category = category

        fields = _CATEGORY_FIELDS.get(category, [])
        for field, prompt_text in fields:
            if field in element.geometry:
                continue
            value = _prompt_float(f"{prompt_text} (element {element.id}): ")
            if value is None:
                continue
            element.geometry[field] = value
            element.metadata[f"manual_{field}"] = str(value)

        bbox = element.metadata.get("markup_bbox")
        if not bbox and _ask_yes_no(
            "Do you want to capture a highlight bounding box for this element? [y/N]: "
        ):
            coords = []
            for name in ("x1", "y1", "x2", "y2"):
                value = _prompt_float(
                    f"Enter normalized {name} (0-1) for element {element.id} or leave blank: "
                )
                if value is None:
                    coords = []
                    break
                coords.append(min(max(value, 0.0), 1.0))
            if len(coords) == 4:
                element.metadata["markup_bbox"] = ",".join(str(c) for c in coords)

        if _needs_geometry(trade, element):
            review.add(_manual_entry_message(element), severity="warning")
        else:
            review.add(
                f"Captured manual geometry for element {element.id} ({element.category}).",
                severity="info",
            )


def _needs_geometry(trade: str, element: DrawingElement) -> bool:
    if element.trade != trade:
        return False

    if not element.geometry:
        return True

    category = element.category
    required_fields = {
        field
        for field, _ in _CATEGORY_FIELDS.get(category, [])
        if not _is_optional_field(category, field)
    }
    return any(field not in element.geometry for field in required_fields)


def _is_optional_field(category: str, field: str) -> bool:
    return category == "footing" and field == "area_sqft"


def _manual_entry_message(element: DrawingElement) -> str:
    source = element.metadata.get("source", "uploaded drawings")
    return (
        f"Provide measurements for element {element.id} (category '{element.category}') from {source}."
    )


def _prompt_float(prompt_text: str) -> float | None:
    try:
        raw = input(prompt_text)
    except EOFError:  # pragma: no cover - non-interactive fallback
        return None
    raw = raw.strip()
    if not raw:
        return None
    try:
        return float(raw)
    except ValueError:
        print("Invalid number. Please try again or press Enter to skip.")
        return _prompt_float(prompt_text)


def _prompt_category(*, default: str | None = None) -> str | None:
    print("Select a concrete category for this element:")
    for idx, name in enumerate(_SUPPORTED_CATEGORIES, start=1):
        print(f"  {idx}. {name}")
    if default:
        print(f"Press Enter to keep existing category '{default}'.")
    try:
        raw = input("Choice (number or name, blank to skip): ")
    except EOFError:  # pragma: no cover
        return default
    choice = raw.strip().lower()
    if not choice:
        return default
    if choice in _CATEGORY_FIELDS:
        return choice
    try:
        index = int(choice)
    except ValueError:
        print("Unrecognized category. Skipping.")
        return default
    if 1 <= index <= len(_SUPPORTED_CATEGORIES):
        return _SUPPORTED_CATEGORIES[index - 1]
    print("Unrecognized category. Skipping.")
    return default


def _ask_yes_no(prompt_text: str) -> bool:
    try:
        raw = input(prompt_text)
    except EOFError:  # pragma: no cover
        return False
    return raw.strip().lower() in {"y", "yes"}

