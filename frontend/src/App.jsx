import { useState } from "react";

const API_BASE = "http://localhost:8000";

const emptyResult = {
  final_report_md: "",
  latest_plan: null,
  itinerary_md: "",
  budget_json: null,
  errors: [],
};

export default function App() {
  const [prompt, setPrompt] = useState(
    "Plan a cheap 2-day trip from Colombo to Kandy for 4 people next weekend",
  );
  const [status, setStatus] = useState("idle");
  const [result, setResult] = useState(emptyResult);

  const canSubmit = prompt.trim().length > 0 && status !== "loading";

  const handleSubmit = async (event) => {
    event.preventDefault();
    if (!canSubmit) return;

    setStatus("loading");
    setResult(emptyResult);

    try {
      const response = await fetch(`${API_BASE}/api/plan`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ prompt }),
      });

      if (!response.ok) {
        const message = await response.text();
        throw new Error(message || "Failed to generate plan");
      }

      const data = await response.json();
      setResult({
        final_report_md: data.final_report_md || "",
        latest_plan: data.latest_plan || null,
        itinerary_md: data.itinerary_md || "",
        budget_json: data.budget_json || null,
        errors: data.errors || [],
      });
      setStatus("success");
    } catch (error) {
      setStatus("error");
      setResult({
        ...emptyResult,
        errors: [error.message],
      });
    }
  };

  return (
    <div className="page">
      <header className="hero">
        <p className="tag">Local AI Crew</p>
        <h1>Sri Lanka Weekend Trip Planner</h1>
        <p className="subhead">
          Drop a prompt, run the crew, and get a ready-to-go itinerary with a
          budget breakdown.
        </p>
      </header>

      <main className="content">
        <section className="panel input-panel">
          <h2>Trip request</h2>
          <form onSubmit={handleSubmit} className="prompt-form">
            <label className="field">
              <span>Prompt</span>
              <textarea
                value={prompt}
                onChange={(event) => setPrompt(event.target.value)}
                rows={4}
                placeholder="Plan a 2-day trip from Colombo to Kandy for 4 people"
              />
            </label>
            <button type="submit" disabled={!canSubmit}>
              {status === "loading" ? "Planning..." : "Generate plan"}
            </button>
          </form>
          {status === "error" && result.errors.length > 0 ? (
            <div className="error">
              <p>Something went wrong.</p>
              <ul>
                {result.errors.map((message, index) => (
                  <li key={index}>{message}</li>
                ))}
              </ul>
            </div>
          ) : null}
        </section>

        <section className="panel output-panel">
          <div className="output-header">
            <h2>Output</h2>
            <span className={`status ${status}`}>{status}</span>
          </div>

          <article className="output-block">
            {result.final_report_md ? (
              <pre>{result.final_report_md}</pre>
            ) : (
              <p className="muted">Run a prompt to see the output.</p>
            )}
          </article>
        </section>
      </main>
    </div>
  );
}
