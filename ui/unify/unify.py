#!/usr/bin/env python3
"""Convert every scraper's output into one unified story-level JSONL format.

Sources (each optional — missing inputs are skipped with a warning):
  ground_news    data/ground_news/ground_news.jsonl        (this repo's scraper)
  gdelt          data/gdelt/gdelt_stories_de_min3.jsonl    (gdelt_dump_pull.py +
                                                            gdelt_cluster_bulk.py; the
                                                            3+-outlet slice of the German
                                                            Jan–Aug 2026 census. The old
                                                            DOC-API gdelt_stories.jsonl
                                                            still works via --gdelt)
  eventregistry  data/eventregistry/articles_germany.jsonl (flat articles, full body)
  allsides       Qbias allsides_crawl output               (external repo)
  multi_source   Qbias multi_source_scrape per-domain dir  (full bodies, joined onto
                                                            AllSides articles by URL —
                                                            it is not its own story list)

Unified record = one news STORY with a list of ARTICLES, each tagged with a
coarse 3-way stance (left/center/right/unknown) and a fine-grained bias rating.
GDELT and Event Registry have no bias ratings, so their articles are stance
"unknown"; Event Registry stories are single-article (it has no clustering).

Schema per line:
{
  "story_id":        "<dataset>__<slug-or-id>",
  "source_dataset":  "ground_news" | "allsides" | "gdelt" | "eventregistry",
  "story_url":       str|null,
  "date":            str|null,     # ISO 8601 where the source allows it
  "title":           str,
  "story_summary":   str|null,
  "stance_summaries": {"left": str|null, "center": ..., "right": ...},
  "topics":          [str],
  "bias_distribution": {"left": float, "center": float, "right": float} | null,
  "meta":            {...},        # story-level source-specific extras, verbatim
  "articles": [{
      "article_id":  "<story_id>__a<idx>",
      "stance":      "left"|"center"|"right"|"unknown",
      "bias_rating": "far_left"|"left"|"lean_left"|"center"|"lean_right"|"right"|"far_right"|"unknown",
      "source_name": str,
      "url":         str,
      "date":        str|null,
      "headline":    str,
      "description": str|null,
      "body_text":   str|null,
      "lang":        str|null,     # as given by the source (GN: "de", ER: "deu")
      "paywall":     bool|null,
      "is_featured": bool,
      "news_type":   str|null,
      "meta":        {...}         # article-level source-specific extras
  }]
}

Outputs one unified_<source>.jsonl per available source plus unified_all.jsonl.
"""
import argparse
import glob
import json
import os
import re
import sys
from urllib.parse import urlparse

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import paths  # noqa: E402
from textlib import lede  # noqa: E402

# fine-grained rating normalization (all datasets -> one vocabulary)
RATING_MAP = {
    "farleft": "far_left", "far left": "far_left",
    "left": "left",
    "leanleft": "lean_left", "lean left": "lean_left",
    "center": "center",
    "leanright": "lean_right", "lean right": "lean_right",
    "right": "right",
    "farright": "far_right", "far right": "far_right",
}
# fine-grained -> coarse stance
STANCE_OF = {
    "far_left": "left", "left": "left", "lean_left": "left",
    "center": "center",
    "lean_right": "right", "right": "right", "far_right": "right",
    "unknown": "unknown",
}


def norm_rating(raw):
    if not raw:
        return "unknown"
    return RATING_MAP.get(str(raw).strip().lower(), "unknown")


def gdelt_ts_to_iso(ts):
    """GDELT timestamp -> 2026-07-31T02:30:00Z (returned as-is if malformed).

    Handles both shapes the GDELT routes produce: the DOC API's
    `20260731T023000Z` and the raw GKG/BigQuery `20260731023000`.
    """
    if not ts:
        return None
    d = re.sub(r"\D", "", str(ts))
    if len(d) != 14:
        return ts
    return f"{d[0:4]}-{d[4:6]}-{d[6:8]}T{d[8:10]}:{d[10:12]}:{d[12:14]}Z"


# ── Ground News ──────────────────────────────────────────────────────────────

def convert_ground_news(path):
    stories = []
    with open(path) as f:
        for line in f:
            if not line.strip():
                continue
            r = json.loads(line)
            story_id = f"groundnews__{r['slug']}"
            articles = []
            for i, s in enumerate(r.get("sources") or []):
                rating = norm_rating(s.get("source_bias"))
                articles.append({
                    "article_id": f"{story_id}__a{i}",
                    "stance": STANCE_OF[rating],
                    "bias_rating": rating,
                    "source_name": s.get("source_name"),
                    "url": s.get("url"),
                    "date": s.get("date"),
                    "headline": s.get("title"),
                    "description": s.get("description") or None,
                    "body_text": None,
                    "lang": s.get("lang"),
                    "paywall": {"yes": True, "no": False}.get(s.get("paywall")),
                    "is_featured": False,
                    "news_type": None,
                    "meta": {
                        "source_slug": s.get("source_slug"),
                        "bias_ratings": s.get("bias_ratings") or [],
                        "factuality": s.get("factuality") or [],
                        "source_place": s.get("source_place") or [],
                        "original_title": s.get("original_title") or None,
                        "original_description": s.get("original_description") or None,
                        "is_german_publisher": s.get("is_german_publisher"),
                        "paywall_raw": s.get("paywall"),
                    },
                })
            stories.append({
                "story_id": story_id,
                "source_dataset": "ground_news",
                "story_url": r.get("share_url"),
                "date": r.get("date"),
                "title": (r.get("title") or "").strip(),
                "story_summary": r.get("description") or None,
                "stance_summaries": {
                    "left": r.get("summary_left") or None,
                    "center": r.get("summary_center") or None,
                    "right": r.get("summary_right") or None,
                },
                "topics": [t["name"] for t in r.get("topics") or [] if t.get("name")],
                "bias_distribution": {
                    "left": r.get("left_pct"),
                    "center": r.get("center_pct"),
                    "right": r.get("right_pct"),
                },
                "meta": {
                    "slug": r.get("slug"),
                    "generated_headline": r.get("generated_headline") or None,
                    "dek": r.get("dek") or None,
                    "blindspot": r.get("blindspot") or None,
                    "bias_comparison": r.get("bias_comparison") or None,
                    "place": r.get("place") or [],
                    "topics_typed": r.get("topics") or [],
                    "source_count": r.get("source_count"),
                    "bias_source_count": r.get("bias_source_count"),
                },
                "articles": articles,
            })
    return stories


# ── AllSides (+ multi_source_scrape bodies) ──────────────────────────────────

def load_body_texts(ms_dir):
    """URL -> full body text, from multi_source_scrape per-domain files."""
    bodies = {}
    for fp in glob.glob(os.path.join(ms_dir, "*.json")):
        with open(fp) as f:
            data = json.load(f)
        for stances in data.values():
            for rec in stances.values():
                if rec.get("execution_status") == "SUCCESS" and rec.get("extracted_body_text"):
                    bodies[rec["url"]] = rec["extracted_body_text"]
    return bodies


def convert_allsides(path, bodies):
    stories = []
    with open(path) as f:
        for line in f:
            if not line.strip():
                continue
            r = json.loads(line)
            slug = urlparse(r["headline_link"]).path.rstrip("/").split("/")[-1]
            story_id = f"allsides__{slug}"
            articles, seen_urls = [], set()

            def add(a, stance, featured):
                url = a.get("link") or ""
                if not a.get("headline") or url in seen_urls:
                    return
                seen_urls.add(url)
                articles.append({
                    "article_id": f"{story_id}__a{len(articles)}",
                    "stance": stance,
                    "bias_rating": norm_rating(a.get("rating")),
                    "source_name": a.get("source"),
                    "url": url,
                    "date": None,
                    "headline": a.get("headline"),
                    "description": a.get("content") or a.get("summary") or None,
                    "body_text": bodies.get(url),
                    "lang": None,
                    "paywall": None,
                    "is_featured": featured,
                    "news_type": a.get("news_type") or None,
                    "meta": {
                        "allsides_link": a.get("allsides_link"),
                        "image_link": a.get("image_link") or None,
                    },
                })

            for stance in ("left", "center", "right"):
                feat = r.get(stance)
                if feat:
                    add(feat, stance, True)
                for a in r.get(f"more_{stance}") or []:
                    add(a, stance, False)

            stories.append({
                "story_id": story_id,
                "source_dataset": "allsides",
                "story_url": r["headline_link"],
                "date": r.get("date"),
                "title": (r.get("headline") or "").strip(),
                "story_summary": r.get("summary") or None,
                "stance_summaries": {"left": None, "center": None, "right": None},
                "topics": sorted({t for t in [r.get("topic"), *(r.get("tags") or [])] if t}),
                "bias_distribution": None,
                "meta": {},
                "articles": articles,
            })
    return stories


# ── GDELT (clustered stories from gdelt_collect.py) ──────────────────────────

def gdelt_topics(story, top_n=10):
    """Story topics from GKG themes, most-shared first.

    The DOC API route put its query probes in `probes`, which doubled as
    topics; the raw-dump/BigQuery routes have one constant probe label but do
    carry GKG's own theme taxonomy per article, which is far more informative.
    Falls back to the probe labels when themes are absent (DOC API data).
    """
    counts = {}
    for a in story.get("articles") or []:
        for entry in (a.get("themes") or "").split(";"):
            name = entry.split(",")[0].strip()
            if name:
                counts[name] = counts.get(name, 0) + 1
    if not counts:
        return sorted({p for p in story.get("probes") or [] if p})
    ranked = sorted(counts, key=lambda t: (-counts[t], t))
    return ranked[:top_n]


def convert_gdelt(path):
    stories = []
    with open(path) as f:
        for line in f:
            if not line.strip():
                continue
            r = json.loads(line)
            story_id = f"gdelt__{r['story_id']}"
            enrichment = r.get("enrichment") or {}
            articles = []
            for i, a in enumerate(r.get("articles") or []):
                enriched_here = bool(enrichment) and enrichment.get("url") == a.get("url")
                articles.append({
                    "article_id": f"{story_id}__a{i}",
                    "stance": "unknown",
                    "bias_rating": "unknown",
                    "source_name": a.get("domain"),
                    "url": a.get("url"),
                    "date": gdelt_ts_to_iso(a.get("seendate")),
                    "headline": a.get("title"),
                    "description": enrichment.get("summary") if enriched_here else None,
                    "body_text": enrichment.get("body") if enriched_here else None,
                    "lang": a.get("language") or "german",
                    "paywall": None,
                    "is_featured": False,
                    "news_type": None,
                    "meta": {
                        "probe": a.get("probe"),
                        "sourcecountry": a.get("sourcecountry"),
                        "socialimage": a.get("socialimage") or None,
                    },
                })
            stories.append({
                "story_id": story_id,
                "source_dataset": "gdelt",
                "story_url": None,
                "date": gdelt_ts_to_iso(r.get("first_seen")),
                "title": (r.get("title") or "").strip(),
                "story_summary": enrichment.get("summary") or None,
                "stance_summaries": {"left": None, "center": None, "right": None},
                "topics": gdelt_topics(r),
                "bias_distribution": None,
                "meta": {
                    "n_outlets": r.get("n_outlets"),
                    "countries": r.get("countries") or [],
                    "first_seen": gdelt_ts_to_iso(r.get("first_seen")),
                    "last_seen": gdelt_ts_to_iso(r.get("last_seen")),
                    "enrichment": enrichment or None,
                },
                "articles": articles,
            })
    return stories


# ── Event Registry ───────────────────────────────────────────────────────────

def convert_eventregistry(path):
    stories, seen = [], set()
    with open(path) as f:
        for line in f:
            if not line.strip():
                continue
            r = json.loads(line)
            uri = r.get("uri") or ""
            if not uri or uri in seen:
                continue
            seen.add(uri)
            story_id = f"eventregistry__{uri}"
            source = r.get("source") or {}
            body = r.get("body") or None
            articles = [{
                "article_id": f"{story_id}__a0",
                "stance": "unknown",
                "bias_rating": "unknown",
                "source_name": source.get("title") or source.get("uri"),
                "url": r.get("url"),
                "date": r.get("dateTimePub") or r.get("dateTime"),
                "headline": r.get("title"),
                "description": (lede(body) if body else None),
                "body_text": body,
                "lang": r.get("lang"),
                "paywall": None,
                "is_featured": False,
                "news_type": None,
                "meta": {
                    "source_uri": source.get("uri"),
                    "authors": [a.get("name") for a in (r.get("authors") or []) if a.get("name")],
                    "image": r.get("image") or None,
                    "sentiment": r.get("sentiment"),
                    "relevance": r.get("relevance"),
                },
            }]
            stories.append({
                "story_id": story_id,
                "source_dataset": "eventregistry",
                "story_url": r.get("url"),
                "date": r.get("dateTimePub") or r.get("dateTime"),
                "title": (r.get("title") or "").strip(),
                "story_summary": (lede(body) if body else None),
                "stance_summaries": {"left": None, "center": None, "right": None},
                "topics": [],
                "bias_distribution": None,
                "meta": {"uri": uri, "isDuplicate": r.get("isDuplicate")},
                "articles": articles,
            })
    return stories


# ── Driver ───────────────────────────────────────────────────────────────────

def dump(path, stories):
    with open(path, "w") as f:
        for s in stories:
            f.write(json.dumps(s, ensure_ascii=False) + "\n")


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    paths.add_data_dir_arg(ap)
    ap.add_argument("--only", choices=paths.SOURCES, action="append", default=None,
                    metavar="SOURCE",
                    help="convert only this source (repeatable); unified_all.jsonl is "
                         "then rebuilt from the per-source files on disk, so a partial "
                         "run never drops the others")
    ap.add_argument("--ground-news", default=None)
    ap.add_argument("--gdelt", default=None,
                    help="clustered stories JSONL from gdelt_collect.py")
    ap.add_argument("--eventregistry", default=None)
    ap.add_argument("--allsides", default=None,
                    help=f"AllSides crawl JSONL (external Qbias repo, ${paths.QBIAS_DIR_ENV})")
    ap.add_argument("--multi-source-dir", default=None,
                    help="per-domain body-text JSONs, joined onto AllSides articles by URL")
    ap.add_argument("--out-dir", default=None)
    args = ap.parse_args()

    paths.use_data_dir(args.data_dir)
    inputs = {
        "ground_news": args.ground_news or os.path.join(paths.source_dir("ground_news"),
                                                        "ground_news.jsonl"),
        "gdelt": args.gdelt or os.path.join(paths.source_dir("gdelt"),
                                            "gdelt_stories_de_min3.jsonl"),
        "eventregistry": args.eventregistry or os.path.join(paths.source_dir("eventregistry"),
                                                            "articles_germany.jsonl"),
        "allsides": args.allsides or paths.allsides_crawl(),
    }
    multi_source_dir = args.multi_source_dir or paths.allsides_bodies_dir()
    out_dir = args.out_dir or paths.unified_dir()
    wanted = set(args.only or paths.SOURCES)

    os.makedirs(out_dir, exist_ok=True)
    converted = set()

    def run(name, fn, *fn_args):
        if name not in wanted:
            return
        stories = fn(*fn_args)
        out = os.path.join(out_dir, f"unified_{name}.jsonl")
        dump(out, stories)
        converted.add(name)
        n_art = sum(len(s["articles"]) for s in stories)
        n_body = sum(1 for s in stories for a in s["articles"] if a["body_text"])
        by_stance = {}
        for s in stories:
            for a in s["articles"]:
                by_stance[a["stance"]] = by_stance.get(a["stance"], 0) + 1
        print(f"{name}: {len(stories)} stories, {n_art} articles "
              f"({n_body} with full body text), stance dist {by_stance} -> {out}")

    for name in ("ground_news", "gdelt", "eventregistry", "allsides"):
        if name not in wanted:
            continue
        src = inputs[name]
        if not src or not os.path.isfile(src):
            print(f"skip {name}: {src or '<no path configured>'} not found", file=sys.stderr)
            continue
        if name == "allsides":
            bodies = load_body_texts(multi_source_dir) if os.path.isdir(multi_source_dir) else {}
            if not bodies:
                print(f"note: no multi_source bodies found under {multi_source_dir}", file=sys.stderr)
            run(name, convert_allsides, src, bodies)
        else:
            run(name, {"ground_news": convert_ground_news, "gdelt": convert_gdelt,
                       "eventregistry": convert_eventregistry}[name], src)

    # unified_all is a concatenation of whatever per-source files exist on
    # disk, not just of this run — so converting one source keeps the others.
    combined = os.path.join(out_dir, "unified_all.jsonl")
    n_all = 0
    with open(combined, "w") as out_fh:
        for src_file in sorted(glob.glob(os.path.join(out_dir, "unified_*.jsonl"))):
            if os.path.basename(src_file) == "unified_all.jsonl":
                continue
            with open(src_file) as in_fh:
                for line in in_fh:
                    if line.strip():
                        out_fh.write(line if line.endswith("\n") else line + "\n")
                        n_all += 1
    print(f"\nunified_all.jsonl: {n_all} stories total "
          f"(converted this run: {', '.join(sorted(converted)) or 'none'})")


if __name__ == "__main__":
    main()
