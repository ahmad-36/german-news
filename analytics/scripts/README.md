# Scripts

| script | reproduces | needs |
|---|---|---|
| `translation_audit.py` | [experiments §4](../docs/experiments.md#4-ground-news-translation-deletes-entities) | Ground News data only (standard library) |
| `outlet_outlier_check.py` | [experiments §3](../docs/experiments.md#3-how-often-does-an-llm-disagree-with-the-outlet-label) | a GPU; runs inside `muws-allsides-dataset/stance_detection_experiment/` |
| `dedup_impact.py` | [experiments §1](../docs/experiments.md#1-are-the-stance-labels-per-article-or-per-outlet) | scikit-learn; runs inside the same folder |

```bash
python scripts/translation_audit.py --data <ground_news.jsonl> [--show]
python outlet_outlier_check.py --cap 250
python dedup_impact.py
```

The last two import `config.py` and `splits.py` from the stance experiment, so copy them
into that folder to run them.
