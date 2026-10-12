import type { PersonalizationContext, VariantId } from "@/lib/personalization";

export type BenchmarkScenario = {
  id: string;
  title: string;
  tension: string;
  expected: VariantId;
  context: PersonalizationContext;
};

export type ContextFeatures = {
  hasAnyUtm: boolean;
  externalCampaign: boolean;
  developerSignals: number;
  productIntentPages: number;
  historyDepth: number;
};

export type HybridRoute =
  | { needsJev: false; variant: VariantId; reason: string }
  | { needsJev: true; reason: string };

export type BenchmarkResult = {
  id: string;
  baseline: VariantId;
  hybrid: VariantId;
  expected: VariantId;
  baselineCorrect: boolean;
  hybridCorrect: boolean;
  decidedBy: "function" | "jev";
  confidence: number;
  routeReason: string;
};

export type BenchmarkResponse = {
  results: BenchmarkResult[];
  summary: {
    total: number;
    baselineCorrect: number;
    hybridCorrect: number;
    jevCalls: number;
    functionCalls: number;
    latencyMs: number;
  };
  disclosure: string;
  source: "live" | "recorded";
  recordedAt?: string;
  error?: string;
};

export const RECORDED_BENCHMARK: BenchmarkResponse = {
  results: [
    { id: "launch-after-reading", baseline: "returning", hybrid: "campaign", expected: "campaign", baselineCorrect: false, hybridCorrect: true, decidedBy: "jev", confidence: 0.84, routeReason: "Signals conflict; semantic judgment required" },
    { id: "developer-evaluation", baseline: "returning", hybrid: "builder", expected: "builder", baselineCorrect: false, hybridCorrect: true, decidedBy: "jev", confidence: 0.9, routeReason: "Signals conflict; semantic judgment required" },
    { id: "commercial-return", baseline: "returning", hybrid: "returning", expected: "returning", baselineCorrect: true, hybridCorrect: true, decidedBy: "function", confidence: 1, routeReason: "Clear product evaluation history" },
    { id: "internal-tag", baseline: "returning", hybrid: "returning", expected: "returning", baselineCorrect: true, hybridCorrect: true, decidedBy: "function", confidence: 1, routeReason: "Clear product evaluation history" },
    { id: "fresh-paid-search", baseline: "campaign", hybrid: "campaign", expected: "campaign", baselineCorrect: true, hybridCorrect: true, decidedBy: "function", confidence: 1, routeReason: "Clear external acquisition" },
    { id: "direct-first-visit", baseline: "builder", hybrid: "builder", expected: "builder", baselineCorrect: true, hybridCorrect: true, decidedBy: "function", confidence: 1, routeReason: "Clear direct visit" },
    { id: "tagged-github-readme", baseline: "campaign", hybrid: "builder", expected: "builder", baselineCorrect: false, hybridCorrect: true, decidedBy: "jev", confidence: 0.87, routeReason: "Signals conflict; semantic judgment required" },
    { id: "newsletter-vs-pricing", baseline: "returning", hybrid: "returning", expected: "returning", baselineCorrect: true, hybridCorrect: true, decidedBy: "jev", confidence: 0.79, routeReason: "Signals conflict; semantic judgment required" },
  ],
  summary: {
    total: 8,
    baselineCorrect: 5,
    hybridCorrect: 8,
    jevCalls: 4,
    functionCalls: 4,
    latencyMs: 254,
  },
  disclosure: "Recorded live Jev run from September 20, 2026. Expected labels were used only for scoring after the response and were not included in Jev state or questions. This proves behavior on the labeled MVP set, not conversion lift.",
  source: "recorded",
  recordedAt: "2026-09-20T10:37:49-07:00",
};

const visit = (path: string, minutesAgo: number) => ({
  path,
  visitedAt: new Date(Date.UTC(2026, 8, 20, 16, 0) - minutesAgo * 60_000).toISOString(),
});

const emptyUtm = {
  source: "",
  medium: "",
  campaign: "",
  content: "",
  term: "",
};

export const BENCHMARK_SCENARIOS: BenchmarkScenario[] = [
  {
    id: "launch-after-reading",
    title: "Launch click after casual reading",
    tension: "Active Product Hunt campaign vs. three editorial page visits",
    expected: "campaign",
    context: {
      referrer: "https://www.producthunt.com/posts/kanso",
      utm: { source: "producthunt", medium: "social", campaign: "launch-week", content: "hero", term: "" },
      pageHistory: [visit("/blog", 42), visit("/blog/system-one", 31), visit("/about", 18)],
      currentPath: "/",
    },
  },
  {
    id: "developer-evaluation",
    title: "Developer evaluation",
    tension: "Deep history normally means returning, but every signal is technical",
    expected: "builder",
    context: {
      referrer: "https://github.com/typesafe-ai/examples",
      utm: emptyUtm,
      pageHistory: [visit("/docs", 28), visit("/docs/api", 19), visit("/examples", 8)],
      currentPath: "/docs/quickstart",
    },
  },
  {
    id: "commercial-return",
    title: "High-intent return",
    tension: "No acquisition signal and repeated commercial exploration",
    expected: "returning",
    context: {
      referrer: "",
      utm: emptyUtm,
      pageHistory: [visit("/product", 1_440), visit("/pricing", 1_420), visit("/security", 40), visit("/pricing", 5)],
      currentPath: "/",
    },
  },
  {
    id: "internal-tag",
    title: "Internal campaign tag",
    tension: "UTM exists, but it marks internal navigation—not acquisition",
    expected: "returning",
    context: {
      referrer: "",
      utm: { source: "internal", medium: "navigation", campaign: "pricing-return", content: "nav", term: "" },
      pageHistory: [visit("/pricing", 36), visit("/enterprise", 22), visit("/security", 9)],
      currentPath: "/contact",
    },
  },
  {
    id: "fresh-paid-search",
    title: "Fresh paid-search visitor",
    tension: "Strong acquisition signal and no meaningful history",
    expected: "campaign",
    context: {
      referrer: "https://www.google.com/search?q=personalization+api",
      utm: { source: "google", medium: "cpc", campaign: "brand-search", content: "api", term: "personalization api" },
      pageHistory: [visit("/", 0)],
      currentPath: "/",
    },
  },
  {
    id: "direct-first-visit",
    title: "Low-context direct visit",
    tension: "No evidence for a specialized experience",
    expected: "builder",
    context: {
      referrer: "",
      utm: emptyUtm,
      pageHistory: [visit("/", 0)],
      currentPath: "/",
    },
  },
  {
    id: "tagged-github-readme",
    title: "Tagged GitHub README",
    tension: "A UTM-tagged link that is still clearly developer traffic",
    expected: "builder",
    context: {
      referrer: "https://github.com/acme/sdk",
      utm: { source: "github", medium: "repository", campaign: "sdk-readme", content: "quickstart", term: "" },
      pageHistory: [visit("/docs/sdk", 0)],
      currentPath: "/docs/sdk",
    },
  },
  {
    id: "newsletter-vs-pricing",
    title: "Newsletter click during evaluation",
    tension: "Fresh email click vs. an established pricing and security journey",
    expected: "returning",
    context: {
      referrer: "https://mail.google.com/",
      utm: { source: "newsletter", medium: "email", campaign: "september-update", content: "feature", term: "" },
      pageHistory: [visit("/pricing", 2_880), visit("/security", 1_420), visit("/enterprise", 60), visit("/pricing", 12)],
      currentPath: "/product/new-feature",
    },
  },
];

export function extractFeatures(context: PersonalizationContext): ContextFeatures {
  const host = (() => {
    try {
      return new URL(context.referrer).hostname.toLowerCase();
    } catch {
      return "";
    }
  })();
  const medium = context.utm.medium.toLowerCase();
  const source = context.utm.source.toLowerCase();
  const paths = [...context.pageHistory.map((item) => item.path), context.currentPath];
  const developerSignals =
    Number(/github|gitlab|docs\./.test(host)) +
    Number(/github|developer|docs/.test(source)) +
    Number(/repository|developer/.test(medium)) +
    paths.filter((path) => /\/(docs|api|sdk|examples)/.test(path)).length;
  const productIntentPages = paths.filter((path) =>
    /\/(product|pricing|security|enterprise|checkout|contact|integrations)/.test(path),
  ).length;
  const externalCampaign =
    /^(cpc|paid|social|email|affiliate|display)$/.test(medium) ||
    /^(producthunt|google|linkedin|newsletter|twitter|facebook)$/.test(source);

  return {
    hasAnyUtm: Object.values(context.utm).some(Boolean),
    externalCampaign,
    developerSignals,
    productIntentPages,
    historyDepth: context.pageHistory.length,
  };
}

export function functionOnlyDecision(context: PersonalizationContext): VariantId {
  const features = extractFeatures(context);
  const referrer = context.referrer.toLowerCase();
  const campaignReferrer = /(producthunt|linkedin|twitter|x\.com|facebook|instagram|google)/.test(referrer);
  if (features.historyDepth >= 3) return "returning";
  if (features.hasAnyUtm || campaignReferrer) return "campaign";
  return "builder";
}

export function routeHybrid(context: PersonalizationContext): HybridRoute {
  const features = extractFeatures(context);

  if (!features.hasAnyUtm && !context.referrer && features.historyDepth <= 1) {
    return { needsJev: false, variant: "builder", reason: "Clear direct visit" };
  }
  if (features.externalCampaign && features.historyDepth <= 1 && features.developerSignals === 0) {
    return { needsJev: false, variant: "campaign", reason: "Clear external acquisition" };
  }
  if (features.productIntentPages >= 3 && !features.externalCampaign) {
    return { needsJev: false, variant: "returning", reason: "Clear product evaluation history" };
  }

  return { needsJev: true, reason: "Signals conflict; semantic judgment required" };
}
