#!/usr/bin/env python
import json
import re
import sys
import warnings
from datetime import date, timedelta
from typing import Dict, List, Optional

from dotenv import load_dotenv

from sri_lanka_trip_planner.crew import SriLankaTripPlanner

warnings.filterwarnings("ignore", category=SyntaxWarning, module="pysbd")


def _next_weekend_dates(today: date) -> List[str]:
    days_ahead = 5 - today.weekday()
    if days_ahead <= 0:
        days_ahead += 7
    saturday = today + timedelta(days=days_ahead)
    sunday = saturday + timedelta(days=1)
    return [saturday.isoformat(), sunday.isoformat()]


def _parse_request(user_request: str) -> Dict[str, Optional[str]]:
    request = user_request.strip()
    lower = request.lower()

    days_match = re.search(r"(\d+)\s*[- ]?day", lower)
    people_match = re.search(r"(\d+)\s*(people|persons|travelers|travellers)", lower)
    route_match = re.search(r"from\s+([a-zA-Z ]+?)\s+to\s+([a-zA-Z ]+?)(\s|$)", request)

    days = int(days_match.group(1)) if days_match else None
    people = int(people_match.group(1)) if people_match else None
    origin = route_match.group(1).strip() if route_match else None
    destination = route_match.group(2).strip() if route_match else None

    budget_focus = None
    if any(keyword in lower for keyword in ["cheap", "budget", "low-cost", "affordable"]):
        budget_focus = "budget"

    travel_dates: List[str] = []
    if "next weekend" in lower:
        travel_dates = _next_weekend_dates(date.today())
    else:
        explicit_dates = re.findall(r"\d{4}-\d{2}-\d{2}", request)
        travel_dates = explicit_dates[:2]

    return {
        "origin": origin,
        "destination": destination,
        "days": str(days) if days is not None else None,
        "people": str(people) if people is not None else None,
        "budget_focus": budget_focus,
        "travel_dates": ",".join(travel_dates) if travel_dates else None,
    }


def build_inputs(user_request: str) -> dict:
    parsed = _parse_request(user_request)
    travel_dates = parsed.get("travel_dates")
    return {
        "user_request": user_request,
        "origin": parsed.get("origin") or "",
        "destination": parsed.get("destination") or "",
        "group_size": parsed.get("people") or "",
        "duration_days": parsed.get("days") or "",
        "travel_dates": travel_dates.split(",") if travel_dates else [],
        "budget_focus": parsed.get("budget_focus") or "",
        "current_date": date.today().isoformat(),
    }


def run() -> None:
    """Run the crew with a user request."""
    load_dotenv()
    user_request = " ".join(sys.argv[1:]).strip()
    if not user_request:
        user_request = input("Enter trip request: ").strip()

    inputs = build_inputs(user_request)
    print("[main] Kickoff inputs:\n" + json.dumps(inputs, indent=2))

    try:
        result = SriLankaTripPlanner().crew().kickoff(inputs=inputs)
        print("[main] Final result:\n", result)
    except Exception as exc:  # noqa: BLE001
        raise Exception(f"An error occurred while running the crew: {exc}")


def train() -> None:
    """Train the crew for a given number of iterations."""
    load_dotenv()
    sample_request = "Plan a cheap 2-day trip from Colombo to Kandy for 4 people next weekend"
    inputs = build_inputs(sample_request)
    try:
        SriLankaTripPlanner().crew().train(
            n_iterations=int(sys.argv[1]),
            filename=sys.argv[2],
            inputs=inputs,
        )
    except Exception as exc:  # noqa: BLE001
        raise Exception(f"An error occurred while training the crew: {exc}")


def replay() -> None:
    """Replay the crew execution from a specific task."""
    try:
        SriLankaTripPlanner().crew().replay(task_id=sys.argv[1])
    except Exception as exc:  # noqa: BLE001
        raise Exception(f"An error occurred while replaying the crew: {exc}")


def test() -> None:
    """Test the crew execution and return the results."""
    load_dotenv()
    sample_request = "Plan a cheap 2-day trip from Colombo to Kandy for 4 people next weekend"
    inputs = build_inputs(sample_request)
    try:
        SriLankaTripPlanner().crew().test(
            n_iterations=int(sys.argv[1]),
            eval_llm=sys.argv[2],
            inputs=inputs,
        )
    except Exception as exc:  # noqa: BLE001
        raise Exception(f"An error occurred while testing the crew: {exc}")


def run_with_trigger() -> None:
    """Run the crew with a trigger payload."""
    if len(sys.argv) < 2:
        raise Exception("No trigger payload provided. Provide JSON as argument.")

    try:
        trigger_payload = json.loads(sys.argv[1])
    except json.JSONDecodeError as exc:
        raise Exception("Invalid JSON payload provided as argument") from exc

    inputs = {
        "crewai_trigger_payload": trigger_payload,
        "user_request": "",
        "origin": "",
        "destination": "",
        "group_size": "",
        "duration_days": "",
        "travel_dates": [],
        "budget_focus": "",
        "current_date": "",
    }

    try:
        result = SriLankaTripPlanner().crew().kickoff(inputs=inputs)
        print("[main] Trigger result:\n", result)
    except Exception as exc:  # noqa: BLE001
        raise Exception(f"An error occurred while running the crew with trigger: {exc}")
