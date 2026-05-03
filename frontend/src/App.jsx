import { useState } from "react";

// Read backend URL from Vite environment variable `VITE_API_BASE` so it can be
// changed at deploy time. Falls back to localhost for local development.
const API_BASE = import.meta.env.VITE_API_BASE || "http://localhost:8000";

const emptyResult = {
  final_report_md: "",
  latest_plan: null,
  itinerary_md: "",
  budget_json: null,
  errors: [],
};

async function parseErrorResponse(response) {
  const text = await response.text();
  try {
    const json = JSON.parse(text);
    if (json?.detail) {
      return typeof json.detail === "string"
        ? json.detail
        : JSON.stringify(json.detail);
    }
  } catch {
    /* plain text */
  }
  return text || `Request failed (${response.status})`;
}

function OutputDisplay({ result, status }) {
  const report = result.final_report_md?.trim() || "";
  const itinerary = result.itinerary_md?.trim() || "";
  const budget = result.budget_json;

  const hasAnything = Boolean(report || itinerary || budget);

  if (status === "success" && !hasAnything) {
    return (
      <p className="muted">
        Nothing was returned. Check the server <code>outputs/</code> folder or
        logs.
      </p>
    );
  }

  if (!hasAnything) {
    return null;
  }

  return (
    <div className="output-stack">
      {report ? (
        <section className="output-section">
          <h3>Final report</h3>
          <pre className="output-plain">{result.final_report_md}</pre>
        </section>
      ) : null}

      {itinerary ? (
        <section className="output-section">
          <h3>Itinerary</h3>
          <pre className="output-plain">{result.itinerary_md}</pre>
        </section>
      ) : null}

      {budget ? (
        <section className="output-section">
          <h3>Budget</h3>
          <pre className="output-plain">
            {typeof budget === "object"
              ? JSON.stringify(budget, null, 2)
              : String(budget)}
          </pre>
        </section>
      ) : null}
    </div>
  );
}

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
        throw new Error(await parseErrorResponse(response));
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

  const showOutput =
    status === "loading" ||
    status === "success" ||
    result.final_report_md ||
    result.itinerary_md ||
    result.budget_json;

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

          <article className="output-block output-block-scroll">
            {status === "loading" ? (
              <p className="muted loading-copy">
                Running the crew (research → budget → itinerary → review). This
                can take a minute on local models…
              </p>
            ) : showOutput ? (
              <OutputDisplay result={result} status={status} />
            ) : (
              <p className="muted">Run a prompt to see the output.</p>
            )}
          </article>
        </section>
      </main>
    </div>
  );
}
