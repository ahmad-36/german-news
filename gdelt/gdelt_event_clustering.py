"""Probe whether GDELT gives AllSides/Ground-News-like cross-outlet event clusters.

For a few impactful topics, pull German-language German-source articles and
group them by near-duplicate title (GDELT has no story-cluster id in the DOC
article list, so clustering must come from title/time similarity on our side).
Reports, per topic, clusters of >=3 outlets covering the same story.
"""
import re
import time
import unicodedata
from collections import defaultdict
from difflib import SequenceMatcher

from gdeltdoc import Filters, GdeltDoc

TOPICS = [
    ("Merz", "kw"),               # chancellor — big running story
    ("Ukraine Waffenstillstand", "kw"),
    ("Bundesliga", "kw"),
    ("Hitzewelle", "kw"),         # weather event
]

def norm_title(t):
    t = unicodedata.normalize("NFKD", t.lower())
    t = re.sub(r"[^a-zäöüß0-9 ]", " ", t)
    return re.sub(r"\s+", " ", t).strip()

def cluster_titles(rows, thresh=0.65):
    """Greedy clustering by title similarity."""
    clusters = []
    for row in rows:
        nt = norm_title(row["title"])
        if not nt:
            continue
        for cl in clusters:
            if SequenceMatcher(None, nt, cl["key"]).ratio() >= thresh:
                cl["rows"].append(row)
                break
        else:
            clusters.append({"key": nt, "rows": [row]})
    return clusters

gd = GdeltDoc()
for topic, _ in TOPICS:
    f = Filters(timespan="3d", num_records=250, country="germany",
                language="german", keyword=topic)
    try:
        df = gd.article_search(f)
    except Exception as e:
        print(f"\n### {topic}: query failed: {e!r}")
        time.sleep(45)
        continue
    if df is None or df.empty:
        print(f"\n### {topic}: 0 articles")
        time.sleep(45)
        continue

    rows = df[["title", "domain", "url", "seendate"]].to_dict("records")
    clusters = cluster_titles(rows)
    multi = [c for c in clusters
             if len({r["domain"] for r in c["rows"]}) >= 3]
    multi.sort(key=lambda c: -len({r["domain"] for r in c["rows"]}))

    print(f"\n### {topic}: {len(rows)} articles, {df['domain'].nunique()} domains, "
          f"{len(clusters)} title-clusters, {len(multi)} clusters with >=3 outlets")
    for cl in multi[:5]:
        doms = sorted({r["domain"] for r in cl["rows"]})
        print(f"  [{len(doms)} outlets] {cl['rows'][0]['title'][:90]}")
        print(f"      {', '.join(doms[:10])}")
    time.sleep(45)
