"use client";

import Link from "next/link";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { useCallback, useEffect, useMemo, useState } from "react";
import {
  VARIANTS,
  fallbackDecision,
  type PageVisit,
  type PersonalizationContext,
  type PersonalizationDecision,
  type UtmContext,
  type VariantId,
} from "@/lib/personalization";

const STATIC_DEMO = process.env.NEXT_PUBLIC_STATIC_DEMO === "1";
const BASE_PATH = process.env.NEXT_PUBLIC_BASE_PATH || "";

const HISTORY_KEY = "jev-demo:page-history";
const REFERRER_KEY = "jev-demo:referrer";
const UTM_KEY = "jev-demo:utm";

const EMPTY_UTM: UtmContext = {
  source: "",
  medium: "",
  campaign: "",
  content: "",
  term: "",
};

function readJson<T>(storage: Storage, key: string, fallback: T): T {
  try {
    return JSON.parse(storage.getItem(key) || "") as T;
  } catch {
    return fallback;
  }
}

function readUtm(searchParams: URLSearchParams): UtmContext {
  return {
    source: searchParams.get("utm_source") || "",
    medium: searchParams.get("utm_medium") || "",
    campaign: searchParams.get("utm_campaign") || "",
    content: searchParams.get("utm_content") || "",
    term: searchParams.get("utm_term") || "",
  };
}

function percent(value: number) {
  return `${Math.round(value * 100)}%`;
}

export function PersonalizationDemo() {
  const pathname = usePathname();
  const router = useRouter();
  const searchParams = useSearchParams();
  const [context, setContext] = useState<PersonalizationContext | null>(null);
  const [decision, setDecision] = useState<PersonalizationDecision | null>(null);
  const [loading, setLoading] = useState(true);
  const [inspectorOpen, setInspectorOpen] = useState(false);
  const [refreshKey, setRefreshKey] = useState(0);

  const collectContext = useCallback(() => {
    const urlUtm = readUtm(new URLSearchParams(window.location.search));
    const hasUrlUtm = Object.values(urlUtm).some(Boolean);
    const storedUtm = readJson<UtmContext>(sessionStorage, UTM_KEY, EMPTY_UTM);
    const utm = hasUrlUtm ? urlUtm : storedUtm;
    if (hasUrlUtm) sessionStorage.setItem(UTM_KEY, JSON.stringify(urlUtm));

    let referrer = sessionStorage.getItem(REFERRER_KEY);
    if (referrer === null) {
      referrer = document.referrer;
      sessionStorage.setItem(REFERRER_KEY, referrer);
    }

    const existing = readJson<PageVisit[]>(localStorage, HISTORY_KEY, []);
    const now = new Date().toISOString();
    const mostRecent = existing.at(-1);
    const nextHistory =
      mostRecent?.path === pathname
        ? existing
        : [...existing, { path: pathname, visitedAt: now }].slice(-6);
    localStorage.setItem(HISTORY_KEY, JSON.stringify(nextHistory));

    setContext({
      referrer,
      utm,
      pageHistory: nextHistory,
      currentPath: pathname,
    });
  }, [pathname]);

  useEffect(() => {
    collectContext();
  }, [collectContext, searchParams, refreshKey]);

  useEffect(() => {
    if (!context) return;
    if (STATIC_DEMO) {
      setDecision(fallbackDecision(context, "Static public demo: function-only preview"));
      setLoading(false);
      return;
    }
    const controller = new AbortController();
    setLoading(true);
    fetch("/api/personalize", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ context }),
      signal: controller.signal,
    })
      .then(async (response) => {
        if (!response.ok) throw new Error("Personalization request failed");
        return (await response.json()) as PersonalizationDecision;
      })
      .then(setDecision)
      .catch((error: unknown) => {
        if ((error as Error).name !== "AbortError") console.error(error);
      })
      .finally(() => setLoading(false));
    return () => controller.abort();
  }, [context]);

  const variantId: VariantId = decision?.variant || "builder";
  const variant = VARIANTS[variantId];
  const campaignLabel = context?.utm.campaign || context?.utm.source;

  const contextLine = useMemo(() => {
    if (!context) return "Reading visitor context";
    if (campaignLabel) return `Campaign: ${campaignLabel}`;
    if (context.pageHistory.length >= 3) return `${context.pageHistory.length} recent page visits`;
    if (context.referrer) return `From ${new URL(context.referrer).hostname}`;
    return "Direct visit";
  }, [campaignLabel, context]);

  function tryCampaign() {
    sessionStorage.removeItem(UTM_KEY);
    localStorage.removeItem(HISTORY_KEY);
    router.push("/?utm_source=producthunt&utm_medium=social&utm_campaign=launch-week");
    setRefreshKey((key) => key + 1);
  }

  function tryReturning() {
    const now = Date.now();
    const seeded: PageVisit[] = ["/docs", "/product", "/pricing"].map((path, index) => ({
      path,
      visitedAt: new Date(now - (3 - index) * 60_000).toISOString(),
    }));
    localStorage.setItem(HISTORY_KEY, JSON.stringify(seeded));
    sessionStorage.removeItem(UTM_KEY);
    router.push("/");
    setRefreshKey((key) => key + 1);
  }

  function resetDemo() {
    localStorage.removeItem(HISTORY_KEY);
    sessionStorage.removeItem(UTM_KEY);
    sessionStorage.setItem(REFERRER_KEY, "");
    router.push("/");
    setRefreshKey((key) => key + 1);
  }

  return (
    <main className="site-shell" style={{ "--accent": variant.accent } as React.CSSProperties}>
      <div className="ambient ambient-one" />
      <div className="ambient ambient-two" />

      <header className="nav-wrap">
        <nav className="nav" aria-label="Main navigation">
          <Link className="brand" href="/" aria-label="Jev Decision Lab home">
            <img className="brand-logo" src={`${BASE_PATH}/jev-decision-lab-logo.png`} alt="" />
            <span>Jev Decision Lab</span>
          </Link>
          <div className="nav-links">
            <Link href="/">Proof lab</Link>
            <a href="https://github.com/RadRebelSam/jev-decision-lab" target="_blank" rel="noreferrer">GitHub</a>
            <a href="https://github.com/RadRebelSam/jev-decision-lab#run-the-live-proof-locally" target="_blank" rel="noreferrer">Run locally</a>
          </div>
          <button className="nav-cta" onClick={() => setInspectorOpen(true)}>
            View decision
          </button>
        </nav>
      </header>

      <section className="hero">
        <div className="hero-copy">
          <div className="signal-pill">
            <span className={`pulse ${loading ? "is-loading" : ""}`} />
            {loading ? "Jev is deciding" : contextLine}
          </div>
          <p className="eyebrow">{variant.eyebrow}</p>
          <h1>{variant.headline}</h1>
          <p className="lede">{variant.body}</p>
          <div className="hero-actions">
            <button className="primary-button">{variant.primaryCta}<span>↗</span></button>
            <button className="text-button">{variant.secondaryCta}<span>→</span></button>
          </div>
          <div className="proof-row">
            <div><strong>3</strong><span>fixed hero variants</span></div>
            <div><strong>4</strong><span>small context signals</span></div>
            <div><strong>&lt;1s</strong><span>decision target</span></div>
          </div>
        </div>

        <div className="decision-card" aria-label="Personalization decision preview">
          <div className="card-topline">
            <span>LIVE DECISION</span>
            <span className={`status ${decision?.source === "jev" ? "live" : "fallback"}`}>
              {loading ? "DECIDING" : decision?.source === "jev" ? "JEV" : "LOCAL FALLBACK"}
            </span>
          </div>
          <div className="variant-orbit">
            <div className="orbit-ring orbit-ring-one" />
            <div className="orbit-ring orbit-ring-two" />
            <div className="center-choice">
              <span>SELECTED</span>
              <strong>{variant.label}</strong>
              <small>{loading ? "—" : percent(decision?.confidence || 0)}</small>
            </div>
            <span className="orbit-node node-one">UTM</span>
            <span className="orbit-node node-two">REF</span>
            <span className="orbit-node node-three">HISTORY</span>
          </div>
          <div className="probability-list">
            {(["builder", "campaign", "returning"] as VariantId[]).map((id) => {
              const value = decision?.probabilities[id] || 0;
              return (
                <div className={`probability-row ${id === variantId ? "selected" : ""}`} key={id}>
                  <span>{VARIANTS[id].label}</span>
                  <div className="bar"><i style={{ width: loading ? "0%" : percent(value) }} /></div>
                  <strong>{loading ? "—" : percent(value)}</strong>
                </div>
              );
            })}
          </div>
          <button className="inspect-button" onClick={() => setInspectorOpen(true)}>
            Inspect the decision <span>⌘ K</span>
          </button>
        </div>
      </section>

      <section className="demo-strip" aria-label="Demo scenarios">
        <div>
          <span className="demo-label">TRY A SIGNAL</span>
          <p>Change only the input context. The hero follows.</p>
        </div>
        <div className="scenario-buttons">
          <button onClick={resetDemo}><span>01</span> Direct visit</button>
          <button onClick={tryCampaign}><span>02</span> UTM campaign</button>
          <button onClick={tryReturning}><span>03</span> Returning visitor</button>
        </div>
      </section>

      <section className="architecture">
        <div className="section-heading">
          <p className="eyebrow">The whole architecture</p>
          <h2>Small enough to trust.<br />Useful enough to ship.</h2>
        </div>
        <div className="flow-grid">
          <article>
            <span>01 / COLLECT</span>
            <h3>Browser context</h3>
            <p>Referrer, five UTM fields, current path, and six recent page visits.</p>
          </article>
          <div className="flow-arrow">→</div>
          <article>
            <span>02 / DECIDE</span>
            <h3>One Jev Choice</h3>
            <p>A server route sends one typed question with exactly three valid answers.</p>
          </article>
          <div className="flow-arrow">→</div>
          <article>
            <span>03 / RENDER</span>
            <h3>One fixed hero</h3>
            <p>The client swaps approved copy—not generated text, layouts, or components.</p>
          </article>
        </div>
      </section>

      <footer>
        <div className="brand"><img className="brand-logo" src={`${BASE_PATH}/jev-decision-lab-logo.png`} alt="" /><span>Jev Decision Lab</span></div>
        <p>Personalization without the platform.</p>
        <span>Jev demo / 2026</span>
      </footer>

      {inspectorOpen && (
        <div className="inspector-backdrop" onMouseDown={() => setInspectorOpen(false)}>
          <aside className="inspector" onMouseDown={(event) => event.stopPropagation()}>
            <div className="inspector-header">
              <div><span>DECISION TRACE</span><h2>Why this hero?</h2></div>
              <button onClick={() => setInspectorOpen(false)} aria-label="Close inspector">×</button>
            </div>
            <div className="inspect-section">
              <span className="inspect-label">OUTPUT</span>
              <div className="output-card">
                <div><span>Variant</span><strong>{variant.label}</strong></div>
                <div><span>Confidence</span><strong>{loading ? "—" : percent(decision?.confidence || 0)}</strong></div>
                <div><span>Source</span><strong>{decision?.source === "jev" ? "Jev API" : "Local rule"}</strong></div>
                <div><span>Latency</span><strong>{decision?.latencyMs ?? "—"} ms</strong></div>
              </div>
              {decision?.reason && <p className="fallback-note">Fallback reason: {decision.reason}</p>}
            </div>
            <div className="inspect-section">
              <span className="inspect-label">INPUT / REFERRER</span>
              <code>{context?.referrer || "direct"}</code>
            </div>
            <div className="inspect-section">
              <span className="inspect-label">INPUT / UTM</span>
              <div className="data-table">
                {Object.entries(context?.utm || EMPTY_UTM).map(([key, value]) => (
                  <div key={key}><span>utm_{key}</span><strong>{value || "—"}</strong></div>
                ))}
              </div>
            </div>
            <div className="inspect-section">
              <span className="inspect-label">INPUT / PAGE HISTORY</span>
              <div className="history-list">
                {context?.pageHistory.length ? context.pageHistory.map((visit, index) => (
                  <div key={`${visit.path}-${index}`}><span>{String(index + 1).padStart(2, "0")}</span><strong>{visit.path}</strong></div>
                )) : <p>No page history yet.</p>}
              </div>
            </div>
          </aside>
        </div>
      )}
    </main>
  );
}
