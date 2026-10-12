import { NextResponse } from "next/server";
import {
  fallbackDecision,
  isVariantId,
  type PersonalizationContext,
  type VariantId,
} from "@/lib/personalization";

export const runtime = "nodejs";

type JevChoiceAnswer = {
  choice?: unknown;
  confidence?: unknown;
  probabilities?: unknown;
};

function normalizeProbabilities(value: unknown): Record<VariantId, number> | null {
  if (!value || typeof value !== "object") return null;
  const record = value as Record<string, unknown>;
  const builder = Number(record.builder);
  const campaign = Number(record.campaign);
  const returning = Number(record.returning);
  if (![builder, campaign, returning].every(Number.isFinite)) return null;
  return { builder, campaign, returning };
}

function isContext(value: unknown): value is PersonalizationContext {
  if (!value || typeof value !== "object") return false;
  const context = value as Partial<PersonalizationContext>;
  return (
    typeof context.referrer === "string" &&
    typeof context.currentPath === "string" &&
    !!context.utm &&
    Array.isArray(context.pageHistory)
  );
}

export async function POST(request: Request) {
  const startedAt = performance.now();
  const body: unknown = await request.json().catch(() => null);
  const context = (body as { context?: unknown } | null)?.context;

  if (!isContext(context)) {
    return NextResponse.json({ error: "Invalid personalization context" }, { status: 400 });
  }

  const apiKey = process.env.TYPESAFE_API_KEY || process.env.JEV_API_KEY;
  if (!apiKey) {
    return NextResponse.json(fallbackDecision(context));
  }

  const baseUrl = (process.env.TYPESAFE_BASE_URL || "https://api.typesafe.ai").replace(/\/$/, "");
  const model = process.env.TYPESAFE_DEFAULT_MODEL || "jev-latest";

  try {
    const response = await fetch(`${baseUrl}/v1/systemone`, {
      method: "POST",
      headers: {
        Authorization: `Bearer ${apiKey}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        model,
        state: {
          referrer: context.referrer || "direct",
          utm: context.utm,
          current_page: context.currentPath,
          recent_page_history: context.pageHistory,
        },
        questions: {
          hero_variant: {
            type: "choice",
            instructions:
              "Choose exactly one hero variant for this visitor. Use only the supplied referrer, UTM parameters, current page, and page history. Prefer campaign when an acquisition message should be continued. Prefer returning when history shows meaningful prior exploration. Prefer builder for direct, developer, or otherwise low-context visits.",
            criteria: {
              builder: "A clear product-led hero for direct, developer, documentation, or low-context traffic.",
              campaign: "A message-match hero for visitors arriving through a campaign, social post, search, or tagged link.",
              returning: "A continuity hero for visitors with meaningful recent page history or repeat exploration.",
            },
          },
        },
      }),
      cache: "no-store",
      signal: AbortSignal.timeout(8000),
    });

    if (!response.ok) {
      throw new Error(`Jev returned HTTP ${response.status}`);
    }

    const data = (await response.json()) as {
      answers?: { hero_variant?: JevChoiceAnswer };
    };
    const answer = data.answers?.hero_variant;
    const choice = answer?.choice;
    const probabilities = normalizeProbabilities(answer?.probabilities);

    if (!isVariantId(choice) || !probabilities) {
      throw new Error("Jev returned an unexpected response shape");
    }

    return NextResponse.json({
      variant: choice,
      confidence: Number(answer?.confidence) || probabilities[choice],
      probabilities,
      source: "jev",
      latencyMs: Math.round(performance.now() - startedAt),
    });
  } catch (error) {
    const reason = error instanceof Error ? error.message : "Jev request failed";
    const fallback = fallbackDecision(context, reason);
    return NextResponse.json({
      ...fallback,
      latencyMs: Math.round(performance.now() - startedAt),
    });
  }
}
