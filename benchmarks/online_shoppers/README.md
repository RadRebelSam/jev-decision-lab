# Online Shoppers Purchasing Intention benchmark

This benchmark tests a real, fixed-label tabular task:

```text
completed ecommerce session features -> purchase / no purchase
```

It uses the [UCI Online Shoppers Purchasing Intention dataset](https://archive.ics.uci.edu/dataset/468/online+shoppers+purchasing+intention+dataset). The dataset contains 12,330 sessions and a real binary `Revenue` outcome. UCI distributes it under CC BY 4.0.

This is not a personalization-component benchmark. The data does not say which hero or UI component should have been shown. It also cannot establish that Jev personalization causes conversion lift.

## Reproduce the structured baselines

From the repository root:

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
python -m pip install -r benchmarks/online_shoppers/requirements.txt
python benchmarks/online_shoppers/benchmark.py
```

The script downloads the canonical 1 MB UCI archive on first run, validates the schema and row count, and writes `results/baseline_results.json`. The CSV stays ignored by Git.

Defaults are reproducible:

- Seed: `42`
- Stratified train/test split: `75% / 25%`
- Logistic Regression threshold: `0.5`
- Logistic Regression class weights: balanced for the 15.5% positive class
- Simple rule: purchase when at least four of five fixed signals are true

The simple rule signals are at least 10 product pages, at least 600 product-page seconds, bounce rate at most 0.02, exit rate at most 0.05, and a returning visitor.

## Run Jev and the stability experiment

Keep the key in the local/server environment:

```bash
# PowerShell
$env:TYPESAFE_API_KEY="your_key"
python benchmarks/online_shoppers/run_jev.py

# macOS/Linux
TYPESAFE_API_KEY="your_key" python benchmarks/online_shoppers/run_jev.py
```

The default is a reproducible, stratified sample of 30 held-out sessions with 5 Jev runs per session. Change it with `--sample-size` and `--repeats`:

```bash
python benchmarks/online_shoppers/run_jev.py --sample-size 50 --repeats 10
```

The output includes accuracy, precision, recall, F1, Brier score and 10-bin ECE when probabilities are available. It also includes request latency, API cost when returned by the service, decision flip rate, and per-session probability mean, population standard deviation, minimum, and maximum. Unavailable measurements are explicitly marked `unavailable`.

Live Jev output is ignored by Git because it may vary by run and model. The public GitHub Pages build does not run this script and makes no live Jev calls.

### Recorded live sample

One `jev-latest` run used the default 30-session sample and five repeats on September 21, 2026. For a fair comparison, all three approaches were scored on the same 30 sessions:

| Approach | Accuracy | Precision | Recall | F1 | Brier | 10-bin ECE |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Simple rule | 0.400 | 0.118 | 0.400 | 0.182 | unavailable | unavailable |
| Logistic Regression | 0.567 | 0.250 | 0.800 | 0.381 | 0.258 | 0.334 |
| Jev | 0.167 | 0.167 | 1.000 | 0.286 | 0.436 | 0.546 |

Jev chose `Purchase` for all 150 decisions. It had a 0% decision flip rate, but that stability is not useful because the decision collapsed to one class. The five batched requests took 2.37 seconds total and used 39,585 input tokens plus 5,140 output tokens. The API response did not provide a dollar cost, so cost is marked `unavailable`.

This result is kept as evidence rather than tuned away. It shows that a stable answer is not necessarily a discriminative or calibrated answer, and that the classical model is a better fit for this fixed-label tabular sample.

## Feature and leakage policy

`Revenue` is target-only. It never enters either model or the Jev state.

`PageValues` is excluded. UCI describes it as the average value of a page visited before an ecommerce transaction. It is late-session and strongly outcome-adjacent, so including it would make this comparison less useful for a prospective decision.

The selected features are:

- Page counts and durations: `Administrative`, `Administrative_Duration`, `Informational`, `Informational_Duration`, `ProductRelated`, `ProductRelated_Duration`
- Aggregate rates: `BounceRates`, `ExitRates`
- Context: `SpecialDay`, `Month`, `OperatingSystems`, `Browser`, `Region`, `TrafficType`, `VisitorType`, `Weekend`

Categorical codes remain codes. The Jev prompt does not invent a meaning for `TrafficType`, browser, operating-system, or region integers.

## Important timing limitation

The UCI rows summarize completed sessions. Counts and durations are updated during a visit, but this file does not contain timestamped snapshots showing exactly what was known at each decision point. Bounce and exit rates are aggregate analytics fields and may also reflect information unavailable at an early personalization moment.

Therefore, this benchmark measures retrospective purchase prediction from session summaries. A real runtime personalization policy would need event-time snapshots, a declared decision timestamp, and only the features available by that timestamp. It would then need an online randomized experiment to measure business impact.

## Methods

- **Simple rule:** fixed, readable heuristic; no training.
- **Logistic Regression:** scaled numeric columns, one-hot encoded categorical columns, and balanced class weights.
- **Jev:** the same selected columns rendered as compact natural-language state. The target and `PageValues` are omitted.
- **CatBoost:** future work. It is a useful stronger tabular baseline, but is not added here to avoid another heavy dependency.

If Logistic Regression wins this structured task, that is an informative result. Stable, fixed-label tabular prediction is exactly where classical ML should be strong. Jev's distinct role is ambiguous, runtime-defined decisions whose options or context may change without retraining a classifier.
