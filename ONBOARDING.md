# Project Onboarding

This guide helps new members set up and run the Sri Lanka Weekend Trip Planner
after cloning the repository.

## Prerequisites

- Python 3.10+
- Ollama installed and running locally

## One-time setup (after clone)

1. Create a virtual environment (only once):

```
python -m venv venv
```

2. Activate it:

- On Windows:

```
venv\Scripts\activate
```

- On Mac/Linux:

```
source venv/bin/activate
```

3. Move into the project folder (the repo already contains it):

```
cd sri_lanka_trip_planner
```

4. Install the project in editable mode with all dependencies:

```
pip install -e .
```

5. Pull the Ollama models:

```
ollama pull qwen3.5:9b
ollama pull nomic-embed-text
```

6. Create your local environment file:

```
copy .env.example .env
```

Note: Ollama typically runs as a background service on Windows. Check the system tray for the Ollama icon. No need to run `ollama serve` manually if it's already running.

## Run the planner

Make sure you're in the `sri_lanka_trip_planner` folder with the venv activated, then:

```
sri_lanka_trip_planner "Plan a cheap 2-day trip from Colombo to Kandy for 4 people next weekend"
```

## Outputs

- outputs/final_report.md
- outputs/budget\_\*.json
- outputs/itinerary\_\*.md

## Tests

```
pytest -q
```

## Project scaffold reference

The project structure was originally created with:

```
crewai create crew sri_lanka_trip_planner
```

If you already cloned the repo, you do not need to run that command again.
