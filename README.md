# German Multi-Perspective News Dataset

Collection of German news from four providers, one unified format, and an analysis of what
each provider offers. **Start with [analytics/README.md](analytics/README.md).**

| folder | what it does |
|---|---|
| [`gdelt/`](gdelt) | GDELT: download → filter → cluster into stories → fetch article text |
| [`ground-news/`](ground-news) | Ground News: scraper, German topic discovery, keyword lists |
| [`eventregistry/`](eventregistry) | Event Registry: German full-text articles via API, clustering evaluation |
| [`ui/`](ui) | converts all sources into one format, plus a Streamlit explorer |
| [`analytics/`](analytics) | the analysis: sources, keywords & APIs, experiments, problems |

AllSides is collected in a separate repository, `muws-allsides-dataset`.
