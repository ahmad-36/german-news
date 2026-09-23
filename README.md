# news-ground-news

Ground News scraper, the German discovery pipeline, and the keyword list.

Lives in `news/` alongside its sister repos, each an independent git repo. Split out of
the former monolithic `news` repo (Sept 2026, now retired to `archive/news`). Sisters:
[news-gdelt](../news-gdelt), [news-eventregistry](../news-eventregistry),
[news-explorer](../news-explorer), and
[muws-allsides-dataset](https://github.com/muws-workshop/muws-allsides-dataset).

## Where data lives

**In this repo, under [`data/`](data) — gitignored, so it is never pushed.** This repo owns
`data/ground_news/` and `data/discovery/` (~22 MB).

No environment variable is needed: [paths.py](paths.py) uses this repo's `data/` for the
sources it owns and finds sibling repos' `data/` for anything else. Every script also
takes `--data-dir`.

## Scraping

Ground News has **no public API** and **no date endpoint** — the crawl axis is
*trending*, not time. The scraper walks the homepage, `/top`, `/blindspot` and ~20
`/interest/<topic>` pages, keeps stories with 3+ sources, and merges into
`data/ground_news/ground_news.jsonl`.

```bash
python scraper.py                                      # trending snapshot
python scraper.py --query "ukraine"                    # subject search
python scraper.py --from-date 2026-03-01 --to-date 2026-03-15   # historical, via Wayback
python scraper.py --refresh-existing                   # re-fetch known stories
python scraper.py --fresh                              # overwrite instead of merge
```

Historical mode replays **Wayback Machine** snapshots of the listing pages — best-effort
and gappy, and the only route to the past. Needs `curl_cffi` Chrome impersonation to get
past bot detection; no browser required.

Yield is roughly **2 stories/day**. This is a label source and an evaluation set, not a
corpus.

## Keywords

[`keywords/`](keywords/) is the German seed-term list, shared verbatim with
[news-gdelt](../news-gdelt) where it doubles as a `--keywords-file` filter.

| file | terms |
|---|---|
| `german_politics.txt` | 30 — parties, institutions, policy, recurring events |
| `german_all.txt` | 86 — plus companies, cities, sport, EU, US/geopolitics |
| `german_keywords.json` | machine-readable, with measured per-term yield |

**The empirical rule behind the list:** proper nouns survive Ground News' English
translation and find hits in German (`Bundeswehr` → 10 events); generic/abstract German
words do not, because the English title uses the English word (`Leitzins` → 0 events,
while `interest rate Germany` → 8). So: **keep proper nouns in German, translate generic
concepts into English and qualify them with "Germany".**

82 of 86 terms returned results; the 4 that returned nothing are marked `# ZERO` in the
files. Full write-up, including how to extend the list:
[news-source-survey/docs/keywords.md](../news-source-survey/docs/keywords.md).

## Discovery pipeline

```bash
python discovery/german_discovery_run.py                 # full run
python discovery/german_discovery_run.py --phase-c-only  # just tag expansion
python discovery/check_scrapeability.py                  # paywall/extraction probe
```

Searches each seed term, scrapes what it finds, then computes new candidate tags from
`place=Germany` stories already in the dataset (phase C). Phase C imports from
[`ui/common.py`](ui/common.py).

## UI

`ui/topic_discovery.py` is the interactive Streamlit driver for the above. It lives here
rather than in [news-explorer](../news-explorer) because it drives *this* scraper.

```bash
streamlit run ui/topic_discovery.py
```

> **Known duplication:** `ui/common.py` and `germanlib.py` are vendored copies also
> present in [news-explorer](../news-explorer). If you change one, change the other. They
> were duplicated rather than packaged so each repo runs standalone.

## Known limits

- **Tiny** — 894 stories over ~14 months.
- **No body text at all** — headline + dek only. Text modelling needs a separate fetch
  against 45,601 URLs.
- **No images** — the record has no image field.
- **Only 12.1% German.**
- **37.4% of bias labels are the literal string `unknown`**, concentrated on exactly the
  small non-English outlets that make up the German tail.
- **Labels are per outlet, and contested.** Ground News does not rate anything itself; it
  averages Media Bias/Fact Check, Ad Fontes and AllSides, which **disagree on 32.1%** of
  articles. Its own docs: *"This rating does not measure the bias of specific news
  articles. The analysis is done at the publication level."*
- **Summaries are LLM-generated** — `summary_left/center/right`, `bias_comparison` and
  `generated_headline`. The *labels* are not.
- **Translation happens before clustering**, and it loses entities —
  [the write-up](../news-source-survey/docs/translation_problem.md).
- Language tags are unreliable (Luxembourgish tagged `de`).

## Environment

`curl_cffi` for the scraper; `streamlit` + `pandas` + `plotly` for the UI page.
