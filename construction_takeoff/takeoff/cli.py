"""Command-line interface for the construction takeoff tool."""

from __future__ import annotations

import argparse
import pathlib

from .project import TakeoffConfig, TakeoffProject


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Automated construction takeoff assistant")
    parser.add_argument("--trade", required=True, help="Trade to estimate (e.g. concrete, roofing)")
    parser.add_argument("--input", required=True, help="Path to directory or zip containing drawing JSON exports")
    parser.add_argument("--output", required=True, help="Path to write the resulting CSV estimate")
    return parser


def main(argv: list[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)

    config = TakeoffConfig(
        trade=args.trade,
        input_path=pathlib.Path(args.input).expanduser().resolve(),
        output_path=pathlib.Path(args.output).expanduser().resolve(),
    )

    project = TakeoffProject(config)
    project.run()


if __name__ == "__main__":  # pragma: no cover
    main()
