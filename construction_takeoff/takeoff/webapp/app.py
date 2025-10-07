"""FastAPI application powering the takeoff UI."""

from __future__ import annotations

import pathlib
from tempfile import TemporaryDirectory
from typing import Dict, List

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from ..estimators import TRADE_REGISTRY
from ..exporters.spreadsheet import render_csv
from ..service import run_trade_takeoff


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""

    app = FastAPI(title="Construction Takeoff Assistant", version="0.2.0")
    base_dir = pathlib.Path(__file__).parent
    templates = Jinja2Templates(directory=str(base_dir / "templates"))
    app.mount("/static", StaticFiles(directory=str(base_dir / "static")), name="static")

    trade_options = sorted(TRADE_REGISTRY.keys())

    @app.get("/", response_class=HTMLResponse)
    async def index(request: Request) -> HTMLResponse:
        return templates.TemplateResponse("index.html", {"request": request, "trades": trade_options})

    @app.get("/api/trades")
    async def list_trades() -> Dict[str, List[str]]:
        return {"trades": trade_options}

    @app.get("/api/health")
    async def healthcheck() -> Dict[str, str]:
        return {"status": "ok"}

    @app.post("/api/takeoff")
    async def perform_takeoff(trade: str = Form(...), drawing: UploadFile = File(...)) -> JSONResponse:
        if not drawing.filename:
            raise HTTPException(status_code=400, detail="Please upload a JSON export or ZIP archive of drawings.")

        suffix = pathlib.Path(drawing.filename).suffix.lower()
        if suffix not in {".json", ".zip"}:
            raise HTTPException(status_code=400, detail="Unsupported file type. Upload a .json or .zip export.")

        try:
            with TemporaryDirectory() as tmp:
                temp_dir = pathlib.Path(tmp)
                input_path = await _persist_upload(drawing, temp_dir)
                run = run_trade_takeoff(trade, input_path)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except Exception as exc:  # pragma: no cover - defensive logging surface
            raise HTTPException(status_code=500, detail="Failed to process takeoff.") from exc

        csv_payload = render_csv(run.result)

        material_cost = run.result.summary.get("material_cost", 0.0)
        labor_cost = run.result.summary.get("labor_cost", 0.0)
        total_cost = material_cost + labor_cost

        response = {
            "trade": run.trade,
            "trade_label": _format_trade_label(run.trade),
            "drawing_count": run.drawing_count,
            "element_count": run.element_count,
            "line_item_count": len(run.result.line_items),
            "line_items": [
                {
                    "description": item.description,
                    "quantity": item.quantity,
                    "unit": item.unit,
                    "material_unit_cost": item.material_unit_cost,
                    "material_cost": item.material_cost,
                    "labor_hours": item.labor_hours,
                    "labor_rate_per_hour": item.labor_rate_per_hour,
                    "labor_cost": item.labor_cost,
                }
                for item in run.result.line_items
            ],
            "summary": run.result.summary,
            "metrics": {
                "material_cost": material_cost,
                "labor_cost": labor_cost,
                "total_cost": total_cost,
                "labor_hours": run.result.summary.get("labor_hours", 0.0),
            },
            "review": [
                {"message": item.message, "severity": item.severity}
                for item in run.review.items
            ],
            "review_summary": run.review.summarize(),
            "csv": csv_payload,
        }

        return JSONResponse(response)

    return app


async def _persist_upload(upload: UploadFile, temp_dir: pathlib.Path) -> pathlib.Path:
    """Persist the uploaded drawing file to a temporary location."""

    payload = await upload.read()
    if not payload:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    filename = pathlib.Path(upload.filename or "drawings")
    suffix = filename.suffix.lower()

    if suffix == ".json":
        target_dir = temp_dir / "input"
        target_dir.mkdir(parents=True, exist_ok=True)
        (target_dir / filename.name).write_bytes(payload)
        await upload.close()
        return target_dir

    target_path = temp_dir / filename.name
    target_path.write_bytes(payload)
    await upload.close()
    return target_path


def _format_trade_label(trade_key: str) -> str:
    return trade_key.replace("_", " ").title()
