"""Entry point for running the takeoff web application."""

from __future__ import annotations

import os

import uvicorn

from .app import create_app


def main() -> None:
    host = os.environ.get("TAKEOFF_HOST", "0.0.0.0")
    port = int(os.environ.get("TAKEOFF_PORT", "8000"))
    uvicorn.run(create_app(), host=host, port=port)


if __name__ == "__main__":  # pragma: no cover
    main()
