import os

from crewai import LLM, Agent, Crew, Process, Task
from crewai.agents.agent_builder.base_agent import BaseAgent
from crewai.memory.unified_memory import Memory
from crewai.project import CrewBase, agent, crew, task
from crewai.rag.embeddings.providers.ollama.ollama_provider import OllamaProvider

from sri_lanka_trip_planner.tools import (
    BudgetTool,
    ItineraryTool,
    ResearchTool,
    ReviewerTool,
)


@CrewBase
class SriLankaTripPlanner:
    """Sri Lanka Weekend Trip Planner crew."""

    agents: list[BaseAgent]
    tasks: list[Task]

    def _llm_config(self) -> LLM:
        model = os.getenv("OLLAMA_MODEL") or os.getenv("MODEL") or "llama3.1:8b"
        model_name = model.replace("ollama/", "")
        if ":" not in model_name:
            model_name = f"{model_name}:8b"
        if model_name not in {"llama3.1:8b", "llama3:8b"}:
            model_name = "llama3.1:8b"
        base_url = (
            os.getenv("OLLAMA_BASE_URL")
            or os.getenv("API_BASE")
            or "http://localhost:11434"
        )
        return LLM(model=f"ollama/{model_name}", base_url=base_url)

    @agent
    def research_agent(self) -> Agent:
        config = dict(self.agents_config["research_agent"])
        config["llm"] = self._llm_config()
        return Agent(config=config, tools=[ResearchTool()], verbose=True)

    @agent
    def budget_agent(self) -> Agent:
        config = dict(self.agents_config["budget_agent"])
        config["llm"] = self._llm_config()
        return Agent(config=config, tools=[BudgetTool()], verbose=True)

    @agent
    def itinerary_agent(self) -> Agent:
        config = dict(self.agents_config["itinerary_agent"])
        config["llm"] = self._llm_config()
        return Agent(config=config, tools=[ItineraryTool()], verbose=True)

    @agent
    def reviewer_agent(self) -> Agent:
        config = dict(self.agents_config["reviewer_agent"])
        config["llm"] = self._llm_config()
        return Agent(config=config, tools=[ReviewerTool()], verbose=True)

    @task
    def research_task(self) -> Task:
        return Task(config=self.tasks_config["research_task"])

    @task
    def budget_task(self) -> Task:
        return Task(
            config=self.tasks_config["budget_task"],
            context=[self.research_task()],
        )

    @task
    def itinerary_task(self) -> Task:
        return Task(
            config=self.tasks_config["itinerary_task"],
            context=[self.research_task(), self.budget_task()],
        )

    @task
    def review_task(self) -> Task:
        return Task(
            config=self.tasks_config["review_task"],
            context=[self.research_task(), self.budget_task(), self.itinerary_task()],
            output_file="outputs/final_report.md",
        )

    def _local_memory(self) -> Memory:
        base_url = (
            os.getenv("OLLAMA_BASE_URL")
            or os.getenv("API_BASE")
            or "http://localhost:11434"
        )
        embedder = OllamaProvider(**{
            "model": "nomic-embed-text",
            "url": f"{base_url}/api/embeddings",
        })
        llm = LLM(model="ollama/llama3.1:8b", base_url=base_url)
        return Memory(embedder=embedder, llm=llm)

    @crew
    def crew(self) -> Crew:
        print("[crew] Initializing Sri Lanka Weekend Trip Planner crew")
        return Crew(
            agents=self.agents,
            tasks=self.tasks,
            process=Process.sequential,
            memory=self._local_memory(),
            verbose=True,
        )
