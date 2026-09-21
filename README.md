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

## Roadmap

### Google Analytics Customer Revenue Prediction

A future, larger experiment can use the Kaggle Google Analytics Customer Revenue Prediction data from the Google Merchandise Store. Fields such as `trafficSource`, `channelGrouping`, `fullVisitorId`, `visitNumber`, `visitStartTime`, `hits`, and `totals` make it possible to reconstruct a richer sequence:

```text
traffic source
-> previous visits
-> page/hit sequence
-> current state
-> runtime decision
```

That is closer to this project's session-aware personalization thesis than another fixed revenue classifier. It also has important constraints:

- The full Kaggle competition data is roughly 35+ GB.
- The schema is nested and much more expensive to preprocess.
- The traffic is historical, from 2016–2018.
- There is no ground-truth label saying which hero or component should have been shown.

The full dataset will not be committed. The intended workflow is:

```text
process in a Kaggle Notebook
-> select a reproducible visitor subset
-> reconstruct session histories
-> extract roughly 100-500 decision points
-> export a small curated benchmark file
-> add it to Jev Decision Lab
```

The goal is to evaluate richer session-aware runtime decisions, not simply another revenue prediction model.

A local streaming prototype now lives in [`benchmarks/google_analytics`](./benchmarks/google_analytics/README.md). It scans `train_v2.csv` without loading the 25 GB file into memory, reconstructs selected visitor histories, and creates leakage-aware decision points after the first three hits. Raw and derived Kaggle data remain ignored because competition rules may restrict redistribution.

A first 20-point `jev-latest` runtime-decision pilot produced all three available experience choices and a 10% decision flip rate across three repeats. Accuracy is intentionally not reported because this dataset has no correct personalization-component label. See the benchmark README for the recorded choice distribution, latency, token usage, and limitations.

The follow-up hybrid router handled 212 of 300 decision points (`70.7%`) with explicit rules and reserved 88 (`29.3%`) for Jev. A context-balanced sample of 20 ambiguous points again produced all three experience choices with a 10% flip rate. This is the intended architecture: rules cover declared policy; Jev is limited to mixed runtime context.

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
