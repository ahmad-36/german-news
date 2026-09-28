# Known Problems and Future Directions

**Status:** 🔴 blocking · 🟠 open, has a workaround · 🟡 known and accepted

---

## Blocking

| # | problem | status |
|---|---|---|
| 1 | **Stance labels are per outlet, not per article.** No provider except Ad Fontes rates articles, so a stance model learns the publisher. [experiments §1](experiments.md#1-are-the-stance-labels-per-article-or-per-outlet) | 🔴 |
| 2 | **Event Registry data cannot be published.** The ToS forbid redistribution, including metadata. | 🔴 |
| 3 | **No single provider has bodies, labels and German together.** A join on the 56 shared domains is needed. [sources](sources.md#joining-the-providers) | 🔴 |
| 4 | **Event Registry's free tier is too small for large or historical pulls**; archive access and multilingual pulls need a paid plan. | 🔴 |

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

None of these breaks the schema.

| # | problem | status |
|---|---|---|
| 19 | The article `lang` field uses each source's own code: `de` (Ground News), `deu` (Event Registry), `German` (GDELT), and none for AllSides. It should be normalised to ISO-639-1. | 🟠 |
| 20 | AllSides articles have no `date`; only the story has one. | 🟡 |
| 21 | One AllSides story ID appears twice: AllSides reused the same URL for two fact-check roundups (2025-05-12 and 2025-12-14). | 🟠 |

## Future directions

| direction | what it needs | status |
|---|---|---|
| **Bias / leaning classification** | article-level labels (e.g. Ad Fontes, or annotating the articles where an LLM and the outlet label disagree) | 🔴 blocked on labels |
| **Stance detection** (article + claim → favor / against / neutral), trained as NLI | a human-annotated set; the NLI setup and controls are ready | 🟡 needs annotation |
| **Cross-lingual event clustering**: translate first vs. cluster per language and link vs. multilingual embeddings | a multilingual pull (paid Event Registry plan, or EMM data) and human verification of ~100 clusters | 🟡 German-only comparison done |
| **Summaries and stance comparison** | human references; the only existing ones are GPT-generated (Ground News). Verifying ~100 Ground News stance comparisons is a first step | not started |
| **A German dataset with structure, text and labels** | joining GDELT stories, Event Registry bodies and Ground News outlet labels on the 56 shared domains | not started |
| **Longer GDELT collection** | an agreed date range and topic list; Jan 2025 → now takes about 15 hours | ready to run |

**The common blocker is the lack of human ground truth.** Candidate partners: EMM (EU
cross-lingual news clustering) and Ad Fontes Media (article-level bias ratings).
