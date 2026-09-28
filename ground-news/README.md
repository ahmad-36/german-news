# Ground News collector (`ground-news/`)

Ground News scraper, the German discovery pipeline, and the keyword list.

Part of the `news` repository, next to `gdelt/`, `eventregistry/`, `ui/` and
`analytics/`. AllSides lives in the separate `muws-allsides-dataset` repository.

## What is human, what is GPT

A Ground News record has three layers, made in three different ways. Don't treat them as
one kind of signal.

| layer | fields | who made it | unit | coverage |
|---|---|---|---|---|
| **Bias labels** | `source_bias`, `bias_ratings`, `left_pct` / `center_pct` / `right_pct` | **Human** — averaged from AllSides, Ad Fontes Media and Media Bias/Fact Check | **outlet**, not article | 62.6% of articles; 37.4% `unknown` |
| **Summaries + bias comparison** | `summary_left` / `summary_center` / `summary_right`, `bias_comparison`, `generated_headline` | **GPT** | **story** | partial — see below |
| **Clustering** | which articles share a story; `topics` | **Ground News' own pipeline**, run on English machine translations | story | all 894 stories |

**Bias labels are human, outlet-level, and US-framed.** Ground News rates nothing itself.
All three agencies are US organisations that place outlets on the American left–right axis.
A German outlet gets a position on a US spectrum, if it is rated at all. The agencies
**disagree on 32.1%** of rated articles, and Ground News averages them into one value.
Every article from an outlet gets the same label, so a classifier trained on it learns the
publisher, not the article's stance. AllSides'
[audit methodology](https://www.allsides.com/sites/default/files/AllSides-Media-Bias-Audit_Example-March-2022.pdf)
shows how the label is made. It samples 5 to 10 headlines, or the top article on a
couple of major stories. US survey respondents rate the outlet as a whole from that
sample, and their ratings are averaged into **one overall score for the publication**. The
same report says the ratings *"reflect the average judgment of the American people."*
Details: `analytics/docs/experiments.md`.

**Summaries and the bias comparison are GPT output, story-level, with partial coverage.**
The page payload stores them in an object named `chatGptSummaries` (read at
[scraper.py:777](scraper.py#L777)). The exact model is not exposed. Coverage over 894
stories:

| field | stories |
|---|---|
| `summary_left` | 320 |
| `summary_center` | 414 |
| `summary_right` | 273 |
| any side summary | 441 (49.3%) |
| all three sides | 209 (23.4%) |
| `bias_comparison` | 499 |
| `generated_headline` | 490 (from `generatedHeadline`; LLM-written, model not named) |

A side is missing when the story has too little coverage from that side. Use these fields
as weak supervision or as a baseline to beat, **never as ground truth**, and never as
human-written text. `title`, `description` and `dek` are **not** generated. They are
editorial text from the outlets and Ground News.

**Clustering is Ground News' own, and it runs after translation.** 41.2% of articles
(18,969 / 46,030) are machine-translated into English before they are clustered and
tagged. The source string survives in `original_title` / `original_description`. For
these articles `title` is the translation, so use `original_title` when you need the
publisher's wording. The translation step also causes a specific error mode: it deletes
entities that clustering depends on.

- Surnames that are also German words are translated away: *Manuel **Neuer*** → "new".
- Club names collide with place names: *FC **Bayern*** → "Bavaria"; *Tor* (goal) → "Gate".
- `USA` / `US-` collapses into the English word "Us" (96 of 4,167 distinct German titles).
- Topic tagging runs on the damaged text. The Neuer/Urbig goalkeeper cluster is tagged
  **"Mohammed Bin Salman"**.

The translation engine and the clustering algorithm are both undocumented. Full write-up:
`analytics/docs/experiments.md`.

## Where data lives

**In this folder, under [`data/`](data) — gitignored, so it is never pushed.** This folder owns
`data/ground_news/` and `data/discovery/` (~22 MB).

No environment variable is needed: [paths.py](paths.py) uses this folder's `data/` for the
sources it owns and finds sibling folders' `data/` for anything else. Every script also
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
`gdelt` where it doubles as a `--keywords-file` filter.

| file | contents |
|---|---|
| `ground_news_interests.txt` | the 17 `/interest/` topic pages this crawl walks |
| `german_politics.txt` | 30 terms — parties, institutions, policy, recurring events |
| `german_all.txt` | 86 terms — plus companies, cities, sport, EU, US/geopolitics |
| `german_keywords.json` | machine-readable, with measured per-term yield |

**Three things decide what ends up in the dataset**, and only the second is a keyword list:
the 17 topic pages plus `/top` and `/blindspot` (the default crawl, no keyword involved),
the 86 search terms, and the 60-name German publisher register in `germanlib.py` that
decides what counts as German. Full breakdown:
`analytics/docs/keywords_and_apis.md`.

**The empirical rule behind the list:** proper nouns survive Ground News' English
translation and find hits in German (`Bundeswehr` → 10 events); generic/abstract German
words do not, because the English title uses the English word (`Leitzins` → 0 events,
while `interest rate Germany` → 8). So: **keep proper nouns in German, translate generic
concepts into English and qualify them with "Germany".**

82 of 86 terms returned results; the 4 that returned nothing are marked `# ZERO` in the
files. Full write-up, including how to extend the list:
`analytics/docs/keywords_and_apis.md`.

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
rather than in `ui` because it drives *this* scraper.

```bash
streamlit run ui/topic_discovery.py
```

> **Known duplication:** `ui/common.py` and `germanlib.py` are vendored copies also
> present in `ui`. If you change one, change the other. They
> were duplicated rather than packaged so each folder runs standalone.

## Known limits

- **Tiny** — 894 stories over ~14 months.
- **No body text at all** — headline + dek only. Text modelling needs a separate fetch
  against 45,601 URLs.
- **No images** — the record has no image field.
- **Only 12.1% German.**
- **37.4% of bias labels are the literal string `unknown`**, concentrated on exactly the
  small non-English outlets that make up the German tail.
- **Labels are per outlet, US-framed, and contested.** Ground News does not rate anything
  itself; it averages Media Bias/Fact Check, Ad Fontes and AllSides, which **disagree on
  32.1%** of articles. Its own docs: *"This rating does not measure the bias of specific
  news articles. The analysis is done at the publication level."*
- **Summaries are GPT-generated** (`chatGptSummaries`) — `summary_left/center/right`,
  `bias_comparison`, plus the LLM-written `generated_headline`. The *labels* are not. See
  [What is human, what is GPT](#what-is-human-what-is-gpt).
- **Translation happens before clustering**, and it loses entities —
  `analytics/docs/experiments.md`.
- Language tags are unreliable (Luxembourgish tagged `de`).

## Environment

`curl_cffi` for the scraper; `streamlit` + `pandas` + `plotly` for the UI page.
