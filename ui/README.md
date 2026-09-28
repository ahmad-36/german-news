# Unified Format and Explorer

Converts the four sources (GDELT, Ground News, Event Registry, AllSides) into one format,
and provides a Streamlit app to browse them.

```bash
python unify/unify.py                    # all sources → data/unified/unified_<source>.jsonl + unified_all.jsonl
python unify/unify.py --only gdelt       # one source
streamlit run ui/dataset_explorer.py     # Story Feed + Dataset Statistics
```

`unify.py` reads each collector's output from the sibling folders, and AllSides from
`muws-allsides-dataset`. A full run takes about 3 minutes.

## Format

One JSON object per line is one **story** containing a list of **articles**:

```
story:   story_id, source_dataset, story_url, date, title, story_summary,
         stance_summaries {left, center, right}, topics[], bias_distribution, meta, articles[]
article: article_id, stance (left|center|right|unknown),
         bias_rating (far_left … far_right | unknown), source_name, url, date, headline,
         description, body_text, lang, paywall, is_featured, news_type, meta
```

Source-specific fields are kept unchanged under `meta`. The full schema is in the
[`unify.py`](unify/unify.py) docstring.

## Caveats

- `stance` is the **outlet's** label, not a judgement of the article. GDELT and Event
  Registry have no labels (`unknown`).
- Ground News `stance_summaries` and `bias_comparison` are GPT-generated. For translated
  articles, `headline` is the English translation and `meta.original_title` is the
  original.
- AllSides repeats the same article across many stories (68,352 entries, 8,072 unique
  URLs), so deduplicate by URL before counting articles.
- Event Registry stories are grouped by its `eventUri`; most articles have none and stay
  single-article stories.
- Event Registry's `story_summary` is the opening of the body, not a real summary.

**Requirements:** `streamlit`, `streamlit-searchbox`, `pandas`, `plotly`.
