# news-explorer

The cross-source layer: one unified format for every provider, and one Streamlit UI that
reads it.

Split out of the former monolithic `news` repo (Sept 2026). The collectors now live in
[news-gdelt](../news-gdelt), [news-ground-news](../news-ground-news),
[news-eventregistry](../news-eventregistry) and
[muws-allsides-dataset](https://github.com/muws-workshop/muws-allsides-dataset).
This repo consumes what they produce.

## Where data lives

```bash
export NEWS_DATA_DIR=/nfs/home/abdullaha/news-data
```

Every collector writes under that root; this repo reads from it. All paths go through
[paths.py](paths.py).

## Unify

```bash
python unify/unify.py                      # all sources -> data/unified/
python unify/unify.py --only gdelt         # one source; unified_all is rebuilt from disk
python unify/analytics.py --markdown --json
```

One JSON object per line = one **story** with an `articles` list. Every article carries a
coarse `stance` (left/center/right/unknown) and a fine `bias_rating` (7-tier); sources
without ratings get `unknown`. Source-specific extras live verbatim under `meta` at both
story and article level. Full schema: the [unify/unify.py](unify/unify.py) docstring.

> **Re-run `unify.py`.** The GDELT enrichment file has grown to **213,532 records**
> (154,084 bodies, 145,078 images, 88,992 captions) since the current unified files were
> built, and they attach almost none of it. This costs nothing and is the single
> highest-value thing to run here.

## Explore

```bash
streamlit run ui/dataset_explorer.py
streamlit run ui/dataset_explorer.py -- --data <root>/unified/unified_gdelt.jsonl
```

One UI for every dataset — each page reads the unified format, so the sidebar picker
switches between sources without changing pages.

- **Story Feed** — filterable feed (topics, places, blindspot, language, dates) with a
  story detail view: lead image, cluster facts, per-source cards, full article text where
  the dataset carries it.
- **Dataset Statistics** — coverage, bias mix, publisher leaderboard, topic clusters, and
  a per-strategy breakdown on `unified_all.jsonl`.

The picker defaults to `unified_ground_news.jsonl`; `unified_all.jsonl` is ~1.8 GB and is
sorted last so it is chosen deliberately.

> The **Topic Discovery** page moved to [news-ground-news](../news-ground-news), because
> it drives that scraper rather than reading the unified format.

> **Known duplication:** `ui/common.py` and `germanlib.py` are vendored copies also
> present in news-ground-news. If you change one, change the other. They were duplicated
> rather than packaged so each repo runs standalone.

## Known caveats in the unified data

- **AllSides articles inflate ~8×** — 68,352 article slots collapse to 8,072 unique URLs,
  because the same article is reused across story pages via the "More from the
  Left/Center/Right" sidebars. **Deduplicate by URL before computing any per-article
  statistic.** This has already produced one materially wrong result — see
  [the write-up](../news-source-survey/docs/stance_labels.md#4-experiment-3--a-correction-the-eval-set-is-42-duplicated).
- `is_featured: false` AllSides articles come from those sidebars and may be off-story.
- Event Registry stories are **100% singletons**; its `eventUri` is dropped by `unify.py`.
- Ground News `stance` derives from `source_bias`, ~37% `unknown`, and is **outlet-level**.
- Event Registry's `story_summary` is *derived* (`lede(body)`), not a real summary.

## Docs

- [docs/dataset_comparison_report.md](docs/dataset_comparison_report.md) — all four
  strategies measured against the data on disk
- [docs/german_news_strategy_comparison.md](docs/german_news_strategy_comparison.md) —
  the earlier three-way comparison; GDELT figures there are superseded
- [news-source-survey](../news-source-survey) — the written provider analysis

## Environment

`streamlit`, `pandas`, `plotly` — conda env `base` here has them.
