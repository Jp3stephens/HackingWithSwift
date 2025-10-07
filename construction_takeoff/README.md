# Construction Takeoff Automation

This project provides a Python-based prototype for automating construction takeoffs with a "human-in-the-loop" workflow. It ingests machine-readable drawing exports, performs trade-specific quantity takeoffs, estimates material and labor costs, and exports a spreadsheet-friendly CSV summary for review.

The tool is intended as a starting point for a richer desktop or web product. It focuses on extensibility and repeatability rather than perfect accuracy on raw PDF drawings; the system expects vector or BIM-derived JSON data extracted from the drawings. Estimators are modular so that trade experts can refine the logic or plug in vendor pricing feeds.

## Features

- Command line interface for running takeoffs per trade.
- Drawing analyzer that aggregates geometry and metadata from JSON exports.
- Pluggable estimators for each trade (concrete example provided).
- Labor and material costing with configuration-driven production rates.
- Human-in-the-loop checkpoints to flag assumptions and require acknowledgement.
- Spreadsheet (CSV) exporter that is compatible with Excel/Google Sheets.

## Usage

```
PYTHONPATH=construction_takeoff python -m takeoff.cli --trade concrete --input /path/to/drawings --output estimate.csv
```

1. Export your construction drawings into JSON using the provided schema (see `docs/sample_drawing.json`).
2. Run the CLI with the trade you want to estimate.
3. Review the generated CSV alongside the human-review notes in the console.
4. Adjust assumptions as needed and rerun.

## Web Experience

An interactive web workspace is available for teams that prefer a visual workflow and richer UX.

### Launch the interface

Keep the virtual environment activated (`source .venv/bin/activate`) and start the development server using the helper script:

```bash
construction_takeoff/scripts/run_ui.sh
# ↳ Boots the FastAPI server with auto-reload and opens the web dashboard at http://localhost:8000.
```

Prefer to launch it manually? Run:

```bash
PYTHONPATH=construction_takeoff uvicorn takeoff.webapp.app:create_app --reload
# ↳ Spins up the same server without the helper script; ideal for custom deployment commands.
```

Navigate to [http://localhost:8000](http://localhost:8000) to access the UI. From there you can:

- Pick a trade from the live registry.
- Drag and drop JSON or ZIP exports of your drawing takeoff data.
- Review an instant dashboard showing material, labor, total costs, and labor hours.
- Inspect human-in-the-loop checkpoints before publishing an estimate.
- Download the spreadsheet-ready CSV directly from the browser.

## Project Layout

- `takeoff/cli.py` – Command-line entry point.
- `takeoff/project.py` – Coordinates parsing, estimation, human review, and exporting.
- `takeoff/drawings.py` – Data model for drawings and utilities to load them from disk or archives.
- `takeoff/estimators/` – Trade-specific estimators implementing material and labor logic.
- `takeoff/exporters/spreadsheet.py` – CSV export utility.
- `takeoff/human_review.py` – Workflow helpers for interactive checkpoints.
- `takeoff/service.py` – Programmatic helpers used by both the CLI and UI.
- `takeoff/webapp/` – FastAPI application delivering the interactive UX.

## Extending to Other Trades

Add a new estimator in `takeoff/estimators/your_trade.py` inheriting from `BaseTradeEstimator`. Register it in `TRADE_REGISTRY` inside `takeoff/estimators/__init__.py`. Each estimator can:

- Define what drawing element categories it cares about.
- Provide unit conversions and waste factors.
- Supply production rates to translate quantities into labor hours.
- Reference vendor pricing files or external APIs.

## Human-in-the-loop Design

The CLI prints out a checklist of assumptions and allows the reviewer to accept or reject them. In a full product this would be replaced by a UI with markup back to the drawing set.

## Future Enhancements

- Native PDF/BIM parsing layer.
- Versioned pricing database with supplier integrations.
- Rich UI for reviewing marked-up takeoffs.
- Collaboration tools for multi-trade coordination.
- Cloud deployment for scale and audit trails.

This prototype demonstrates the architecture and core mechanics for an automated takeoff assistant similar to "Cursor" but tailored to construction workflows.
