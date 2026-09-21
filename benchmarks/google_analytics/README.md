# Google Analytics session-history extractor

This local-only experiment streams the Kaggle Google Analytics Customer Revenue Prediction `train_v2.csv`. It does not load the 25 GB file into memory.

Dataset credit: the [Google Analytics Customer Revenue Prediction Kaggle competition](https://www.kaggle.com/competitions/ga-customer-revenue-prediction), hosted by RStudio with Google Merchandise Store data. Competition contributors include Christopher Crosbie, Mark McDonald, Mikhail Chrestkha, Phil Culliton, Roger Oberg, and Sina Chavoshi. The data is subject to the competition rules and is not redistributed here.

The extractor:

- selects visitors with a deterministic SHA-256 bucket;
- reconstructs each selected visitor's ordered session history;
- creates a decision point after the first three hits of a session;
- excludes current-session totals from the decision state;
- excludes sessions where a transaction already occurred by the decision point;
- keeps transaction and revenue data only under `outcome_for_scoring_only`;
- strips URL query strings;
- replaces raw visitor and visit identifiers with local aliases;
- creates at most 300 decision points by default.

Run from the repository root:

```bash
python benchmarks/google_analytics/extract_decision_points.py
```

Output is written to `benchmarks/google_analytics/local_results/decision_points.json`. Both the raw Kaggle data and derived output are ignored by Git because the competition rules may restrict redistribution.

The default export intentionally targets a 20% positive share so the small evaluation set contains useful purchase examples. This is not the dataset's natural prevalence. Accuracy on the exported sample must not be presented as population accuracy.

This dataset still does not provide a correct hero or component label. The output supports later experiments on session-aware runtime decisions; it does not prove which personalization should have been shown or whether personalization improves business outcomes.

## Jev runtime-decision pilot

The pilot asks Jev which experience to prioritize after the first three hits:

- continue the previous journey;
- guide product discovery;
- reduce purchase friction.

Run the default 20-point, three-repeat pilot locally:

```bash
python benchmarks/google_analytics/run_jev_pilot.py
```

It reports decision stability, option distribution, latency, token usage, and API cost when returned. Accuracy is deliberately unavailable because the dataset has no ground-truth component label. Later purchase is shown only as a descriptive cross-tab; it is not treated as proof that a choice was correct or caused the outcome.

### Recorded pilot

A `jev-latest` pilot on September 21, 2026 used 20 deterministic decision points and three repeats per point:

| Measurement | Result |
| --- | ---: |
| Guide product discovery | 15/20 modal decisions |
| Continue previous journey | 2/20 modal decisions |
| Reduce purchase friction | 3/20 modal decisions |
| Points with a decision flip | 2/20 |
| Decision flip rate | 10% |
| Total batched latency | 1.47 seconds |
| Input tokens | 19,713 |
| Output tokens | 3,369 |
| API dollar cost | unavailable |

The two changing decisions had probabilities near the option boundary. All three sessions assigned to `reduce_purchase_friction` later purchased, but this is a tiny descriptive cross-tab—not accuracy, uplift, or causal evidence. Only a randomized experiment can test whether showing that experience improves an outcome.
