import { NextResponse } from "next/server";
import {
  BENCHMARK_SCENARIOS,
  extractFeatures,
  functionOnlyDecision,
  routeHybrid,
} from "@/lib/benchmark";
import { isVariantId, type VariantId } from "@/lib/personalization";

export const runtime = "nodejs";

type JevAnswer = {
  choice?: unknown;
  confidence?: unknown;
  probabilities?: unknown;
};

export async function POST() {
  const startedAt = performance.now();
  const apiKey = process.env.TYPESAFE_API_KEY || process.env.JEV_API_KEY;
  const routed = BENCHMARK_SCENARIOS.map((scenario) => ({
    scenario,
    baseline: functionOnlyDecision(scenario.context),
    route: routeHybrid(scenario.context),
  }));
  const ambiguous = routed.filter((item) => item.route.needsJev);

  if (!apiKey) {
    return NextResponse.json(
      { error: "TYPESAFE_API_KEY is not configured. The benchmark cannot prove live Jev behavior." },
      { status: 503 },
    );
  }

  const questions = Object.fromEntries(
    ambiguous.map(({ scenario }) => [
      scenario.id,
      {
        type: "choice",
        instructions: [
          `Choose the best hero for visitor case '${scenario.id}'.`,
          "Use only that case's referrer, UTM, current page, derived features, and recent page history.",
          "Policy: campaign continues a meaningful external acquisition promise; returning continues an established product evaluation journey; builder serves developer-oriented or genuinely low-context visits.",
          "Treat internal navigation tags as non-acquisition. Page meaning matters more than raw page count. When signals conflict, choose the visitor's dominant current intent.",
        ].join(" "),
        criteria: {
          builder: "Developer, documentation, SDK, repository, direct, or low-context product introduction.",
          campaign: "External paid, social, launch, search, or email acquisition whose message should be continued.",
          returning: "Meaningful prior product, pricing, security, enterprise, or commercial evaluation that should continue.",
        },
      },
    ]),
  );

  const state = ambiguous.map(({ scenario }) => ({
    id: scenario.id,
    context: scenario.context,
    derived_features: extractFeatures(scenario.context),
  }));

  try {
    const baseUrl = (process.env.TYPESAFE_BASE_URL || "https://api.typesafe.ai").replace(/\/$/, "");
    const response = await fetch(`${baseUrl}/v1/systemone`, {
      method: "POST",
      headers: {
        Authorization: `Bearer ${apiKey}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        model: process.env.TYPESAFE_DEFAULT_MODEL || "jev-latest",
        state,
        questions,
      }),
      cache: "no-store",
      signal: AbortSignal.timeout(10_000),
    });

    if (!response.ok) throw new Error(`Jev returned HTTP ${response.status}`);
    const data = (await response.json()) as { answers?: Record<string, JevAnswer> };

    const results = routed.map(({ scenario, baseline, route }) => {
      let hybrid: VariantId;
      let decidedBy: "function" | "jev";
      let confidence: number;

      if (!route.needsJev) {
        hybrid = route.variant;
        decidedBy = "function";
        confidence = 1;
      } else {
        const answer = data.answers?.[scenario.id];
        if (!isVariantId(answer?.choice)) {
          throw new Error(`Invalid Jev answer for ${scenario.id}`);
        }
        hybrid = answer.choice;
        decidedBy = "jev";
        confidence = Number(answer.confidence) || 0;
      }

      return {
        id: scenario.id,
        baseline,
        hybrid,
        expected: scenario.expected,
        baselineCorrect: baseline === scenario.expected,
        hybridCorrect: hybrid === scenario.expected,
        decidedBy,
        confidence,
        routeReason: route.reason,
      };
    });

    const baselineCorrect = results.filter((result) => result.baselineCorrect).length;
    const hybridCorrect = results.filter((result) => result.hybridCorrect).length;

    return NextResponse.json({
      results,
      summary: {
        total: results.length,
        baselineCorrect,
        hybridCorrect,
        jevCalls: ambiguous.length,
        functionCalls: results.length - ambiguous.length,
        latencyMs: Math.round(performance.now() - startedAt),
      },
      disclosure: "Expected labels were used only for scoring after the Jev response. They were not included in Jev state or questions. This proves decision behavior on the labeled MVP set, not conversion lift.",
      source: "live",
    });
  } catch (error) {
    return NextResponse.json(
      { error: error instanceof Error ? error.message : "Benchmark failed" },
      { status: 502 },
    );
  }
}
