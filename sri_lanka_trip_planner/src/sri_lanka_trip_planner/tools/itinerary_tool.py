from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

from crewai.tools import BaseTool
from pydantic import BaseModel, Field

DEFAULT_DAY_TIMES = ["08:00", "10:30", "13:00", "15:30", "18:00"]


def _project_root() -> Path:
    current = Path(__file__).resolve()
    for parent in current.parents:
        if (parent / "pyproject.toml").exists():
            return parent
    return current.parents[4]


def _safe_slug(text: str) -> str:
    return re.sub(r"[^a-z0-9_-]+", "-", text.lower()).strip("-")


def _normalize_attractions(raw: Any) -> List[str]:
    if isinstance(raw, list):
        items: List[str] = []
        for item in raw:
            if isinstance(item, dict):
                title = str(item.get("title", "")).strip()
                if title:
                    items.append(title)
            else:
                value = str(item).strip()
                if value:
                    items.append(value)
        return items
    return []


def create_itinerary_file(plan_data: dict) -> str:
    """Create a markdown itinerary from structured plan data.

    Args:
        plan_data: Dictionary with trip details, budget, and attractions.

    Returns:
        Absolute path to the generated itinerary markdown file.

    Raises:
        ValueError: If required fields like destination or days are missing.
    """
    destination = str(plan_data.get("destination", "")).strip()
    origin = str(plan_data.get("origin", "")).strip()
    if not destination:
        raise ValueError("plan_data.destination is required")

    days = int(plan_data.get("days") or plan_data.get("duration_days") or 2)
    group_size = int(plan_data.get("group_size") or plan_data.get("people") or 1)
    travel_dates = plan_data.get("travel_dates") or []
    budget = plan_data.get("budget") or {}
    budget_file = str(budget.get("budget_file", ""))
    weather = plan_data.get("weather") or {}
    attractions = _normalize_attractions(plan_data.get("attractions"))

    output_dir = _project_root() / "outputs"
    output_dir.mkdir(parents=True, exist_ok=True)
    filename = (
        f"itinerary_{_safe_slug(destination)}_"
        f"{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.md"
    )
    output_path = output_dir / filename

    lines: List[str] = []
    lines.append(f"# Sri Lanka Weekend Trip Plan: {origin} to {destination}")
    lines.append("")
    lines.append("## Trip Overview")
    lines.append(f"- Origin: {origin or 'TBD'}")
    lines.append(f"- Destination: {destination}")
    lines.append(f"- Group size: {group_size}")
    if travel_dates:
        lines.append(f"- Dates: {', '.join(travel_dates)}")
    else:
        lines.append("- Dates: TBD")
    if budget_file:
        lines.append(f"- Budget file: {budget_file}")
    if weather:
        lines.append(
            "- Weather snapshot: "
            f"{weather.get('temp_min_c')}C to {weather.get('temp_max_c')}C, "
            f"precip {weather.get('precip_prob_percent')}%"
        )

    if not attractions:
        attractions = ["Local market walk", "Historic site visit", "Scenic viewpoint"]

    attraction_index = 0

    for day in range(1, days + 1):
        date_label = travel_dates[day - 1] if len(travel_dates) >= day else "TBD"
        lines.append("")
        lines.append(f"## Day {day} - {date_label}")
        if day == 1:
            lines.append(f"{DEFAULT_DAY_TIMES[0]} - Depart {origin or 'origin'}")
        for time_slot in DEFAULT_DAY_TIMES[1:]:
            if attraction_index < len(attractions):
                attraction = attractions[attraction_index]
                lines.append(f"{time_slot} - Visit {attraction}")
                attraction_index += 1
            else:
                lines.append(f"{time_slot} - Flexible time / local exploration")
        lines.append("20:00 - Dinner and rest")
        if day == days:
            lines.append("21:00 - Pack and prep for return")

    lines.append("")
    lines.append("## Budget Summary")
    if budget:
        lines.append(f"- Total (LKR): {budget.get('total_lkr', 'TBD')}")
        lines.append(f"- Total (USD): {budget.get('total_usd', 'TBD')}")
    else:
        lines.append("- Budget data pending")

    lines.append("")
    lines.append("## Notes")
    lines.append("- Confirm train or bus schedules 48 hours before travel.")
    lines.append("- Reserve key tickets in advance when possible.")

    output_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"[itinerary_tool] Itinerary written to {output_path}")

    state_path = output_dir / "latest_plan.json"
    plan_data_with_path = dict(plan_data)
    plan_data_with_path["itinerary_path"] = str(output_path)
    state_path.write_text(json.dumps(plan_data_with_path, indent=2), encoding="utf-8")
    return str(output_path)


class ItineraryToolInput(BaseModel):
    """Input schema for create_itinerary_file."""

    plan_data: Dict[str, Any] = Field(..., description="Structured trip plan data.")


class ItineraryTool(BaseTool):
    name: str = "create_itinerary_file"
    description: str = "Create a markdown itinerary file from structured plan data."
    args_schema = ItineraryToolInput

    def _run(self, plan_data: Dict[str, Any]) -> str:
        print("[ItineraryTool] tool_call plan_data keys:", list(plan_data.keys()))
        return create_itinerary_file(plan_data=plan_data)
