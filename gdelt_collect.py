"""GDELT → clustered German-language story dataset (env: scrap2).

Queries the GDELT DOC API with language="german" only — NO country filter, so
Austrian/Swiss/other German-language outlets are included; each article keeps
its `sourcecountry`. Articles are clustered into cross-outlet "stories" by
title similarity (GDELT returns a flat article list — it has no story id), and
written to data/gdelt/gdelt_stories.jsonl, which the UI's GDELT page reads.

Every run MERGES into the existing output: previously collected articles are
loaded, new ones deduped by URL, and everything is re-clustered.

Rate limiting (see GDELT_NOTES.md): 15s buffer between queries, 60s backoff on
RateLimitError, max 3 attempts. Keep runs small; rerun to grow the dataset.

Usage:
  python gdelt_collect.py                               # default probes, last 3 days
  python gdelt_collect.py --keyword Merz --keyword Bundesliga --timespan 7d
  python gdelt_collect.py --start 2026-08-01 --end 2026-08-04 --keyword Hitzewelle
  python gdelt_collect.py --seed-csv data/gdelt/gdelt_articles_sample.csv   # no API calls
"""
import argparse
import hashlib
import json
import os
import sys
import re
import time
import unicodedata
from difflib import SequenceMatcher

from gdeltdoc import Filters, GdeltDoc

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import paths  # noqa: E402

REPO_ROOT = paths.REPO_ROOT


def default_out():
    """Resolved after --data-dir is parsed, so the flag actually takes effect."""
    return os.path.join(paths.source_dir("gdelt"), "gdelt_stories.jsonl")

DEFAULT_KEYWORDS = ["Merz", "Ukraine", "Bundesliga", "Wetter", "Wirtschaft"]

QUERY_BUFFER_S = 15    # polite gap between queries — never look like rapid search
RATELIMIT_BACKOFF_S = 60
MAX_ATTEMPTS = 3

# Outlets sharing one CMS/newsroom (Ippen group) republish identical articles;
# for the per-story outlet count they are collapsed to one so counts reflect
# independent coverage, not syndication.
MEDIA_GROUPS = {
    "ippen": {"merkur.de", "tz.de", "wa.de", "hna.de", "come-on.de", "fnp.de",
              "op-online.de", "kreiszeitung.de", "24vita.de", "24hamburg.de",
              "fr.de", "ippen.media", "mangfall24.de", "rosenheim24.de",
              "wetterauer-zeitung.de", "giessener-allgemeine.de"},
}

def media_group(domain):
    for name, doms in MEDIA_GROUPS.items():
        if domain in doms:
            return name
    return domain  # its own group

def norm_title(t):
    t = unicodedata.normalize("NFKD", str(t).lower())
    t = re.sub(r"[^a-zäöüß0-9 ]", " ", t)
    return re.sub(r"\s+", " ", t).strip()

def cluster_articles(articles, thresh=0.65):
    """Greedy title-similarity clustering. Returns a list of story dicts."""
    clusters = []
    for art in sorted(articles, key=lambda a: a.get("seendate") or ""):
        nt = norm_title(art["title"])
        if not nt:
            continue
        for cl in clusters:
            if SequenceMatcher(None, nt, cl["key"]).ratio() >= thresh:
                cl["articles"].append(art)
                break
        else:
            clusters.append({"key": nt, "articles": [art]})

    stories = []
    for cl in clusters:
        arts = cl["articles"]
        domains = sorted({a["domain"] for a in arts})
        groups = sorted({media_group(a["domain"]) for a in arts})
        seen = sorted(a.get("seendate") or "" for a in arts)
        probes = sorted({a.get("probe") for a in arts if a.get("probe")})
        story_id = hashlib.sha1(cl["key"].encode()).hexdigest()[:16]
        stories.append({
            "story_id": story_id,
            "title": arts[0]["title"],
            "n_articles": len(arts),
            "n_outlets": len(groups),       # media-group-deduped
            "domains": domains,
            "countries": sorted({a.get("sourcecountry") or "?" for a in arts}),
            "first_seen": seen[0],
            "last_seen": seen[-1],
            "probes": probes,
            "articles": arts,
        })
    stories.sort(key=lambda s: (-s["n_outlets"], -s["n_articles"]))
    return stories

def load_existing_articles(path):
    if not os.path.isfile(path):
        return []
    arts = []
    with open(path) as fh:
        for line in fh:
            line = line.strip()
            if line:
                arts.extend(json.loads(line)["articles"])
    return arts

def df_to_articles(df, probe):
    arts = []
    for _, r in df.iterrows():
        arts.append({
            "title": r.get("title", ""),
            "url": r.get("url", ""),
            "domain": r.get("domain", ""),
            "seendate": r.get("seendate", ""),
            "sourcecountry": r.get("sourcecountry", ""),
            "language": r.get("language", ""),
            "socialimage": r.get("socialimage", "") or "",
            "probe": probe,
        })
    return arts

def query_gdelt(gd, probe_label, **filter_kw):
    f = Filters(num_records=250, language="german", **filter_kw)
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            df = gd.article_search(f)
            time.sleep(QUERY_BUFFER_S)
            return df
        except Exception as e:
            print(f"  {probe_label}: attempt {attempt} failed ({e!r})"
                  + (f" — backing off {RATELIMIT_BACKOFF_S}s" if attempt < MAX_ATTEMPTS else ""))
            if attempt < MAX_ATTEMPTS:
                time.sleep(RATELIMIT_BACKOFF_S)
    return None

def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--keyword", action="append", default=[],
                    help="keyword probe (repeatable); default: a small topic mix")
    ap.add_argument("--timespan", default="3d",
                    help="lookback window, e.g. 3d, 12h (ignored if --start given)")
    ap.add_argument("--start", help="start date YYYY-MM-DD (temporal mode, back to 2017)")
    ap.add_argument("--end", help="end date YYYY-MM-DD")
    ap.add_argument("--seed-csv",
                    help="ingest an existing GDELT sample CSV instead of querying the API")
    paths.add_data_dir_arg(ap)
    ap.add_argument("--out", default=None,
                    help="output stories JSONL (merged into on every run)")
    args = ap.parse_args()
    paths.use_data_dir(args.data_dir)
    args.out = args.out or default_out()
    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)

    new_articles = []
    if args.seed_csv:
        import pandas as pd
        df = pd.read_csv(args.seed_csv)
        probe_col = df["probe"] if "probe" in df else None
        for probe, g in (df.groupby("probe") if probe_col is not None else [("csv", df)]):
            new_articles.extend(df_to_articles(g, probe))
        print(f"Seeded {len(new_articles)} articles from {args.seed_csv}")
    else:
        keywords = args.keyword or DEFAULT_KEYWORDS
        window = ({"start_date": args.start, "end_date": args.end}
                  if args.start else {"timespan": args.timespan})
        gd = GdeltDoc()
        for kw in keywords:
            df = query_gdelt(gd, f"kw:{kw}", keyword=kw, **window)
            if df is None or df.empty:
                print(f"  kw:{kw}: no articles")
                continue
            print(f"  kw:{kw}: {len(df)} articles, {df['domain'].nunique()} domains")
            new_articles.extend(df_to_articles(df, f"kw:{kw}"))

    existing = load_existing_articles(args.out)
    by_url = {a["url"]: a for a in existing}
    added = 0
    for a in new_articles:
        if a["url"] and a["url"] not in by_url:
            by_url[a["url"]] = a
            added += 1
    print(f"\n{len(existing)} existing + {added} new articles "
          f"(deduped from {len(new_articles)} fetched)")

    stories = cluster_articles(list(by_url.values()))
    multi = sum(1 for s in stories if s["n_outlets"] >= 3)
    with open(args.out, "w") as fh:
        for s in stories:
            fh.write(json.dumps(s, ensure_ascii=False) + "\n")
    print(f"Wrote {len(stories)} stories ({multi} with >=3 independent outlets) → {args.out}")

if __name__ == "__main__":
    main()
