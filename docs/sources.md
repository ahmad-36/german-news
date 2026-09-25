# Per-Source Reference

For each provider: **how scraping works**, **what you get**, and **what the limits are**.
All figures measured against the data on disk (Jan–Aug 2026, ~7.3 GB).
Every limit noted here also appears, with status, in the [problems register](problems.md).

---

## AllSides

> US political news, presented as left/center/right triplets per story.
> Repo: [`muws-allsides-dataset`](../../muws-allsides-dataset) — scraper and data, `output/`

### How scraping works

**Axis: by date.** AllSides publishes "headline roundup" story pages; the scraper walks
them over an explicit date range. This is the cleanest historical interface of the four
providers — you ask for a window and you get it.

```bash
python allsides_scraper.py --start 2025-01-01 --end 2026-12-31 --out-dir output
```

Two stages:

1. **Roundup crawl** → `allsides_<start>_<end>.jsonl`, one record per story, plus an
   `images/` folder. Writes incrementally, so a crash loses only in-flight stories;
   re-running resumes and skips completed stories (`--fresh` forces a full re-scrape).
2. **Full-text scrape** → one bespoke scraper per publisher domain, because each outlet
   needs custom HTML parsing:
   ```bash
   python news_scrapers/<domain>.py --mode scrape   # new articles
   python news_scrapers/<domain>.py --mode patch    # retry failures
   python news_scrapers/<domain>.py --mode refresh  # update images/captions
   python news_scrapers/<domain>.py --mode audit    # coverage report
   ```

There is **no search endpoint** — you cannot ask AllSides for "articles about Ukraine".
Topic is an attribute of a story you have already fetched, not a crawl axis.

### What you get

| | |
|---|---|
| Stories / articles | 1,919 / 68,352 slots — **8,072 unique URLs** |
| Median outlets per story | 22 (max 48) |
| Headline, URL, description | 100% / 100% / 99.4% |
| **Body text** | **17.3%** (11,838), median 3,993 chars |
| **Images** | **68.9%** have an image URL (47,122). Downloaded: 2,448 stance thumbnails + 8,268 article images, 5,306 with captions. See [images.md](images.md) |
| Stance label | 99.9% (68,290), 7-point scale |
| Topics | 100%, human-readable (`Donald Trump`, `Immigration`, `Economy And Jobs`) |
| Story summary | 100%, editorial |
| Language tag | absent |

### Limits

- 🔴 **US-only — zero German articles.** Disqualifying for the German dataset.
- 🔴 **~8× article inflation** — 68,352 slots, 8,072 unique URLs. Deduplicate before
  computing anything per-article; this has already produced one wrong headline result.
- 🔴 **Labels are per outlet**, so the corpus is balanced by construction (22,967 / 22,669
  / 22,716) — a layout artefact, not a property of the news.
- ⚠️ Bodies on only 17.3%, and each outlet needs its own scraper.
- ⚠️ `is_featured: false` articles come from sidebars and may be off-story.
- ⚠️ Scraped content — the usual redistribution caveats.

---

## Ground News

> Worldwide stories with per-outlet bias ratings, blindspot flags and AI stance summaries.
> Scraper: `scrapers/ground_news/scraper.py` in [`ahmad-36/news`](https://github.com/ahmad-36/news)

### How scraping works

**Axis: by trending, not by date.** The scraper crawls the homepage, `/top`, `/blindspot`
and ~20 `/interest/<topic>` pages, keeps stories with 3+ sources, and merges into
`data/ground_news/ground_news.jsonl`. There is **no date endpoint** — you get what is
trending when you run it.

```bash
uv run python scrapers/ground_news/scraper.py                      # trending snapshot
uv run python scrapers/ground_news/scraper.py --query "ukraine"    # subject search
uv run python scrapers/ground_news/scraper.py --from-date 2026-03-01 --to-date 2026-03-15
                                                                   # historical via Wayback
uv run python scrapers/ground_news/scraper.py --refresh-existing   # re-fetch known stories
```

Historical mode replays **Wayback Machine snapshots** of the listing pages — coverage is
best-effort and gappy, and this is the only route to the past. Requires `curl_cffi` Chrome
impersonation to get past bot detection; no browser needed.

### What you get

| | |
|---|---|
| Stories / articles | 894 / 46,030 |
| Median outlets per story | 16 (max 1,166) |
| German articles | 5,563 (12.1%), in 537 of 894 stories |
| Headline, dek | 100% / 98.1% (real editorial dek) |
| **Body text** | **0%** — headline + dek only |
| **Images** | **none** — no image field exists in the record |
| Stance label | 62.6% (28,833); **37.4% is the literal string `unknown`** |
| Per-stance summaries | 49.3% (441/894; all three sides 209) — **GPT-generated** |
| `bias_comparison` paragraph | 499/894 — **GPT-generated** |
| Blindspot flag | 89 stories |
| Topics | 99.8%, human-readable |
| Paywall flag | 5,270 articles flagged |
| Unique domains | **5,477** — a worldwide long tail |

### Limits

- 🔴 **Tiny** — 894 stories in ~14 months (~2/day). A label source, not a corpus.
- 🔴 **No body text and no images at all** — headline + dek only.
- 🔴 **Only 12.1% German.**
- 🔴 **Labels are per outlet, US-framed and contested** — averaged from MBFC, Ad Fontes and
  AllSides (all US organisations, American left–right axis), which disagree on **32.1%**.
  37.4% are the literal string `unknown`, concentrated on the German tail.
- ⚠️ **Summaries are GPT-generated** (`summary_*` and `bias_comparison` come from Ground
  News' `chatGptSummaries` object; `generated_headline` is also LLM-written). The labels
  are not. `summary_right` is often empty when left and center are populated.
- ⚠️ **Translation runs before clustering** and loses entities.
- ⚠️ Language tags are unreliable (Luxembourgish tagged `de`); factuality field is 0% populated.

---

## GDELT

> A complete open census of world news metadata. The backbone of the German dataset.
> Scrapers: `scrapers/gdelt/` in [`ahmad-36/news`](https://github.com/ahmad-36/news)

### How scraping works

Three routes, and **only one of them is usable for volume**:

| Route | Script | Verdict |
|---|---|---|
| **Raw 15-min dumps** | `gdelt_dump_pull.py` | ✅ **the one to use** — complete, no result cap |
| BigQuery | `gdelt_bq_pull.py` | ⚠️ 1 TB/month free sandbox; `Extras` is the expensive column |
| DOC API | `gdelt_collect.py` | 🔴 **capped at 250 results, no pagination** — do not use for volume |

**Axis: by date** — every 15-minute GKG slot since **2015-02-19** is a downloadable file.
The Jan–Aug 2026 pull took 20,350 of 20,350 slots with zero failures. Filtering by language
and country is **ours to do**, on the dump.

```bash
python scrapers/gdelt/gdelt_dump_pull.py       # bulk pull of the raw dumps
python scrapers/gdelt/gdelt_cluster_bulk.py    # title-similarity clustering
python scrapers/gdelt/gdelt_enrich_bulk.py     # fetch bodies + images from the outlets
```

Clustering is ours: greedy single-pass, bucketed by day, blocked on a rare-token inverted
index, similarity = `SequenceMatcher` over normalised titles, **threshold 0.65**,
`--min-outlets 3`. Media-group domains (the Ippen network — merkur.de, tz.de, hna.de,
fr.de, …) collapse to one outlet first, so syndication cannot fake breadth.

The DOC API's filter set is genuinely rich (`theme`, `tone`, `near`, `repeat`, image
operators) — it is only the 250-result cap that makes it useless for collection. Full
reference: [api_filters.md](api_filters.md).

### What you get

| | |
|---|---|
| Articles / stories (3+ outlets) | 1,408,753 / 173,388 |
| German | **100%** — 474 German domains |
| Median outlets per story | 5 (mean 6.43, max 77) |
| **Stories reaching 30+ independent outlets** | **3,811** ← the headline asset |
| Headline, URL | 100% |
| **Body text** | **0% native.** Our own crawl has fetched **154,084** German bodies |
| **Images** | **0% native.** Our crawl has **145,078** `og:image` URLs + **88,992 captions** |
| Themes | 100%, GKG V2Themes (machine-assigned) |
| Stance label | **none** |
| Time span | 2026-01 → 2026-08 in our pull; available from 2015-02-19 |

> **Note:** the enrichment file has grown to **213,532 records** (154,084 bodies,
> 145,078 images, 88,992 captions). The unified files were built before most of this
> existed and currently attach almost none of it — re-running `unify.py` costs nothing and
> fixes it.

### Limits

- 🔴 **No body text and no bias signal.** Bodies need our own second crawl: 154,084 fetched
  of 1.4M.
- 🟠 **Clustering is ours and shallow** — `SequenceMatcher` at 0.65 within a day bucket.
  Different headlines never merge; a story crossing midnight splits in two.
- ⚠️ **Titles live in the `Extras` XML**, not a GKG column — dropping `Extras` to save
  BigQuery quota silently destroys clustering.
- ⚠️ **No publisher country on the dump route** — all stories carry `countries: ["?"]`.
- ⚠️ Themes are high-recall/low-precision, and the top ones are artefacts of our own
  language filter.
- ⚠️ Indexes section fronts and homepages; `--min-outlets 3` is why 173,388 of 2,015,373
  stories survive.
- 🟢 **Openly licensed** — the only source here we may republish.

---

## Event Registry (newsapi.ai)

> Full-text German articles via a clean REST API. Legally unpublishable.
> Scraper: `scrapers/eventregistry/eventregistry_german_sources.py`

### How scraping works

**Axis: by date + language**, through an authenticated, paginated REST API. Easiest
integration of the four by a wide margin.

```bash
python scrapers/eventregistry/eventregistry_german_sources.py \
    --skip-discovery --days 7 --pull 5000
```

Needs `EVENTREGISTRY_API_KEY` or `~/.eventregistry_key`. Costs **1 token per 100-article
page**. The script sets `allowUseOfArchive=False` as a guard against accidentally spending
archive tokens.

The filter set is the richest of any provider here — `lang`, `conceptUri`, `categoryUri`,
`sourceUri`, `sourceLocationUri`, `authorUri`, `startSourceRankPercentile`, `dataType`
(news/pr/blog), plus `ignore*` negations of every one. Full reference:
[api_filters.md](api_filters.md).

### What you get

| | |
|---|---|
| Articles | 129,628 (one 7-day window, 320 sources) |
| German | **100%** |
| **Body text** | **100%**, median 2,111 chars, clean UTF-8 |
| **Images** | **98.6%** image URL |
| Image captions | none |
| Authors | ✅ |
| Description | 100%, but **derived** from the body — not a real dek |
| Stance label | **none** |
| Topics | **none collected** |
| Time span | 2026-07-30 → 2026-08-07; peak 24,285 articles/day |

### Limits

- 🔴 **Redistribution prohibited.** The ToS claim even structured metadata. Internal
  evaluation only — the blocking constraint on any public release.
- 🔴 **461 of 2,000 free tokens left**; 30-day window; archive costs 5 tokens/year. A second
  7-day pull is unaffordable.
- 🔴 **Not a story dataset** — 100% singletons; 83.5% have no `eventUri`.
- 🔴 **The duplicate flag deletes the best clusters** — one dpa item at 48 independent
  outlets is excluded from the event graph. Recoverable locally by title-clustering (51.7%
  of articles, zero API cost).
- ⚠️ **Zero topics collected** — default `returnInfo` excludes concepts and categories.
- ⚠️ `lang="deu"` blocks cross-lingual coverage; `sueddeutsche.de` returns 300-char teasers;
  601 articles carry stale pre-2026 publisher timestamps (filter on `dateTime`).

---

## Cross-provider joins

The 56 domains present in all three German-capable providers are where they can be joined:

| pair | shared domains |
|---|---|
| Event Registry ∩ GDELT | **163** |
| Ground News ∩ GDELT | 114 |
| Event Registry ∩ Ground News | 80 |
| **all three German methods** | **56** |

Those 56 outlets account for ~28–30% of both German pipelines. The join that matters:
**take a GDELT cluster → pull the matching Event Registry body → attach the Ground News
outlet bias label.** That is the only route to a German dataset with structure, text and
labels at the same time.
