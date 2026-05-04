"""Task guardrails and post-kickoff repair so tool JSON and itinerary files stay reliable."""

import ast
import json
from pathlib import Path
from typing import Any, Optional, Tuple

_kickoff_inputs: dict[str, Any] = {}
_last_research_dict: Optional[dict[str, Any]] = None
_last_budget_dict: Optional[dict[str, Any]] = None


def set_kickoff_inputs(inputs: dict[str, Any]) -> None:
    """Store kickoff inputs for guardrail fallbacks (must be called before crew.kickoff)."""
    global _kickoff_inputs, _last_research_dict, _last_budget_dict
    _kickoff_inputs = dict(inputs)
    _last_research_dict = None
    _last_budget_dict = None


def get_kickoff_inputs() -> dict[str, Any]:
    return dict(_kickoff_inputs)


def _strip_code_fences(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines)
    return text.strip()


def extract_json_object(text: str) -> Optional[dict[str, Any]]:
    """Parse a dict from LLM output; tolerate markdown fences and trailing junk."""
    raw = _strip_code_fences(text)
    try:
        data = json.loads(raw)
        if isinstance(data, dict):
            return data
    except json.JSONDecodeError:
        pass
    try:
        lit = ast.literal_eval(raw)
        if isinstance(lit, dict):
            return lit
    except (SyntaxError, ValueError, TypeError):
        pass
    start = raw.find("{")
    while start != -1:
        depth = 0
        for i in range(start, len(raw)):
            if raw[i] == "{":
                depth += 1
            elif raw[i] == "}":
                depth -= 1
                if depth == 0:
                    chunk = raw[start : i + 1]
                    try:
                        data = json.loads(chunk)
                        if isinstance(data, dict):
                            return data
                    except json.JSONDecodeError:
                        pass
                    break
        start = raw.find("{", start + 1)
    return None


def _research_dict_valid(data: dict[str, Any]) -> bool:
    if not str(data.get("destination") or "").strip():
        return False
    if not isinstance(data.get("weather"), dict):
        return False
    att = data.get("attractions")
    if not isinstance(att, list) or len(att) == 0:
        return False
    return True


def _budget_dict_valid(data: dict[str, Any]) -> bool:
    required = ("total_lkr", "total_usd", "budget_file", "budget_breakdown")
    return all(k in data for k in required)


def _safe_pos_int(value: Any, default: int) -> int:
    try:
        n = int(str(value).strip())
        return n if n > 0 else default
    except (TypeError, ValueError):
        return default


def research_output_guardrail(result: Any) -> Tuple[bool, Any]:
    """Ensure research output is valid tool JSON; refetch with the research tool if not."""
    global _last_research_dict
    from crewai.tasks.task_output import TaskOutput

    if not isinstance(result, TaskOutput):
        return (False, "Internal error: invalid task output type.")

    raw_text = str(result.raw or "")
    data = extract_json_object(raw_text)
    if data and _research_dict_valid(data):
        _last_research_dict = data
        return (True, json.dumps(data, ensure_ascii=False))

    inputs = get_kickoff_inputs()
    dest = str(inputs.get("destination") or "").strip()
    weather_date = str(inputs.get("weather_date") or inputs.get("current_date") or "").strip()

    if dest and weather_date:
        from sri_lanka_trip_planner.tools.research_tool import get_weather_and_attractions

        print("[guardrail] Research answer invalid; refetching via get_weather_and_attractions")
        fixed = get_weather_and_attractions(dest, weather_date)
        _last_research_dict = fixed
        return (True, json.dumps(fixed, ensure_ascii=False))

    return (
        False,
        "Final Answer must be ONLY the JSON returned by get_weather_and_attractions "
        "(keys: destination, weather, attractions, …). Do not output any other JSON.",
    )


def budget_output_guardrail(result: Any) -> Tuple[bool, Any]:
    """Ensure budget output matches calculate_trip_budget JSON."""
    global _last_budget_dict
    from crewai.tasks.task_output import TaskOutput

    if not isinstance(result, TaskOutput):
        return (False, "Internal error: invalid task output type.")

    raw_text = str(result.raw or "")
    data = extract_json_object(raw_text)
    if data and _budget_dict_valid(data):
        _last_budget_dict = data
        return (True, json.dumps(data, ensure_ascii=False))

    inputs = get_kickoff_inputs()
    dest = str(inputs.get("destination") or "").strip()
    people = _safe_pos_int(inputs.get("group_size"), 1)
    days = _safe_pos_int(inputs.get("duration_days"), 2)

    if dest:
        from sri_lanka_trip_planner.tools.budget_tool import calculate_trip_budget

        print("[guardrail] Budget answer invalid; refetching via calculate_trip_budget")
        fixed = calculate_trip_budget(people=people, destination=dest, days=days)
        _last_budget_dict = fixed
        return (True, json.dumps(fixed, ensure_ascii=False))

    return (
        False,
        "Final Answer must be ONLY the JSON returned by calculate_trip_budget.",
    )


def _first_existing_itinerary_path(raw_text: str) -> Optional[str]:
    for candidate in (raw_text.splitlines()[0].strip() if raw_text else "", raw_text.strip()):
        if not candidate:
            continue
        path_str = candidate.strip().strip('"').strip("'")
        try:
            path = Path(path_str)
            if path.is_file() and path.suffix.lower() == ".md":
                return str(path.resolve())
        except OSError:
            continue
    return None


def itinerary_output_guardrail(result: Any) -> Tuple[bool, Any]:
    """Ensure itinerary task ends with a real file path; rebuild from stored tool JSON if needed."""
    from crewai.tasks.task_output import TaskOutput

    if not isinstance(result, TaskOutput):
        return (False, "Internal error: invalid task output type.")

    raw_text = str(result.raw or "")
    existing = _first_existing_itinerary_path(raw_text)
    if existing:
        return (True, existing)

    research = _last_research_dict
    budget = _last_budget_dict
    inputs = get_kickoff_inputs()

    if research is None or budget is None:
        return (
            False,
            "Your Final Answer must be exactly the path string from create_itinerary_file, "
            "or ensure previous tasks produced valid research and budget JSON.",
        )

    from sri_lanka_trip_planner.tools.itinerary_tool import create_itinerary_file

    print("[guardrail] Itinerary answer invalid; rebuilding via create_itinerary_file")
    plan_data = assemble_plan_data_from_inputs(inputs, research, budget)
    path = create_itinerary_file(plan_data)
    return (True, path)


def assemble_plan_data_from_inputs(
    inputs: dict[str, Any], research: dict[str, Any], budget: dict[str, Any]
) -> dict[str, Any]:
    """Build plan_data for create_itinerary_file from kickoff inputs + task JSON."""
    travel_dates = inputs.get("travel_dates") or []
    if isinstance(travel_dates, str):
        travel_dates = [travel_dates]
    travel_dates = [str(d) for d in travel_dates if d]

    days = _safe_pos_int(inputs.get("duration_days"), 0)
    if days <= 0:
        days = _safe_pos_int(budget.get("days"), 2)

    group_size = _safe_pos_int(inputs.get("group_size"), 0)
    if group_size <= 0:
        group_size = _safe_pos_int(budget.get("people"), 1)

    return {
        "origin": str(inputs.get("origin") or "").strip(),
        "destination": str(inputs.get("destination") or research.get("destination") or "").strip(),
        "days": days,
        "group_size": group_size,
        "travel_dates": travel_dates,
        "budget": budget,
        "weather": research.get("weather") if isinstance(research.get("weather"), dict) else {},
        "attractions": research.get("attractions") if isinstance(research.get("attractions"), list) else [],
    }


def repair_itinerary_after_kickoff(result: Any) -> None:
    """If itinerary task did not produce a real file path, call create_itinerary_file once."""
    outputs = getattr(result, "tasks_output", None)
    if not outputs or len(outputs) < 3:
        return

    itinerary_raw = str(outputs[2].raw or "").strip()
    for candidate in (itinerary_raw.splitlines()[0].strip() if itinerary_raw else "", itinerary_raw):
        if not candidate:
            continue
        path_str = candidate.strip().strip('"').strip("'")
        try:
            if Path(path_str).is_file() and path_str.lower().endswith(".md"):
                return
        except OSError:
            continue

    inputs = get_kickoff_inputs()
    research = extract_json_object(str(outputs[0].raw or ""))
    budget = extract_json_object(str(outputs[1].raw or ""))

    if not research or not budget:
        print("[repair] Skipping itinerary repair: could not parse research or budget JSON.")
        return

    from sri_lanka_trip_planner.tools.itinerary_tool import create_itinerary_file

    plan_data = assemble_plan_data_from_inputs(inputs, research, budget)
    path = create_itinerary_file(plan_data)
    print(f"[repair] Regenerated itinerary via tool: {path}")
    try:
        outputs[2].raw = path
    except Exception:
        pass
