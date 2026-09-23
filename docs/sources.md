# Per-Source Reference

For each provider: **how scraping works**, **what you get**, and **what the limits are**.
All figures measured against the data on disk (Jan–Aug 2026, ~7.3 GB).

---

## AllSides

> US political news, presented as left/center/right triplets per story.
> Scraper: [`muws-workshop/muws-allsides-dataset`](https://github.com/muws-workshop/muws-allsides-dataset)

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
| **Images** | **68.9%** have an image URL (47,122); the scraper also downloads them locally |
| Stance label | 99.9% (68,290), 7-point scale |
| Topics | 100%, human-readable (`Donald Trump`, `Immigration`, `Economy And Jobs`) |
| Story summary | 100%, editorial |
| Language tag | absent |

### Limits

- 🔴 **US-only. Zero German articles.** This is disqualifying for the German dataset and
  no amount of scraping changes it.
- 🔴 **~8× article inflation.** 68,352 slots collapse to 8,072 distinct URLs, because the
  same article is reused across many story pages via the "More from the Left/Center/Right"
  sidebars. **Any per-article statistic computed without deduplicating is wrong** — see
  [stance_labels.md](stance_labels.md) §4 for a case where this inflated a headline result
  by 22 points.
- ⚠️ `is_featured: false` articles come from those sidebars and may not be about the story.
  Filter them before treating them as story members.
- ⚠️ Body text on only 17.3%, and it requires a separate per-domain scraper per outlet.
- ⚠️ Labels are **per outlet**, and the three-column layout makes the corpus balanced by
  construction (left 22,967 / center 22,669 / right 22,716) — a layout artefact, not a
  property of the news.
- ⚠️ Scraped content; the usual redistribution caveats apply.

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
| Per-stance summaries | 49.3% (441/894) — **LLM-generated** |
| `bias_comparison` paragraph | **LLM-generated** |
| Blindspot flag | 89 stories |
| Topics | 99.8%, human-readable |
| Paywall flag | 5,270 articles flagged |
| Unique domains | **5,477** — a worldwide long tail |

### Limits

- 🔴 **Tiny.** 894 stories after ~14 months of scraping — roughly 2 stories/day. Not a
  corpus; treat it as a label source and an evaluation set.
- 🔴 **No body text at all.** Any text-based modelling needs a separate fetch against
  45,601 URLs.
- 🔴 **No images at all.**
- 🔴 **Only 12.1% German**, and its German slice is three orders of magnitude below GDELT.
- ⚠️ **37.4% of labels are `unknown`**, concentrated on exactly the small and non-English
  outlets that make up the German tail.
- ⚠️ **Labels are per outlet and contested.** Aggregated from MBFC (25,435 articles),
  Ad Fontes (19,034) and AllSides (8,330); **the three disagree on 32.1%**.
- ⚠️ **Factuality field exists but is 0% populated** in this dump.
- ⚠️ `summary_right` is often the empty string even when left and center are populated,
  which biases any study conditioning on all three.
- ⚠️ **Translation happens before clustering** and destroys entities — see
  [translation_problem.md](translation_problem.md).
- ⚠️ Language tags are unreliable (Luxembourgish tagged `de`).
- ⚠️ 5,477 domains is a worldwide long tail at median 1–2 articles per outlet, not depth.

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

- 🔴 **No body text, no descriptions natively.** GKG gives title + URL + themes. Bodies and
  images require our own crawl of the outlets.
- 🔴 **No bias signal whatsoever** — stance is `unknown` for all 1,408,753 articles.
- ⚠️ **Clustering is ours and it is shallow.** Two outlets rewriting the same event under
  different headlines will not merge; a story crossing midnight splits into two ids; a 0.65
  title threshold merges recurring headlines (weather, market wraps) within a day.
- ⚠️ **GKG has no title column** — titles come from `<PAGE_TITLE>` inside the `Extras` XML.
  Dropping `Extras` to save BigQuery quota silently destroys clustering.
- ⚠️ **Junk records.** GDELT indexes section fronts and homepages. `--min-outlets 3` is why
  the delivered file is 173,388 of 2,015,373 stories (8.6%).
- ⚠️ **No outlet-country field on the bulk route** (unlike the DOC API's `sourcecountry`) —
  all 173,388 stories carry `countries: ["?"]`.
- ⚠️ **Expensive to pull.** 172 GB of bandwidth for Jan–Aug 2026 (~5 h at 8 workers).
- ⚠️ GKG themes are high-recall/low-precision, and `TAX_ETHNICITY_GERMAN` /
  `TAX_WORLDLANGUAGES_GERMAN` are artefacts of our own language filter, not subjects.
- 🟢 **Upside: openly licensed.** The only provider here whose data we may republish.

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

- 🔴 **Redistribution prohibited.** The ToS forbid sharing or sublicensing data from the
  service and claim even structured metadata as Event Registry's property. **This dataset
  cannot be published** — internal evaluation only. This is the blocking constraint for any
  public release.
- 🔴 **Cost wall.** 2,000 non-renewing free tokens; the 7-day pull consumed ~1,540, leaving
  **461**. A second 7-day pull (~1,790 tokens) is no longer affordable.
- 🔴 **30-day window.** Anything older needs the paid archive at 5 tokens *per searched
  year*, so pre-July-2026 German news is effectively unavailable.
- 🔴 **Not a story dataset.** 100% singletons after unification; 83.5% of articles have no
  `eventUri` even in the raw file.
- 🔴 **The duplicate flag destroys the interesting clusters.** Of 59,088 articles flagged
  `isDuplicate: true`, exactly **2** carry an `eventUri` — ER routes duplicates to an
  original rather than into an event. And the flag fires across distributors: 6,164 of
  14,830 distinct duplicate-flagged titles appear at ≥2 domains, up to **48 domains** for
  one dpa wire item. The case you most want as a cluster is the case ER deletes.
  **Recoverable:** title-clustering the raw file yields 67,005 clustered articles (51.7%)
  at zero API cost — ~8× what `eventUri` surfaces.
- ⚠️ **`lang="deu"` blocks cross-lingual coverage.** ~9.5% of events are anchored in a
  non-German language and we hold only their German tail. Per-language re-pulls multiply
  cost.
- ⚠️ **No topics, concepts or `storyUri`** — all excluded by the default `returnInfo`.
  A scraper defect, but fixing it costs tokens.
- ⚠️ **`sueddeutsche.de` is `private: true`** → ~300-char teaser bodies only, despite being
  the 5th largest source (2,645 articles).
- ⚠️ Volume skewed to low-signal material — finance wires (wallstreet-online.de 4,249;
  finanzen.at 3,725) and the Ippen local network dominate.
- ⚠️ 601 articles carry a `dateTimePub` before 2026-07 (min 2014-01-27) — stale publisher
  timestamps, not archive access. Filter on `dateTime` (crawl time) for a clean window.

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
