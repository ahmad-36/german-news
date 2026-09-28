# What We Can Filter On

AllSides and Ground News have **no API** — they are scraped, so the only "filters" are
whichever listing pages exist. This page is about the two that do have one.

---

## GDELT

Three ways in. We use one of them.

| route | do we use it? | filtering | ceiling |
|---|---|---|---|
| **Raw 15-min dumps** | ✅ **yes — 100% of our data** | none server-side; we filter locally | bandwidth only |
| BigQuery | ❌ never run | full SQL | 1 TB/month free |
| DOC 2.0 API | ⚠️ tried early, abandoned | rich (see below) | **250 results, no pagination** |

**What we actually do:** download every 15-minute GKG file for a date range and filter in
memory. The German-language filter is hard-coded; topic and keyword filters were added in
Sept 2026 (`--keywords-file`, `--themes-file`) — see
[collection_policy.md](collection_policy.md).

**Why not the DOC API**, despite having the best filters: it caps at **250 results with no
pagination**, and only covers the **last 3 months**. That cap — not news volume — is why an
early pull produced just 654 stories. It is fine for probing a query, useless for
collection.

**Why not BigQuery:** it would work, but the raw dumps already give complete coverage at no
quota cost. Worth revisiting only if we need server-side filtering over a long range. Note
the `Extras` column is both the expensive one and the one holding article titles — dropping
it to save quota silently destroys clustering.

### DOC API filters, if we ever go back to it

Useful ones: `sourcelang`, `sourcecountry`, `domain`/`domainis`, `theme` (GKG themes),
`tone` / `toneabs`, `near20:"a b"` (proximity), `repeat3:"word"`, phrases in quotes,
`(a OR b)`, and `-` to negate anything.

It also has **image filters nothing else here offers** — `imagetag` (10k recognised
objects), `imageocrmeta` (text *inside* the image, 80+ languages), `imagewebtag`
(reverse-image-search terms), `imagenumfaces`, `imagefacetone`. Unused so far, and the only
route to image-level selection in this project.

### What GDELT cannot filter on

Bias or stance (no such field), paywall status, body text (GKG carries none), and — on the
dump route only — **publisher country**, so all our stories carry `countries: ["?"]`.

---

## Event Registry

A genuinely rich filter set. **We use four of them.**

```python
QueryArticlesIter(
    sourceLocationUri = germany_uri,   # publisher located in Germany
    lang              = "deu",
    dateStart, dateEnd,                # 30-day window on the free tier
    sourceUri         = ...            # optional, specific outlets
)
```

Plus `allowUseOfArchive=False` as a guard, so a mistyped date can never trigger the
5-tokens-per-year archive charge.

### Three we should be using and are not

| filter | what it would fix |
|---|---|
| `startSourceRankPercentile` | our pull is dominated by finance wires and the Ippen local network — the material that clusters worst. A percentile floor drops them at the API. |
| `eventFilter=skipArticlesWithoutEvent` | 83.5% of what we pulled has no `eventUri` and became a singleton. ⚠️ but this also excludes the wire stories ER wrongly flags as duplicates, which is the material we most want. |
| `conceptUri` / `categoryUri` | we collected **zero topics**, because the default `returnInfo` excludes concepts and categories. A scraper defect, not a provider limit. |

Also available and unused: `keywords` (+ `keywordsLoc` to search title vs body),
`authorUri`, `locationUri` (where the *event* happened, as opposed to where the publisher
is), `dataType` to exclude press releases, and an `ignore*` negation of every single filter.

⚠️ **`minSentiment`/`maxSentiment` silently restrict results to English.** Setting either on
a German pull returns nothing useful.

### Cost

2,000 non-renewing free tokens, **461 left**. 1 token per 100-article page. 30-day recency
window; the archive costs 5 tokens *per searched year*.

### What Event Registry cannot filter on

Bias or stance, image presence, paywall status (`private: true` appears in results but is
not queryable).
