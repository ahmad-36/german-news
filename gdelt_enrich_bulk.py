"""Fetch article bodies for a large GDELT story set (env: scrap2).

gdelt_enrich.py fetches one story at a time with a fixed 1.5s sleep, which is
right for a few hundred stories and ~78 hours for the 173k-story German set.
This does the same extraction concurrently, while staying polite:

  * one in-flight request per domain, and at least --domain-delay seconds
    between two requests to the SAME domain — concurrency comes from working
    many domains at once, never from hammering one,
  * the representative article per story is chosen to spread load across the
    outlets that covered it (gdelt_enrich.py's PREFERRED list would funnel
    173k requests onto ~15 domains), preferring known-scrapeable outlets only
    as a tie-break between equally-loaded ones,
  * the cache is append-only JSONL, so the run is resumable and an interrupted
    job never loses fetched work.

Enrichment records keep gdelt_enrich.py's shape (url/summary/body/image/
image_caption/text_len), so unify.py and the UI need no changes.

Usage:
  python gdelt_enrich_bulk.py --stories data/gdelt/gdelt_stories_de_min3.jsonl
  python gdelt_enrich_bulk.py --stories ... --workers 24 --limit 5000
  python gdelt_enrich_bulk.py --attach-only     # no fetching: cache -> stories
"""
import argparse
import json
import os
import sys
import multiprocessing
import time
from collections import defaultdict
from concurrent.futures import ProcessPoolExecutor

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import paths  # noqa: E402

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gdelt_enrich import PREFERRED, extract  # noqa: E402

REPO_ROOT = paths.REPO_ROOT
_PREF_RANK = {d: i for i, d in enumerate(PREFERRED)}


# Work is sharded one-domain-per-task and run in PROCESSES, not threads:
# curl_cffi's libcurl bindings corrupt the heap under concurrent thread use
# ("double free or corruption" / "malloc_consolidate(): unaligned fastbin
# chunk") at 32+ threads. Processes isolate that state, and because a domain
# is never split across tasks, the per-domain delay needs no shared clock.
_W = {}


def _init_worker(cache_path, lock, delay):
    _W["cache"] = cache_path
    _W["lock"] = lock
    _W["delay"] = delay


def fetch_domain(job):
    """Fetch one domain's articles sequentially, appending each record."""
    _domain, arts = job
    ok = err = 0
    out = []
    for i, a in enumerate(arts):
        if i:
            time.sleep(_W["delay"])
        try:
            rec = extract(a["url"])
        except Exception as e:
            rec = {"url": a["url"], "error": f"{type(e).__name__}: {e}"[:150]}
        out.append(rec)
        if rec.get("error"):
            err += 1
        else:
            ok += 1
        # Flush in batches so a killed run loses at most a few fetches.
        if len(out) >= 20 or i == len(arts) - 1:
            with _W["lock"]:
                with open(_W["cache"], "a") as fh:
                    for r in out:
                        fh.write(json.dumps(r, ensure_ascii=False) + "\n")
            out = []
    return ok, err


def choose_articles(stories, good_urls, tried_urls):
    """One untried article per still-unenriched story, balancing domain load.

    A story is done only once some outlet yielded a body. Outlets that failed
    (403 paywalls, 404/410 link rot — together ~27% of first attempts) are
    skipped, so re-running the script retries those stories via a *different*
    outlet that covered the same event rather than refetching the dead URL.
    """
    load = defaultdict(int)
    picked = []
    # Stories with the fewest outlets have the least choice, so let them pick
    # first; wide stories then fill in whichever domain is still least loaded.
    order = sorted(range(len(stories)), key=lambda i: len(stories[i].get("domains") or ()))
    for i in order:
        s = stories[i]
        arts = s.get("articles") or []
        if not arts:
            continue
        if any(a.get("url") in good_urls for a in arts):
            continue
        candidates = [a for a in arts if a.get("url") not in tried_urls]
        if not candidates:
            continue          # every outlet for this story has already failed
        best = min(candidates, key=lambda a: (load[a.get("domain", "")],
                                              _PREF_RANK.get(a.get("domain", ""), 999)))
        load[best.get("domain", "")] += 1
        picked.append((s.get("n_outlets", 0), best))
    # Fetch the most-covered stories first: --limit and any interruption then
    # leave the corpus with its most useful stories enriched, not its thinnest.
    picked.sort(key=lambda p: -p[0])
    return [a for _, a in picked], load


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    paths.add_data_dir_arg(ap)
    ap.add_argument("--stories", default=None, help="stories JSONL to enrich")
    ap.add_argument("--cache", default=None, help="append-only JSONL enrichment cache")
    ap.add_argument("--out", default=None, help="enriched stories JSONL (default: in place)")
    ap.add_argument("--workers", type=int, default=24)
    ap.add_argument("--domain-delay", type=float, default=2.0,
                    help="minimum seconds between two requests to the same domain")
    ap.add_argument("--limit", type=int, default=0, help="max fetches this run (0 = all)")
    ap.add_argument("--attach-only", action="store_true",
                    help="skip fetching; just attach the existing cache to the stories")
    args = ap.parse_args()

    paths.use_data_dir(args.data_dir)
    gdelt_dir = paths.source_dir("gdelt")
    args.stories = args.stories or os.path.join(gdelt_dir, "gdelt_stories_de_min3.jsonl")
    args.cache = args.cache or os.path.join(gdelt_dir, "gdelt_enrichment_de.jsonl")
    args.out = args.out or args.stories

    with open(args.stories) as fh:
        stories = [json.loads(l) for l in fh if l.strip()]
    print(f"{len(stories)} stories from {os.path.relpath(args.stories, REPO_ROOT)}")

    cache = {}
    if os.path.isfile(args.cache):
        with open(args.cache) as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                except json.JSONDecodeError:
                    continue          # tolerate a half-written final line
                if rec.get("url"):
                    cache[rec["url"]] = rec
        print(f"cache: {len(cache)} urls already fetched")

    if not args.attach_only:
        good = {u for u, r in cache.items() if not r.get("error") and r.get("body")}
        picks, load = choose_articles(stories, good, set(cache))
        if args.limit:
            picks = picks[:args.limit]
        print(f"{len(picks)} articles to fetch across {len(load)} domains "
              f"(busiest: {sorted(load.values(), reverse=True)[:3]})")

        by_domain = defaultdict(list)
        for a in picks:
            by_domain[a.get("domain", "")].append(a)
        # Biggest domains first so the longest pole starts at t=0.
        jobs = sorted(by_domain.items(), key=lambda kv: -len(kv[1]))
        print(f"{len(jobs)} domain shards, largest {len(jobs[0][1])} articles "
              f"(~{len(jobs[0][1]) * args.domain_delay / 3600:.1f}h floor)")

        t0 = time.time()
        ok = err = 0
        lock = multiprocessing.Manager().Lock()
        with ProcessPoolExecutor(max_workers=args.workers, initializer=_init_worker,
                                 initargs=(args.cache, lock, args.domain_delay)) as ex:
            for i, (o, e) in enumerate(ex.map(fetch_domain, jobs), 1):
                ok += o
                err += e
                if i % 20 == 0 or i == len(jobs):
                    el = time.time() - t0
                    rate = (ok + err) / el if el else 0
                    left = len(picks) - (ok + err)
                    print(f"  shard {i}/{len(jobs)} | ok {ok} err {err} | "
                          f"{rate:.1f}/s | ETA {left / rate / 3600:.1f}h" if rate else
                          f"  shard {i}/{len(jobs)}", flush=True)
        print(f"fetched {ok} ok, {err} errors")

        # Re-read the cache: workers appended to it directly.
        with open(args.cache) as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if rec.get("url"):
                    cache[rec["url"]] = rec

    # Attach: a story takes the first of its articles that has a good record.
    n = 0
    for s in stories:
        for a in s.get("articles") or []:
            rec = cache.get(a.get("url"))
            if rec and not rec.get("error") and rec.get("body"):
                s["enrichment"] = rec
                n += 1
                break
    tmp = args.out + ".tmp"
    with open(tmp, "w") as fh:
        for s in stories:
            fh.write(json.dumps(s, ensure_ascii=False) + "\n")
    os.replace(tmp, args.out)
    print(f"attached enrichment to {n}/{len(stories)} stories → "
          f"{os.path.relpath(args.out, REPO_ROOT)}")


if __name__ == "__main__":
    main()
