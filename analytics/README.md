# News Sources for a German Multi-Perspective Dataset: Analysis

The written analysis for building a **German-language, multi-perspective news dataset**:
which providers exist, what each actually delivers, which keywords and API filters were
used, and what the experiments on the data found. Every number was measured on the data
on disk (Jan–Aug 2026), not taken from provider documentation.

This folder holds only the write-up and three small reproduction scripts. The code and data
for each source are in the sibling folders of the same repository:

| folder | role |
|---|---|
| [`gdelt/`](../gdelt) | GDELT: bounded dump pull → title clustering → body/image enrichment |
| [`ground-news/`](../ground-news) | Ground News: topic-page crawl, keyword search, German discovery |
| [`eventregistry/`](../eventregistry) | Event Registry: REST pull of German articles, plus the clustering evaluation |
| [`ui/`](../ui) | unifies all four sources into one format, plus a Streamlit explorer |
| `muws-allsides-dataset` (separate repo) | AllSides: roundup crawler, per-outlet scrapers, stance experiments |

## Documents

| document | what it answers |
|---|---|
| [docs/sources.md](docs/sources.md) | Per provider: how to collect, what you get, limits, images. Also ten other providers |
| [docs/keywords_and_apis.md](docs/keywords_and_apis.md) | The keywords and topic pages used, GDELT / Event Registry filters, bounded collection |
| [docs/experiments.md](docs/experiments.md) | Stance-label audit, publisher-name swap test, LLM outlier check, translation audit, clustering evaluation |
| [docs/problems.md](docs/problems.md) | Every known problem with its status, plus what is blocked and what I need |

## Main findings

1. **Stance labels are per outlet, not per article.** AllSides and Ground News give every
   article its publisher's rating. All 15 outlets in the AllSides eval set have 100% label
   purity. A classifier trained on these labels learns the publisher: deduplicated, it gets
   72.6% on a random split but **30.9% on unseen outlets**, the same as that split's 28.1%
   majority baseline.
2. **Classifiers read the publisher's name.** Replacing the outlet name with an
   opposite-side outlet moves the prediction **+24 points** toward that side. The effect is
   asymmetric: inserting "Fox News" into centre articles moves them +51 toward right, while
   inserting "Politico" moves them only +20 toward left.
3. **An LLM agrees with the outlet label on only 50% of articles.** Fox News is the *most*
   consistent outlet (29% disagreement), and `center` articles are almost never predicted
   as centre (78% disagreement).
4. **Ground News' machine translation deletes entities** (*Neuer* → "new", *Bayern* →
   "Bavaria", *USA* → "Us"), and its topic tags are computed from the damaged text. Its
   clustering method is undocumented.
5. **Clustering (German, scored against Event Registry's event IDs):** BGE-M3 on full
   bodies reaches **0.79 F1** and TF-IDF on title + lede ties it. Our production GDELT
   clusterer scores **0.45**, missing about two-thirds of same-event pairs.
6. **Collection is now bounded.** One keyword-filtered GDELT week gives **273** German
   political stories with 3+ outlets in about 10 minutes, instead of a 172 GB census.

## The four providers at a glance

| | **GDELT** | **Event Registry** | **Ground News** | **AllSides** |
|---|---|---|---|---|
| Access | open bulk dumps | REST API (key) | scraped | scraped |
| Collected by | date + keyword/theme | date + language | trending pages + keyword | date |
| Stories / articles | 173,388 / 1,408,753 | 110,941 / 129,628 | 894 / 46,030 | 1,919 / 68,352 (8,072 unique) |
| German | 100% | 100% | 12.1% | 0% |
| Body text | 154,084 (our crawl) | 100% | none | 17.3% |
| Images | 145,078 URLs (our crawl) | 98.6% URLs | none | 10,716 files on disk |
| Stance label | none | none | 62.6%, per outlet | 99.9%, per outlet |
| Clustering | ours (title similarity) | ER `eventUri`, 16.5% of articles | theirs, undocumented | editorial |
| May republish | ✅ | ❌ ToS forbids | ⚠️ scraped | ⚠️ scraped |

**They complement each other:** GDELT gives story structure, Event Registry gives text,
Ground News gives labels and AllSides gives the template. The only way to get all three
for German news is to join them on the **56 domains** that appear in GDELT, Event Registry
and Ground News.

## Unified data format

The `ui/` folder converts all four sources into one JSONL schema: one line per **story**,
holding a list of **articles**, each with `stance` (left / center / right / unknown) and a
7-point `bias_rating`. The schema is in [`ui/unify/unify.py`](../ui/unify/unify.py). The current files were checked
on 2026-09-28: all 287,142 stories parse, have every field, and use only allowed values.
Three small inconsistencies remain (see [problems #19–21](docs/problems.md#data-format)):
language codes differ by source, AllSides articles have no date, and one AllSides story ID
appears twice. Data is never committed; each folder keeps it in a gitignored `data/` folder.

## Scripts

[scripts/](scripts/) reproduces three measurements: the translation audit, the LLM outlier
check and the deduplication impact. See [scripts/README.md](scripts/README.md).
