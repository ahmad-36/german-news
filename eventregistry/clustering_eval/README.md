# Clustering Evaluation

How well do different methods group German articles into the same events that Event
Registry's `eventUri` defines?

```bash
python clustering_eval/prepare.py    # select events, split dev/test
python clustering_eval/embed.py      # compute embeddings (GPU, ~7 min)
python clustering_eval/evaluate.py   # cluster, tune on dev, score on test (~6 min)
```

## Setup

- **Data:** 2,117 events and 17,810 articles (31 Jul – 7 Aug 2026), from events with 2+
  sources. Split 50/50 by event into dev and test; thresholds are tuned on dev.
- **Windows:** articles are clustered within 2-day blocks, as in the GDELT clusterer.
- **Methods:** BGE-M3, multilingual-e5-large, LaBSE, gbert-large, word and character
  TF-IDF, and the production SequenceMatcher, each on title, title + lede, or full body.
  Clustering is agglomerative or HDBSCAN.
- **Metrics:** BCubed P/R/F1, with paired bootstrap confidence intervals.

## Results (test set)

| method | P | R | **F1** |
|---|---|---|---|
| *ceiling: perfect clustering within each 2-day window* | 1.00 | 0.79 | *0.88* |
| BGE-M3, full body | 0.85 | 0.74 | **0.79** |
| TF-IDF word, title + lede | 0.84 | 0.73 | 0.78 |
| mE5-large, title + lede | 0.81 | 0.74 | 0.77 |
| BGE-M3, title + lede | 0.84 | 0.71 | 0.77 |
| LaBSE, title + lede | 0.86 | 0.68 | 0.76 |
| gbert-large, title + lede | 0.78 | 0.71 | 0.74 |
| SequenceMatcher, title, tuned (t = 0.45) | 0.84 | 0.37 | 0.51 |
| SequenceMatcher, title, **production** (t = 0.65) | 0.98 | 0.29 | 0.45 |

## Findings

1. The production GDELT clusterer is precise but misses most same-event pairs.
2. The German model (gbert) is worse than the multilingual ones.
3. Adding the lede helps every model. The full body helps BGE-M3 a little, but it only
   ties TF-IDF on title + lede.
4. The 2-day window costs more than the choice of model, because 53% of events span
   longer.

**Caveats:** the gold labels are Event Registry's own clustering and are not verified by
humans. Duplicate-flagged wire copies are missing from them. The data covers 8 days in
German only.
