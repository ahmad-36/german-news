# Ground News Collector

Scrapes stories from [Ground News](https://ground.news), which groups coverage of one
event from many outlets and labels each outlet's political bias.

## Usage

```bash
python scraper.py                                             # current topic pages
python scraper.py --query "Bundeswehr"                        # keyword search
python scraper.py --from-date 2026-03-01 --to-date 2026-03-15 # past pages, via the Wayback Machine
python discovery/german_discovery_run.py                      # find German stories from seed keywords
streamlit run ui/topic_discovery.py                           # interactive version of the above
```

There is no public API and no way to request a date. The scraper walks the homepage,
`/top`, `/blindspot` and 17 `/interest/<topic>` pages, and keeps stories with 3+ sources.
It uses `curl_cffi` browser impersonation to get past bot detection.

## What a record contains

| part | fields | made by |
|---|---|---|
| Bias labels | `source_bias`, `bias_ratings` | **humans**, per outlet: averaged from AllSides, Ad Fontes and Media Bias/Fact Check |
| Summaries | `summary_left/center/right`, `bias_comparison`, `generated_headline` | **GPT** (stored as `chatGptSummaries`) |
| Stories and topics | which articles share a story, `topics` | Ground News, method undocumented |
| Headlines | `title`, `dek`; `original_title` for translated articles | the outlets |

## Keywords

[`keywords/`](keywords/) holds the 17 topic pages and the German search terms (30 politics
terms, 86 in total). Proper nouns stay in German, while general concepts are written in
English plus "Germany". Ground News searches its English translation, so `Leitzins` finds
nothing but `interest rate Germany` does. Details:
[analytics/docs/keywords_and_apis.md](../analytics/docs/keywords_and_apis.md).

## Limits

- Small: 894 stories in about 14 months, 12.1% of articles German.
- No article text and no images, only headline and dek.
- Labels are per outlet and US-framed; the three agencies disagree on 32.1% of articles,
  and 37.4% of articles are `unknown`.
- 41% of articles are machine-translated to English, and the translation damages names
  (*Neuer* → "new", *Bayern* → "Bavaria"). See
  [analytics/docs/experiments.md](../analytics/docs/experiments.md#4-ground-news-translation-deletes-entities).

**Requirements:** `curl_cffi`, `beautifulsoup4`, `trafilatura`, `tqdm`; `streamlit`,
`pandas` and `plotly` for the UI.
