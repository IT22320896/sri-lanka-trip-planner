# Sri Lanka Weekend Trip Planner (CrewAI + Ollama)

This project is a complete, ready-to-run multi-agent system for the assignment
"Sri Lanka Weekend Trip Planner". It uses CrewAI with a local Ollama model and
produces a markdown report, a budget JSON file, and a detailed itinerary file.

## Agents and Tools

- Research Agent (curious travel researcher)
  - Tool: get_weather_and_attractions (Open-Meteo + Wikipedia)
- Budget Agent (strict accountant)
  - Tool: calculate_trip_budget (exchange rates + budget JSON output)
- Itinerary Agent (super-organized scheduler)
  - Tool: create_itinerary_file (writes itinerary markdown)
- Reviewer Agent (careful quality checker)
  - Tool: validate_plan (checks realism, timing, budget references)

## Requirements

- Python 3.10+
- Ollama installed locally
- Model: llama3.1:8b (or llama3:8b)

## Setup

1. Create a virtual environment and install dependencies:

```bash
python -m venv venv
source venv/Scripts/activate
pip install -r requirements.txt
```

2. Pull and run the Ollama model:

```bash
ollama pull llama3.1:8b
ollama serve
```

3. Configure environment variables:

```bash
copy .env.example .env
```

## Run the Planner

```bash
python -m sri_lanka_trip_planner.main "Plan a cheap 2-day trip from Colombo to Kandy for 4 people next weekend"
```

## Outputs

- outputs/final_report.md
- outputs/budget\_\*.json
- outputs/itinerary\_\*.md

## Observability

- Crew and agents run with verbose=2
- Tools emit explicit print logs for every call and output
- Shared memory is enabled at the crew level

## Testing

```bash
pytest -q
```

## Assignment Compliance

- Ollama model configured for llama3.1:8b
- 4 distinct agents and 4 sequential tasks
- One custom tool per agent with strict type hints and detailed docstrings
- Real-world tool interactions (file I/O + public APIs)
- Shared state passed through task outputs + crew memory
- Full logging and output files for reporting
