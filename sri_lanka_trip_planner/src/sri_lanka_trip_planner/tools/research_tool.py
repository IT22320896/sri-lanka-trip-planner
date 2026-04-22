from __future__ import annotations

import json
import os
import re
from datetime import date as date_type
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests
from crewai.tools import BaseTool
from pydantic import BaseModel, Field

USER_AGENT = "sri-lanka-trip-planner/1.0"
GEOCODE_URL = "https://geocoding-api.open-meteo.com/v1/search"
WEATHER_URL = "https://api.open-meteo.com/v1/forecast"
WIKI_URL = "https://en.wikipedia.org/w/api.php"

FALLBACK_COORDS: Dict[str, Dict[str, float]] = {
    "colombo": {"latitude": 6.9271, "longitude": 79.8612},
    "kandy": {"latitude": 7.2906, "longitude": 80.6337},
    "galle": {"latitude": 6.0535, "longitude": 80.2210},
    "ella": {"latitude": 6.8667, "longitude": 81.0466},
    "sigiriya": {"latitude": 7.9570, "longitude": 80.7603},
}

FALLBACK_ATTRACTIONS: Dict[str, List[str]] = {
    "colombo": [
        "Galle Face Green",
        "Gangaramaya Temple",
        "Pettah Market",
    ],
    "kandy": [
        "Temple of the Tooth Relic",
        "Kandy Lake",
        "Peradeniya Botanical Gardens",
    ],
    "galle": [
        "Galle Fort",
        "Dutch Reformed Church",
        "Unawatuna Beach",
    ],
    "ella": [
        "Nine Arches Bridge",
        "Little Adam's Peak",
        "Ella Rock",
    ],
    "sigiriya": [
        "Sigiriya Rock Fortress",
        "Pidurangala Rock",
        "Sigiriya Museum",
    ],
}


def _project_root() -> Path:
    current = Path(__file__).resolve()
    for parent in current.parents:
        if (parent / "pyproject.toml").exists():
            return parent
    return current.parents[4]


def _strip_html(text: str) -> str:
    return re.sub(r"<.*?>", "", text)


def _fetch_json(url: str, params: Dict[str, str]) -> Dict[str, Any]:
    response = requests.get(
        url,
        params=params,
        timeout=12,
        headers={"User-Agent": USER_AGENT},
    )
    response.raise_for_status()
    return response.json()


def _read_cache(cache_path: Path) -> Dict[str, Any]:
    if not cache_path.exists():
        return {}
    try:
        return json.loads(cache_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def _write_cache(cache_path: Path, cache: Dict[str, Any]) -> None:
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    cache_path.write_text(json.dumps(cache, indent=2), encoding="utf-8")


def get_weather_and_attractions(destination: str, date: str) -> dict:
    """Fetch weather and top attractions for a destination on a given date.

    Args:
        destination: City or region name, such as "Kandy" or "Galle".
        date: Trip date in ISO 8601 format (YYYY-MM-DD).

    Returns:
        A dictionary containing destination, date, weather summary, attractions,
        source URLs, and error notes if any calls fail.

    Raises:
        ValueError: If destination or date is missing or invalid.
    """
    destination = destination.strip()
    if not destination:
        raise ValueError("destination is required")
    try:
        trip_date = date_type.fromisoformat(date)
    except ValueError as exc:
        raise ValueError("date must be YYYY-MM-DD") from exc

    offline = os.getenv("CREWAI_OFFLINE", "").lower() in {"1", "true", "yes"}
    cache_key = f"{destination.lower()}|{trip_date.isoformat()}"
    cache_path = _project_root() / "data" / "research_cache.json"
    cache = _read_cache(cache_path)

    if offline and cache_key in cache:
        cached = dict(cache[cache_key])
        cached["cached"] = True
        print(f"[research_tool] Using cached data for {destination} on {date}")
        return cached

    print(f"[research_tool] Fetching weather + attractions for {destination} on {date}")
    errors: List[str] = []
    coords: Optional[Dict[str, float]] = None

    if offline:
        coords = FALLBACK_COORDS.get(destination.lower())
    else:
        try:
            geocode = _fetch_json(
                GEOCODE_URL,
                {"name": destination, "count": "1", "language": "en", "format": "json"},
            )
            results = geocode.get("results", [])
            if results:
                coords = {
                    "latitude": float(results[0]["latitude"]),
                    "longitude": float(results[0]["longitude"]),
                }
        except Exception as exc:  # noqa: BLE001 - capture for tool resilience
            errors.append(f"geocode_error: {exc}")

    if coords is None:
        coords = FALLBACK_COORDS.get(destination.lower())

    weather: Dict[str, Any] = {}
    if coords is not None and not offline:
        try:
            forecast = _fetch_json(
                WEATHER_URL,
                {
                    "latitude": str(coords["latitude"]),
                    "longitude": str(coords["longitude"]),
                    "daily": "weather_code,temperature_2m_max,temperature_2m_min,precipitation_probability_max",
                    "timezone": "auto",
                    "start_date": trip_date.isoformat(),
                    "end_date": trip_date.isoformat(),
                },
            )
            daily = forecast.get("daily", {})
            if daily:
                weather = {
                    "date": trip_date.isoformat(),
                    "temp_max_c": daily.get("temperature_2m_max", [None])[0],
                    "temp_min_c": daily.get("temperature_2m_min", [None])[0],
                    "precip_prob_percent": daily.get("precipitation_probability_max", [None])[0],
                    "weather_code": daily.get("weather_code", [None])[0],
                }
        except Exception as exc:  # noqa: BLE001
            errors.append(f"weather_error: {exc}")

    if not weather:
        weather = {
            "date": trip_date.isoformat(),
            "temp_max_c": None,
            "temp_min_c": None,
            "precip_prob_percent": None,
            "weather_code": None,
        }

    attractions: List[Dict[str, str]] = []
    if not offline:
        try:
            wiki = _fetch_json(
                WIKI_URL,
                {
                    "action": "query",
                    "list": "search",
                    "srsearch": f"attractions in {destination}",
                    "format": "json",
                    "srlimit": "5",
                },
            )
            for item in wiki.get("query", {}).get("search", []):
                title = str(item.get("title", "")).strip()
                snippet = _strip_html(str(item.get("snippet", "")).strip())
                if title:
                    attractions.append({"title": title, "snippet": snippet})
        except Exception as exc:  # noqa: BLE001
            errors.append(f"attractions_error: {exc}")

    if not attractions:
        fallback = FALLBACK_ATTRACTIONS.get(destination.lower(), [])
        attractions = [{"title": item, "snippet": ""} for item in fallback]

    result = {
        "destination": destination,
        "date": trip_date.isoformat(),
        "coordinates": coords,
        "weather": weather,
        "attractions": attractions,
        "sources": {
            "geocode": GEOCODE_URL,
            "weather": WEATHER_URL,
            "wikipedia": WIKI_URL,
        },
        "errors": errors,
        "cached": False,
    }

    cache[cache_key] = result
    _write_cache(cache_path, cache)
    print(f"[research_tool] Stored cache key {cache_key}")
    return result


class ResearchToolInput(BaseModel):
    """Input schema for get_weather_and_attractions."""

    destination: str = Field(..., description="Destination city or region.")
    date: str = Field(..., description="Trip date in YYYY-MM-DD format.")


class ResearchTool(BaseTool):
    name: str = "get_weather_and_attractions"
    description: str = (
        "Fetch daily weather and top attractions for a Sri Lanka destination "
        "using Open-Meteo and Wikipedia."
    )
    args_schema = ResearchToolInput

    def _run(self, destination: str, date: str) -> dict:
        print(f"[ResearchTool] tool_call destination={destination} date={date}")
        return get_weather_and_attractions(destination=destination, date=date)
