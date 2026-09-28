# Event Registry Collector

Pulls German full-text articles from the [Event Registry](https://eventregistry.org)
(newsapi.ai) API.

```bash
export EVENTREGISTRY_API_KEY=...
python eventregistry_german_sources.py --skip-discovery --days 7 --pull 5000
```

The query uses `lang="deu"`, publishers located in Germany, and a date window. It costs
1 API token per 100-article page, and `allowUseOfArchive=False` prevents archive charges.

## What one 7-day pull gave

| | |
|---|---|
| Articles | 129,628 from 320 German sources |
| Body text | 100%, median 2,111 characters |
| Images | 98.6% have an image URL (no captions) |
| Authors | yes |
| Events | 16.5% of articles carry Event Registry's `eventUri` |
| Topics, stance | none |

## Limits

- **The terms of service forbid redistributing the data**, including metadata. Use it
  for internal evaluation only.
- **Few articles are grouped into events.** Articles flagged as duplicates are left out of
  events, so wire stories carried by many outlets end up as singletons.
- **Topics were not collected.** The default `returnInfo` excludes concepts and
  categories; request them explicitly to get topics.
- Some outlets (e.g. `sueddeutsche.de`) return only ~300-character teasers.

## Clustering evaluation

[`clustering_eval/`](clustering_eval/) compares story-clustering methods against Event
Registry's own events.

**Requirements:** `eventregistry`; `sentence-transformers`, `scikit-learn` and `scipy`
for the clustering evaluation.
