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
