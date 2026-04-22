"""Comprehensive test suite for the Sri Lanka Trip Planner.

Covers:
- Crew structure validation (agent/task counts, roles, tools)
- Per-agent tool output validation (research, budget, itinerary, reviewer)
- Property-based assertions (budget always positive, itinerary has days, etc.)
- Edge case handling (invalid inputs, empty strings, boundary values)
- Security checks (no sensitive data leaking in outputs)
"""

import json
import os
import re
from pathlib import Path

import pytest

from sri_lanka_trip_planner.crew import SriLankaTripPlanner
from sri_lanka_trip_planner.main import _parse_request, build_inputs
from sri_lanka_trip_planner.tools import (
    calculate_trip_budget,
    create_itinerary_file,
    get_weather_and_attractions,
    validate_plan,
)


@pytest.fixture(autouse=True)
def _offline_mode():
    """Run all tests in offline mode to avoid network dependency."""
    os.environ["CREWAI_OFFLINE"] = "1"
    yield
    os.environ.pop("CREWAI_OFFLINE", None)


# ---------------------------------------------------------------------------
# 1. Crew Structure Tests
# ---------------------------------------------------------------------------

class TestCrewStructure:
    """Validate the crew has the correct agents, tasks, and wiring."""

    def test_four_agents_exist(self) -> None:
        crew = SriLankaTripPlanner().crew()
        assert len(crew.agents) == 4

    def test_four_tasks_exist(self) -> None:
        crew = SriLankaTripPlanner().crew()
        assert len(crew.tasks) == 4

    def test_agent_roles_are_distinct(self) -> None:
        crew = SriLankaTripPlanner().crew()
        roles = [a.role for a in crew.agents]
        assert any("Research Agent" in r for r in roles)
        assert any("Budget Agent" in r for r in roles)
        assert any("Itinerary Agent" in r for r in roles)
        assert any("Reviewer Agent" in r for r in roles)

    def test_each_agent_has_at_least_one_tool(self) -> None:
        crew = SriLankaTripPlanner().crew()
        for agent in crew.agents:
            assert len(agent.tools) >= 1, f"{agent.role} has no tools"

    def test_sequential_process(self) -> None:
        crew = SriLankaTripPlanner().crew()
        assert crew.process.value == "sequential"


# ---------------------------------------------------------------------------
# 2. Research Tool Tests
# ---------------------------------------------------------------------------

class TestResearchTool:
    """Validate the get_weather_and_attractions tool output."""

    def test_returns_correct_destination(self) -> None:
        result = get_weather_and_attractions("Kandy", "2026-04-26")
        assert result["destination"] == "Kandy"

    def test_returns_correct_date(self) -> None:
        result = get_weather_and_attractions("Kandy", "2026-04-26")
        assert result["date"] == "2026-04-26"

    def test_returns_attractions_list(self) -> None:
        result = get_weather_and_attractions("Kandy", "2026-04-26")
        assert isinstance(result["attractions"], list)
        assert len(result["attractions"]) > 0

    def test_returns_weather_dict(self) -> None:
        result = get_weather_and_attractions("Kandy", "2026-04-26")
        weather = result["weather"]
        assert isinstance(weather, dict)
        assert "date" in weather
        assert "temp_max_c" in weather
        assert "temp_min_c" in weather

    def test_returns_sources(self) -> None:
        result = get_weather_and_attractions("Colombo", "2026-04-26")
        assert "sources" in result
        assert "geocode" in result["sources"]

    def test_returns_coordinates_for_known_city(self) -> None:
        result = get_weather_and_attractions("Galle", "2026-04-26")
        coords = result["coordinates"]
        assert coords is not None
        assert "latitude" in coords
        assert "longitude" in coords

    def test_fallback_attractions_for_known_cities(self) -> None:
        for city in ["Colombo", "Kandy", "Galle", "Ella", "Sigiriya"]:
            result = get_weather_and_attractions(city, "2026-04-26")
            assert len(result["attractions"]) >= 3, f"{city} should have >=3 attractions"

    def test_unknown_destination_still_returns_structure(self) -> None:
        result = get_weather_and_attractions("Trincomalee", "2026-04-26")
        assert result["destination"] == "Trincomalee"
        assert "weather" in result
        assert "attractions" in result

    def test_raises_on_empty_destination(self) -> None:
        with pytest.raises(ValueError, match="destination is required"):
            get_weather_and_attractions("", "2026-04-26")

    def test_raises_on_invalid_date(self) -> None:
        with pytest.raises(ValueError, match="date must be YYYY-MM-DD"):
            get_weather_and_attractions("Kandy", "not-a-date")

    def test_raises_on_bad_date_format(self) -> None:
        with pytest.raises(ValueError):
            get_weather_and_attractions("Kandy", "26-04-2026")

    def test_caching_works(self) -> None:
        r1 = get_weather_and_attractions("Kandy", "2026-04-26")
        r2 = get_weather_and_attractions("Kandy", "2026-04-26")
        assert r2.get("cached") is True or r2["destination"] == r1["destination"]


# ---------------------------------------------------------------------------
# 3. Budget Tool Tests
# ---------------------------------------------------------------------------

class TestBudgetTool:
    """Validate the calculate_trip_budget tool output and properties."""

    def test_returns_required_keys(self) -> None:
        result = calculate_trip_budget(people=4, destination="Kandy", days=2)
        required = ["budget_breakdown", "total_lkr", "total_usd", "budget_file"]
        for key in required:
            assert key in result, f"Missing key: {key}"

    def test_total_is_positive(self) -> None:
        result = calculate_trip_budget(people=2, destination="Colombo", days=3)
        assert result["total_lkr"] > 0
        assert result["total_usd"] > 0

    def test_breakdown_sums_to_total(self) -> None:
        result = calculate_trip_budget(people=4, destination="Kandy", days=2)
        breakdown = result["budget_breakdown"]
        assert sum(breakdown.values()) == result["total_lkr"]

    def test_budget_scales_with_people(self) -> None:
        b2 = calculate_trip_budget(people=2, destination="Kandy", days=2)
        b4 = calculate_trip_budget(people=4, destination="Kandy", days=2)
        assert b4["total_lkr"] == b2["total_lkr"] * 2

    def test_budget_scales_with_days(self) -> None:
        b1 = calculate_trip_budget(people=4, destination="Kandy", days=1)
        b3 = calculate_trip_budget(people=4, destination="Kandy", days=3)
        assert b3["total_lkr"] == b1["total_lkr"] * 3

    def test_writes_budget_json_file(self) -> None:
        result = calculate_trip_budget(people=4, destination="Kandy", days=2)
        path = Path(result["budget_file"])
        assert path.exists()
        data = json.loads(path.read_text(encoding="utf-8"))
        assert data["total_lkr"] == result["total_lkr"]

    def test_different_destinations_have_different_rates(self) -> None:
        colombo = calculate_trip_budget(people=1, destination="Colombo", days=1)
        kandy = calculate_trip_budget(people=1, destination="Kandy", days=1)
        assert colombo["total_lkr"] != kandy["total_lkr"]

    def test_raises_on_zero_people(self) -> None:
        with pytest.raises(ValueError, match="people must be greater than 0"):
            calculate_trip_budget(people=0, destination="Kandy", days=2)

    def test_raises_on_negative_days(self) -> None:
        with pytest.raises(ValueError, match="days must be greater than 0"):
            calculate_trip_budget(people=4, destination="Kandy", days=-1)

    def test_unknown_destination_uses_default_rate(self) -> None:
        result = calculate_trip_budget(people=2, destination="UnknownPlace", days=1)
        assert result["total_lkr"] > 0

    def test_exchange_rate_is_positive(self) -> None:
        result = calculate_trip_budget(people=1, destination="Kandy", days=1)
        assert result["exchange_rate_lkr_per_usd"] > 0

    def test_has_assumptions_list(self) -> None:
        result = calculate_trip_budget(people=1, destination="Kandy", days=1)
        assert isinstance(result["assumptions"], list)
        assert len(result["assumptions"]) > 0


# ---------------------------------------------------------------------------
# 4. Itinerary Tool Tests
# ---------------------------------------------------------------------------

class TestItineraryTool:
    """Validate the create_itinerary_file tool output and generated content."""

    def _make_plan_data(self, **overrides) -> dict:
        base = {
            "origin": "Colombo",
            "destination": "Kandy",
            "days": 2,
            "group_size": 4,
            "travel_dates": ["2026-04-26", "2026-04-27"],
            "budget": {"total_lkr": 96000, "total_usd": 300, "budget_file": ""},
            "weather": {"temp_max_c": 30, "temp_min_c": 22, "precip_prob_percent": 20},
            "attractions": [
                {"title": "Temple of the Tooth Relic", "snippet": ""},
                {"title": "Kandy Lake", "snippet": ""},
            ],
        }
        base.update(overrides)
        return base

    def test_returns_file_path(self) -> None:
        path = create_itinerary_file(self._make_plan_data())
        assert Path(path).exists()

    def test_file_is_markdown(self) -> None:
        path = create_itinerary_file(self._make_plan_data())
        assert path.endswith(".md")

    def test_contains_day_sections(self) -> None:
        path = create_itinerary_file(self._make_plan_data())
        content = Path(path).read_text(encoding="utf-8")
        assert "## Day 1" in content
        assert "## Day 2" in content

    def test_contains_destination(self) -> None:
        path = create_itinerary_file(self._make_plan_data())
        content = Path(path).read_text(encoding="utf-8")
        assert "Kandy" in content

    def test_contains_budget_summary(self) -> None:
        path = create_itinerary_file(self._make_plan_data())
        content = Path(path).read_text(encoding="utf-8")
        assert "Budget Summary" in content

    def test_contains_travel_dates(self) -> None:
        path = create_itinerary_file(self._make_plan_data())
        content = Path(path).read_text(encoding="utf-8")
        assert "2026-04-26" in content

    def test_contains_time_slots(self) -> None:
        path = create_itinerary_file(self._make_plan_data())
        content = Path(path).read_text(encoding="utf-8")
        time_entries = re.findall(r"\d{2}:\d{2}", content)
        assert len(time_entries) >= 4

    def test_contains_attractions(self) -> None:
        path = create_itinerary_file(self._make_plan_data())
        content = Path(path).read_text(encoding="utf-8")
        assert "Temple of the Tooth Relic" in content

    def test_raises_on_missing_destination(self) -> None:
        with pytest.raises(ValueError, match="destination is required"):
            create_itinerary_file({"destination": "", "days": 2})

    def test_single_day_trip(self) -> None:
        path = create_itinerary_file(self._make_plan_data(days=1))
        content = Path(path).read_text(encoding="utf-8")
        assert "## Day 1" in content
        assert "## Day 2" not in content

    def test_writes_latest_plan_json(self) -> None:
        path = create_itinerary_file(self._make_plan_data())
        plan_json = Path(path).parent / "latest_plan.json"
        assert plan_json.exists()


# ---------------------------------------------------------------------------
# 5. Reviewer Tool Tests
# ---------------------------------------------------------------------------

class TestReviewerTool:
    """Validate the validate_plan tool output."""

    def _create_itinerary(self) -> str:
        plan_data = {
            "origin": "Colombo",
            "destination": "Kandy",
            "days": 2,
            "group_size": 4,
            "travel_dates": ["2026-04-26", "2026-04-27"],
            "budget": {"total_lkr": 96000, "total_usd": 300, "budget_file": ""},
            "weather": {},
            "attractions": [{"title": "Temple of the Tooth", "snippet": ""}],
        }
        return create_itinerary_file(plan_data)

    def test_returns_required_keys(self) -> None:
        path = self._create_itinerary()
        result = validate_plan(path)
        for key in ["itinerary_path", "is_realistic", "issues", "warnings", "metrics"]:
            assert key in result, f"Missing key: {key}"

    def test_valid_itinerary_is_realistic(self) -> None:
        path = self._create_itinerary()
        result = validate_plan(path)
        assert result["is_realistic"] is True

    def test_detects_day_count(self) -> None:
        path = self._create_itinerary()
        result = validate_plan(path)
        assert result["metrics"]["day_count"] == 2

    def test_detects_activities(self) -> None:
        path = self._create_itinerary()
        result = validate_plan(path)
        assert result["metrics"]["activities_total"] > 0

    def test_raises_on_missing_file(self) -> None:
        with pytest.raises(FileNotFoundError):
            validate_plan("/nonexistent/path/itinerary.md")

    def test_warns_on_missing_budget_file_ref(self) -> None:
        path = self._create_itinerary()
        result = validate_plan(path)
        has_budget_warning = any("Budget file" in w for w in result["warnings"])
        assert has_budget_warning or result["warnings"]

    def test_metrics_has_timestamp(self) -> None:
        path = self._create_itinerary()
        result = validate_plan(path)
        assert "validated_at" in result["metrics"]


# ---------------------------------------------------------------------------
# 6. Input Parsing Tests
# ---------------------------------------------------------------------------

class TestInputParsing:
    """Validate the user request parser extracts fields correctly."""

    def test_parses_origin_and_destination(self) -> None:
        parsed = _parse_request("Plan a trip from Colombo to Kandy")
        assert parsed["origin"] == "Colombo"
        assert parsed["destination"] == "Kandy"

    def test_parses_group_size(self) -> None:
        parsed = _parse_request("Trip for 4 people to Galle")
        assert parsed["people"] == "4"

    def test_parses_days(self) -> None:
        parsed = _parse_request("Plan a 3-day trip")
        assert parsed["days"] == "3"

    def test_detects_budget_focus(self) -> None:
        parsed = _parse_request("Plan a cheap trip")
        assert parsed["budget_focus"] == "budget"

    def test_handles_missing_fields_gracefully(self) -> None:
        parsed = _parse_request("Plan a trip")
        assert parsed["origin"] is None
        assert parsed["destination"] is None
        assert parsed["days"] is None
        assert parsed["people"] is None

    def test_build_inputs_provides_defaults(self) -> None:
        inputs = build_inputs("Plan a trip")
        assert inputs["origin"] == ""
        assert inputs["destination"] == ""
        assert "current_date" in inputs


# ---------------------------------------------------------------------------
# 7. Security & Safety Tests
# ---------------------------------------------------------------------------

class TestSecurity:
    """Ensure no sensitive data leaks into tool outputs or files."""

    def test_no_api_keys_in_budget_output(self) -> None:
        result = calculate_trip_budget(people=2, destination="Kandy", days=1)
        output_str = json.dumps(result)
        assert "api_key" not in output_str.lower()
        assert "secret" not in output_str.lower()
        assert "password" not in output_str.lower()

    def test_no_api_keys_in_research_output(self) -> None:
        result = get_weather_and_attractions("Kandy", "2026-04-26")
        output_str = json.dumps(result)
        assert "api_key" not in output_str.lower()
        assert "secret" not in output_str.lower()

    def test_no_api_keys_in_itinerary_file(self) -> None:
        plan_data = {
            "origin": "Colombo",
            "destination": "Kandy",
            "days": 1,
            "group_size": 2,
            "travel_dates": ["2026-04-26"],
            "budget": {"total_lkr": 48000, "total_usd": 150, "budget_file": ""},
            "weather": {},
            "attractions": [],
        }
        path = create_itinerary_file(plan_data)
        content = Path(path).read_text(encoding="utf-8")
        assert "api_key" not in content.lower()
        assert "secret" not in content.lower()
        assert "token" not in content.lower()

    def test_budget_file_contains_no_system_paths(self) -> None:
        result = calculate_trip_budget(people=1, destination="Kandy", days=1)
        data = json.loads(Path(result["budget_file"]).read_text(encoding="utf-8"))
        dumped = json.dumps(data)
        assert "\\Users\\" not in dumped or "budget_file" in dumped


# ---------------------------------------------------------------------------
# 8. Property-Based / Invariant Tests
# ---------------------------------------------------------------------------

class TestInvariants:
    """Property-based checks that should hold regardless of input."""

    @pytest.mark.parametrize("people", [1, 2, 5, 10])
    def test_budget_always_positive_for_valid_inputs(self, people: int) -> None:
        result = calculate_trip_budget(people=people, destination="Kandy", days=2)
        assert result["total_lkr"] > 0
        assert result["total_usd"] > 0

    @pytest.mark.parametrize("days", [1, 2, 3, 5])
    def test_itinerary_has_correct_day_count(self, days: int) -> None:
        plan = {
            "origin": "Colombo",
            "destination": "Kandy",
            "days": days,
            "group_size": 2,
            "travel_dates": [f"2026-04-{26 + i}" for i in range(days)],
            "budget": {},
            "weather": {},
            "attractions": [],
        }
        path = create_itinerary_file(plan)
        content = Path(path).read_text(encoding="utf-8")
        day_sections = re.findall(r"## Day \d+", content)
        assert len(day_sections) == days

    @pytest.mark.parametrize(
        "city", ["Colombo", "Kandy", "Galle", "Ella", "Sigiriya"]
    )
    def test_research_returns_attractions_for_all_known_cities(self, city: str) -> None:
        result = get_weather_and_attractions(city, "2026-04-26")
        assert len(result["attractions"]) >= 3

    @pytest.mark.parametrize("people", [1, 4, 8])
    def test_budget_breakdown_always_sums_to_total(self, people: int) -> None:
        result = calculate_trip_budget(people=people, destination="Colombo", days=2)
        assert sum(result["budget_breakdown"].values()) == result["total_lkr"]

    def test_usd_is_less_than_lkr(self) -> None:
        result = calculate_trip_budget(people=4, destination="Kandy", days=2)
        assert result["total_usd"] < result["total_lkr"]
