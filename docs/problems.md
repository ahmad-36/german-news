# Known Problems

Every problem found so far, in one place. Detail lives in the linked docs — this page is
the register, so nothing gets lost between them.

**Status key:** 🔴 blocking · 🟠 open, works around · 🟡 known, accepted · ✅ fixed

---

## Blocking

| # | Problem | Status | Detail |
|---|---|---|---|
| 1 | **Stance labels are per outlet, not per article.** No provider surveyed rates individual articles. Ground News says so outright: *"The analysis is done at the publication level."* AllSides' audit methodology samples 5–10 headlines and averages them into one overall score for the publication. All 15 AllSides outlets have 100% label purity, so the ground truth **is** publisher identity. This makes stance prediction a mislabelled task. | 🔴 | [stance_labels.md](stance_labels.md) |
| 2 | **Event Registry data cannot be published.** Its ToS forbid sharing or sublicensing and claim even structured metadata. This is the constraint on any public release. | 🔴 | [sources.md](sources.md#event-registry-newsapiai) |
| 3 | **No single provider has bodies + labels + German.** GDELT has structure, Event Registry has text, Ground News has labels, AllSides has neither German nor volume. Everything needs a cross-provider join on the 56 shared domains. | 🔴 | [sources.md](sources.md#cross-provider-joins) |

## Data quality

| # | Problem | Status | Detail |
|---|---|---|---|
| 4 | **Ground News translates before it clusters**, and the translation deletes entities — `Neuer`→"new", `Bayern`→"Bavaria", `USA`→"Us" (96 titles, 2.3%). One Bundesliga cluster ends up tagged "Mohammed Bin Salman". Measured rates are small; the *mechanism* is the finding. | 🟠 | [translation_problem.md](translation_problem.md) |
| 5 | **AllSides inflates articles ~8×** — 68,352 article slots collapse to 8,072 unique URLs, because sidebar articles repeat across story pages. Any per-article statistic computed without deduplicating is wrong. | 🟠 | see #6 · [stance_labels.md](stance_labels.md) |
| 6 | **The AllSides eval set is 4.2× duplicated with train/test leakage.** 11,779 records hold 2,807 distinct texts; 77.9% of records are affected. This inflated the headline TF-IDF result by 22 points (94.6% → 72.6% deduplicated). | 🟠 | [stance_labels.md](stance_labels.md#4-experiment-3--a-correction-the-eval-set-is-42-duplicated) |
| 7 | **Ground News' three rating agencies disagree on 32.1%** of rated articles (MBFC, Ad Fontes, AllSides). Ground News averages them and presents one value. | 🟡 | [stance_labels.md](stance_labels.md) |
| 8 | **37.4% of Ground News bias labels are the literal string `unknown`**, concentrated on exactly the small non-English outlets that make up its German tail. | 🟡 | [sources.md](sources.md#ground-news) |
| 9 | **Event Registry's duplicate flag deletes the best clusters.** Of 59,088 duplicate-flagged articles, exactly 2 carry an `eventUri` — so one dpa wire item carried by 48 independent German outlets is excluded from the event graph. Recoverable by title-clustering locally (51.7% of articles) at zero API cost. | 🟠 | [sources.md](sources.md#event-registry-newsapiai) |
| 10 | **Ground News misidentifies languages** — `rtl.lu` publishes Luxembourgish, tagged `de`, so the translator passes it through untranslated and it shares no content words with its own cluster. | 🟡 | [translation_problem.md](translation_problem.md) |
| 11 | **GDELT themes are noisy.** `TAX_ETHNICITY_GERMAN` and `TAX_WORLDLANGUAGES_GERMAN` are artefacts of our own German-language filter, not subjects; `ALLIANCE` fires on 183% of political articles. Usable as features, not as topics. | 🟡 | [collection_policy.md](collection_policy.md#2b-which-gkg-themes-to-filter-on) |
| 11b | **Six of the 17 Ground News topic pages may be silently empty.** The crawl list uses bare slugs (`us-politics`, `crime`, `energy`, `law`, `media`), but the scraped data only ever contains hash-suffixed variants (`us-politics_3c3c3c`, …); `world` never appears at all. One of the seventeen (`education_fb8947`) *is* suffixed, so the list is internally inconsistent. Unverified — needs one manual check. | 🟠 | [keywords.md](keywords.md#1-what-we-used) |
| 11c | **German coverage is capped by a 60-name publisher register.** Neither the Ground News topic pages nor the search filter by language — German is decided afterwards by matching the publisher against `germanlib.py`. Nothing outside those 60 names counts as German, however German it is. | 🟡 | `news-ground-news/germanlib.py` |
| 12 | **`sueddeutsche.de` returns ~300-char teasers** (`private: true`) despite being Event Registry's 5th largest source. | 🟡 | [sources.md](sources.md#event-registry-newsapiai) |

## Coverage and cost

| # | Problem | Status | Detail |
|---|---|---|---|
| 13 | **GDELT has no body text and no bias signal.** Bodies require our own second crawl of the outlets; 154,084 fetched so far of 1.4M articles. | 🟠 | [sources.md](sources.md#gdelt) |
| 14 | **Ground News is tiny** — 894 stories in ~14 months (~2/day), no bodies, no images, only 12.1% German. A label source, not a corpus. | 🟡 | [sources.md](sources.md#ground-news) |
| 15 | **AllSides is US-only** — zero German articles, and no amount of scraping changes that. | 🟡 | [sources.md](sources.md#allsides) |
| 16 | **Event Registry: 461 free tokens left**, 30-day recency window, archive costs 5 tokens/year. A second 7-day pull is unaffordable. | 🔴 | [api_filters.md](api_filters.md#cost) |
| 17 | **Event Registry collected zero topics** — the default `returnInfo` excludes concepts and categories. A scraper defect, but fixing it costs tokens we don't have. | 🟠 | [api_filters.md](api_filters.md#three-we-should-be-using-and-are-not) |
| 18 | **No publisher country on the GDELT dump route**, so all 173,388 stories carry `countries: ["?"]`. The DOC API has it, but the DOC API is unusable for volume. | 🟡 | [api_filters.md](api_filters.md#what-gdelt-cannot-filter-on) |

## Method

| # | Problem | Status | Detail |
|---|---|---|---|
| 19 | **GDELT clustering is ours and it is shallow** — `SequenceMatcher` on titles at 0.65 within a day bucket. Two outlets rewriting an event under different headlines never merge; a story crossing midnight splits into two ids. | 🟠 | [sources.md](sources.md#gdelt) |
| 20 | **The `center` class is negatively defined** and collapses. It means "absence of lean", for which no positive lexical markers exist. An LLM disagrees with the label on 78.3% of center-rated articles vs 32.0% of right-rated ones. | 🟠 | [stance_labels.md](stance_labels.md#3-experiment-2--the-outlier-check-how-often-does-an-llm-disagree-with-the-label) |
| 21 | **Publisher boilerplate cannot be scrubbed out.** Deleting 9% of every character in the corpus moved the random split 1.2 points. What remains is house style and naming convention (`donald trump` vs `president trump`). | 🟡 | [stance_labels.md](stance_labels.md#5-experiment-4--earlier-results-in-context) |
| 22 | **`strip_publisher` injected its own artifact** — substituting the constant `"the news outlet"` let the *count* of that token re-identify the outlet. Delete names rather than substitute. | 🟠 | [stance_labels.md](stance_labels.md#5-experiment-4--earlier-results-in-context) |

## Fixed

| # | Problem | Fixed |
|---|---|---|
| 23 | **GDELT was being collected as a census** — 172 GB for 1.4M articles with no text or labels, 91% discarded after collection. | ✅ Sept 2026 — bounded by date range + keyword/theme filter. One week = 4,220 articles → 273 stories in ~10 min. [collection_policy.md](collection_policy.md) |
| 24 | **The unified files were stale**, predating the GDELT enrichment, so the UI showed 0 GDELT bodies. | ✅ Sept 2026 — rebuilt; 154,084 bodies now attached. Old files archived, not deleted. |
| 25 | **Four keyword terms returned nothing**, and four more under-performed — all generic German compounds where the English form was needed. | ✅ Diagnosed; fixes listed. [keywords.md](keywords.md#2-how-we-picked-them) |
| 26 | **The explorer UI imported the Ground News scraper** for two helpers, coupling the repos. | ✅ Sept 2026 — extracted to `germanlib.py`. |

---

## The three that would change the plan if solved

1. **Article-level labels** (#1). Ad Fontes is the only provider offering them — ≥3 human
   analysts per article, −42…+42 scale. Everything about stance prediction is blocked on
   this. [other_sources.md](other_sources.md)
2. **German full text we may republish** (#2, #13). CC-NEWS is the obvious candidate:
   openly licensed, multilingual, full HTML.
3. **Cluster-then-translate instead of translate-then-cluster** (#4). This is the
   architecture the JRC's Europe Media Monitor uses today across 80 languages, and it is a
   directly testable claim for a paper.
