"""Cluster a large German GDELT article dump into stories (env: scrap2).

gdelt_collect.cluster_articles() compares every article against every existing
cluster with SequenceMatcher — fine for the ~1k articles the DOC API returned,
hopeless for the millions that gdelt_bq_pull.py / gdelt_dump_pull.py produce.

This does the same job at scale:
  * articles are bucketed by day, and only compared within a +/-1 day window
    (news stories are picked up within hours, not weeks),
  * inside a bucket, candidates are narrowed by a token inverted index before
    any expensive similarity call.

Output is the same story schema gdelt_stories.jsonl already uses, so the UI's
GDELT page and gdelt_enrich.py keep working unchanged.

Usage:
  python gdelt_cluster_bulk.py --articles data/gdelt/gdelt_articles_de.jsonl
  python gdelt_cluster_bulk.py --articles ... --min-outlets 3 --out stories.jsonl
"""
import argparse
import hashlib
import json
import os
import sys
import re
import unicodedata
from collections import defaultdict
from concurrent.futures import ProcessPoolExecutor
from difflib import SequenceMatcher

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import paths  # noqa: E402

REPO_ROOT = paths.REPO_ROOT


def default_out():
    """Resolved after --data-dir is parsed, so the flag actually takes effect."""
    return os.path.join(paths.source_dir("gdelt"), "gdelt_stories_de.jsonl")

MEDIA_GROUPS = {
    "ippen": {"merkur.de", "tz.de", "wa.de", "hna.de", "come-on.de", "fnp.de",
              "op-online.de", "kreiszeitung.de", "24vita.de", "24hamburg.de",
              "fr.de", "ippen.media", "mangfall24.de", "rosenheim24.de",
              "wetterauer-zeitung.de", "giessener-allgemeine.de"},
}

STOP = {"der", "die", "das", "und", "in", "im", "von", "mit", "auf", "für", "ist",
        "des", "dem", "den", "zu", "ein", "eine", "einen", "am", "als", "auch",
        "nach", "bei", "aus", "wird", "sich", "es", "an", "so", "wie", "vor"}


def media_group(domain):
    for name, doms in MEDIA_GROUPS.items():
        if domain in doms:
            return name
    return domain


def norm_title(t):
    t = unicodedata.normalize("NFKD", str(t).lower())
    t = re.sub(r"[^a-zäöüß0-9 ]", " ", t)
    return re.sub(r"\s+", " ", t).strip()


def tokens(nt):
    return [w for w in nt.split() if len(w) > 3 and w not in STOP]


def day_of(seendate):
    return str(seendate)[:8]


def cluster_bucket(arts, thresh, index_top):
    """Greedy clustering inside one day-bucket, narrowed by a token index."""
    clusters = []
    postings = defaultdict(list)          # token -> cluster indices
    for art in arts:
        nt = norm_title(art.get("title", ""))
        if not nt:
            continue
        toks = tokens(nt)
        if not toks:
            continue
        # only clusters sharing a rare-ish token are worth comparing
        cand = set()
        for t in toks[:index_top]:
            cand.update(postings[t])
        best, best_i = 0.0, -1
        for i in cand:
            r = SequenceMatcher(None, nt, clusters[i]["key"]).ratio()
            if r > best:
                best, best_i = r, i
        if best >= thresh:
            clusters[best_i]["articles"].append(art)
        else:
            clusters.append({"key": nt, "articles": [art]})
            for t in toks[:index_top]:
                postings[t].append(len(clusters) - 1)
    return clusters


def build_stories(job):
    """Cluster one window and return its story dicts. Runs in a worker process."""
    arts, thresh, index_top, min_outlets = job
    arts.sort(key=lambda a: a.get("seendate") or "")
    out = []
    for cl in cluster_bucket(arts, thresh, index_top):
        a_list = cl["articles"]
        groups = sorted({media_group(a["domain"]) for a in a_list})
        if len(groups) < min_outlets:
            continue
        seen = sorted(a.get("seendate") or "" for a in a_list)
        # The day is part of the id: windows are per-day, so a recurring
        # headline ("Die Wetteraussichten") would otherwise hash to the same
        # id every day and collide downstream.
        ident = f"{cl['key']}|{day_of(seen[0])}"
        out.append({
            "story_id": hashlib.sha1(ident.encode()).hexdigest()[:16],
            "title": a_list[0]["title"],
            "n_articles": len(a_list),
            "n_outlets": len(groups),
            "domains": sorted({a["domain"] for a in a_list}),
            "countries": sorted({a.get("sourcecountry") or "?" for a in a_list}),
            "first_seen": seen[0],
            "last_seen": seen[-1],
            "probes": sorted({a.get("probe") for a in a_list if a.get("probe")}),
            "articles": a_list,
        })
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--articles", required=True, help="article JSONL from a puller")
    paths.add_data_dir_arg(ap)
    ap.add_argument("--out", default=None)
    ap.add_argument("--thresh", type=float, default=0.65)
    ap.add_argument("--index-top", type=int, default=6,
                    help="tokens per title used for blocking")
    ap.add_argument("--min-outlets", type=int, default=1,
                    help="only write stories with at least this many independent outlets")
    ap.add_argument("--span-days", type=int, default=1,
                    help="merge buckets across +/- this many days")
    ap.add_argument("--workers", type=int, default=min(32, os.cpu_count() or 8),
                    help="parallel worker processes (windows are independent)")
    args = ap.parse_args()
    paths.use_data_dir(args.data_dir)
    args.out = args.out or default_out()

    by_day = defaultdict(list)
    seen_urls = set()
    n_read = n_dup = n_notitle = 0
    with open(args.articles) as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            a = json.loads(line)
            n_read += 1
            u = a.get("url")
            if not u or u in seen_urls:
                n_dup += 1
                continue
            seen_urls.add(u)
            if not a.get("title"):
                n_notitle += 1
                continue
            by_day[day_of(a.get("seendate"))].append(a)
    print(f"read {n_read} rows | {n_dup} dupe urls | {n_notitle} without title | "
          f"{len(seen_urls)-n_dup} usable across {len(by_day)} days")

    # Group consecutive days into overlapping windows so a story that breaks
    # near midnight is not split across two buckets.
    days = sorted(by_day)
    windows = []
    if args.span_days <= 0:
        windows = [[d] for d in days]
    else:
        step = args.span_days + 1
        for i in range(0, len(days), step):
            windows.append(days[i:i + step])

    # Windows are fully independent, so fan them out across cores — clustering
    # is the slow half of this pipeline and is pure CPU.
    jobs = [([a for d in grp for a in by_day[d]],
             args.thresh, args.index_top, args.min_outlets) for grp in windows]
    stories = []
    print(f"clustering {len(jobs)} windows across {args.workers} processes ...", flush=True)
    with ProcessPoolExecutor(max_workers=args.workers) as ex:
        for w, out in enumerate(ex.map(build_stories, jobs), 1):
            stories.extend(out)
            if w % 10 == 0 or w == len(jobs):
                print(f"  window {w}/{len(jobs)} | {len(stories)} stories so far", flush=True)

    stories.sort(key=lambda s: (-s["n_outlets"], -s["n_articles"]))
    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    with open(args.out, "w") as fh:
        for s in stories:
            fh.write(json.dumps(s, ensure_ascii=False) + "\n")
    multi = sum(1 for s in stories if s["n_outlets"] >= 3)
    print(f"\nWrote {len(stories)} stories ({multi} with >=3 independent outlets) → {args.out}")


if __name__ == "__main__":
    main()
