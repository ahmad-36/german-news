# Problems, Blocked Tasks and What Is Needed

**Status:** 🔴 blocking · 🟠 open, has a workaround · 🟡 known and accepted · ✅ fixed

---

## Blocking

| # | problem | status |
|---|---|---|
| 1 | **Stance labels are per outlet, not per article.** No provider except Ad Fontes rates articles, so a stance model learns the publisher. [experiments §1](experiments.md#1-are-the-stance-labels-per-article-or-per-outlet) | 🔴 |
| 2 | **Event Registry data cannot be published.** The ToS forbid redistribution, including metadata. | 🔴 |
| 3 | **No single provider has bodies, labels and German together.** A join on the 56 shared domains is needed. [sources](sources.md#joining-the-providers) | 🔴 |
| 4 | **Event Registry has 461 free tokens left** and a 30-day window. A second pull is unaffordable. | 🔴 |

## Data quality

| # | problem | status |
|---|---|---|
| 5 | Ground News translation deletes entities, and its topic tags are computed on the translation. [experiments §4](experiments.md#4-ground-news-translation-deletes-entities) | 🟠 |
| 6 | AllSides inflates articles about 8× (68,352 slots → 8,072 URLs). Deduplicate before counting. | 🟠 |
| 7 | The AllSides eval set is 4.2× duplicated, with leakage between train and test (94.6% → 72.6% after deduplication). | 🟠 |
| 8 | Ground News' three rating agencies disagree on 32.1% of articles; 37.4% of labels are `unknown`. | 🟡 |
| 9 | Event Registry's duplicate flag removes wire stories from events. Local title grouping would recover 51.7% of articles. | 🟠 |
| 10 | GDELT themes are noisy, and some are side effects of our own language filter. | 🟡 |
| 11 | Six Ground News topic-page slugs may be silently empty (bare slug vs hash-suffixed). | 🟠 |
| 12 | Ground News German coverage is limited to the 60 publishers listed in `germanlib.py`. | 🟡 |
| 13 | Event Registry collected zero topics, because the default `returnInfo` excludes them. | 🟠 |

## Coverage and method

| # | problem | status |
|---|---|---|
| 14 | GDELT has no body text or labels. Our crawl has fetched 154,084 bodies for 1.4M articles. | 🟠 |
| 15 | Ground News is tiny (894 stories) and AllSides has no German. | 🟡 |
| 16 | Our GDELT clusterer reaches only 0.45 F1 (recall 0.29), and stories crossing midnight split. | 🟠 |
| 17 | `center` is defined only as the absence of lean, and both classifiers and LLMs fail on it. | 🟠 |
| 18 | Stripping publisher boilerplate cannot remove house style. | 🟡 |

## Data format

Found by validating the unified files on 2026-09-28. None of these breaks the schema.

| # | problem | status |
|---|---|---|
| 19 | The article `lang` field uses each source's own code: `de` (Ground News), `deu` (Event Registry), `German` (GDELT), and none for AllSides. It should be normalised to ISO-639-1. | 🟠 |
| 20 | AllSides articles have no `date`; only the story has one. | 🟡 |
| 21 | One AllSides story ID appears twice: AllSides reused the same URL for two fact-check roundups (2025-05-12 and 2025-12-14). | 🟠 |

## Fixed

| problem | fix |
|---|---|
| GDELT collected as a 172 GB census | ✅ bounded by date range and keyword/theme filter. [keywords_and_apis §5](keywords_and_apis.md#5-bounded-collection-sept-2026) |
| Stale unified files showed 0 GDELT bodies | ✅ rebuilt; 154,084 bodies attached |
| Event Registry was 100% singleton stories in the unified file | ✅ `unify.py` now groups by `eventUri` (2,392 multi-article stories) |
| Four keyword terms returned nothing | ✅ diagnosed; the English replacements are listed in [keywords_and_apis §2](keywords_and_apis.md#2-ground-news) |
| The explorer UI imported the Ground News scraper | ✅ helpers extracted to `germanlib.py` |

---

## Tasks and what blocks them

| task | done so far | blocked by |
|---|---|---|
| Bias / leaning classification | label audit, name-swap test, retraining on unseen outlets, LLM check | 🔴 needs article-level labels |
| Stance detection (article + claim → favor / against / neutral) | task defined; NLI setup and controls planned | 🟡 needs human annotation |
| Event clustering | 6 methods compared on German ER data | 🟡 needs human verification; the cross-lingual version needs a paid ER account |
| Summaries, stance comparison | not started | the only references are GPT-generated (Ground News) |

**The common blocker is the lack of human ground truth.** Two things are small enough to
do alone: judging about 100 Event Registry clusters, and verifying about 100 Ground News
stance comparisons. Article-level stance labels and human-written summaries need
annotators.

## What I need from the supervisor

1. **Scope:** the final date range and topic list, so the long GDELT run is done once
   (about 15 hours for Jan 2025 → now).
2. **Direction:** source-audit write-up, stance comparison with human verification, or
   cross-lingual clustering.
3. **A paid Event Registry account**, needed only for cross-lingual clustering.
4. **Permission to contact** EMM (EU cross-lingual clustering) and Ad Fontes (article-level
   ratings).
5. **Annotators or budget** for human labels.
