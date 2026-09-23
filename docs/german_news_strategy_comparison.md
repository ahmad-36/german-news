# German news extraction — strategy comparison

Which pipeline should we invest in for collecting **German news**? This compares the
three strategies implemented in this repo (AllSides is deliberately excluded — it is
US-only and contributes nothing German). Numbers below are from the unified dataset as
of **2026-08-07**; regenerate them any time with:

```bash
python3 unify/unify.py && python3 unify/analytics.py --markdown --json
```

(full per-strategy publisher tables land in `data/unified/analytics.md`).

## The three strategies at a glance

| | **Ground News** (`scrapers/ground_news/`) | **GDELT DOC API** (`scrapers/gdelt/`) | **Event Registry / newsapi.ai** (`scrapers/eventregistry/`) |
|---|---|---|---|
| What one record is | Story: one event, N outlets, each bias-rated | Story: cross-outlet cluster we build by title similarity | Single article (no clustering; only an `eventUri` id) |
| Yield so far | 894 stories / 46,030 articles — but only **5,471 (12%) German-language** | 654 stories / 994 articles, 100% German-language | **129,628 articles**, 100% German, from one 7-day pull |
| Unique publishers (German scope) | ~5,400 total, worldwide; German outlets a small slice | 110 German-language domains (82 in one 3-probe sample) | 318 German sources |
| Bias ratings | ✅ per outlet (AllSides / Ad Fontes / MBFC), 63% of articles rated | ❌ none | ❌ none |
| Cross-outlet story clustering | ✅ native (Ground News editorial) | ⚠️ ours, title-similarity only | ❌ (eventUri exists but unused on free tier) |
| Full body text | ❌ (headline + description only) | ⚠️ via our enrichment fetch (89/654 stories so far) | ✅ 100% — full text in the API response |
| Images | ❌ | ⚠️ og:image + figcaption via enrichment | ⚠️ image URL, **no caption** |
| Per-side AI summaries / blindspot | ✅ unique to Ground News | ❌ | ❌ |
| Historical reach | Wayback replay, best-effort | ✅ back to **2017-01-01**, 15-min freshness | ❌ 30-day window on free tier (archive is paid) |
| Rate limits / cost | Polite scraping (1.5–4 s delays); free | Free but harsh IP rate-limit: ~1 query/min, 250 articles/query, no pagination | **2,000 non-renewing free tokens**; the 7-day pull cost ~1,540 (461 left) |
| Licensing for a public dataset | Scraped content — usual scraped-data caveats | ✅ metadata is open; bodies we fetch ourselves | ❌ **ToS forbids redistribution** — evaluation only |
| German coverage quality | Mostly *international* coverage about Germany; German outlets present (Zeit, Welt, Handelsblatt) but minority | GDELT's crawl list: broad incl. regional (n-tv, merkur, badische-zeitung, Ippen network) | Broadest: Spiegel/taz/tagesschau confirmed present; Süddeutsche bodies are ~300-char teasers; volume skewed by finance wires + Ippen syndication |

Top publishers per strategy (article counts): Ground News → Reuters 197, Zeit Online 192,
The Independent 183, Welt 165, Handelsblatt 150 (i.e., international-heavy). GDELT →
n-tv.de 82, merkur.de 70, wa.de 52, zeit.de 50, hna.de 50. Event Registry →
wallstreet-online 4,249, finanzen.at 3,725, N-tv 2,705, Welt 2,669, Süddeutsche 2,645.

## Strengths and dealbreakers

**Ground News** is the only source with the thing this project is actually about —
per-outlet **bias ratings and cross-outlet framing** (per-side AI summaries, blindspot
flags). But it is a poor *German* collector: its editorial pipeline is anglophone, so
German-language articles are only 12% of its yield even after the German seed-keyword
discovery runs (`scrapers/discovery/german_discovery_run.py`). Use it for the bias signal,
not for German coverage volume.

**GDELT** is the only strategy with deep, free **history (back to 2017)** and open
licensing, and its German-language filter genuinely captures the regional press. Its two
gaps are structural: metadata-only records (fixed by our `gdelt_enrich.py` fetch step —
which the scrapeability probe showed works for the major open outlets: n-tv, focus,
t-online, zeit, welt, spiegel, and the Ippen papers) and a brutal rate limit (~1
query/minute, 250 articles/query), which makes it a slow-drip accumulator rather than a
bulk downloader.

**Event Registry** wins on raw throughput and data completeness by an order of magnitude —
129k full-text German articles from a single 7-day window, with clean per-source metadata.
Two dealbreakers: the free tier is a **one-shot budget** (2,000 tokens total, non-renewing,
30-day content horizon — we have 461 tokens ≈ ~4 more days of pulling left), and the ToS
**forbids redistributing the data**, so this corpus cannot ship in a public dataset —
it's an evaluation/prototyping corpus only.

## Recommendation

- **For a public, redistributable German dataset:** GDELT as the backbone (temporal
  collection per day + per-outlet `domain_exact` probes), with our own enrichment fetch
  for bodies/images from the verified-open outlets. It is slow but free, historical, and
  legally clean.
- **For bias/framing labels:** keep Ground News running as the labeling layer — its
  bias-rated story clusters are unique — and join German outlets found in both datasets
  (e.g., Zeit, Welt, n-tv appear in all three).
- **For prototyping models that need full text now:** use the Event Registry corpus
  internally (it's already the largest thing we have), but don't build anything on it
  that assumes we can publish or refresh it — the remaining token budget is nearly spent.
- The **discovery pipeline** (`scrapers/discovery/`) stays useful regardless of the choice:
  its outlet list + scrapeability report (`data/discovery/scrapeability_report.json`)
  tells any strategy which German domains can be fetched for full text and images.
