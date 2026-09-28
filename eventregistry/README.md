# Event Registry collector (`eventregistry/`)

Event Registry (newsapi.ai) pull for full-text German articles.

Part of the `news` repository, next to `gdelt/`, `ground-news/`, `ui/` and `analytics/`.

> ## ⚠️ Read this before collecting
>
> - **Redistribution is prohibited.** The ToS forbid sharing or sublicensing data from
>   the service and claim even structured metadata as Event Registry's property. **This
>   data cannot be published** — internal evaluation only. It is the blocking constraint
>   on any public dataset release.
> - **461 free tokens remain** of a 2,000 non-renewing allowance. One 7-day pull cost
>   ~1,540. A second is no longer affordable.
> - **30-day recency window.** Older data needs the paid archive at **5 tokens per
>   searched year**; the script sets `allowUseOfArchive=False` as a guard.

## Where data lives

**In this folder, under [`data/`](data) — gitignored, so it is never pushed.** This folder owns
`data/eventregistry/` (~201 MB). Given the ToS above, that gitignore is doing real work:
this data must not end up in a pushed commit.

```bash
export EVENTREGISTRY_API_KEY=...        # or ~/.eventregistry_key
```

## Usage

```bash
python eventregistry_german_sources.py --skip-discovery --days 7 --pull 5000
```

Costs **1 token per 100-article page**.

## What you get

| | |
|---|---|
| Articles pulled | 129,628 (one 7-day window, 320 sources) |
| German | 100% |
| **Full body text** | **100%**, median 2,111 chars, clean UTF-8 |
| Images | 98.6% URL (no captions) |
| Authors | ✅ |
| Topics | **none collected** — see below |
| Stance labels | none |

## Three filters we should be using and are not

The API has the richest filter set of any provider in this project, and our pull uses
almost none of it:

1. **`startSourceRankPercentile`** — our pull is dominated by finance wires
   (wallstreet-online.de 4,249) and the Ippen local network, which cluster worst and carry
   the least editorial signal. A percentile floor drops them at the API.
2. **`eventFilter=skipArticlesWithoutEvent`** — 83.5% of what we pulled has no `eventUri`
   and became a singleton. (Caveat: this also excludes the wire stories ER wrongly marks
   duplicates — which is the material we most want. Use knowingly.)
3. **`conceptUri` / `categoryUri`** — we collected **zero topics**, because the default
   `returnInfo` excludes `concepts` and `categories`. A scraper defect, not a provider
   limit, but fixing it costs tokens.

Full reference: `analytics/docs/keywords_and_apis.md`.

## Known limits

- **Not a story dataset.** 83.5% of articles have no `eventUri`, so after unification 108,549 of 110,941 stories are single-article.
- **The duplicate flag destroys the interesting clusters.** Of 59,088 articles flagged
  `isDuplicate: true`, exactly **2** carry an `eventUri` — up to **48 independent German
  outlets** carrying one dpa wire item get deleted from the event graph.
  **Recoverable:** title-clustering the raw file yields 67,005 clustered articles (51.7%)
  at zero API cost, ~8× what `eventUri` surfaces.
- **`lang="deu"` blocks cross-lingual coverage** — ~9.5% of events are anchored in another
  language and we hold only their German tail.
- **`sueddeutsche.de` is `private: true`** → ~300-char teasers only, despite being the 5th
  largest source.
- 601 articles have a `dateTimePub` before 2026-07 — stale publisher timestamps, not
  archive access. Filter on `dateTime` (crawl time).

Detail: [docs/EVENTREGISTRY.md](docs/EVENTREGISTRY.md).

## Environment

Needs `eventregistry` — conda env `scrap2` here.
