# Data Sources

For each provider: how it is collected, what you get, and its limits. The last two
sections list ten further providers and where the four can be joined. Figures are measured
on the data on disk (Jan–Aug 2026).

---

## Where each provider sits in the pipeline

Target pipeline: **① collect → ② filter (language, country, topic) → ③ topic clustering →
④ same-event clustering → ④b split each story by stance → ⑤ downstream tasks** (article /
topic / stance summaries, stance comparison, stance prediction). A diagram is in
[../assets/pipeline.svg](../assets/pipeline.svg).

| stage | GDELT | Event Registry | Ground News | AllSides |
|---|---|---|---|---|
| ① collect | by date (census or filtered) | by date + language | trending pages | by date |
| ② filter | **ours** | provider (rich filters) | provider (topic pages) | none (US politics only) |
| ③ topics | GKG themes (machine, noisy) | **not collected** (default `returnInfo`) | machine tags, computed on translated text | human editorial tags |
| ④ event clusters | **ours** (title similarity) | `eventUri` on only 16.5% | theirs, **method undocumented** | editorial |
| ④b stance split | impossible (no labels) | impossible (no labels) | per-outlet labels | per-outlet labels |
| ⑤ downstream | — | — | ships **GPT-generated** stance summaries | — |

---

## GDELT: the backbone for German story structure

**Collection.** The raw 15-minute GKG dump files (every slot since 2015-02-19) are
downloaded and filtered locally. We use this route for all our data. The alternatives are
BigQuery (1 TB/month free, never needed) and the DOC API (capped at 250 results with no
pagination, so it is not usable for volume).

```bash
python gdelt_dump_pull.py --start 2026-01-05 --end 2026-01-12 --keywords-file keywords/german_politics.txt
python gdelt_cluster_bulk.py      # cluster titles into stories
python gdelt_enrich_bulk.py       # fetch body, og:image and caption from each outlet
```

**Clustering is ours.** It is single-pass and bucketed by day. Similarity is
`SequenceMatcher` on normalised titles with threshold 0.65, and a story must have at least
3 outlets. Outlets from the same media group (the Ippen network: merkur.de, tz.de, hna.de,
…) count as one outlet first, so syndicated copies cannot inflate a story's breadth.

| | |
|---|---|
| Stories (3+ outlets) / articles | 173,388 / 1,408,753, all German, 474 domains |
| Outlets per story | median 5, max 77; **3,811 stories reach 30+ outlets** |
| Body text | none from GDELT; our enrichment crawl fetched **154,084** |
| Images | none from GDELT; our crawl found **145,078** `og:image` URLs and 88,992 captions (not downloaded) |
| Topics | GKG themes on every article (machine-assigned, high recall, low precision) |
| Stance | none |

**Limits.** No body text and no bias signal. The title-only clusterer misses about
two-thirds of same-event pairs (see [experiments.md §5](experiments.md#5-event-clustering)).
A story that crosses midnight splits into two. The dump route has no publisher country.
On the plus side, GDELT is **openly licensed** and is the only source here that can be republished.

---

## Event Registry: clean full German text

**Collection.** An authenticated, paginated REST API. We queried
`lang="deu"` + publisher in Germany + a date window, and set `allowUseOfArchive=False` so a
mistyped date can never spend archive tokens.

```bash
python eventregistry_german_sources.py --skip-discovery --days 7 --pull 5000
```

| | |
|---|---|
| Articles | 129,628 from 320 sources, 2026-07-30 → 08-07 |
| Body text | **100%**, median 2,111 characters |
| Images | 98.6% have an image URL; no captions |
| Authors | yes |
| Topics | **none**: the default `returnInfo` excludes concepts and categories |
| Stance | none |
| Events | 21,416 articles (16.5%) carry an `eventUri`, forming 2,392 multi-article stories |

**Limits.**
- 🔴 **The terms of service forbid redistribution**, including metadata. The data can be used
  for internal evaluation only.
- 🔴 **The free tier is limited:** 2,000 non-renewing tokens (1 per 100-article page) and
  only the last 30 days. Older data needs the paid archive.
- The duplicate flag removes wire stories from events. Of 59,088 duplicate-flagged
  articles, only 2 have an `eventUri`, so one dpa story carried by 48 outlets never forms a
  cluster. Grouping by normalised title would turn 51.7% of articles into multi-source
  stories at no API cost.
- `sueddeutsche.de` returns only 300-character teasers.

---

## Ground News: the only stance labels and summaries

**Collection.** There is no API and no date endpoint. The scraper walks the homepage,
`/top`, `/blindspot` and 17 `/interest/<topic>` pages, and supports keyword search
(`--query`). Historical data is only available through Wayback Machine replay, which is
best-effort. Requests need `curl_cffi` Chrome impersonation to get past bot detection.

| | |
|---|---|
| Stories / articles | 894 / 46,030 from 5,477 domains (about 2 stories per day) |
| German | 5,563 articles (12.1%) |
| Body text | none (headline + dek only) |
| Images | none |
| Stance label | 62.6% labelled; **37.4% are literally `unknown`** |
| Per-stance summaries | 441 stories (49.3%), **GPT-generated** |
| Also | blindspot flag (89 stories), paywall flag, topics |

**What is human and what is GPT:**
- **Bias labels**: human, per outlet. They are averaged from three US agencies (Media
  Bias/Fact Check, Ad Fontes, AllSides), which **disagree on 32.1%** of rated articles.
- **`summary_left/center/right`, `bias_comparison`, `generated_headline`**: GPT. The page
  stores them in an object named `chatGptSummaries`.
- **Clustering**: Ground News' own, and undocumented.

**Limits.** It is too small to be a corpus, but it is useful as a label and evaluation set.
It machine-translates 41% of articles and the translation deletes entities (see
[experiments.md §4](experiments.md#4-ground-news-translation-deletes-entities)).
Luxembourgish is mislabelled as `de`. German articles are identified only by matching
publishers against a 60-name list (`germanlib.py`).

---

## AllSides: the template, but no German

**Collection.** The crawler walks AllSides' headline-roundup pages over a date range. A
separate scraper for each outlet then fetches full article text and images.

| | |
|---|---|
| Stories / article slots | 1,919 / 68,352, of which **only 8,072 are unique URLs** |
| Outlets per story | median 22 |
| Body text | 17.3% (11,838) |
| Images | **10,716 files on disk (8.0 GB)**: 2,448 stance thumbnails and 8,268 article images (5,306 with captions) |
| Stance label | 99.9%, 7-point, per outlet |
| Topics, summary | 100%, human editorial |

**Limits.** It is US-only, so there are **no German articles**. Articles are inflated
about 8× because sidebar articles repeat across story pages, so always deduplicate before
counting. Labels are per outlet, and the classes are balanced only because the page layout
shows one article per side.

---

## Images: where they are

| | files on disk | URLs | captions |
|---|---|---|---|
| AllSides | **10,716 files** (`muws-allsides-dataset/*/output/images/`) | 47,122 | 5,306 |
| GDELT | none | 145,078 (from our crawl) | 88,992 |
| Event Registry | none | 98.6% of articles | none |
| Ground News | none | none | none |

GDELT image URLs will stop working as outlets change their CDNs, so they should be
downloaded soon if they are needed. The unified format keeps image URLs only, in each
article's `meta`.

---

## Other providers checked (not used)

| provider | what it offers | German | stance labels | access |
|---|---|---|---|---|
| **EMM** (EU JRC) | 80 languages, **clusters per language and then links clusters across languages** | yes | framing detection, no left/right | ask the JRC |
| **Ad Fontes Media** | **article-level** ratings by 3+ human analysts (bias −42…+42) | probably not | **per article** | commercial |
| **CC-NEWS** | Common Crawl news HTML since 2016 | yes | none | **free, openly licensed** |
| **Media Cloud** | academic archive, about 20 languages | yes | none | free API |
| **NewsCatcher** | commercial API with real event clustering | yes | none | paid |
| Perigon, Webz.io | commercial full-text APIs | yes | none | paid |
| MBFC, NewsGuard | outlet ratings (bias / trust) | rates German outlets | per outlet | paid |
| NELA-GT | static research dataset | no (US only) | per outlet | free |

**Worth acting on:** Ad Fontes, the only source of article-level labels; CC-NEWS, the only
source of German full text we could republish; EMM, which already uses the cluster-then-link
approach for multiple languages.

---

## Joining the providers

| providers | shared domains |
|---|---|
| Event Registry ∩ GDELT | 163 |
| Ground News ∩ GDELT | 114 |
| Event Registry ∩ Ground News | 80 |
| **all three** | **56** (about 30% of each German pipeline) |

The join that matters: **GDELT story → Event Registry body → Ground News outlet label.**
It is the only route to German stories that have structure, text and labels at once.
