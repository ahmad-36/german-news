# Project overview & Event Registry notes

This repo collects German/international news data for the news-bias dataset from
three independent pipelines, plus a browser UI:

| Piece | What it does | Output |
|---|---|---|
| `scrapers/ground_news/scraper.py` | Ground News stories + per-outlet bias/factuality ratings (curl_cffi, no browser) | `data/ground_news/ground_news.jsonl` |
| `scrapers/gdelt/gdelt_german_outlets.py` | German outlet discovery via GDELT DOC API (theme/keyword probes → domain ranking) | `data/gdelt/` CSV/JSON |
| `scrapers/eventregistry/eventregistry_german_sources.py` | German sources + full-text articles via Event Registry (newsapi.ai) | `data/eventregistry/` |
| `ui/dataset_explorer.py` | Streamlit app: Story Feed, Dataset Statistics, Topic Discovery, Event Registry tabs | `uv run streamlit run ui/dataset_explorer.py` |

The rest of this file documents the Event Registry pipeline (env: `scrap2`,
key via `EVENTREGISTRY_API_KEY` or `~/.eventregistry_key`).

## Usage

```bash
conda activate scrap2
python scrapers/eventregistry/eventregistry_german_sources.py                  # discovery: suggest + top-100 sourceAggr
python scrapers/eventregistry/eventregistry_german_sources.py --sample          # + 10 example articles
python scrapers/eventregistry/eventregistry_german_sources.py --skip-discovery --days 7 --pull 5000 \
    [--pull-sources zeit.de faz.net ...]                 # scrape articles → JSONL
```

Articles land in `data/eventregistry/articles_germany.jsonl` (one JSON/line,
merged + deduped by article `uri` across runs — same accumulating pattern as
the Ground News scraper). The Streamlit "Event Registry" tab reads this file;
its loader is `@st.cache_resource`-cached, so **restart the app (or clear
cache) after every new pull** or you'll keep seeing the old data.

## Token economics (free plan, measured 2026-08-07)

- 2,000 tokens total, **non-renewing**; content window = last 30 days only.
- Article pull: **1 token per 100-article page** (measured, despite ambiguous docs).
- Aggregate queries (`sourceAggr`): ~5 tokens each.
- Historical/archive queries: 5 tokens *per searched year* — the script sets
  `allowUseOfArchive=False` so these can never fire accidentally.
- Autosuggest calls (`suggestSourcesAtPlace`, `getLocationUri`) are free.
- A full 7-day Germany window is ~179k articles ≈ ~1,790 tokens.
- Watch the live counter on the https://newsapi.ai dashboard; the script also
  prints remaining tokens after every call.

## Schema notes

Each article has: `uri`, `title`, **`body` (full text)**, `url`, `lang`,
`date`/`time`/`dateTime`/`dateTimePub`, `source` (uri + title), `authors`,
`image`, `sentiment`, `eventUri` (same-event clustering id), `isDuplicate`.

- **Image captions are NOT present in Event Registry.** The `image` field is a
  bare URL only — no caption text is provided anywhere in the schema.
- No cross-publisher story clustering in the article schema itself (only the
  `eventUri` id) and **no bias ratings** — Ground News' "story = many outlets,
  rated left/center/right" model doesn't exist here.

## Caveats

- **Licensing / ToS (standing caveat):** the free tier is licensed for
  evaluation/testing only and the ToS forbids redistributing the data — fine
  for exploring coverage, but this JSONL **can't go into the public dataset
  as-is**. At most, derived statistics/aggregates; even structured metadata is
  claimed as Event Registry's property.
- **Notable absences from the top 100** (7-day sourceAggr, 2026-07-30..08-06):
  spiegel.de, taz.de, and tagesschau.de. Spiegel especially is a red flag —
  either Event Registry doesn't index it or it's restricted. Süddeutsche is
  marked `"private": true` in the response, which in Event Registry means the
  full article body won't be returned to you. Worth checking a couple of these
  before assuming coverage.
  - **Verified in the full 7-day pull (2026-08-07, 129,628 articles, 320
    sources):** spiegel.de (379), taz.de (323), and tagesschau.de (233) ARE
    indexed — they were just below the top-100 volume cutoff. But the
    Süddeutsche restriction is real: its bodies are ~300-char teasers
    (median 297 chars over 2,645 articles) vs. full text elsewhere (e.g.
    taz 4,194, tagesschau 3,345, faz 3,000, spiegel 2,100 median chars).
    Treat sueddeutsche.de as headline/teaser-only in this corpus.
- **Mild location noise:** finanzen.at and derstandard.de (Austrian brands'
  .de operations) slipped in despite the Germany source-location filter.
- **Volume ≠ importance:** the ranking is dominated by finance wires
  (wallstreet-online.de) and the Ippen local-paper network (hna.de, wa.de,
  come-on.de, …) which syndicate largely identical content.

## Date-wise retrieval

Date-wise retrieval — yes, but with a hard horizon. `QueryArticles` takes
arbitrary `dateStart`/`dateEnd`, so you can slice German news by day, and the
full 7-day pull is exactly a date-windowed query. The catch: the free plan
only reaches the **last 30 days**. Older dates require archive access — paid,
at 5 tokens per searched year, back to 2014. So day-by-day coverage of "the
entire German news" works going *forward* (pull each window while it's inside
the 30-day horizon), but you can't backfill history on the free tier. Also
"entire" has the coverage holes noted above — no Spiegel/taz/tagesschau in
what we've seen so far; the full pull will let us verify whether they appear
at all.
