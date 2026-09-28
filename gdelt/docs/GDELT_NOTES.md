# GDELT — notes

> **Scale note (Aug 2026).** Everything below the "DOC API" heading describes
> the *search frontend*, which is capped at 250 results per query. That cap —
> not German news volume — is why `gdelt_stories.jsonl` only held 654 stories:
> four probes were ever run and all four returned exactly 250 rows, i.e. all
> four were truncated. The backend routes documented in
> "Full backend — raw dumps and BigQuery" remove the cap entirely.
>
> **Delivered dataset (2026-01-01 → 2026-08-01, German only, raw-dump route):**
> 20,350/20,350 slots, zero failures — a complete census of what GDELT saw.
>
> | file | contents |
> |---|---|
> | `data/gdelt/gdelt_articles_de.jsonl` | 3,835,367 articles (4.5 GB) |
> | `data/gdelt/gdelt_stories_de.jsonl` | 2,015,373 clustered stories (5.1 GB) |
> | `data/gdelt/gdelt_stories_de_min3.jsonl` | 173,388 stories with 3+ outlets (1.9 GB) |
>
> 473 distinct outlets; coverage is flat at 23–28k multi-outlet stories/month;
> 3,811 stories reached 30+ independent outlets. The old `gdelt_stories.jsonl`
> (654 stories, 41 with 3+ outlets) is left in place untouched.
>
> `unify.py` now defaults its `--gdelt` input to the min3 file, so
> `data/unified/unified_gdelt.jsonl` holds 173,388 stories / 1,408,753 articles
> and the UI picks it up from its dataset dropdown with no code change. The
> previous DOC-API unified output is kept at
> `data/unified/archive/unified_gdelt.docapi-654stories.jsonl`.

## Full backend — raw dumps and BigQuery

The DOC API is a frontend over GDELT's database. The database itself is exposed
two other ways, both uncapped:

**Raw 15-minute dumps** (`gdelt_dump_pull.py`, no credentials needed).
`masterfilelist-translation.txt` indexes the translingual feed (65 languages,
back to 2015-02-19). Each 15-minute slot ships `export` / `mentions` / `gkg`
zips; the **GKG** file is the one with per-article records. The puller streams
each zip, filters in memory, and never writes the raw file — so Jan–Aug 2026 is
172 GB of *bandwidth* but only ~5 GB of output. Measured throughput on this
cluster: ~68 slots/min with 8 workers, so the 20,446-slot range takes ~5 hours.

**BigQuery** (`gdelt_bq_pull.py`, needs a GCP project).
`gdelt-bq.gdeltv2.gkg_partitioned` holds the same rows. Always filter on
`_PARTITIONTIME` and select few columns — the free sandbox tier is 1 TB/month
and `Extras` is the expensive column. The script dry-runs every monthly window
and prints the scanned-byte estimate before executing.

### GKG gotchas (both routes)

- **GKG has no title column.** The page title is inside the `Extras` XML as
  `<PAGE_TITLE>`, HTML-entity encoded — present on 100% of sampled German rows.
  Since the clusterer keys on titles, dropping `Extras` to save BigQuery quota
  costs you clustering.
- Language lives in `TranslationInfo` as `srclc:deu`. German is consistently
  the 3rd–4th largest language in the translingual feed (~9% of rows).
- The 27-column TSV is 0-indexed as: `DATE`=1, `SourceCommonName`=3,
  `DocumentIdentifier`=4, `V2Themes`=8, `SharingImage`=18, `TranslationInfo`=25,
  `Extras`=26. Getting `TranslationInfo` off by one silently yields zero German
  rows rather than an error.
- `SharingImage` is populated on ~74% of German rows; there is no
  outlet-country field, unlike the DOC API's `sourcecountry`.
- GDELT indexes section fronts and homepages too, so singleton "stories" include
  junk like `BÖRSE ONLINE – Seit 1987 …`. Filter with `--min-outlets 2` or higher.

### Clustering at this scale

`gdelt_collect.cluster_articles()` compares each article against every existing
cluster — fine for ~1k articles, hopeless for millions. Use
`gdelt_cluster_bulk.py`, which buckets by day, blocks on a token inverted index
before any similarity call, and fans the (independent) windows across processes.
It emits the same story schema, so the UI and `gdelt_enrich.py` are unaffected.

**Use `--span-days 0`.** Cost per window is superlinear in window size, so
merging days is doubly bad: it makes each window disproportionately more
expensive *and* leaves fewer windows to parallelise over. Measured: one day
(~20k articles) clusters in ~3 min, but a 60k/3-window run with `--span-days 1`
took 8m38s wall with only ~1.6x effective parallelism, because the largest
window dominated. Per-day windows give ~213 balanced jobs — roughly 20 minutes
across 32 workers for the full Jan–Aug range.

The tradeoff is that a story breaking near midnight is split into two records.
That is usually acceptable (and arguably right — it is a separate day's coverage
snapshot); use `--span-days 1` only if cross-midnight merging actually matters.

### Feeding the UI

`ui/gdelt_viewer.py` takes the stories path as a text input, so it needs no code
change to read `gdelt_stories_de.jsonl` — but it loads the whole file into a
dataframe, and the full range is ~2M stories with their articles inlined. Keep a
filtered file for the UI (`n_outlets >= 3` is ~8% of stories) and reserve the
full file for analysis. Note also that GKG has no outlet-country field, so every
story's `countries` is `["?"]` and the viewer's country filter is inert on this
data; derive country from the domain if you need it.

### Enrichment does not scale to this dataset

`gdelt_enrich.py` fetches sequentially with `FETCH_DELAY_S = 1.5` and defaults to
`--limit 80`. That is right for a ~650-story set; at ~187k stories with 3+
outlets it is ~78 hours of serial fetching. Enriching the full range needs a
parallel, per-domain-throttled rewrite — and unlike the GDELT dumps, this stage
hits publisher sites directly, so it deserves an explicit decision about scope
and politeness rather than being run wholesale. Enrich a sampled subset instead
unless full-corpus bodies are genuinely required.

## DOC API — rate limiting (important)

GDELT rate-limits this cluster's IP hard — after ~5 rapid queries it returns
`RateLimitError` with a cooldown that outlasted a 4-minute wait. Any production
use needs ~1 query/minute pacing or should switch to GDELT's raw CSV dumps.

Practical rules used by `gdelt_collect.py`:

- **15-second buffer between queries** (so it never looks like rapid search),
- on `RateLimitError`: back off 60s and retry, max 3 attempts per query,
- keep runs small (a handful of probes per run) and let repeated runs
  accumulate via the merge-on-rerun behavior instead of one giant crawl.

## Query shape

- **Language is the filter that matters: `language="german"`.**
  `country=` is *not* set — German-language coverage includes Austrian and
  Swiss outlets (and German-language services elsewhere); the article's
  `sourcecountry` field tells you where each outlet is from.
- The DOC API refuses fully unfiltered queries — every query needs at least
  one keyword / theme / domain. Broad discovery therefore samples across
  several diverse probes and aggregates.
- Max **250 articles per query, no pagination.** To go deeper, narrow the
  time window (per-day, per-hour) and/or query per outlet with `domain_exact`.
- Keywords must not be too short — `"Merz"` is rejected with *"The specified
  phrase is too short"*; use a longer phrase like `"Friedrich Merz"`.

## Temporal coverage — can we get German-news over time?

Yes. The DOC API accepts `start_date` / `end_date` **back to January 1 2017**
and its index updates every ~15 minutes, so a *temporal* collection method is:

```
for each day D in range:                      # or hour, for hot topics
    for each probe (keyword/theme or domain_exact=outlet):
        query(language="german", start_date=D, end_date=D+1)
        sleep 15s
```

Two caveats:

1. **"All German news agencies" ≈ "all outlets GDELT monitors."** Coverage is
   very broad (a single 7-day, 3-probe sample already surfaced 82 distinct
   German-language domains) but it is GDELT's crawl list, not a guaranteed
   census of every German outlet. Per-outlet `domain_exact` queries make the
   outlet set explicit and reproducible.
2. GDELT stores **metadata only** (title, url, date, outlet, social image) —
   article bodies must be fetched from the outlets themselves (see
   `check_scrapeability.py`; scrapeability report in
   `data/discovery/scrapeability_report.json`).

## Enrichment — why and how

Right — that's GDELT's inherent gap: it only gives title/url/outlet/timestamp,
no body, no images (and the seeded sample didn't even keep the social-preview
image). The fix is an enrichment step: fetch each story's main article from
the outlet itself and extract a summary, lead image, and its caption — which
the scrapeability check already proved works for the open outlets.

That's what `gdelt_enrich.py` does: one representative article per story
(preferring the open outlets from the scrapeability report), extracting
summary (trafilatura), lead image (`og:image`) and its `<figcaption>`. Results
attach to stories as an `enrichment` field and are cached per-URL in
`data/gdelt/gdelt_enrichment.json`, so re-clustering never loses fetched work.

## Scripts

| script | env | purpose |
|---|---|---|
| `gdelt_dump_pull.py` | scrap2 | **uncapped** German pull from raw 15-min dumps, no credentials → `data/gdelt/gdelt_articles_de.jsonl` |
| `gdelt_bq_pull.py` | scrap2 | **uncapped** German pull via BigQuery (needs GCP project); dry-runs cost first |
| `gdelt_cluster_bulk.py` | scrap2 | scalable day-bucketed clustering for the above → `gdelt_stories_de.jsonl` |
| `gdelt_german_outlets.py` | scrap2 | one-off domain discovery / ranking |
| `gdelt_collect.py` | scrap2 | temporal collection → clustered `data/gdelt/gdelt_stories.jsonl` (feeds the UI's GDELT page) |
| `gdelt_enrich.py` | scrap2 | fetch summary + lead image + caption per story → `enrichment` field |
| `gdelt_event_clustering.py` | scrap2 | live clustering probe (ad-hoc) |
| `check_scrapeability.py` | scrap2 | paywall / extraction / image check per outlet |
