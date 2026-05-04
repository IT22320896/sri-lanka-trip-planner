"""Assemble one structured trip plan (places, weather, budget, schedule) for API/UI."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _extract_validation_section(md: str) -> str:
    if not md.strip():
        return ""
    for heading in ("## Validation Results", "## Validation", "### Validation"):
        if heading in md:
            return md[md.find(heading) :].strip()
    return ""


def _strip_first_h1(md: str) -> str:
    lines = md.splitlines()
    if lines and lines[0].lstrip().startswith("# "):
        return "\n".join(lines[1:]).lstrip("\n")
    return md


def _normalize_attractions(raw: Any) -> List[Dict[str, str]]:
    out: List[Dict[str, str]] = []
    if not isinstance(raw, list):
        return out
    for item in raw:
        if isinstance(item, dict):
            title = str(item.get("title", "")).strip()
            snippet = str(item.get("snippet", "")).strip()
            if title or snippet:
                out.append({"title": title or "Place", "snippet": snippet})
        elif item:
            out.append({"title": str(item).strip(), "snippet": ""})
    return out


def build_unified_plan(
    latest_plan: Optional[Dict[str, Any]],
    itinerary_md: str,
    budget_json: Optional[Dict[str, Any]],
    final_report_md: str = "",
) -> Dict[str, Any]:
    """Single structured object: trip, weather, places, budget, schedule, validation."""
    lp = latest_plan if isinstance(latest_plan, dict) else {}

    origin = str(lp.get("origin", "") or "").strip()
    destination = str(lp.get("destination", "") or "").strip()
    group_size = _safe_int(lp.get("group_size"), 0) or _safe_int(lp.get("people"), 0)
    days = _safe_int(lp.get("days"), 0) or _safe_int(lp.get("duration_days"), 0)
    travel_dates = lp.get("travel_dates") or []
    if isinstance(travel_dates, str):
        travel_dates = [travel_dates]
    travel_dates = [str(d) for d in travel_dates if d]

    weather = lp.get("weather") if isinstance(lp.get("weather"), dict) else {}
    places = _normalize_attractions(lp.get("attractions"))

    budget = budget_json if isinstance(budget_json, dict) else {}
    if not budget and isinstance(lp.get("budget"), dict):
        budget = dict(lp["budget"])

    itinerary_path = str(lp.get("itinerary_path", "") or "")

    validation_snippet = _extract_validation_section(final_report_md)

    return {
        "trip": {
            "origin": origin,
            "destination": destination,
            "group_size": group_size or None,
            "duration_days": days or None,
            "travel_dates": travel_dates,
        },
        "weather": weather,
        "places": places,
        "budget": budget,
        "schedule": {
            "format": "markdown",
            "body": itinerary_md.strip(),
            "source_file": itinerary_path or None,
        },
        "review": {
            "summary_markdown": final_report_md.strip() or None,
            "validation_section_markdown": validation_snippet or None,
        },
    }


def build_unified_report_md(unified: Dict[str, Any]) -> str:
    """One readable markdown document: overview, places, weather, budget, schedule, review."""
    trip = unified.get("trip") or {}
    weather = unified.get("weather") or {}
    places = unified.get("places") or []
    budget = unified.get("budget") or {}
    schedule = unified.get("schedule") or {}
    review = unified.get("review") or {}

    origin = trip.get("origin") or "—"
    dest = trip.get("destination") or "—"
    lines: List[str] = []

    lines.append(f"# Trip plan: {origin} → {dest}")
    lines.append("")

    lines.append("## 1. Overview")
    lines.append(f"- **Origin:** {origin}")
    lines.append(f"- **Destination:** {dest}")
    if trip.get("group_size"):
        lines.append(f"- **Group size:** {trip['group_size']} people")
    if trip.get("duration_days"):
        lines.append(f"- **Duration:** {trip['duration_days']} days")
    if trip.get("travel_dates"):
        lines.append(f"- **Dates:** {', '.join(trip['travel_dates'])}")
    lines.append("")

    lines.append("## 2. Places & highlights")
    if places:
        for p in places:
            title = p.get("title", "")
            snippet = (p.get("snippet") or "").strip()
            if snippet:
                lines.append(f"- **{title}** — {snippet}")
            else:
                lines.append(f"- **{title}**")
    else:
        lines.append("- *(No attraction list in plan data.)*")
    lines.append("")

    lines.append("## 3. Weather snapshot")
    if weather:
        lines.append(
            f"- **Range:** {weather.get('temp_min_c', '—')}°C – "
            f"{weather.get('temp_max_c', '—')}°C"
        )
        lines.append(f"- **Precipitation chance:** {weather.get('precip_prob_percent', '—')}%")
        if weather.get("date"):
            lines.append(f"- **Date:** {weather['date']}")
    else:
        lines.append("- *(No weather data attached.)*")
    lines.append("")

    lines.append("## 4. Budget")
    if budget:
        total_lkr = budget.get("total_lkr")
        total_usd = budget.get("total_usd")
        if total_lkr is not None:
            lines.append(f"- **Total (LKR):** {int(total_lkr):,}")
        else:
            lines.append("- **Total (LKR):** —")
        if total_usd is not None:
            lines.append(f"- **Total (USD):** {total_usd}")
        br = budget.get("budget_breakdown") or budget.get("breakdown_lkr")
        if isinstance(br, dict) and br:
            lines.append("")
            lines.append("| Category | Amount (LKR) |")
            lines.append("|----------|-------------|")
            for k, v in br.items():
                if isinstance(v, (int, float)):
                    lines.append(f"| {k} | {int(v):,} |")
                else:
                    lines.append(f"| {k} | {v} |")
        assumptions = budget.get("assumptions")
        if isinstance(assumptions, list) and assumptions:
            lines.append("")
            lines.append("**Assumptions:**")
            for a in assumptions:
                lines.append(f"- {a}")
    else:
        lines.append("- *(No budget data attached.)*")
    lines.append("")

    lines.append("## 5. Daily schedule")
    body = _strip_first_h1(str(schedule.get("body") or "").strip())
    if body:
        lines.append(body)
    else:
        lines.append("*(No itinerary text.)*")
    lines.append("")

    val = review.get("validation_section_markdown") or ""
    full_review = str(review.get("summary_markdown") or "").strip()
    if val:
        lines.append("## 6. Validation")
        lines.append(val)
    elif full_review:
        lines.append("## 6. Review & validation")
        lines.append(full_review)
    else:
        lines.append("## 6. Review & validation")
        lines.append("*(No reviewer output.)*")

    return "\n".join(lines).strip()


def write_unified_artifacts(
    output_dir: Path,
    unified: Dict[str, Any],
    unified_md: str,
) -> None:
    """Persist unified_plan.json and unified_report.md under outputs/."""
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "unified_plan.json").write_text(
        json.dumps(unified, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    (output_dir / "unified_report.md").write_text(unified_md, encoding="utf-8")
