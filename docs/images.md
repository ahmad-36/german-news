# Images: what was collected, how, and where it is

Only **AllSides** has actual image files on disk. **GDELT** and **Event Registry** store image
*URLs* only. **Ground News** has no images. Counts were measured on the data on disk
(Sept 2026).

| | **AllSides** | **Ground News** | **GDELT** | **Event Registry** |
|---|---|---|---|---|
| Image URL | 68.9% of story slots (47,122) | none: no image field | 0% native `og:image`; 145,078 from our own enrichment crawl | 98.6% |
| Captions | 5,306 of 8,398 article images (63%) | none | 88,992 (41.7% of enriched pages) | none: not in the API schema |
| **Files downloaded** | **10,716 files, 8.0 GB** | none | **none**, URLs only | **none**, URLs only |
| How the image was found | AllSides roundup thumbnail + per-outlet HTML parsers | — | `og:image` meta tag + `<figcaption>` | API `image` field |

---

## AllSides: two separate image paths

Everything lives under `~/muws-allsides-dataset/allsides_crawl/output/images/` (story images) and `multi_source_scrape/output/images/` (article images).

### 1. Stance thumbnails (AllSides roundup page)

- **Script:** [`allsides_scraper.py`](../../../muws-allsides-dataset/allsides_crawl/crawler/allsides_crawler.py)
- **Source:** the image AllSides shows next to each left/center/right headline on the
  story page, taken from the `<img>` that is not the bias-rating badge.
- **Stored as:** `image_link` (URL) on every stance slot. For featured stances the file is
  also downloaded to `images/<story-slug>/<stance>/`, and its path is recorded as
  `image_local_path`.
- **Counts:** 47,122 slots have an `image_link`, but only **2,448** (featured stances) have a
  downloaded file. The "more left/center/right" slots are URL-only.
- **No captions.** `--no-images` skips the download step.

### 2. Article images (the outlet's own page)

- **Scripts:** one parser per domain in
  [`multi_source_scrape/scrapers/`](../../../muws-allsides-dataset/multi_source_scrape/scrapers/). The shared download step is
  `download_article_images` in `news_scrapers/base.py`.
- **Source:** the images inside the article body on the outlet's site, together with their
  captions where the page has them.
- **Stored as:** `extracted_images: [{url, caption, local_path}]` in
  `output/full_articles/<domain>.json`. Files are saved to `images/<domain>/<story>/<slot>/`.
- **Counts:** 2,819 of the 2,897 scraped articles have at least one image. That is 8,398
  images, **8,268 of them downloaded**, and 5,306 with captions.
- `--mode refresh` re-scrapes successful articles to update images and captions.

Per outlet:

| outlet | articles | images | downloaded | captioned |
|---|---:|---:|---:|---:|
| nypost.com | 324 | 1,724 | 1,724 | 1,382 |
| foxnews.com | 486 | 1,451 | 1,435 | 1,441 |
| reuters.com | 104 | 1,058 | 1,058 | 59 |
| apnews.com | 194 | 1,001 | 1,001 | 756 |
| newsweek.com | 281 | 688 | 688 | 267 |
| bbc.com | 266 | 427 | 427 | 248 |
| thehill.com | 372 | 372 | 370 | 0 |
| foxbusiness.com | 98 | 345 | 337 | 318 |
| cnn.com | 163 | 310 | 310 | 302 |
| nbcnews.com | 113 | 291 | 291 | 122 |
| washingtonexaminer.com | 179 | 199 | 199 | 68 |
| theguardian.com | 113 | 188 | 176 | 188 |
| washingtonpost.com | 99 | 145 | 145 | 90 |
| nytimes.com | 20 | 107 | 107 | 0 |
| politico.com | 85 | 92 | **0** | 65 |
| **total** | **2,897** | **8,398** | **8,268** | **5,306** |

Caveats:
- Politico images were extracted but **never downloaded**.
- The Hill and NYT parsers capture no captions. Reuters captions only 6% of its images.
- The number of images per article varies a lot between parsers (Reuters about 10 per
  article, The Hill exactly 1), so image counts are not comparable across outlets.

---

## GDELT: lead image from our own enrichment crawl

GDELT stores metadata only. The raw dumps do carry a `SharingImage` column (the
social-preview URL, filled on ~74% of German rows). The pull scripts keep it as
`socialimage`, but it is a URL only.

- **Scripts:** [`gdelt_enrich.py`](../../news-gdelt/gdelt_enrich.py) and
  [`gdelt_enrich_bulk.py`](../../news-gdelt/gdelt_enrich_bulk.py) (env `scrap2`)
- **Method:** fetch one article per story from the outlet itself. Take the lead image from
  the `og:image` meta tag and the caption from the lead `<figcaption>`. The body text comes
  from trafilatura in the same pass.
- **Stored as:** `image` and `image_caption` per URL in
  `news-gdelt/data/gdelt/gdelt_enrichment_de.jsonl` (and `gdelt_enrichment.json`).
- **Counts:** 145,078 image URLs and 88,992 captions across 213,532 enrichment records.
- **Not downloaded.** Many of these URLs will stop working as outlets rotate their CDNs.
  Download them soon if they are needed.
- **Not yet in the unified dataset.** `unify.py` was run before most of the enrichment
  existed, so it needs to be re-run (see [problems.md](problems.md)).

## Event Registry: API image URL

- **Script:** [`eventregistry_german_sources.py`](../../news-eventregistry/eventregistry_german_sources.py)
- **Method:** the API returns an `image` field on each article. Nothing is scraped.
- **Counts:** 98.6% of the 129,628 articles have an image URL. There are **no captions**
  anywhere in the schema.
- **Not downloaded.** The ToS also forbids redistribution, so the images could not go into a
  public release either.

## Ground News

No image field in the record. Not collected.

## Unified dataset (`news-explorer`)

[`unify.py`](../../news-explorer/unify/unify.py) carries image **URLs** only, in `meta`:
`image_link` (AllSides), `socialimage` (GDELT), `image` (Event Registry). The story viewer
shows a story's `lead_image` (the enrichment image, falling back to the social preview)
straight from its URL. The downloaded AllSides files are shown only by the AllSides repo's
own `dataset_explorer`.
