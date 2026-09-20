"use client";

import Link from "next/link";
import { useState } from "react";
import { BENCHMARK_SCENARIOS, RECORDED_BENCHMARK, type BenchmarkResponse } from "@/lib/benchmark";
import { VARIANTS, type VariantId } from "@/lib/personalization";

const STATIC_DEMO = process.env.NEXT_PUBLIC_STATIC_DEMO === "1";
const BASE_PATH = process.env.NEXT_PUBLIC_BASE_PATH || "";
const GITHUB_URL = "https://github.com/RadRebelSam/jev-decision-lab";

const pct = (correct: number, total: number) => `${Math.round((correct / total) * 100)}%`;

function VariantBadge({ value }: { value: VariantId }) {
  return <span className={`variant-badge ${value}`}>{VARIANTS[value].label}</span>;
}

export function ProofLab() {
  const [data, setData] = useState<BenchmarkResponse | null>(
    STATIC_DEMO ? RECORDED_BENCHMARK : null,
  );
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function runBenchmark() {
    setLoading(true);
    setError("");
    if (STATIC_DEMO) {
      window.setTimeout(() => {
        setData(RECORDED_BENCHMARK);
        setLoading(false);
      }, 420);
      return;
    }
    try {
      const response = await fetch("/api/benchmark", { method: "POST" });
      const payload = (await response.json()) as BenchmarkResponse;
      if (!response.ok) throw new Error(payload.error || "Benchmark failed");
      setData(payload);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Benchmark failed");
    } finally {
      setLoading(false);
    }
  }

  const resultById = new Map(data?.results.map((result) => [result.id, result]));

  return (
    <main className="proof-shell">
      <header className="nav-wrap proof-nav-wrap">
        <nav className="nav">
          <Link className="brand" href="/"><img className="brand-logo" src={`${BASE_PATH}/jev-decision-lab-logo.png`} alt="" /><span>Jev Decision Lab</span></Link>
          <div className="nav-links"><Link href="/demo">Personalization demo</Link><a href="#cases">Test set</a><a href="#method">Method</a></div>
          <a className="nav-cta nav-link-button" href={GITHUB_URL} target="_blank" rel="noreferrer">GitHub ↗</a>
        </nav>
      </header>

      <section className="proof-hero">
        <div className="proof-kicker"><span /> HYBRID DECISION BENCHMARK</div>
        <h1>Rules for the obvious.<br /><em>Jev for the ambiguous.</em></h1>
        <p>Eight labeled visitor journeys. One transparent baseline. Expected answers are withheld from Jev until scoring.</p>
        <button className="run-button" onClick={runBenchmark} disabled={loading}>
          {loading ? <><i /> Loading benchmark</> : <>{STATIC_DEMO ? "Replay recorded proof" : "Run live proof"}<span>→</span></>}
        </button>
        <a className="local-run-link" href={`${GITHUB_URL}#run-the-live-proof-locally`} target="_blank" rel="noreferrer">Run live with your own key ↗</a>
        {error && <p className="benchmark-error">{error}</p>}
      </section>

      <section className="scoreboard" aria-live="polite">
        <div className="score-card baseline-score">
          <div><span>FUNCTION ONLY</span><small>One fixed priority tree</small></div>
          <strong>{data ? pct(data.summary.baselineCorrect, data.summary.total) : "—"}</strong>
          <p>{data ? `${data.summary.baselineCorrect} of ${data.summary.total} matched the labeled rubric` : "Run the benchmark to score"}</p>
        </div>
        <div className="versus">VS</div>
        <div className="score-card hybrid-score">
          <div><span>FUNCTION + JEV</span><small>Rules route; Jev resolves conflict</small></div>
          <strong>{data ? pct(data.summary.hybridCorrect, data.summary.total) : "—"}</strong>
          <p>{data ? `${data.summary.hybridCorrect} of ${data.summary.total} matched the labeled rubric` : "Run the benchmark to score"}</p>
        </div>
        <div className="efficiency-card">
          <span>API EFFICIENCY</span>
          <strong>{data ? `${data.summary.functionCalls}/${data.summary.total}` : "—"}</strong>
          <p>cases handled by function without Jev</p>
          {data && <small>{data.summary.jevCalls} judgments · {data.summary.latencyMs} ms total</small>}
        </div>
      </section>

      <section className="case-section" id="cases">
        <div className="case-heading">
          <div><span>THE TEST SET</span><h2>Every answer is inspectable.</h2></div>
          <p>The baseline always prioritizes page-count first, then UTM/referrer, then default. The hybrid uses functions for clear cases and sends only conflicts to Jev.</p>
        </div>
        <div className="case-table">
          <div className="case-table-head">
            <span>Visitor journey</span><span>Expected</span><span>Function only</span><span>Hybrid result</span>
          </div>
          {BENCHMARK_SCENARIOS.map((scenario, index) => {
            const result = resultById.get(scenario.id);
            return (
              <article className="case-row" key={scenario.id}>
                <div className="case-title"><small>{String(index + 1).padStart(2, "0")}</small><div><strong>{scenario.title}</strong><p>{scenario.tension}</p></div></div>
                <div><VariantBadge value={scenario.expected} /><small className="cell-label">Labeled rubric</small></div>
                <div className={result ? (result.baselineCorrect ? "correct-cell" : "wrong-cell") : ""}>
                  {result ? <><VariantBadge value={result.baseline} /><b>{result.baselineCorrect ? "✓" : "×"}</b></> : <span className="pending-value">—</span>}
                </div>
                <div className={result ? (result.hybridCorrect ? "correct-cell" : "wrong-cell") : ""}>
                  {result ? <><VariantBadge value={result.hybrid} /><b>{result.hybridCorrect ? "✓" : "×"}</b><small className={`decider ${result.decidedBy}`}>{result.decidedBy}</small></> : <span className="pending-value">—</span>}
                </div>
              </article>
            );
          })}
        </div>
      </section>

      <section className="method-section" id="method">
        <div className="method-copy"><span>MVP ARCHITECTURE</span><h2>The function is the frame.<br />Jev fills the gap.</h2></div>
        <div className="method-flow">
          <article><span>01</span><h3>Function extracts facts</h3><p>Normalize referrer, classify UTM, count meaningful paths, and detect obvious cases.</p></article>
          <i>→</i>
          <article><span>02</span><h3>Jev resolves conflict</h3><p>Only ambiguous combinations become typed, three-way Jev choices.</p></article>
          <i>→</i>
          <article><span>03</span><h3>Function enforces safety</h3><p>Validate the answer, restrict it to three variants, and fall back on failure.</p></article>
        </div>
        <div className="fairness-note">
          <span>FAIRNESS CHECK</span>
          <p>{data?.disclosure || (STATIC_DEMO ? "This public site replays a recorded live run. Clone the repository to rerun it with your own key." : "Expected labels exist in the browser test set, but the API constructs a separate Jev payload without them. This tests decision quality, not conversion lift.")}</p>
        </div>
        <div className="open-source-cta"><div><span>OPEN SOURCE</span><h3>Verify it on your machine.</h3><p>Clone the repository, add your own TypeSafe key locally, and rerun every case.</p></div><a href={GITHUB_URL} target="_blank" rel="noreferrer">View on GitHub <span>↗</span></a></div>
      </section>
    </main>
  );
}
