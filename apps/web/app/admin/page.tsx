"use client";

import { useEffect, useState } from "react";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
type Run = { id: number; status: string; started_at: string; finished_at?: string; summary: Record<string, number> };

export default function AdminPage() {
  const [runs, setRuns] = useState<Run[]>([]);
  const [running, setRunning] = useState(false);

  async function refresh() {
    const response = await fetch(`${API}/api/ingestion/runs`);
    setRuns(await response.json());
  }

  useEffect(() => { refresh().catch(() => setRuns([])); }, []);

  async function ingest() {
    setRunning(true);
    try {
      await fetch(`${API}/api/ingestion/runs`, { method: "POST" });
      await refresh();
    } finally {
      setRunning(false);
    }
  }

  return <main className="admin">
    <section className="panel admin-card">
      <div className="admin-heading">
        <div><span>ADMIN</span><h1>Ingestion runs</h1><p>Discover PDFs, TV5Monde series and matching audio tracks without manual content entry.</p></div>
        <button onClick={ingest} disabled={running}>{running ? "Importing…" : "Run ingestion"}</button>
      </div>
      <div className="run-list">
        {runs.length === 0 && <p className="muted">No ingestion runs have been recorded.</p>}
        {runs.map((run) => <article key={run.id}>
          <strong>Run #{run.id} · {run.status}</strong>
          <small>{new Date(run.started_at).toLocaleString()}</small>
          <div className="stats">
            {Object.entries(run.summary).map(([key, value]) => <span key={key}><b>{value}</b>{key.replace("_", " ")}</span>)}
          </div>
        </article>)}
      </div>
    </section>
  </main>;
}

