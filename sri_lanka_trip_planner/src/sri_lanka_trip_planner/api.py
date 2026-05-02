from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Optional

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from sri_lanka_trip_planner.crew import SriLankaTripPlanner
from sri_lanka_trip_planner.main import build_inputs

app = FastAPI(title="Sri Lanka Trip Planner API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"] ,
    allow_headers=["*"] ,
)


class PlanRequest(BaseModel):
    prompt: str = Field(..., min_length=1)


class PlanResponse(BaseModel):
    final_report_md: str
    latest_plan: Optional[Dict[str, Any]] = None
    itinerary_md: str
    budget_json: Optional[Dict[str, Any]] = None
    errors: list[str] = []


@app.get("/api/health")
def health() -> Dict[str, str]:
    return {"status": "ok"}


def _project_root() -> Path:
    current = Path(__file__).resolve()
    for parent in current.parents:
        if (parent / "pyproject.toml").exists():
            return parent
    return current.parents[4]


def _latest_file(output_dir: Path, pattern: str) -> Optional[Path]:
    matches = list(output_dir.glob(pattern))
    if not matches:
        return None
    return max(matches, key=lambda path: path.stat().st_mtime)


def _read_text(path: Optional[Path]) -> str:
    if path and path.exists():
        return path.read_text(encoding="utf-8")
    return ""


def _read_json(path: Optional[Path]) -> Optional[Dict[str, Any]]:
    if path and path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return None


@app.post("/api/plan", response_model=PlanResponse)
def plan_trip(request: PlanRequest) -> PlanResponse:
    load_dotenv()
    prompt = request.prompt.strip()
    if not prompt:
        raise HTTPException(status_code=400, detail="Prompt is required")

    inputs = build_inputs(prompt)

    try:
        SriLankaTripPlanner().crew().kickoff(inputs=inputs)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=str(exc))

    root = _project_root()
    output_dir = root / "outputs"
    final_report_md = _read_text(output_dir / "final_report.md")
    latest_plan = _read_json(output_dir / "latest_plan.json")

    itinerary_path: Optional[Path] = None
    budget_path: Optional[Path] = None

    if latest_plan:
        budget_file = latest_plan.get("budget", {}).get("budget_file")
        if budget_file:
            budget_path = Path(budget_file)
        itinerary_candidate = latest_plan.get("itinerary_path")
        if itinerary_candidate:
            itinerary_path = Path(itinerary_candidate)

    if not itinerary_path:
        itinerary_path = _latest_file(output_dir, "itinerary_*.md")
    if not budget_path:
        budget_path = _latest_file(output_dir, "budget_*.json")

    itinerary_md = _read_text(itinerary_path)
    budget_json = _read_json(budget_path)

    return PlanResponse(
        final_report_md=final_report_md,
        latest_plan=latest_plan,
        itinerary_md=itinerary_md,
        budget_json=budget_json,
        errors=[],
    )
