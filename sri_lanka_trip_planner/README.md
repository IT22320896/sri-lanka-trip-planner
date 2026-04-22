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
- Models:
  - `qwen3.5:9b` — main LLM for all agents (~5.5 GB)
  - `nomic-embed-text` — local embedder for crew memory (~274 MB)

## Setup

1. Create a virtual environment and install dependencies:

```bash
python -m venv venv
source venv/Scripts/activate
pip install -r requirements.txt
```

2. Pull the Ollama models:

```bash
ollama pull qwen3.5:9b
ollama pull nomic-embed-text
```

3. Start the Ollama server (if not already running):

```bash
ollama serve
```

4. Configure environment variables:

```bash
copy .env.example .env
```

## Run the Planner

```bash
sri_lanka_trip_planner "Plan a cheap 2-day trip from Colombo to Kandy for 4 people next weekend"
```

## Outputs

- outputs/final_report.md
- outputs/budget\_\*.json
- outputs/itinerary\_\*.md

## Model Configuration

The system uses `qwen3.5:9b` for better tool-calling reliability. The model is configured via:
- `.env` file (`OLLAMA_MODEL=qwen3.5:9b`)
- Automatically overrides the placeholder `llama3.1:8b` in `agents.yaml`

To switch models, just update `OLLAMA_MODEL` in your `.env` file.

## Observability

- Crew and agents run with verbose=True
- Tools emit explicit print logs for every call and output
- Shared memory is enabled at the crew level using local Ollama models (no OpenAI key required)

## Testing

```bash
pytest -q
```

## Assignment Compliance

- Ollama model configured for qwen3.5:9b (better tool-calling than llama3.1:8b)
- 4 distinct agents and 4 sequential tasks
- One custom tool per agent with strict type hints and detailed docstrings
- Real-world tool interactions (file I/O + public APIs)
- Shared state passed through task outputs + crew memory
- Full logging and output files for reporting
- Comprehensive test suite with 45+ tests covering edge cases and security
