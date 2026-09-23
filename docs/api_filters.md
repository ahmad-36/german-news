# API Filter Reference — GDELT and Event Registry

What each API actually lets you filter on. AllSides and Ground News have **no public API**;
both are scraped from HTML, so their "filters" are whichever listing pages exist
(date-range roundups for AllSides; `/top`, `/blindspot`, `/interest/<topic>` and a keyword
search for Ground News).

---

## GDELT

Three access routes with **very different capabilities**. This is the thing to get right:
the rich filter set belongs to the route you cannot collect volume from.

| Route | Filters | Volume ceiling | Use for |
|---|---|---|---|
| **DOC 2.0 API** | 🟢 the full set below | 🔴 **250 results, no pagination** | probing, prototyping |
| **Raw 15-min dumps** | 🟡 none — you filter locally | 🟢 unlimited (bandwidth-bound) | **collection** |
| **BigQuery** | 🟢 SQL over all columns | 🟡 1 TB/month free sandbox | targeted large pulls |

### DOC 2.0 API operators

**Source and language**

| Operator | Syntax | Notes |
|---|---|---|
| `sourcelang` | `sourcelang:german` | 65 machine-translated languages |
| `sourcecountry` | `sourcecountry:germany` | 2-char FIPS code or name. **Not available on the dump route** |
| `domain` | `domain:zeit.de` | partial match |
| `domainis` | `domainis:un.org` | exact match — prefer this |

**Content**

| Operator | Syntax | Notes |
|---|---|---|
| `theme` | `theme:TERROR` | GKG themes; qualifies at 100+ articles in 2 years |
| `tone` | `tone<-5`, `tone>5` | range roughly −20…+20 |
| `toneabs` | `toneabs>10` | emotional intensity regardless of direction |
| `near` | `near20:"trump putin"` | max word distance; word order affects it |
| `repeat` | `repeat3:"trump"` | **single word only**, no phrases; "at least N times" |
| phrase | `"donald trump"` | quoted exact phrase |
| boolean OR | `(clinton OR sanders OR trump)` | **cannot be nested** |
| negation | `-sourcelang:spanish` | prefixes any operator, word or phrase |

**Images** — a capability we are not currently using at all, and the only route to
image-level filtering across any provider here:

| Operator | Syntax | What it does |
|---|---|---|
| `imagetag` | `imagetag:"safesearchviolence"` | 10,000+ recognised objects |
| `imageocrmeta` | `imageocrmeta:"zika"` | OCR of text *in* the image, 80+ languages |
| `imagewebtag` | `imagewebtag:"drone"` | reverse-image-search descriptors |
| `imagewebcount` | `imagewebcount>100` | how widely the image is reused (≤200 pages tracked) |
| `imagenumfaces` | `imagenumfaces>3` | foreground faces only |
| `imagefacetone` | `imagefacetone<-1.5` | facial expression tone, roughly +2…−2 |

**Time**

| Parameter | Syntax | Limit |
|---|---|---|
| `timespan` | `timespan=1d`, `3w`, `1m` | minimum 15 min; **default 3 months** |
| `startdatetime` / `enddatetime` | `20260101000000` | 🔴 **must fall within the last 3 months** |

> ⚠️ **The 3-month window is the DOC API's real limit**, alongside the 250-result cap.
> Historical collection *must* go through the dumps or BigQuery, which reach back to
> **2015-02-19**.

**Results**

| Parameter | Options | Notes |
|---|---|---|
| `maxrecords` | up to **250** | default 75 |
| `sort` | `datedesc`, `dateasc`, `tonedesc`, `toneasc`, `hybridrel` | |
| `format` | `html`, `csv`, `json`, `jsonp`, `rss`, `jsonfeed` | |
| `mode` | `artlist`, `timelinevol`, `imagecollage`, `tonechart`, … | 15+ modes |

### What GDELT does *not* filter on

- 🔴 **Bias or stance** — no such field exists.
- 🔴 **Paywall status.**
- 🔴 **Article length or body presence** — GKG carries no body at all.
- 🔴 **Outlet country on the dump route** — all our 173,388 stories carry `countries: ["?"]`.

---

## Event Registry (newsapi.ai)

The richest filter set of any provider surveyed, and the only one with first-class
*negation* of every dimension. Applies to `QueryArticles` / `QueryArticlesIter`.

### Positive conditions

| Parameter | What it selects |
|---|---|
| `keywords` | articles mentioning keyword(s)/phrase(s); single string or list |
| `keywordsLoc` | **where** to search: `body` (default), `title`, `body,title` |
| `keywordSearchMode` | `phrase` (default), `exact`, `simple` |
| `conceptUri` | articles mentioning a **concept** (entity/topic URI) |
| `categoryUri` | articles assigned to a category |
| `sourceUri` | specific news sources |
| `sourceLocationUri` | 🟢 **sources located in a geography** — the correct country filter |
| `sourceGroupUri` | sources in a named source group |
| `authorUri` | specific authors |
| `locationUri` | articles about an **event at** a location (distinct from source location) |
| `lang` | article language(s) — we use `deu` |
| `dateStart` / `dateEnd` | publication date range |
| `dateMentionStart` / `dateMentionEnd` | articles that *mention* a date in range |

> **`sourceLocationUri` vs `locationUri`** is the distinction worth internalising: the
> first is where the *publisher* sits, the second is where the *event* happened. For a
> German-media dataset you want `sourceLocationUri`; for German *news coverage* wherever
> published, `locationUri`.

### Negative conditions

Every positive filter has an `ignore*` twin: `ignoreKeywords`, `ignoreConceptUri`,
`ignoreCategoryUri`, `ignoreSourceUri`, `ignoreSourceLocationUri`, `ignoreSourceGroupUri`,
`ignoreAuthorUri`, `ignoreLocationUri`, `ignoreLang`.

### Quality and dedup filters

| Parameter | Options | Why it matters here |
|---|---|---|
| `isDuplicateFilter` | `skipDuplicates` / `keepOnlyDuplicates` / `keepAll` | 🔴 **the critical one** — see below |
| `hasDuplicateFilter` | `skipHasDuplicates` / `keepOnlyHasDuplicates` / `keepAll` | selects the *originals* of copied articles |
| `eventFilter` | `skipArticlesWithoutEvent` / `keepOnlyArticlesWithoutEvent` / `keepAll` | 🟢 would let us pull only clustered articles |
| `startSourceRankPercentile` / `endSourceRankPercentile` | 0–100 | 🟢 **drop the low-quality long tail** — directly addresses our finance-wire skew |
| `minSentiment` / `maxSentiment` | −1…1 | ⚠️ **silently forces English-only** |
| `dataType` | `news` (default), `pr`, `blog` | exclude press releases |

> ⚠️ **`minSentiment`/`maxSentiment` restrict results to English.** Setting either one on a
> German pull would silently return nothing useful.

### Three filters we should be using and are not

1. **`startSourceRankPercentile`** — our pull is dominated by finance wires
   (wallstreet-online.de 4,249 articles) and the Ippen local network, which cluster worst
   and carry the least editorial signal. A percentile floor would remove them at the API.
2. **`eventFilter=skipArticlesWithoutEvent`** — 83.5% of what we pulled has no `eventUri`
   and became a singleton. This filter would have spent tokens only on clustered articles.
   (Caveat: it would also have excluded the wire stories ER wrongly marks as duplicates —
   which is exactly the material we most want. Use knowingly.)
3. **`conceptUri` / `categoryUri`** — our pull collected **no topics at all**, because the
   default `returnInfo` excludes `concepts` and `categories`. This is a scraper defect, not
   a provider limit.

### Cost model

| | |
|---|---|
| Free allowance | **2,000 non-renewing tokens** (~461 remaining) |
| Article pull | 1 token per 100-article page |
| Recency window | **30 days** |
| Archive access | **5 tokens per searched year** — guarded off via `allowUseOfArchive=False` |

### What Event Registry does *not* filter on

- 🔴 **Bias or stance** — no such field.
- 🔴 **Image presence** (images are returned at 98.6% but are not a query dimension).
- 🔴 **Paywall status** as a filter (`private: true` appears in results only).
