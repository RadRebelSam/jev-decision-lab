# Jev Decision Lab

**Rules for the obvious. Classical ML for stable structured prediction. Jev for ambiguous runtime decisions.**

Jev Decision Lab is an open-source evidence project for matching a decision problem to the right tool. It compares deterministic rules, classical machine learning, and Jev across three different experiments instead of assuming one approach should solve everything.

Public site: [radrebelsam.github.io/jev-decision-lab](https://radrebelsam.github.io/jev-decision-lab/)

> The public interactive site demonstrates Experiment 1. Experiments 2 and 3 are reproducible Python benchmarks in this repository.

## Evidence at a glance

| Experiment | Question | Recorded result |
| --- | --- | --- |
| 1. Designed Hybrid Benchmark | Can rules handle clear personalization cases while Jev resolves designed conflicts? | Function only: 5/8. Function + Jev: 8/8. |
| 2. Real Ecommerce Session Benchmark | Is Jev competitive with classical ML on fixed-label tabular prediction? | On the same 30-session sample, Logistic Regression F1: 0.381. Jev F1: 0.286. |
| 3. Google Analytics Session-History Benchmark | Can rules narrow API use and reserve Jev for runtime-defined choices? | Rules handled 212/300 points. Jev received 88/300. Balanced Jev pilot flip rate: 10%. |

These results support an architecture, not a conversion claim. Only an online randomized experiment can show whether a personalization policy improves revenue, conversion, average order value, or margin.

## Decision model

```text
known policy                     -> deterministic rules
stable features + fixed labels   -> classical ML
changing context or options      -> rules, then Jev for ambiguity
business-impact claim            -> randomized experiment
```

## Experiment 1 — Designed Hybrid Benchmark

### Question

Can a hybrid router keep explicit personalization policy in functions and use Jev only when visitor signals conflict?

### Setup

- Eight designed visitor journeys.
- Three allowed outputs: `builder | campaign | returning`.
- Expected labels withheld from Jev until scoring.
- Function-only baseline: page-count first, then campaign signals, then a default.
- Hybrid route: functions handle clear cases; Jev receives conflicts.

### Result

| Approach | Result |
| --- | ---: |
| Function only | 5/8 · 63% |
| Function + Jev | 8/8 · 100% |
| Cases handled without Jev | 4/8 |

This is a behavioral proof-of-concept on eight designed cases. It is not statistical evidence and does not show conversion lift.

### Architecture

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

Use the [public proof page](https://radrebelsam.github.io/jev-decision-lab/) to replay the recorded run. A local server can run it live with your own TypeSafe key.

## Experiment 2 — Real Ecommerce Session Benchmark

### Question

How does Jev compare with structured baselines on a real purchase/no-purchase prediction task?

### Dataset and methods

The [Online Shoppers Purchasing Intention dataset](https://archive.ics.uci.edu/dataset/468/online+shoppers+purchasing+intention+dataset) contains 12,330 real ecommerce sessions and a binary `Revenue` outcome.

The benchmark compares:

- a fixed, transparent rule;
- balanced Logistic Regression;
- `jev-latest` on a reproducible held-out sample.

`Revenue` is target-only. `PageValues` is excluded because it is late-session and strongly outcome-adjacent. The rows summarize completed sessions, so this is retrospective prediction—not an early-session production decision.

### Results

Full 3,083-row held-out test set:

| Approach | Accuracy | Precision | Recall | F1 | Brier | 10-bin ECE |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Simple rule | 0.498 | 0.205 | 0.782 | 0.325 | unavailable | unavailable |
| Logistic Regression | 0.636 | 0.263 | 0.753 | 0.390 | 0.212 | 0.274 |

Same 30-session Jev sample:

| Approach | Accuracy | Precision | Recall | F1 | Brier | 10-bin ECE |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Simple rule | 0.400 | 0.118 | 0.400 | 0.182 | unavailable | unavailable |
| Logistic Regression | 0.567 | 0.250 | 0.800 | 0.381 | 0.258 | 0.334 |
| Jev | 0.167 | 0.167 | 1.000 | 0.286 | 0.436 | 0.546 |

Jev selected `Purchase` for all 150 repeated decisions. Its 0% flip rate was stable but not useful because the output collapsed to one class. Logistic Regression was the better fit for this fixed-label tabular task.

See [`benchmarks/online_shoppers`](./benchmarks/online_shoppers/README.md) for feature policy, reproduction commands, latency, token usage, and limitations.

## Experiment 3 — Google Analytics Session-History Benchmark

### Question

Can richer visitor history support runtime-defined experience choices while explicit rules keep Jev usage narrow?

### Dataset and extraction

The local workflow uses the Kaggle Google Analytics Customer Revenue Prediction data from the Google Merchandise Store:

```text
stream train_v2.csv
-> deterministically sample visitors
-> reconstruct prior sessions
-> capture state after the first three hits
-> remove current-session outcomes
-> route clear policy cases with functions
-> send mixed context to Jev
```

The extractor:

- scanned 1,708,337 sessions;
- selected 13,042 visitors;
- found 4,504 valid candidate points;
- exported 300 local decision points;
- removed raw visitor IDs, raw visit IDs, URL query strings, and current-session revenue from decision state.

The local export contains 60 later purchases and 240 non-purchases. Positive outcomes are intentionally oversampled for evaluation, so its accuracy must not be presented as population accuracy.

### Runtime options

Jev chooses among three experiences:

- `continue_previous_journey`
- `guide_product_discovery`
- `reduce_purchase_friction`

The dataset does not say which option is correct. Accuracy is therefore unavailable.

### Hybrid result

Across all 300 points, explicit policy rules handled 212 (`70.7%`) and reserved 88 (`29.3%`) for Jev:

| Function decision | Count |
| --- | ---: |
| Guide product discovery | 124 |
| Continue previous journey | 60 |
| Reduce purchase friction | 28 |

A Jev pilot balanced 20 ambiguous points between contexts with and without prior-session history. Each point ran three times:

| Jev modal decision | Count |
| --- | ---: |
| Guide product discovery | 15 |
| Continue previous journey | 4 |
| Reduce purchase friction | 1 |

- Decision flip rate: 10%.
- Batched latency: 1.69 seconds total.
- Token usage: 20,781 input and 3,369 output.
- Dollar cost: unavailable from the API response.

Later purchase is recorded only as a descriptive outcome. It is not a correct-choice label or evidence that a selected experience caused the purchase.

See [`benchmarks/google_analytics`](./benchmarks/google_analytics/README.md) for extraction, routing rules, reproduction commands, and data-handling limits.

## What the experiments teach us

- The eight designed cases show that the hybrid control flow works as intended.
- The structured benchmark shows that Jev should not replace classical ML by default.
- The session-history benchmark shows that deterministic routing can reduce potential Jev calls by 70.7%.
- A stable Jev answer is not necessarily a correct or useful answer.
- Low-confidence or unstable Jev decisions need an abstention policy and safe fallback.
- No experiment in this repository proves business impact.

## Run locally

### Web app and Experiment 1

Requirements:

- Node.js 22
- A TypeSafe API key for live mode

```bash
git clone https://github.com/RadRebelSam/jev-decision-lab.git
cd jev-decision-lab
npm install
```

Create `.env.local`:

```env
TYPESAFE_API_KEY=your_own_key
```

Start the app:

```bash
npm run dev
```

Open `http://localhost:3000` and select **Run live proof**.

### Experiment 2

```bash
python -m pip install -r benchmarks/online_shoppers/requirements.txt
python benchmarks/online_shoppers/benchmark.py
python benchmarks/online_shoppers/run_jev.py
```

The Jev command requires `TYPESAFE_API_KEY` in the local environment.

### Experiment 3

After obtaining `train_v2.csv` through Kaggle:

```bash
python benchmarks/google_analytics/extract_decision_points.py
python benchmarks/google_analytics/run_jev_pilot.py
python benchmarks/google_analytics/run_hybrid_pilot.py
```

Raw and derived Kaggle data stay local and are ignored by Git.

## Build the public static site

The static build replays recorded Experiment 1 results and makes no Jev requests:

```bash
npm run build:static
```

Upload `out/` to a static host. See [DEPLOY.md](./DEPLOY.md) for GitHub Pages and custom-domain notes.

## Security and data handling

```env
TYPESAFE_API_KEY=
TYPESAFE_BASE_URL=https://api.typesafe.ai
TYPESAFE_DEFAULT_MODEL=jev-latest
```

- Never prefix the API key with `NEXT_PUBLIC_`.
- Live calls occur only from the local/server environment.
- The public static build makes no live Jev calls.
- Downloaded datasets and local Jev outputs are ignored by Git.
- Scoring-only outcomes are excluded from Jev decision state.
- Kaggle competition data is not redistributed by this repository.

## Project structure

```text
app/
  api/benchmark/       Experiment 1 live Jev benchmark
  api/personalize/     Live personalization decision
  demo/                Interactive personalization demo
  page.tsx             Public proof page
components/
  proof-lab.tsx        Experiment 1 benchmark UI
  personalization-demo.tsx
lib/
  benchmark.ts         Designed cases, routing, recorded result
  personalization.ts  Three fixed variants and fallback
benchmarks/
  online_shoppers/     Experiment 2 structured benchmark
  google_analytics/    Experiment 3 extraction and runtime pilots
```

## Roadmap

### Priority 0 — Define what “better personalization” means

- Choose one production decision point and a small set of experiences that can actually be deployed.
- Create a blinded offline review set for ambiguous cases.
- Ask multiple independent reviewers to select the most appropriate experience.
- Measure reviewer agreement; keep low-agreement cases marked as genuinely ambiguous.
- Define the online comparison before launch: rules-only control versus rules-plus-Jev treatment.
- Pre-register one primary business outcome, such as conversion, revenue per visitor, or margin per visitor.

Human labels answer, “Does this decision look appropriate?” The randomized experiment answers, “Did this policy improve a real business outcome?” Both are needed, and they are not interchangeable.

### Priority 1 — Make the hybrid safe enough to test

- Add a Jev abstention policy using probability, option margin, and repeated-run variance.
- Fall back to a deterministic default when confidence is low or the decision flips.
- Version prompts, model names, seeds, dataset hashes, and result metadata together.
- Add automated checks proving that scoring-only fields never enter a Jev request.

### Priority 2 — Complete the offline gate

- Run all 88 ambiguous Google Analytics points after estimating token cost.
- Compare Jev decisions with the independent reviewer labels.
- Report agreement, disagreement categories, flip rate, latency, and fallback rate.
- Add CatBoost as a stronger baseline for Experiment 2.
- Calibrate Logistic Regression using a separate validation split.

### Priority 3 — Run the randomized experiment

- Instrument assignment, exposure, conversion, revenue, margin, and latency.
- Calculate the required sample size before starting.
- Set guardrails for errors, latency, cost, and customer harm.
- Run rules-only versus rules-plus-Jev with random assignment.
- Report effect size and uncertainty, not only whether the result is statistically significant.
- Use newer first-party data before making production recommendations from 2016–2018 traffic.

### Priority 4 — Improve operations

- Cache decisions when normalized state and options are unchanged.
- Add latency and token budgets to routing policy.
- Track fallbacks, malformed responses, drift, and option-distribution changes.
- Publish only aggregate results that comply with licensing and privacy rules.

## Dataset credits

- **Online Shoppers Purchasing Intention:** created by C. O. Sakar and Yomi Kastro; available from the [UCI Machine Learning Repository](https://archive.ics.uci.edu/dataset/468/online+shoppers+purchasing+intention+dataset) under CC BY 4.0; also available through [Akash Patel's Kaggle mirror](https://www.kaggle.com/datasets/imakash3011/online-shoppers-purchasing-intention-dataset).
- **Google Analytics Customer Revenue Prediction:** provided through the [Kaggle competition](https://www.kaggle.com/competitions/ga-customer-revenue-prediction) hosted by RStudio with Google Merchandise Store data. Credit to competition contributors Christopher Crosbie, Mark McDonald, Mikhail Chrestkha, Phil Culliton, Roger Oberg, and Sina Chavoshi. The data is subject to the Kaggle competition rules and is not redistributed by this repository.

## Independence

Independent Jev experiment by [RadRebelDeveloper](https://radrebeldeveloper.com). Not affiliated with TypeSafe AI.

## License

[MIT](./LICENSE)
