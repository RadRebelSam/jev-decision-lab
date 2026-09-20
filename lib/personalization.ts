export const VARIANT_IDS = ["builder", "campaign", "returning"] as const;

export type VariantId = (typeof VARIANT_IDS)[number];

export type UtmContext = {
  source: string;
  medium: string;
  campaign: string;
  content: string;
  term: string;
};

export type PageVisit = {
  path: string;
  visitedAt: string;
};

export type PersonalizationContext = {
  referrer: string;
  utm: UtmContext;
  pageHistory: PageVisit[];
  currentPath: string;
};

export type PersonalizationDecision = {
  variant: VariantId;
  confidence: number;
  probabilities: Record<VariantId, number>;
  source: "jev" | "fallback";
  latencyMs: number;
  reason?: string;
};

export const VARIANTS: Record<
  VariantId,
  {
    label: string;
    eyebrow: string;
    headline: string;
    body: string;
    primaryCta: string;
    secondaryCta: string;
    accent: string;
  }
> = {
  builder: {
    label: "Builder",
    eyebrow: "A decision layer for product teams",
    headline: "Make every first visit feel intentional.",
    body: "Turn a small amount of session context into a fast, typed experience decision—without building a rules engine.",
    primaryCta: "Start building",
    secondaryCta: "Read the docs",
    accent: "#7c5cff",
  },
  campaign: {
    label: "Campaign",
    eyebrow: "Message match, from click to landing page",
    headline: "Keep the promise that brought them here.",
    body: "Jev reads campaign signals and selects the hero most likely to continue the visitor’s journey.",
    primaryCta: "Launch a campaign",
    secondaryCta: "See how it works",
    accent: "#ff6f4d",
  },
  returning: {
    label: "Returning",
    eyebrow: "Welcome back—your momentum is waiting",
    headline: "Pick up where you left off.",
    body: "Recent page history tells Jev when a visitor is exploring deeply, so the page can move the conversation forward.",
    primaryCta: "Continue exploring",
    secondaryCta: "View your path",
    accent: "#20b486",
  },
};

export function fallbackDecision(
  context: PersonalizationContext,
  reason = "Jev API key is not configured",
): PersonalizationDecision {
  const hasUtm = Object.values(context.utm).some(Boolean);
  const referrer = context.referrer.toLowerCase();
  const isCampaignReferrer = /(producthunt|linkedin|twitter|x\.com|facebook|instagram|google)/.test(referrer);
  const isReturning = context.pageHistory.length >= 3;

  let variant: VariantId = "builder";
  let probabilities: Record<VariantId, number> = {
    builder: 0.72,
    campaign: 0.16,
    returning: 0.12,
  };

  if (isReturning) {
    variant = "returning";
    probabilities = { builder: 0.08, campaign: 0.12, returning: 0.8 };
  } else if (hasUtm || isCampaignReferrer) {
    variant = "campaign";
    probabilities = { builder: 0.08, campaign: 0.84, returning: 0.08 };
  }

  return {
    variant,
    confidence: probabilities[variant],
    probabilities,
    source: "fallback",
    latencyMs: 0,
    reason,
  };
}

export function isVariantId(value: unknown): value is VariantId {
  return typeof value === "string" && VARIANT_IDS.includes(value as VariantId);
}
