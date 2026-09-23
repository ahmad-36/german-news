# Multi-Perspective News Sources — Provider Survey

A decision document for building a **German-language, multi-perspective news dataset**:
what each candidate provider actually gives you, how you get it out, where it breaks,
and how each one maps onto the processing pipeline we want to run.

Four providers are covered in depth — **AllSides**, **Ground News**, **GDELT**, and
**Event Registry** — plus a survey of [nine further providers](docs/other_sources.md)
that were not previously considered.

Every number in this repo was measured directly against the data on disk
(~7.3 GB, collected Jan–Aug 2026) rather than taken from provider marketing. This repo is
the written analysis; the collection code lives in one repo per source:

| repo | what it collects |
|---|---|
| [muws-allsides-dataset](https://github.com/muws-workshop/muws-allsides-dataset) | AllSides |
| [news-gdelt](../news-gdelt) | GDELT — collection, clustering, enrichment |
| [news-ground-news](../news-ground-news) | Ground News — scraper, discovery, keyword list |
| [news-eventregistry](../news-eventregistry) | Event Registry |
| [news-explorer](../news-explorer) | unified format + Streamlit UI (cross-source) |

All share one data root via `NEWS_DATA_DIR`. They were split out of a single `news` repo
in Sept 2026, which is now retired to `archive/`.

---

## Start here

| Document | What it answers |
|---|---|
| **[Comparison table](#the-comparison-table)** (below) | Side-by-side: method, content, labels, images, limits |
| [docs/sources.md](docs/sources.md) | Per provider: how scraping works, what you get, what the limits are |
| [docs/pipeline.md](docs/pipeline.md) | The pipeline diagram, and how each provider performs each step |
| [docs/tasks.md](docs/tasks.md) | The five downstream tasks, defined separately |
| [docs/stance_labels.md](docs/stance_labels.md) | Where stance labels come from, and our experiments on them |
| [docs/translation_problem.md](docs/translation_problem.md) | Ground News mistranslation → wrong clustering (paper-worthy) |
| [docs/api_filters.md](docs/api_filters.md) | Exactly which filters GDELT and Event Registry expose |
| [docs/other_sources.md](docs/other_sources.md) | Nine providers beyond the four |
| [docs/keywords.md](docs/keywords.md) | The German keyword list, how it performed, how to extend it |
| [docs/collection_policy.md](docs/collection_policy.md) | Why collection is now bounded, and a measured one-week test |

---

## Three findings that should change the plan

**1. AllSides and Ground News stance labels are outlet-level, not article-level.**
Ground News states it outright: *"This rating does not measure the bias of specific news
articles. The analysis is done at the publication level."* In our AllSides eval set, all
15 outlets have **100% label purity** — every Fox News article is `right`, every Hill
article is `center`. Training a stance classifier on this predicts the *publisher*, not
the article. A bag of bigrams reaches **94.6%** on a random split and **27.3%** when test
outlets are held out — below the 46.8% majority baseline. Details and the full experiment
set: [docs/stance_labels.md](docs/stance_labels.md).

**2. Ground News labels are not GPT-generated — but a third of them are contested.**
The bias ratings are aggregated from three human rating agencies (Media Bias/Fact Check,
Ad Fontes Media, AllSides). Across 28,833 rated articles the three raters **disagree on
32.1%**. What *is* machine-generated on a Ground News page are the per-stance summaries,
the `bias_comparison` paragraph and the `generated_headline` — not the labels.

**3. Ground News translates before it clusters, and the translation destroys entities.**
41% of its articles (18,969 / 46,030) are machine-translated into English, and clustering
runs on the translation. In one Bundesliga cluster, goalkeeper *Manuel **Neuer*** is
translated into the adjective "new", *FC **Bayern*** becomes the state of "Bavaria", *Tor*
(goal) becomes "Gate" — and the cluster ends up tagged with the topic **"Mohammed Bin
Salman"**. The most frequent defect is `USA`/`US-` collapsing into the English stopword
"Us" (96 of 4,167 distinct German titles, 2.3%). The measured rates are small; the
*mechanism* is the finding. Worked example:
[docs/translation_problem.md](docs/translation_problem.md).

---

## The comparison table

### Rating legend

| | Meaning |
|---|---|
| 🟢 | **Present and usable as-is** — authoritative, well-populated |
| 🟡 | **Present but caveated** — AI-generated, derived, sparse, or not what the field name suggests |
| 🟠 | **Not provided, but obtainable** — recoverable with work we have specified and costed |
| 🔴 | **Absent** — not available from this provider at all |

Yellow is the important cell colour: it marks a field that *exists* and will pass a
schema check, but that you cannot cite as ground truth. Read the note in every 🟡 cell.

### A. Scale and shape

| | **AllSides** | **Ground News** | **GDELT** | **Event Registry** |
|---|---|---|---|---|
| **What one record is** | one editorially-curated story page | one curated story (event + N outlets) | one title-similarity cluster *we* build | one article (flat feed) |
| Stories | 1,919 | 894 | 173,388 | 129,628 |
| Articles | 68,352 *(8,072 unique URLs)* | 46,030 | 1,408,753 | 129,628 |
| Median outlets/story | 22 | 16 | 5 | **1** |
| German articles | 0 | 5,563 (12.1%) | **1,408,753 (100%)** | 129,628 (100%) |
| Time span held | 2025-01 → 2026-05 | 2025-05 → 2026-08 | 2026-01 → 2026-08 | 2026-07-30 → 2026-08-07 |
| Unique domains | 353 | 5,477 | 474 | 320 |

### B. Scraping method — how you actually get the data

| | **AllSides** | **Ground News** | **GDELT** | **Event Registry** |
|---|---|---|---|---|
| **Access route** | HTML scrape (no API) | HTML/JSON scrape (no public API) | open bulk dumps + BigQuery + DOC API | authenticated REST API |
| **Primary axis** | 🟢 **by date** — `--start`/`--end` over roundup pages | 🟡 **by trending** — homepage/`/top`/`/blindspot`/`/interest/<topic>` | 🟢 **by date** — every 15-min dump since 2015-02-19 | 🟢 **by date + language** — paginated window |
| **By topic** | 🟡 topic is a story attribute, not a crawl axis | 🟢 ~20 `/interest/<topic>` pages | 🟢 `theme:` (GKG themes) | 🟢 `categoryUri` / `conceptUri` |
| **By keyword** | 🔴 no search endpoint | 🟢 `--query "ukraine"` subject search | 🟢 full boolean + `near`/`repeat` | 🟢 `keywords` + `keywordsLoc` |
| **Historical backfill** | 🟢 native — date range is the interface | 🟠 Wayback Machine replay, best-effort | 🟢 native to 2015 | 🔴 **30-day window**; archive costs 5 tokens/year |
| **Anti-bot posture** | plain requests | 🟡 needs `curl_cffi` Chrome impersonation | none (static files) | none (API key) |
| **Rate/volume ceiling** | politeness only | politeness only | bandwidth (172 GB for Jan–Aug) | 🔴 **2,000 non-renewing tokens; 461 left** |
| Full filter reference | — | — | [docs/api_filters.md](docs/api_filters.md) | [docs/api_filters.md](docs/api_filters.md) |

### C. Available content — what lands in the record

| | **AllSides** | **Ground News** | **GDELT** | **Event Registry** |
|---|---|---|---|---|
| Headline | 🟢 100% | 🟢 100% | 🟢 100% | 🟢 100% |
| URL | 🟢 | 🟢 | 🟢 | 🟢 |
| **Full body text** | 🟡 **17.3%** (11,838) via per-domain scrapers | 🔴 **0%** — headline + dek only | 🟠 **0% native**; 154,084 fetched by our own crawl (11% of articles) | 🟢 **100%**, median 2,111 chars |
| Description / lede | 🟢 99.4% | 🟢 98.1% (real editorial dek) | 🔴 0% | 🟡 100% but *derived* — first lines of body |
| **Images** | 🟢 **68.9%** image URL (47,122); local download supported | 🔴 **no image field at all** | 🟠 67.9% of *enriched* pages (145,078) via `og:image` | 🟢 **98.6%** image URL |
| **Image captions** | 🔴 | 🔴 | 🟠 41.7% of enriched (88,992) | 🔴 URL only, no caption |
| Story summary | 🟢 100% editorial | 🟡 99.7% — **LLM-generated** | 🔴 | 🟡 derived, not a real summary |
| **Per-stance summaries** | 🔴 | 🟡 **49.3%** (441/894) — **LLM-generated**; `summary_right` often empty | 🔴 | 🔴 |
| Bias-comparison paragraph | 🔴 | 🟡 **LLM-generated** | 🔴 | 🔴 |
| Blindspot flag | 🔴 | 🟢 89 stories | 🔴 | 🔴 |
| Topics | 🟢 100% human labels | 🟢 99.8% human labels | 🟡 100% GKG themes — machine, high recall / low precision | 🔴 **not collected** (default `returnInfo`); recoverable |
| Language tag | 🔴 absent | 🟡 ISO-2, **misassigns Luxembourgish as `de`** | 🟢 | 🟢 `deu` |
| Outlet country | 🔴 | 🟢 per-source place | 🟡 DOC API only; bulk route gives `"?"` | 🟢 |
| Paywall flag | 🔴 | 🟢 5,270 flagged | 🔴 | 🟡 `private: true` → 300-char teasers |
| Authors | 🔴 | 🔴 | 🔴 | 🟢 |

### D. Labels — the decisive row

| | **AllSides** | **Ground News** | **GDELT** | **Event Registry** |
|---|---|---|---|---|
| **Stance label present** | 🟢 99.9% (68,290) | 🟡 62.6% (28,833) — **37.4% literally `unknown`** | 🔴 none | 🔴 none |
| **Granularity** | 🟡 **per outlet, not per article** | 🟡 **per outlet** (provider states this explicitly) | — | — |
| **Who assigns it** | 🟢 trained human panels + blind surveys | 🟡 **aggregate of 3 agencies** (MBFC, Ad Fontes, AllSides) | — | — |
| **Inter-rater agreement** | n/a (single rater) | 🔴 **raters disagree on 32.1%** (9,244/28,833) | — | — |
| Scale | 🟢 7-point | 🟢 7-point incl. `farLeft`/`farRight` | — | — |
| Factuality rating | 🔴 | 🔴 field exists, **0% populated** | 🔴 | 🔴 |
| Label purity per outlet | 🔴 **100%** — label ≡ publisher identity | 🔴 100% by construction | — | — |

> **Read row "Granularity" together with [docs/stance_labels.md](docs/stance_labels.md).**
> No provider here offers article-level stance. The only provider that does is
> **Ad Fontes Media**, which rates individual articles with panels of ≥3 human analysts
> of mixed political self-identification — see [docs/other_sources.md](docs/other_sources.md).

### E. Limits and blockers

| | **AllSides** | **Ground News** | **GDELT** | **Event Registry** |
|---|---|---|---|---|
| **Hard blocker** | US-only — **zero German** | tiny: 894 stories in 14 months (~2/day) | no bodies, no bias signal | 🔴 **redistribution prohibited by ToS** |
| Cost | free (scraped) | free (scraped) | free | 2,000 tokens, **461 remaining** |
| Redistributable | 🟡 scraped — usual caveats | 🟡 scraped — usual caveats | 🟢 **metadata openly licensed** | 🔴 **no** — ToS claims metadata too |
| Article-count inflation | 🔴 ~8× (68,352 slots → 8,072 URLs) | 🟢 none | 🟢 none | 🟢 none |
| Clustering quality | 🟢 editorial | 🟡 editorial, but **on translated text** | 🟡 ours: `SequenceMatcher` @ 0.65, day-bucketed | 🔴 **100% singletons**; `eventUri` null on 83.5% |
| Other notable limits | `is_featured:false` articles come from sidebars and may be off-story | 37.4% `unknown` labels concentrate on the German tail | midnight split; section-front junk; `Extras` column needed for titles | duplicate flag deletes exactly the wire stories carried by 48 outlets |

### F. One-line verdict

| Provider | Verdict |
|---|---|
| **GDELT** | The only source of **German multi-outlet story structure at scale**, and the only one we may republish. No text, no labels. |
| **Event Registry** | The only source of **clean full German bodies**. Not a story dataset, and legally unpublishable. |
| **Ground News** | The only source of **stance labels, per-stance summaries and blindspots**. Too small to be a corpus; valuable as a label/eval set. |
| **AllSides** | Best **story structure + human topics**, richest per-story outlet count. Contributes nothing German. |

They are complements, not alternatives: **GDELT gives the structure, Event Registry gives
the text, Ground News gives the labels, AllSides gives the template.**

---

## Collection is now bounded

The Jan–Aug 2026 GDELT census cost **172 GB of bandwidth** for 1.4M articles with no text
and no labels, 91% of which was discarded after collection. GDELT collection now defaults
to **a short date range plus a topic or keyword filter**.

Measured on one week (2026-01-05 → 01-12) with the 30-term German-politics list:
**4,220 articles kept of 127,705 seen (3.3%)** → **273 stories with 3+ independent
outlets**, median 4 outlets per story, max 48 — in about **10 minutes**.

Details, including what a Jan-2025-onward range would cost:
[docs/collection_policy.md](docs/collection_policy.md).

## Recommended next moves

1. **Stop treating outlet-level ratings as article stance.** Either reframe the task as
   *outlet identification* (honest, and the numbers are strong), or acquire article-level
   labels. Ad Fontes is the only provider offering them.
2. **Re-run `unify.py`.** The GDELT enrichment file has grown from 11,899 records to
   **213,532** (154,084 bodies, 145,078 images) since the unified files were built. Those
   bodies and images are on disk and currently unattached.
3. **Add title-clustering to Event Registry ingestion.** Grouping the raw file by
   normalised title turns 67,005 of 129,628 articles (51.7%) into multi-source stories at
   zero API cost — ~8× more than its own `eventUri` surfaces.
4. **Join on the 56 shared domains** (GDELT ∩ ER ∩ Ground News). That is the only path to
   a German dataset with structure, text and labels simultaneously.
5. **Do not spend the remaining 461 Event Registry tokens on more articles.** If spent at
   all, spend them enabling `concepts`/`categories`/`storyUri` on a small pull.
6. **Evaluate Ad Fontes and Media Cloud** before committing to the current four.
