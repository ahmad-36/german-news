# Story clustering vs. Event Registry's eventUri

How well do cheap and embedding-based clusterers reproduce Event Registry's own
event clustering on German news? ER's `eventUri` is the gold label.

```bash
conda activate rag
python clustering_eval/prepare.py                                             # CPU, seconds
srun -p p_48G --gres=gpu:1 --cpus-per-task=8 --mem=64G python clustering_eval/embed.py      # ~7 min
srun -p p_48G --cpus-per-task=32 --mem=128G python clustering_eval/evaluate.py              # ~6 min
```

Outputs go to `data/clustering_eval/` (gitignored): `articles.jsonl`, `emb/*.npy`,
`truncation.json`, `results.json`, `results.md`.

## Setup

- **Data.** Raw ER pull (`articles_germany.jsonl`, 31 Jul – 7 Aug 2026). Kept:
  German-anchored events (`deu-*`) with 2+ distinct sources, giving **2,117 events and 17,810
  articles**. Split 50/50 by event (seed 13): dev 1,058 events / 8,689 articles, test 1,059 /
  9,121. Thresholds are tuned on dev and reported on test.
- **Time window.** Reproduces `gdelt/gdelt_cluster_bulk.py` with its default
  `--span-days 1`: the sorted crawl days are cut into consecutive **2-day blocks**
  (4 windows), and each window is clustered independently. The blocks do not overlap,
  despite that script's comment. Day = ER crawl time (`dateTime`). `dateTimePub` was not
  used because it has publisher-side day/month swaps.
- **Representations.** BGE-M3, multilingual-e5-large (`query:` prefix), LaBSE, and
  gbert-large-paraphrase-cosine, each on `title` and `title + lede` (lede = `textlib.lede`,
  about 600 chars of opening prose). BGE-M3 also runs on `title + full body`. Baselines: the
  production greedy SequenceMatcher (titles, imported from `gdelt_cluster_bulk`), plus
  word TF-IDF and char (3–5) TF-IDF cosine.
- **Clustering.** Agglomerative (cosine, average/complete/single linkage,
  `distance_threshold` 0.01–1.00) and HDBSCAN (precomputed cosine,
  `min_cluster_size=2`, `min_samples` 1–3, `cluster_selection_epsilon` 0–0.8,
  eom/leaf; noise points become singletons). The scipy linkage cuts match sklearn
  `AgglomerativeClustering` exactly (ARI 1.0, checked for all three linkages).
- **Metrics.** BCubed P/R/F1 and ARI. Gold = eventUri across the whole split, so an event
  cut by a window boundary costs recall. The **window-oracle** row (perfect clustering
  inside each window) is the ceiling. Significance comes from a paired event-level
  bootstrap (2,000 resamples) on test BCubed F1.

## Results (test, dev-tuned)

Method = the one with the best dev F1 for that representation. The full table, with every linkage and HDBSCAN, is in `results.md`.

| representation | best method | P | R | **F1** | ARI |
|---|---|---|---|---|---|
| *window oracle (ceiling)* | – | 1.000 | 0.793 | *0.884* | 0.772 |
| BGE-M3, full body | agglo-average t=0.35 | 0.847 | 0.737 | **0.788** | 0.601 |
| TF-IDF word, title+lede | agglo-average t=0.86 | 0.841 | 0.731 | 0.782 | 0.635 |
| TF-IDF char, title+lede | agglo-average t=0.79 | 0.838 | 0.718 | 0.774 | 0.617 |
| mE5-large, title+lede | agglo-average t=0.11 | 0.810 | 0.738 | 0.772 | 0.593 |
| BGE-M3, title+lede | agglo-average t=0.37 | 0.842 | 0.712 | 0.772 | 0.593 |
| LaBSE, title+lede | HDBSCAN ms=1 eps=0.2 | 0.863 | 0.678 | 0.760 | 0.566 |
| gbert-large, title+lede | HDBSCAN ms=1 eps=0.2 | 0.778 | 0.712 | 0.743 | 0.516 |
| BGE-M3, title | agglo-average t=0.49 | 0.814 | 0.672 | 0.736 | 0.541 |
| mE5-large, title | agglo-average t=0.16 | 0.781 | 0.693 | 0.735 | 0.562 |
| gbert-large, title | HDBSCAN ms=1 eps=0.3 | 0.790 | 0.649 | 0.713 | 0.494 |
| TF-IDF char, title | agglo-average t=0.84 | 0.807 | 0.605 | 0.691 | 0.456 |
| LaBSE, title | HDBSCAN ms=1 eps=0.3 | 0.797 | 0.603 | 0.687 | 0.454 |
| TF-IDF word, title | agglo-average t=0.87 | 0.807 | 0.580 | 0.675 | 0.430 |
| SequenceMatcher, title (tuned t=0.45) | greedy | 0.840 | 0.370 | 0.513 | 0.224 |
| SequenceMatcher, title (**production t=0.65**) | greedy | 0.981 | 0.293 | 0.451 | 0.136 |

Tuning on dev instead of test costs at most 0.004 F1 for any representation.

## Findings

1. **The production GDELT clusterer is precise but misses most same-event pairs.** At t=0.65:
   P 0.98, R 0.29, F1 0.45. Tuning its threshold only reaches 0.51. Every embedding model
   beats it by 0.17–0.28 F1 (BGE-M3 title vs. tuned SequenceMatcher: +0.22, CI [0.20, 0.24]).
2. **The German model loses to the multilingual ones.** gbert-large is worse than BGE-M3 and
   mE5 in both conditions (−0.02 to −0.03 F1, all CIs exclude 0). It beats LaBSE on titles
   (+0.026) but loses to it on title+lede (−0.017).
3. **Adding the lede helps every model**: +0.036 BGE-M3, +0.038 mE5, +0.031 gbert,
   +0.073 LaBSE, and +0.107 word TF-IDF. All CIs exclude 0.
4. **Full body helps a little.** BGE-M3 body vs. title+lede: +0.017, CI [0.012, 0.021].
   The gain is real but small. It is also **not distinguishable from word TF-IDF on
   title+lede** (+0.006, CI [−0.005, 0.016]). On title+lede, TF-IDF actually beats BGE-M3
   (+0.010, CI [0.002, 0.021]).
5. **The window costs more than the model.** Perfect clustering inside the 2-day blocks
   still loses 21% recall (oracle F1 0.884), because 53% of events span 2–6 days. The
   best system reaches 89% of that ceiling.
6. **Average-linkage agglomerative is the dev pick for BGE-M3, mE5 and both TF-IDFs.**
   HDBSCAN is the dev pick for gbert and LaBSE in both conditions. Complete and single
   linkage are consistently worse.

## Truncation

| model / condition | max tokens | truncated | tokens p50 / p95 / max | tokens dropped |
|---|---|---|---|---|
| BGE-M3 body | 8192 | **14 (0.08%)** | 487 / 1410 / 15531 | 0.28% |
| LaBSE title+lede | 256 | **315 (1.77%)** | 182 / 243 / 423 | 0.16% |
| all other model/condition pairs | 512 or 8192 | 0 | ≤ 457 max | 0% |

Truncation is not a factor in any comparison above.

## Caveats

- **No distractors.** Only articles inside 2+-source ER events are clustered. The 108k
  unclustered ER articles are excluded, so precision is optimistic compared with a real
  crawl.
- **Wire duplicates are missing from the gold labels.** ER leaves `isDuplicate` articles out
  of events, so the near-identical syndicated copies that SequenceMatcher handles best are
  not in the test set. This set is biased against title-string matching compared with
  GDELT's actual input.
- **The gold labels are ER's own clustering.** Its method is not documented in detail. If
  it uses article bodies, which seems likely, it may favour body-level representations.
- **Short and German-only.** 8 days, one pull, German-anchored events only.
