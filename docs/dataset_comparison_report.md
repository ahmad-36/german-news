# Dataset comparison report — Event Registry vs Ground News vs GDELT

Comprehensive comparison of every collection strategy in this repo, measured directly
against the files on disk on **2026-08-11**. AllSides is included as a fourth column
throughout because it sits in the same unified format, but it is US-only and
contributes nothing German.

Regenerate the base numbers with:

```bash
python3 unify/unify.py && python3 unify/analytics.py --markdown --json
```

> Supersedes the GDELT figures in `docs/german_news_strategy_comparison.md` and in
> `data/unified/analytics.md`, both of which still describe the 654-story DOC-API pull.

---

## 1. Executive summary

| | Event Registry | Ground News | GDELT | AllSides |
|---|---|---|---|---|
| **What one record is** | one article | one editorially-curated story | one title-similarity cluster we build | one AllSides "story" page |
| **Stories** | 129,628 | 894 | 173,388 | 1,919 |
| **Articles** | 129,628 | 46,030 | 1,408,753 | 68,352 |
| **Median related articles/story** | **0** | **15** | **4** | 32 |
| **German articles** | 129,628 (100%) | 5,563 (12.1%) | 1,408,753 (100%) | 0 |
| **Full body text** | ✅ 100% | ❌ 0% | ⚠️ 11,899 fetched, not merged | ⚠️ 17.3% |
| **Left/center/right labels** | ❌ | ✅ 62.6% | ❌ | ✅ 99.9% |
| **Per-side summaries** | ❌ | ✅ 441 stories | ❌ | ❌ |
| **Unique providers** | 320 | 5,477 | 474 | 353 |
| **Cost / limit** | 2,000 non-renewing tokens, **461 left** | free, polite scraping | free, bandwidth-bound | free, scraped |
| **Redistributable** | ❌ ToS forbids | ⚠️ scraped | ✅ metadata open | ⚠️ scraped |

**The one-line verdict per strategy:**

- **Event Registry** — the only source of clean full German bodies, but it is a *flat
  article feed*, not a story dataset, and you cannot legally publish it.
- **Ground News** — the only source of bias labels, per-side summaries and blindspots,
  but tiny (894 stories) and only 12% German.
- **GDELT** — by far the largest German story corpus with real cross-outlet clusters,
  but zero bodies and zero bias signal out of the box.

They are complements, not alternatives: GDELT gives the story structure, Event Registry
gives the text, Ground News gives the labels.

---

## 2. Dataset size and files on disk

### Unified layer (`data/unified/`)

| strategy | file | size | stories | articles | unique URLs |
|---|---|---|---|---|---|
| eventregistry | `unified_eventregistry.jsonl` | 687.5 MB | 129,628 | 129,628 | 129,624 |
| ground_news | `unified_ground_news.jsonl` | 59.0 MB | 894 | 46,030 | 45,601 |
| gdelt | `unified_gdelt.jsonl` | 971.6 MB | 173,388 | 1,408,753 | 1,408,753 |
| allsides | `unified_allsides.jsonl` | 135.5 MB | 1,919 | 68,352 | **8,072** |
| **all** | `unified_all.jsonl` | 1.81 GB | 305,829 | 1,652,763 | — |

> AllSides: 68,352 article slots but only 8,072 distinct URLs — the same article is
> reused across many story pages via the "More from the Left/Center/Right" sidebars.
> Combined with the `is_featured` caveat, treat its article count as inflated ~8×.

### Raw layer

| strategy | file | size | records |
|---|---|---|---|
| eventregistry | `data/eventregistry/articles_germany.jsonl` | 440.2 MB | 129,628 articles |
| ground_news | `data/ground_news/ground_news.jsonl` | 50.9 MB | 894 stories |
| gdelt | `data/gdelt/gdelt_articles_de.jsonl` | 4.16 GB | 3,835,367 articles |
| gdelt | `data/gdelt/gdelt_stories_de.jsonl` | 4.75 GB | 2,015,373 stories (all sizes) |
| gdelt | `data/gdelt/gdelt_stories_de_min3.jsonl` | 1.77 GB | 173,388 stories (3+ outlets) |
| gdelt | `data/gdelt/gdelt_enrichment_de.jsonl` | 56.2 MB | 14,320 fetched pages |

### Time coverage

| strategy | range | shape |
|---|---|---|
| eventregistry | 2026-07-30 → 2026-08-07 | one 7-day pull; peak 24,285 articles/day |
| ground_news | 2025-05-29 → 2026-08-06 | sparse, ~2 stories/day |
| gdelt | 2026-01-01 → 2026-08-01 | flat census, 22.9k–27.6k stories/month |
| allsides | 2025-01-24 → 2026-05-15 | ~4 stories/day |

601 Event Registry articles carry a `dateTimePub` before 2026-07 (min `2014-01-27`) —
stale publisher timestamps on re-published pages, not archive access. Filter on
`dateTime` (crawl time) rather than `dateTimePub` if you need a clean window.

---

## 3. Field availability — what each method actually gives you

| field | Event Registry | Ground News | GDELT | AllSides |
|---|---|---|---|---|
| headline | ✅ 100% | ✅ 100% | ✅ 100% | ✅ 100% |
| URL | ✅ | ✅ | ✅ | ✅ |
| **body text** | ✅ **129,628 (100%)**, median 2,111 chars | ❌ 0 | ❌ 0 in unified · 11,899 in enrichment file | ⚠️ 11,838 (17.3%), median 3,993 chars |
| description / lede | ✅ 100% (derived from body) | ✅ 98.1% (real dek) | ❌ 0% | ✅ 99.4% |
| **story summary** | ⚠️ 100% but **derived** — `lede(body)`, not a real summary | ✅ 99.7% real editorial summary | ❌ 0% | ✅ 100% |
| **per-stance summaries** (left/center/right) | ❌ | ✅ **441 / 894 stories (49.3%)** | ❌ | ❌ |
| bias comparison paragraph | ❌ | ✅ | ❌ | ❌ |
| blindspot flag | ❌ | ✅ 89 stories | ❌ | ❌ |
| **stance left/center/right** | ❌ | ✅ 28,833 / 46,030 (62.6%) | ❌ | ✅ 68,290 / 68,352 (99.9%) |
| fine-grained bias rating | ❌ | ✅ 7-point | ❌ | ✅ 7-point |
| bias distribution per story | ❌ | ✅ 894 (100%) | ❌ | ❌ |
| factuality rating | ❌ | ⚠️ key present, **0% populated** in this dump | ❌ | ❌ |
| topics | ❌ **none requested** | ✅ 99.8%, human labels | ✅ 100%, GKG V2Themes | ✅ 100%, human labels |
| language tag | ✅ `deu` | ✅ ISO-2 | ✅ `German` | ❌ absent |
| paywall flag | ❌ | ✅ 5,270 flagged | ❌ | ❌ |
| image | ✅ URL, no caption | ❌ | ⚠️ via enrichment (og:image + caption) | ✅ |
| authors | ✅ | ❌ | ❌ | ❌ |
| sentiment | ⚠️ field present, always `null` for German | ❌ | ❌ | ❌ |

### Bias-label detail

**Ground News** — 46,030 articles, all carry a `source_bias` value, but 37.4% of it is
the literal string `unknown`:

| rating | articles |
|---|---|
| unknown | 17,197 (37.4%) |
| center | 12,089 |
| leanLeft | 8,308 |
| leanRight | 5,962 |
| right | 1,450 |
| left | 615 |
| farRight | 361 |
| farLeft | 48 |

Skewed centre-and-lean; the poles are 2.3% combined. `unknown` concentrates on the long
tail of small/non-English outlets — which is exactly where the German publishers live.

**AllSides** — balanced by construction (left 22,967 / center 22,669 / right 22,716),
which is a design artefact of the three-column layout, not a property of the news.

### Body text — the GDELT gap is closeable today

`data/gdelt/gdelt_enrichment_de.jsonl` (written 2026-08-11 05:50) already holds **11,899
fetched bodies + 11,899 summaries**, 0 truncated. `unified_gdelt.jsonl` was built
2026-08-09 03:38, *before* that file existed, so `unify.py` merged nothing. Re-running
`unify.py` attaches them. Note the join in
[unify.py:282-295](../unify/unify.py#L282-L295) matches enrichment to **one** article per
story by exact URL — so 11,899 bodies land on at most 11,899 of 173,388 stories (6.9%),
one article each.

---

## 4. Clustering — how each method groups articles into stories

| | Event Registry | Ground News | GDELT | AllSides |
|---|---|---|---|---|
| mechanism | ER's own event pipeline (`eventUri`) — **discarded by `unify.py`** | editorial + vendor pipeline | ours: greedy title similarity | AllSides editorial |
| articles/story median | **1** | **16** | **5** | 33 |
| articles/story mean | 1.00 | 51.49 | 8.12 | 35.62 |
| articles/story max | 1 | 1,166 | 109 | 48 |
| **median related articles** | **0** | **15** | **4** | 32 |
| distinct outlets/story median | 1 | 16 | 5 | 22 |
| single-article stories | **129,628 (100%)** | 0 | 0 | 0 |

### Story-size distribution

| articles per story | eventregistry | ground_news | gdelt | allsides |
|---|---|---|---|---|
| 1 | 129,628 | 0 | 0 | 0 |
| 2–4 | 0 | 134 | 71,492 | 0 |
| 5–9 | 0 | 178 | 55,017 | 0 |
| 10–24 | 0 | 229 | 39,788 | 0 |
| 25–49 | 0 | 141 | 6,414 | 1,919 |
| 50+ | 0 | 212 | 677 | 0 |

### GDELT clustering internals

[`gdelt_cluster_bulk.py`](../scrapers/gdelt/gdelt_cluster_bulk.py) — greedy single-pass
clustering, bucketed by day, blocked on a rare-token inverted index, similarity =
`SequenceMatcher` ratio over normalized titles, **threshold 0.65**, `--min-outlets 3`
for the delivered file. Domains belonging to the same media group (Ippen: merkur.de,
tz.de, hna.de, come-on.de, fnp.de, op-online.de, kreiszeitung.de, fr.de, …) collapse to
one outlet before the min-outlets test, so syndication does not fake breadth.

Result: `n_outlets` median 4, mean 6.43, max 77; **3,811 stories reached 30+ independent
outlets**. That last figure is the headline asset of the whole repo — nothing else here
produces multi-outlet German story clusters at that scale.

Known weakness: day-bucketing means a story spanning midnight splits into two story_ids,
and a 0.65 title threshold merges near-identical *recurring* headlines within a day
(weather, market wraps).

### Event Registry clustering — the 80%+ singleton problem, quantified

The raw file **does** carry an `eventUri`; `convert_eventregistry`
([unify.py:330-379](../unify/unify.py#L330-L379)) emits one story per article and drops
it. But even in the raw file it is sparse:

| | count | share |
|---|---|---|
| articles with non-null `eventUri` | 21,416 | 16.5% |
| distinct events | 2,729 | |
| events with ≥2 distinct sources | 2,370 | |
| articles inside multi-source events | 20,905 | |
| event size median / max | 5 / 292 | |

**Why 83.5% is null — the duplicate flag is the mechanism.** Of 59,088 articles flagged
`isDuplicate: true`, exactly **2** carry an `eventUri`. ER routes duplicates to an
original instead of into an event. Restricted to the 70,540 non-duplicate articles,
clustering coverage is **30.4%**.

And the duplicate flag fires *across distributors*, which is the damaging part:

- **6,164 of 14,830** distinct duplicate-flagged titles appear at **≥2 different
  domains** — up to **48 domains** for a single dpa wire item
  (`Mehr Drohnensichtungen an deutschen Flughäfen`, 48 outlets;
  `Innenminister Dobrindt verlängert Grenzkontrollen`, 47 outlets).
- `sim` mean is 0.024 for duplicate-flagged vs 0.228 for the rest, and **57,211 of
  59,088** duplicates have `sim == 0` — the flag is a lexical near-identity decision
  made without regard to whether the publishers are independent.

So the exact cases you would most want as a cluster — one wire story carried by 48
independent German outlets — are the cases ER deletes from its event graph.

**Recoverable signal.** Grouping the raw file by normalized title yields **9,678 titles
appearing at ≥2 distinct domains, covering 67,005 articles (51.7% of the file)**, median
4 and max 61 articles per cluster. Only 7,654 of those articles currently carry an
`eventUri` — i.e. title-clustering recovers roughly **8× more clustered articles** than
ER's own event field surfaces. Zero API cost; the data is already local.

**Cross-lingual loss.** Event IDs are language-anchored. Of 2,729 events:
`deu` 2,469, `eng` 182, `spa` 26, `fra` 17, `rus` 16, `por` 8, `ita` 6, `ukr` 3, `tur` 2.
So ~9.5% of events are anchored in a non-German language and we hold only their German
tail — the pull sets `lang="deu"`, so any English/French/Spanish article covering the
same event was never requested. Cross-lingual coverage comparison is impossible with the
current query, and re-pulling other languages multiplies the token cost per language.

---

## 5. German coverage per method

| method | German articles | share of method | notes |
|---|---|---|---|
| **gdelt** | **1,408,753** | 100% | census, Jan–Aug 2026, 474 German domains |
| **eventregistry** | **129,628** | 100% | one 7-day window, 320 sources |
| **ground_news** | **5,563** | 12.1% | 537 / 894 stories contain ≥1 German article |
| allsides | 0 | 0% | US-only |

GDELT holds **253× more German articles than Ground News** and **10.9× more than Event
Registry**, and it is the only one that covers more than a week. Ground News's German
slice is not a German dataset — it is international coverage that happens to include
German outlets.

---

## 6. Providers — count, top channels, overlap

### Unique data providers

| method | unique domains | unique publisher names | domains unique to this method |
|---|---|---|---|
| ground_news | **5,477** | 5,391 | **5,090** |
| gdelt | 474 | 473 | 253 |
| allsides | 353 | 411 | 101 |
| eventregistry | 320 | 318 | 133 |

Ground News's 5,477 is a worldwide long tail (median 1–2 articles per outlet), not depth.
GDELT and Event Registry are the German-focused rosters.

### Top channels per method

| # | eventregistry | gdelt | ground_news | allsides |
|---|---|---|---|---|
| 1 | wallstreet-online.de (4,249) | az-online.de (61,540) | reuters.com (197) | thehill.com (5,782) |
| 2 | finanzen.at (3,725) | welt.de (57,991) | zeit.de (192) | foxnews.com (4,082) |
| 3 | n-tv.de (2,705) | merkur.de (56,729) | independent.co.uk (182) | nytimes.com (3,005) |
| 4 | welt.de (2,669) | hna.de (53,960) | straitstimes.com (173) | reuters.com (2,921) |
| 5 | sueddeutsche.de (2,645) | zeit.de (50,159) | welt.de (165) | justthenews.com (2,911) |
| 6 | web.de (2,547) | kreiszeitung.de (44,678) | n-tv.de (161) | newsweek.com (2,170) |
| 7 | news.de (2,521) | n-tv.de (39,596) | handelsblatt.com (150) | wsj.com (2,165) |
| 8 | gmx.net (2,486) | finanznachrichten.de (32,131) | thestar.com (143) | apnews.com (2,037) |
| 9 | augsburger-allgemeine.de (2,232) | op-online.de (27,176) | winnipegfreepress.com (139) | nypost.com (1,914) |
| 10 | zeit.de (2,172) | tz.de (24,904) | apnews.com (131) | nationalreview.com (1,897) |

Both German pipelines are dominated by the **Ippen regional network** (merkur/hna/tz/
come-on/fnp/op-online/kreiszeitung) and finance wires — the material that clusters worst
and carries the least editorial signal.

### Overlap between methods (by domain)

| pair | shared domains |
|---|---|
| eventregistry ∩ gdelt | **163** |
| ground_news ∩ gdelt | 114 |
| eventregistry ∩ ground_news | 80 |
| ground_news ∩ allsides | 252 |
| gdelt ∩ allsides | 3 |
| eventregistry ∩ allsides | 1 |
| **all three German methods** | **56** |
| all four | 1 |

### Top 5 overlapping providers (present in all three German methods)

Ranked by combined article volume across Event Registry + Ground News + GDELT:

| domain | ER articles | % of ER | GN articles | % of GN | GDELT articles | % of GDELT |
|---|---|---|---|---|---|---|
| **welt.de** | 2,669 | 2.06% | 165 | 0.36% | 57,991 | 4.12% |
| **hna.de** | 1,965 | 1.52% | 40 | 0.09% | 53,960 | 3.83% |
| **zeit.de** | 2,172 | 1.68% | 192 | 0.42% | 50,159 | 3.56% |
| **n-tv.de** | 2,705 | 2.09% | 161 | 0.35% | 39,596 | 2.81% |
| **tz.de** | 1,864 | 1.44% | 61 | 0.13% | 24,904 | 1.77% |
| **top-5 combined** | 11,375 | **8.78%** | 619 | **1.34%** | 226,610 | **16.09%** |
| **all 56 shared combined** | | **30.31%** | | **6.63%** | | **27.96%** |

Reading: the 56 shared outlets account for ~28–30% of both German pipelines but only
6.6% of Ground News. Those 56 are the domains where the three methods can be joined and
cross-validated — e.g. take a GDELT cluster, pull the matching ER body, attach the GN
bias label for that outlet.

### Top topics per method

| eventregistry | ground_news | gdelt (GKG V2Themes) | allsides |
|---|---|---|---|
| — none collected — | Politics (319) | CRISISLEX_CRISISLEXREC (44,182) | Donald Trump (606) |
| | Europe (207) | CRISISLEX_C07_SAFETY (37,109) | Trump Administration (428) |
| | Germany (174) | UNGP_FORESTS_RIVERS_OCEANS (32,114) | Politics (411) |
| | United States (132) | TAX_ETHNICITY_GERMAN (27,696) | Immigration (224) |
| | US Politics (116) | LEADER (24,167) | Middle East (187) |
| | Asia (100) | TAX_WORLDLANGUAGES_GERMAN (23,962) | Iran (133) |
| | Economy (98) | SECURITY_SERVICES (23,424) | World (128) |
| | Middle East (87) | MANMADE_DISASTER_IMPLIED (22,813) | Israel (124) |
| | Sports (84) | TAX_ECON_PRICE (21,865) | Economy And Jobs (123) |
| | Donald Trump (82) | AFFECT (21,486) | Defense And Security (112) |

Event Registry topics are **absent, not empty** — the scraper uses default `returnInfo`,
which excludes `concepts` and `categories`. Recovering them requires a re-pull.

GDELT themes are machine-assigned GKG codes: high recall, low precision, and
`TAX_ETHNICITY_GERMAN` / `TAX_WORLDLANGUAGES_GERMAN` are artefacts of the German-language
filter rather than real subject matter. Usable as features, not as human-readable topics.

---

## 7. Limitations per strategy

### Event Registry

- **Cost wall.** 2,000 non-renewing free tokens; the 7-day pull consumed ~1,540, leaving
  **461**. 1 token per 100-article page. Anything older than the **30-day window** needs
  the paid archive at 5 tokens *per searched year*, so pre-July-2026 German news is
  effectively unavailable — the script sets `allowUseOfArchive=False` as a guard. A second
  7-day pull (~1,790 tokens) is no longer affordable.
- **Not a story dataset.** 100% singletons after unification; 83.5% have no `eventUri`
  even in the raw file. See §4 for the duplicate-flag mechanism.
- **Duplicate flag destroys the interesting clusters.** Wire copy carried by up to 48
  independent outlets is marked `isDuplicate` and excluded from events, with `sim == 0`
  on 96.8% of them — a lexical decision blind to distributor independence.
- **Language filter blocks cross-lingual coverage.** `lang="deu"` means the non-German
  members of ~9.5% of events were never requested; per-language re-pulls multiply cost.
- **Volume skewed to niche/low-signal material.** Finance wires (wallstreet-online,
  finanzen.at) and the Ippen local network top the ranking; they cluster at 1.7–7%
  (`fnp.de` 1.7%, `come-on.de` 4.6%) versus `freiepresse.de` 69% and `n-tv.de` 45.5%.
- **`sueddeutsche.de` is `private: true`** → ~300-char teaser bodies only, despite being
  the 5th largest source (2,645 articles).
- **Redistribution prohibited.** ToS forbid sharing/sublicensing data from the service,
  and claim even structured metadata as Event Registry's property. **This dataset cannot
  be published**, only used for evaluation. Blocking constraint for a public release.
- **No topics, no concepts, no `storyUri`** — all off in default `returnInfo`; only
  recoverable by spending tokens on a fresh pull.
- Upside: easiest API by a wide margin, full bodies, clean UTF-8, authors, images.

### Ground News

- **Tiny.** 894 stories after ~14 months of scraping — ~2 stories/day. Not a corpus.
- **Only 12.1% German**, and its German slice is 5,563 articles, three orders of
  magnitude below GDELT.
- **37.4% of bias labels are `unknown`**, concentrated on exactly the small and
  non-English outlets that make up the German tail.
- **No body text at all** — headline + dek only. Any text-based modelling needs a
  separate fetch against 45,601 URLs.
- **Factuality is empty** in this dump despite the field existing.
- **Per-side summaries on only 49.3% of stories** (441/894); `summary_right` is often the
  empty string even when left/center are populated, which biases any study that
  conditions on having all three.
- Scraped content — the usual redistribution caveats.
- Upside: the *only* source of stance labels, per-side summaries, blindspots and a story
  bias distribution. Irreplaceable as a label source and as an evaluation set.

### GDELT

- **No body text, no descriptions.** GKG gives title + URL + themes. Bodies require our
  own crawl; 11,899 fetched so far out of 1.4M articles (0.8%).
- **No bias signal whatsoever**; stance is `unknown` for all 1,408,753 articles.
- **Clustering is ours and it is shallow** — `SequenceMatcher` on titles at 0.65 within
  a day bucket. Two outlets rewriting the same event under different headlines will not
  merge; a story crossing midnight splits.
- **GKG has no title column** — titles come from `<PAGE_TITLE>` inside the `Extras` XML.
  Dropping `Extras` to save BigQuery quota silently destroys clustering.
- **Junk records.** GDELT indexes section fronts and homepages, so unfiltered stories
  include things like `BÖRSE ONLINE – Seit 1987 …`. Mitigated here by `--min-outlets 3`,
  which is also why the delivered file is 173,388 of 2,015,373 stories (8.6%).
- **Expensive to pull.** The Jan–Aug 2026 raw-dump route is 172 GB of bandwidth (~5 h at
  ~68 slots/min with 8 workers) for ~5 GB of output. BigQuery alternative is capped at
  1 TB/month on the free sandbox and `Extras` is the expensive column.
- **No outlet-country field** on the raw-dump route (unlike the DOC API's
  `sourcecountry`) — all 173,388 stories carry `countries: ["?"]`.
- The DOC API frontend is capped at **250 results/query with no pagination**; that cap,
  not news volume, is why the old `gdelt_stories.jsonl` held only 654 stories. Do not
  use it for volume.
- Upside: metadata is openly licensed, the census is complete and gap-free
  (20,350/20,350 slots, zero failures), it reaches back to 2015-02-19, and it is the only
  method producing multi-outlet German story clusters at scale.

### AllSides

- US-only, 0 German articles.
- 68,352 article slots collapse to 8,072 unique URLs (~8× inflation).
- `is_featured: false` articles come from "More from the Left/Center/Right" sidebars and
  may be off-story — filter before using them as story members.
- Bodies on only 17.3%, via the Qbias multi-source scrape joined by exact URL.

---

## 8. Recommended next moves

1. **Re-run `unify.py`.** It costs nothing and attaches the 11,899 GDELT bodies written
   on 2026-08-11 that the current unified file predates.
2. **Add title-clustering to `convert_eventregistry`.** Group by normalized title with an
   `eventUri` override where present, singleton fallback otherwise. Turns 67,005 of
   129,628 ER articles (51.7%) into multi-source stories at zero API cost, and is the
   single highest-value change available right now.
3. **Join on the 56 shared domains.** GDELT cluster → ER body → GN outlet bias is the
   only path to a German dataset that has structure, text and labels simultaneously.
4. **Do not spend the remaining 461 ER tokens on more articles.** If they are spent at
   all, spend them on a small pull with `concepts`/`categories`/`storyUri` enabled, to
   learn whether ER's own topic layer is worth a paid plan.
5. **Plan the public release around GDELT.** It is the only pipeline whose licensing
   permits redistribution. Event Registry text can support internal evaluation only.

---

*Sources: `data/unified/*.jsonl`, `data/eventregistry/articles_germany.jsonl`,
`data/gdelt/gdelt_stories_de_min3.jsonl`, `data/gdelt/gdelt_enrichment_de.jsonl`,
`data/ground_news/ground_news.jsonl`. Clustering internals from
`scrapers/gdelt/gdelt_cluster_bulk.py`; conversion logic from `unify/unify.py`.*
