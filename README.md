# news

German multi-perspective news dataset: collection from four providers, one unified format,
and the written analysis.

**Start with [analytics/README.md](analytics/README.md)**, which summarises the findings
and links the four docs (sources, keywords & APIs, experiments, problems).

| folder | what it does |
|---|---|
| [`gdelt/`](gdelt) | GKG dumps → cluster → enrich, bounded by a keyword/theme filter |
| [`ground-news/`](ground-news) | topic-page crawl, keyword search, German discovery, keyword lists |
| [`eventregistry/`](eventregistry) | REST pull of German full-text articles (ToS forbid redistribution), clustering evaluation |
| [`ui/`](ui) | `unify.py` → one format for all four sources, plus the Streamlit explorer |
| [`analytics/`](analytics) | the written analysis and reproduction scripts |

AllSides lives in its own repository, `muws-allsides-dataset`.

## Data

Data is **never committed**. Each folder keeps what it collects in its own gitignored
`data/`, about 11 GB in total. Scripts find paths through each folder's `paths.py`, which
uses the local `data/` and falls back to the sibling folder that owns a source, so no
environment variable is needed. Set `$NEWS_DATA_DIR` to use one shared data root instead.

## History

Until Sept 2026 each folder was its own git repository. Their full histories were merged
into this one by a single commit, so `git log` shows every earlier commit. Commits from
before the merge use the old paths (`paths.py` rather than `gdelt/paths.py`).
