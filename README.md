# Jev Decision Lab

**Rules for the obvious. Classical ML for stable structured prediction. Jev for the ambiguous.**

An open-source Next.js MVP that compares a fixed personalization function with a hybrid function-plus-Jev decision architecture.

Public site: [radrebelsam.github.io/jev-decision-lab](https://radrebelsam.github.io/jev-decision-lab/)

## What it demonstrates

- Function-only baseline: page-count first, then campaign signals, then a default.
- Hybrid route: functions handle clear cases; Jev receives only conflicting cases.
- Fixed output schema: `builder | campaign | returning`.
- Transparent labeled test set with the expected answers withheld from Jev.
- Public static replay with no hosted API key.
- Local live mode where each developer uses their own TypeSafe key.

The recorded MVP run scored:

| Approach | Result |
| --- | ---: |
| Function only | 5/8 · 63% |
| Function + Jev | 8/8 · 100% |
| Cases handled without Jev | 4/8 |

This is a behavioral proof-of-concept on eight designed cases. It shows how the hybrid routing architecture behaves against a labeled rubric. It is not statistical proof and is not evidence of conversion lift. Production validation requires an online randomized experiment.

## Evidence levels

### 1. Designed Hybrid Benchmark

Tests whether rules plus Jev can handle clear and ambiguous personalization decisions across the existing eight designed cases.

### 2. Real Ecommerce Session Benchmark

Tests Jev against structured baselines using real ecommerce session data and a real purchase outcome.

### 3. Online Randomized Experiment

Required to determine whether a Jev-powered personalization policy actually improves conversion, revenue per visitor, average order value, margin, or another business outcome.

## Findings

| Experiment | Finding | What it supports |
| --- | --- | --- |
| Eight designed personalization cases | Function only: 5/8. Function + Jev: 8/8. | A hybrid router can preserve explicit rules while using Jev for designed conflicts. This is behavioral proof, not statistical evidence. |
| Real structured ecommerce prediction | On the same 30-session sample, Logistic Regression F1 was 0.381 and Jev F1 was 0.286. Jev predicted `Purchase` for all 150 repeated decisions. | Jev was a poor fit for this fixed-label tabular task. Classical ML is the better default here. |
| Google Analytics runtime decisions | Rules handled 212/300 points (`70.7%`). Jev was reserved for 88 mixed-context points. A balanced 20-point Jev sample used all three options and had a 10% flip rate. | Explicit routing can reduce API use. Jev can express runtime choices, but stability is not correctness. |

The evidence supports a narrower and more useful thesis:

- Use deterministic functions when policy is known.
- Use classical ML when labels and features are stable.
- Use Jev when the decision options or context are defined at runtime.
- Use confidence thresholds and safe fallbacks when Jev is uncertain.
- Use randomized experiments before claiming business impact.

The evidence does **not** show that Jev personalization improves conversion, revenue, average order value, or margin. The Google Analytics dataset has no correct personalization-component label. The observed relationship between a selected experience and a later purchase is descriptive only.

## Project feedback

### What is working

- Negative results are reported instead of hidden.
- The project distinguishes behavioral, predictive, and causal evidence.
- API keys remain server-side, and the public build uses static results.
- Target and late-session leakage are explicitly controlled.
- The Google Analytics extractor reconstructs history without loading 25 GB into memory.
- The hybrid router makes API usage narrow and auditable.

### Current weaknesses

- Jev evaluations are small: 30 structured sessions and 20 runtime decision points.
- The runtime task has no human or experimental ground-truth component labels.
- Jev confidence is recorded but is not yet used for abstention or fallback.
- The balanced Logistic Regression probabilities are poorly calibrated.
- There is no stronger tree-based tabular baseline such as CatBoost.
- Dollar cost is unavailable because the API response reports tokens but not price.
- The Google Analytics traffic is historical, from 2016–2018.
- Kaggle competition rules prevent this repository from redistributing the derived data.

## Real Ecommerce Session Benchmark

The second benchmark uses the [UCI Online Shoppers Purchasing Intention dataset](https://archive.ics.uci.edu/dataset/468/online+shoppers+purchasing+intention+dataset). It was selected because it is small, reproducible, and contains 12,330 real ecommerce sessions with a real binary `Revenue` outcome.

The task is deliberately narrow:

```text
session features -> predict purchase / no purchase
```

The benchmark compares a simple rule, Logistic Regression, and an optional local Jev run. It reports accuracy, precision, recall, F1, latency, and—when probability output is available—Brier score and calibration error. A configurable repeated-run sample measures Jev decision flips and probability variation.

The reproducible seed-42 baseline run currently records:

| Approach | Accuracy | Precision | Recall | F1 | Brier | 10-bin ECE |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Simple rule | 0.498 | 0.205 | 0.782 | 0.325 | unavailable | unavailable |
| Logistic Regression | 0.636 | 0.263 | 0.753 | 0.390 | 0.212 | 0.274 |

The dataset is imbalanced: 1,908 of 12,330 sessions end in a purchase. Logistic Regression uses balanced class weights, which improves positive-class detection but makes its raw probabilities less calibrated. The machine-readable result is in [`baseline_results.json`](./benchmarks/online_shoppers/results/baseline_results.json).

A separate live `jev-latest` run evaluated the same 30 held-out sessions five times. Jev selected `Purchase` for all 150 decisions: accuracy `0.167`, F1 `0.286`, Brier score `0.436`, and 10-bin ECE `0.546`. Its decision flip rate was `0%`, but the stable output had collapsed to one class. On those same 30 sessions, Logistic Regression reached accuracy `0.567` and F1 `0.381`. This supports the project's thesis rather than being hidden: classical ML was the better fit for this fixed-label tabular sample.

The dataset does **not** provide a correct hero or UI-component label. It does **not** prove conversion lift from Jev personalization. Its rows summarize completed sessions, so the benchmark is retrospective structured prediction rather than an early-session production decision. `Revenue` is target-only, and the late-session, outcome-adjacent `PageValues` field is excluded from every model and Jev prompt.

See [`benchmarks/online_shoppers`](./benchmarks/online_shoppers/README.md) for the feature policy, limitations, exact reproduction commands, and stability method.

### Interpretation

The result is informative regardless of which model wins. If Logistic Regression wins the structured prediction task, that supports using classical ML for stable, fixed-label tabular problems instead of routing everything through Jev.

Jev's more interesting role is in ambiguous, runtime-defined decisions where the available options or decision context may change without retraining a classifier.

## Run the live proof locally

Requirements:

- Node.js 22
- A TypeSafe API key

Clone and install:

```bash
git clone https://github.com/RadRebelSam/jev-decision-lab.git
cd jev-decision-lab
npm install
```

Create `.env.local` in the project root:

```env
TYPESAFE_API_KEY=your_own_key
```

Start the live app:

```bash
npm run dev
```

Open `http://localhost:3000` and select **Run live proof**.

The key stays in the local Next.js server. It is never bundled into browser JavaScript. Files matching `.env*` are ignored by Git, except `.env.example`.

## Build the public static site

The static build uses the recorded benchmark and makes no Jev requests:

```bash
npm run build:static
```

Upload the contents of `out/` to any static host.

## Project structure

```text
app/
  api/benchmark/       Live local Jev benchmark
  api/personalize/     Live local personalization decision
  demo/                Interactive personalization demo
  page.tsx             Public proof page
components/
  proof-lab.tsx        Rules-vs-hybrid benchmark UI
  personalization-demo.tsx
lib/
  benchmark.ts         Cases, features, routing, recorded result
  personalization.ts  Three fixed variants and fallback
benchmarks/
  online_shoppers/     Real ecommerce baselines and Jev stability run
  google_analytics/    Local session-history extraction and hybrid pilot
```

## Decision architecture

```text
referrer + UTM + page history
              |
       function extracts facts
          /              \
   clear case         conflicting case
      |                     |
 function choice         Jev Choice
          \              /
        schema validation
               |
    builder | campaign | returning
```

## Environment variables

```env
TYPESAFE_API_KEY=
TYPESAFE_BASE_URL=https://api.typesafe.ai
TYPESAFE_DEFAULT_MODEL=jev-latest
```

Never prefix the API key with `NEXT_PUBLIC_`.

## Deploy

See [DEPLOY.md](./DEPLOY.md) for the GitHub Pages deployment and custom-domain notes.

## Google Analytics Session-History Benchmark

The local [`benchmarks/google_analytics`](./benchmarks/google_analytics/README.md) workflow now:

```text
stream 25 GB train_v2.csv
-> deterministically sample visitors
-> reconstruct prior sessions
-> capture state after the first three hits
-> remove current-session outcomes
-> route clear policy cases with functions
-> send mixed context to Jev
```

The extractor scanned 1,708,337 sessions, selected 13,042 visitors, found 4,504 valid candidate points, and exported 300 local decision points. The local export contains 60 later purchases and 240 non-purchases. Raw visitor IDs, raw visit IDs, URL query strings, and current-session revenue are excluded from the decision state.

The full dataset and derived points are not committed. The source is approximately 35.9 GB, uses a nested schema, contains historical 2016–2018 traffic, and is subject to Kaggle competition rules.

## Roadmap

### Priority 0 — Make decisions safer

- Add a Jev abstention policy based on probability, option margin, and repeated-run variance.
- Fall back to a deterministic default when confidence is low or the decision flips.
- Version prompts, model names, sampling seeds, dataset hashes, and result metadata together.
- Add automated checks proving that scoring-only fields never enter a Jev request.

### Priority 1 — Strengthen offline evidence

- Add CatBoost as the stronger tabular baseline.
- Calibrate Logistic Regression using a separate validation split.
- Run the full set of 88 ambiguous Google Analytics points after estimating token cost.
- Ask independent reviewers to label a blinded subset of runtime decisions.
- Report reviewer agreement before treating those labels as ground truth.

### Priority 2 — Test the product claim

- Define one production decision point and a small set of deployable experiences.
- Instrument assignment, exposure, conversion, revenue, margin, and latency.
- Pre-register the primary metric, guardrails, stopping rule, and sample-size calculation.
- Run an online randomized experiment against a non-Jev control.
- Use newer first-party data before making production recommendations from 2016–2018 traffic.

### Priority 3 — Improve operations

- Cache repeated decisions when the normalized state and options are unchanged.
- Add latency and token budgets to routing policy.
- Track fallbacks, malformed responses, drift, and option-distribution changes.
- Publish only aggregate results that comply with source-data licensing and privacy rules.

## Project thesis

**Rules for the obvious.**

**Classical ML for stable structured prediction.**

**Jev for ambiguous runtime decisions.**

**Randomized experiments for proving business impact.**

## Dataset credits

- **Online Shoppers Purchasing Intention:** created by C. O. Sakar and Yomi Kastro; available from the [UCI Machine Learning Repository](https://archive.ics.uci.edu/dataset/468/online+shoppers+purchasing+intention+dataset) under CC BY 4.0; also available through [Akash Patel's Kaggle mirror](https://www.kaggle.com/datasets/imakash3011/online-shoppers-purchasing-intention-dataset).
- **Google Analytics Customer Revenue Prediction:** provided through the [Kaggle competition](https://www.kaggle.com/competitions/ga-customer-revenue-prediction) hosted by RStudio with Google Merchandise Store data. Credit to competition contributors Christopher Crosbie, Mark McDonald, Mikhail Chrestkha, Phil Culliton, Roger Oberg, and Sina Chavoshi. The data is subject to the Kaggle competition rules and is not redistributed by this repository.

## Independence

Independent Jev experiment by [RadRebelDeveloper](https://radrebeldeveloper.com). Not affiliated with TypeSafe AI.

## License

[MIT](./LICENSE)
