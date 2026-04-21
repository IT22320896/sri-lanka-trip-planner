from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path
from typing import List

from crewai.tools import BaseTool
from pydantic import BaseModel, Field


def validate_plan(itinerary_path: str) -> dict:
    """Validate itinerary realism, timing, and budget hints.

    Args:
        itinerary_path: Path to the itinerary markdown file.

    Returns:
        A dictionary with validation issues, warnings, and metrics.

    Raises:
        FileNotFoundError: If the itinerary file does not exist.
    """
    path = Path(itinerary_path)
    if not path.exists():
        raise FileNotFoundError(f"Itinerary file not found: {itinerary_path}")

    content = path.read_text(encoding="utf-8")
    day_sections = re.split(r"^## Day\s+\d+\s*-", content, flags=re.MULTILINE)
    day_count = max(0, len(day_sections) - 1)
    time_entries = re.findall(r"\b([01]\d|2[0-3]):[0-5]\d\b", content)

    activities_per_day: List[int] = []
    if day_count:
        for section in day_sections[1:]:
            activities = len(re.findall(r"\b([01]\d|2[0-3]):[0-5]\d\b", section))
            activities_per_day.append(activities)

    warnings: List[str] = []
    issues: List[str] = []

    if day_count == 0:
        issues.append("No day-by-day sections were found.")

    for idx, count in enumerate(activities_per_day, start=1):
        if count < 3:
            warnings.append(f"Day {idx} has very few scheduled items.")
        if count > 7:
            warnings.append(f"Day {idx} has too many activities for a weekend pace.")

    if "Budget Summary" not in content:
        warnings.append("Budget Summary section is missing.")

    if not re.search(r"\bLKR\b|\bUSD\b", content):
        warnings.append("No currency amounts found in the itinerary.")

    budget_file_match = re.search(r"Budget file: (.+)", content)
    if budget_file_match:
        budget_path = Path(budget_file_match.group(1).strip())
        if not budget_path.exists():
            warnings.append("Budget file referenced in itinerary was not found.")
    else:
        warnings.append("Budget file path not listed in itinerary.")

    metrics = {
        "day_count": day_count,
        "activities_total": len(time_entries),
        "activities_per_day": activities_per_day,
        "validated_at": datetime.utcnow().isoformat() + "Z",
    }

    is_realistic = not issues
    return {
        "itinerary_path": str(path),
        "is_realistic": is_realistic,
        "issues": issues,
        "warnings": warnings,
        "metrics": metrics,
    }


class ReviewerToolInput(BaseModel):
    """Input schema for validate_plan."""

    itinerary_path: str = Field(..., description="Path to the itinerary markdown file.")


class ReviewerTool(BaseTool):
    name: str = "validate_plan"
    description: str = "Validate timing, budget hints, and realism of the itinerary."
    args_schema = ReviewerToolInput

    def _run(self, itinerary_path: str) -> dict:
        print(f"[ReviewerTool] tool_call itinerary_path={itinerary_path}")
        return validate_plan(itinerary_path=itinerary_path)
