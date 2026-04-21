from __future__ import annotations

import json
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

import requests
from crewai.tools import BaseTool
from pydantic import BaseModel, Field

EXCHANGE_URL = "https://api.exchangerate.host/latest"
FALLBACK_LKR_PER_USD = 320.0

PER_PERSON_LKR_BY_DESTINATION: Dict[str, int] = {
    "colombo": 16000,
    "kandy": 12000,
    "galle": 14000,
    "ella": 13000,
    "sigiriya": 15000,
}


def _project_root() -> Path:
    current = Path(__file__).resolve()
    for parent in current.parents:
        if (parent / "pyproject.toml").exists():
            return parent
    return current.parents[4]


def _safe_slug(text: str) -> str:
    return re.sub(r"[^a-z0-9_-]+", "-", text.lower()).strip("-")


def _fetch_exchange_rate() -> float:
    response = requests.get(
        EXCHANGE_URL,
        params={"base": "USD", "symbols": "LKR"},
        timeout=10,
    )
    response.raise_for_status()
    data = response.json()
    return float(data.get("rates", {}).get("LKR", FALLBACK_LKR_PER_USD))


def calculate_trip_budget(people: int, destination: str, days: int) -> dict:
    """Estimate a Sri Lanka trip budget and persist a JSON report.

    Args:
        people: Number of travelers.
        destination: Primary destination city or region.
        days: Trip length in days.

    Returns:
        A dictionary containing a budget breakdown in LKR and USD, plus the
        output file path used for the budget JSON.

    Raises:
        ValueError: If people or days are not positive integers.
    """
    if people <= 0:
        raise ValueError("people must be greater than 0")
    if days <= 0:
        raise ValueError("days must be greater than 0")

    destination_key = destination.strip().lower()
    daily_lkr = PER_PERSON_LKR_BY_DESTINATION.get(destination_key, 12000)
    print(
        f"[budget_tool] Calculating budget for {people} people, {days} days, "
        f"destination={destination_key}"
    )

    lodging = daily_lkr * people * days * 0.45
    food = daily_lkr * people * days * 0.25
    transport = daily_lkr * people * days * 0.20
    activities = daily_lkr * people * days * 0.08
    contingency = daily_lkr * people * days * 0.02

    breakdown_lkr = {
        "lodging": round(lodging),
        "food": round(food),
        "transport": round(transport),
        "activities": round(activities),
        "contingency": round(contingency),
    }
    total_lkr = int(sum(breakdown_lkr.values()))

    offline = os.getenv("CREWAI_OFFLINE", "").lower() in {"1", "true", "yes"}
    exchange_rate = FALLBACK_LKR_PER_USD
    rate_source = "fallback"
    if not offline:
        try:
            exchange_rate = _fetch_exchange_rate()
            rate_source = "api"
        except Exception as exc:  # noqa: BLE001
            print(f"[budget_tool] Exchange rate fetch failed: {exc}")

    total_usd = round(total_lkr / exchange_rate, 2)

    output_dir = _project_root() / "outputs"
    output_dir.mkdir(parents=True, exist_ok=True)
    filename = (
        f"budget_{_safe_slug(destination_key)}_{days}d_{people}p_"
        f"{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"
    )
    output_path = output_dir / filename

    report = {
        "destination": destination,
        "people": people,
        "days": days,
        "daily_per_person_lkr": daily_lkr,
        "budget_breakdown": breakdown_lkr,
        "breakdown_lkr": breakdown_lkr,
        "total_lkr": total_lkr,
        "exchange_rate_lkr_per_usd": exchange_rate,
        "exchange_rate_source": rate_source,
        "total_usd": total_usd,
        "budget_file": str(output_path),
        "assumptions": [
            "Mid-range guesthouse pricing with budget focus.",
            "Public or shared transport for intercity travel.",
            "Local meals with one paid activity per day.",
        ],
    }

    output_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"[budget_tool] Budget file written to {output_path}")
    return report


class BudgetToolInput(BaseModel):
    """Input schema for calculate_trip_budget."""

    people: int = Field(..., description="Number of travelers.")
    destination: str = Field(..., description="Primary destination.")
    days: int = Field(..., description="Trip length in days.")


class BudgetTool(BaseTool):
    name: str = "calculate_trip_budget"
    description: str = (
        "Estimate a budget in LKR and USD, then write the budget report to JSON."
    )
    args_schema = BudgetToolInput

    def _run(self, people: int, destination: str, days: int) -> dict:
        print(
            f"[BudgetTool] tool_call people={people} destination={destination} days={days}"
        )
        return calculate_trip_budget(people=people, destination=destination, days=days)
