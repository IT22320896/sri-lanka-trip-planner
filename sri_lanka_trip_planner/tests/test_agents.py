import os
from pathlib import Path

from sri_lanka_trip_planner.crew import SriLankaTripPlanner
from sri_lanka_trip_planner.tools import (
    calculate_trip_budget,
    create_itinerary_file,
    get_weather_and_attractions,
    validate_plan,
)


def test_agent_and_task_counts() -> None:
    planner = SriLankaTripPlanner()
    crew = planner.crew()
    assert len(crew.agents) == 4
    assert len(crew.tasks) == 4

    roles = [agent.role for agent in crew.agents]
    assert any("Research Agent" in role for role in roles)
    assert any("Budget Agent" in role for role in roles)
    assert any("Itinerary Agent" in role for role in roles)
    assert any("Reviewer Agent" in role for role in roles)


def test_tools_run_offline() -> None:
    os.environ["CREWAI_OFFLINE"] = "1"

    research = get_weather_and_attractions("Kandy", "2026-04-26")
    assert research["destination"] == "Kandy"
    assert research["attractions"]

    budget = calculate_trip_budget(people=4, destination="Kandy", days=2)
    budget_path = Path(budget["budget_file"])
    assert budget_path.exists()

    plan_data = {
        "origin": "Colombo",
        "destination": "Kandy",
        "days": 2,
        "group_size": 4,
        "travel_dates": ["2026-04-26", "2026-04-27"],
        "budget": budget,
        "weather": research.get("weather"),
        "attractions": research.get("attractions"),
    }
    itinerary_path = create_itinerary_file(plan_data)
    assert Path(itinerary_path).exists()

    review = validate_plan(itinerary_path)
    assert review["itinerary_path"]
    assert "issues" in review
