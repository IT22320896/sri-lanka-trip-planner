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

3. Install the required packages (the same ones used during setup):

```
pip install crewai crewai-tools langchain-ollama
```

4. Move into the project folder (the repo already contains it):

```
cd sri_lanka_trip_planner
```

5. Create your local environment file:

```
copy .env.example .env
```

6. Pull and serve the Ollama model:

```
ollama pull llama3.1:8b
ollama serve
```

## Run the planner

```
python -m sri_lanka_trip_planner.main "Plan a cheap 2-day trip from Colombo to Kandy for 4 people next weekend"
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
