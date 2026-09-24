# news-explorer

The cross-source layer: one unified format for every provider, and one Streamlit UI that
reads it.

Lives in `news/` alongside its sister repos, each an independent git repo. Split out of
the former monolithic `news` repo (Sept 2026, now retired to `archive/news`). The
collectors now live in
[news-gdelt](../news-gdelt), [news-ground-news](../news-ground-news),
[news-eventregistry](../news-eventregistry) and
[muws-allsides-dataset](../muws-allsides-dataset).
This repo consumes what they produce.

## Where data lives

**In this repo, under [`data/`](data) — gitignored, so it is never pushed.** This repo owns
`data/unified/` (~1.3 GB), the output of `unify.py`.

Its *inputs* live in the collector repos, and [paths.py](paths.py) finds them
automatically — no environment variable required:

```
data/unified/                            ← written here
../news-gdelt/data/gdelt/                ← read from the sibling
../news-ground-news/data/ground_news/    ← read from the sibling
../news-eventregistry/data/eventregistry/← read from the sibling
../muws-allsides-dataset/output/          ← read from the sibling
```

## Raw vs unified — which files are which

Each collector repo's `data/` holds that source's **raw, native-shape** output. This repo's
`data/unified/` holds the **converted** copies. They are different files, and both are kept.

| file | shape |
|---|---|
| `../news-gdelt/data/gdelt/gdelt_stories_de_min3.jsonl` | raw — `n_outlets`, `probes`, `seendate`, `socialimage`, `themes` |
| `../news-ground-news/data/ground_news/ground_news.jsonl` | raw — `sources`, `summary_left`, `source_bias`, `dek` |
| `../news-eventregistry/data/eventregistry/articles_germany.jsonl` | raw — one flat article per line |
| **`data/unified/unified_*.jsonl`** | **unified — `articles[]` each with `stance`, `bias_rating`, `body_text`, `meta`** |

**Ground News provenance carries into unified.** In `unified_ground_news.jsonl`,
`stance_summaries` and `meta.bias_comparison` are **GPT output**, and `meta.generated_headline`
is LLM-written. Article `stance` is a **human, outlet-level, US-framed** label. For
translated articles, `headline` is Ground News' English machine translation, and the
original is in `meta.original_title`. Details:
[news-ground-news → What is human, what is GPT](../news-ground-news/README.md#what-is-human-what-is-gpt).

The UI only ever reads the unified files. Raw is kept as the archive, because unification is
lossy: source-specific fields survive only inside `meta`, so a schema change is a cheap
re-run from raw rather than a re-crawl.

## Why unification is a separate step, not done at crawl time

It would be neater if each crawler simply wrote the unified format directly. It cannot,
for three concrete reasons — the unified record depends on data that does not exist yet
when the crawler runs:

1. **GDELT bodies and images arrive later.** `convert_gdelt` reads each story's
   `enrichment` field, which `gdelt_enrich_bulk.py` produces by crawling the outlets
   *after* collection. At `gdelt_dump_pull.py` time there are no bodies to write.
2. **GDELT stories do not exist at collection time.** A unified record is story-level, but
   the collector emits *articles*; `gdelt_cluster_bulk.py` groups them into stories in a
   later pass.
3. **AllSides bodies come from a different repo.** They are joined by URL out of the Qbias
   `multi_source_scrape` output, which is an independent crawl on its own schedule.

And the cost it would save is small. A **full** unification of all four sources — the
entire 7.3 GB corpus — takes **178 seconds** (~4 GB peak RSS). It is not the bottleneck;
collection is. Running it is also how stale output gets repaired: the run on 2026-09-23
attached **154,084 GDELT bodies** that the previous unified files predated and therefore
showed as zero.

If unification later does become slow, the fix is to make it *incremental* (convert only
stories whose raw mtime is newer than the unified output), not to fold it into the
crawlers — that would couple every collector to the unified schema and make a schema change
require a re-crawl instead of a 3-minute local pass.

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

> **Done 2026-09-23.** The unified files were rebuilt and now carry the GDELT enrichment
> (**154,084 bodies**, up from 0). The previous files are kept at
> `data/unified/archive/pre-enrichment-20260923/`. Re-run `unify.py` whenever a collector
> has produced new data — it is a full rebuild and takes ~3 minutes.

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
