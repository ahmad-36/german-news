# news-gdelt

GDELT collection, clustering and enrichment for German-language news.

Lives in `news/` alongside its sister repos, each an independent git repo. Split out of
the former monolithic `news` repo (Sept 2026, now retired to `archive/news`). Sisters:
[news-ground-news](../news-ground-news), [news-eventregistry](../news-eventregistry),
[news-explorer](../news-explorer), and
[muws-allsides-dataset](https://github.com/muws-workshop/muws-allsides-dataset).

## Where data lives

**In this repo, under [`data/`](data) — gitignored, so it is never pushed.** This repo owns
`data/gdelt/` (~5.9 GB: the raw article dump, clustered stories, and enrichment).

Nothing here builds a path of its own; everything goes through [paths.py](paths.py).
No environment variable is needed — `paths.source_dir()` uses this repo's `data/` for
sources it owns and finds the sibling repo's `data/` for anything it doesn't. Override
per run with `--data-dir`, or globally with `$NEWS_DATA_DIR`.

## ⚠️ Collect bounded, not at scale

The Jan–Aug 2026 census cost **172 GB of bandwidth** and produced 3.8M articles that
nobody has fully used. Don't repeat it. The default working mode is **a short date range
plus a topic or keyword filter**:

```bash
# one week, filtered to German politics — the normal way to run this
python gdelt_dump_pull.py --start 2026-01-05 --end 2026-01-12 \
    --keywords-file keywords/german_politics.txt

# filter by GKG theme instead
python gdelt_dump_pull.py --start 2026-01-05 --end 2026-01-12 \
    --themes ELECTION,DEMOCRACY,LEADER

# bound an exploratory run to N 15-minute slots
python gdelt_dump_pull.py --start 2026-01-05 --end 2026-01-12 --max-slots 20 \
    --keywords-file keywords/german_politics.txt
```

Filters are OR-ed: an article is kept if its **title** matches any keyword **or** its
**GKG themes** match any theme. With no filter, you get the full German census for the
range and the script says so loudly.

Measured selectivity on 2026-01-05 → 2026-01-12 with `german_politics.txt` (30 terms):
**1.9% of German articles kept**. A week is ~672 slots, roughly 15 minutes at
`--workers 8`.

### German keyword matching

German compounds and inflects, so strict word-boundary matching under-matches badly —
it would miss `Bundestag` inside *Bundestagswahl* and `Grüne` inside *Die Grünen*. The
default therefore anchors only the **left** edge of a term: it must start a word, but may
continue. That keeps the compounds; the cost is that `SPD` also matches *SPDR*. Pass
`--whole-word` if precision matters more than recall for your list.

| term | title | default | `--whole-word` |
|---|---|---|---|
| `Bundestag` | Bundestagswahl 2026 | ✅ | ❌ |
| `Grüne` | Die Grünen fordern | ✅ | ❌ |
| `Koalition` | Koalitionsvertrag steht | ✅ | ❌ |
| `SPD` | SPDR ETF steigt | ⚠️ false positive | ❌ |
| `AfD` | Schafdorf brennt | ❌ | ❌ |

## Keywords

[`keywords/`](keywords/) holds the German seed-term list, shared with
[news-ground-news](../news-ground-news). See
[news-source-survey/docs/keywords.md](../news-source-survey/docs/keywords.md) for how the
list was built and how it performed.

| file | terms |
|---|---|
| `german_politics.txt` | 30 — parties, institutions, policy, recurring events |
| `german_all.txt` | 86 — the above plus companies, cities, sport, EU, US/geopolitics |
| `german_keywords.json` | machine-readable, with per-term measured yield |

## Pipeline

```bash
# 1. collect (bounded!)
python gdelt_dump_pull.py --start ... --end ... --keywords-file keywords/german_politics.txt

# 2. cluster into cross-outlet stories
python gdelt_cluster_bulk.py --articles <articles.jsonl> --min-outlets 3

# 3. fetch bodies + images from the outlets themselves
python gdelt_enrich_bulk.py
```

| script | what it does |
|---|---|
| `gdelt_dump_pull.py` | **the collector** — raw 15-min GKG dumps, no result cap, back to 2015-02-19 |
| `gdelt_bq_pull.py` | BigQuery alternative; 1 TB/month free sandbox, `Extras` is the expensive column |
| `gdelt_collect.py` | DOC API — **capped at 250 results, no pagination**; probing only, never volume |
| `gdelt_cluster_bulk.py` | greedy title-similarity clustering, day-bucketed, threshold 0.65 |
| `gdelt_enrich_bulk.py` | body/image/caption fetch at scale |
| `gdelt_enrich.py` | same, for small runs |
| `gdelt_german_outlets.py`, `gdelt_retry_probes.py` | outlet discovery |
| `gdelt_event_clustering.py` | ad-hoc clustering probe |

## Known limits

- **No body text, no descriptions.** GKG gives title + URL + themes; bodies need our own
  crawl of the outlets.
- **No bias or stance signal of any kind.**
- **Clustering is ours and it is shallow** — `SequenceMatcher` on titles at 0.65 within a
  day bucket. A story crossing midnight splits into two ids.
- **GKG has no title column.** Titles come from `<PAGE_TITLE>` inside the `Extras` XML —
  dropping `Extras` to save BigQuery quota silently destroys clustering.
- **No outlet-country on the dump route** (the DOC API has `sourcecountry`); stories carry
  `countries: ["?"]`.
- GKG themes are high-recall/low-precision, and `TAX_ETHNICITY_GERMAN` /
  `TAX_WORLDLANGUAGES_GERMAN` are artefacts of the German-language filter, not subjects.
- 🟢 **Upside: metadata is openly licensed** — the only source here we may republish.

Detail: [docs/GDELT_NOTES.md](docs/GDELT_NOTES.md) and the
[provider survey](../news-source-survey/docs/sources.md#gdelt).

## Environment

Needs `gdeltdoc`, `trafilatura` — conda env `scrap2` here.
