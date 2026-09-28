"""Enrich GDELT stories with summary + lead image + caption (env: scrap2).

GDELT stores metadata only — no body text, no pictures. This script fills the
gap by fetching ONE representative article per story from the outlet itself
(preferring outlets known to be open/scrapeable, see GDELT_NOTES.md and
data/discovery/scrapeability_report.json) and extracting:

  - body           the extracted article text, page furniture stripped (capped)
  - summary        the article's first real prose paragraphs (~600 chars)
  - image          og:image (outlets put the lead image there predictably)
  - image_caption  <figcaption> of the lead figure, when the page has one

Results are attached to each story as an "enrichment" field in
data/gdelt/gdelt_stories.jsonl AND cached per-URL in data/gdelt/gdelt_enrichment.json,
so re-clustering by gdelt_collect.py never loses fetched work — just rerun
this script afterwards and cached stories re-attach without refetching.

Usage:
  python gdelt_enrich.py                    # enrich stories with >=2 outlets, up to 80 fetches
  python gdelt_enrich.py --min-outlets 1 --limit 200
  python gdelt_enrich.py --reclean          # no fetching: re-derive body/summary from the cache
"""
import argparse
import json
import os
import re
import sys
import time

import trafilatura
from bs4 import BeautifulSoup
from curl_cffi import requests as creq

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import paths  # noqa: E402
from textlib import clean_text, lede  # noqa: E402

REPO_ROOT = paths.REPO_ROOT

# Outlets verified open + cleanly extractable (check_scrapeability.py results),
# in preference order. Stories are enriched from the first of these that
# covered them; anything else is a fallback.
PREFERRED = ["n-tv.de", "focus.de", "t-online.de", "ndr.de", "mdr.de", "zeit.de",
             "welt.de", "spiegel.de", "merkur.de", "tz.de", "wa.de", "hna.de",
             "fnp.de", "op-online.de", "come-on.de"]

FETCH_DELAY_S = 1.5
# Chars of article text kept per story; None = keep the whole extraction (the
# longest German article seen here is ~85k chars, so the corpus stays small).
# Records stored under an older, lower cap carry "truncated": True — refetch
# them with --refetch-truncated.
BODY_CAP = None
LEGACY_BODY_CAP = 8000  # the cap older cache entries were stored under

def pick_article(story):
    by_domain = {}
    for a in story["articles"]:
        by_domain.setdefault(a["domain"], a)
    for dom in PREFERRED:
        if dom in by_domain:
            return by_domain[dom]
    return story["articles"][0]

def extract(url):
    try:
        r = creq.get(url, impersonate="chrome", timeout=25)
    except Exception as e:
        return {"url": url, "error": str(e)[:150]}
    if r.status_code != 200:
        return {"url": url, "error": f"HTTP {r.status_code}"}
    html_text = r.text

    text = clean_text(trafilatura.extract(html_text, url=url) or "")
    # Summary = the article's opening paragraphs; the full (cleaned) body is
    # kept separately, capped, for the UI's full-text view.
    summary = lede(text)
    body = text[:BODY_CAP]  # BODY_CAP None → whole text

    soup = BeautifulSoup(html_text, "lxml")
    og = soup.find("meta", property="og:image")
    image = (og.get("content") or "") if og else ""

    caption = ""
    fig = soup.find("figure")
    if fig:
        fc = fig.find("figcaption")
        if fc:
            caption = " ".join(fc.get_text(" ", strip=True).split())[:300]

    return {"url": url, "summary": summary, "body": body, "image": image,
            "image_caption": caption, "text_len": len(text),
            "truncated": BODY_CAP is not None and len(text) > BODY_CAP}

def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--min-outlets", type=int, default=2,
                    help="only enrich stories with at least this many independent outlets")
    ap.add_argument("--limit", type=int, default=80,
                    help="max article fetches this run (cached stories are free)")
    paths.add_data_dir_arg(ap)
    ap.add_argument("--stories", default=None,
                    help="stories JSONL from gdelt_collect.py (enriched in place)")
    ap.add_argument("--cache", default=None,
                    help="per-URL enrichment cache JSON")
    ap.add_argument("--reclean", action="store_true",
                    help="don't fetch anything: re-run clean_text/lede over the "
                         "bodies already in the cache (use after changing the cleaning rules)")
    ap.add_argument("--refetch-truncated", action="store_true",
                    help="refetch only the articles whose stored body was cut off by an "
                         "earlier BODY_CAP, so they get their full text")
    args = ap.parse_args()

    paths.use_data_dir(args.data_dir)
    gdelt_dir = paths.source_dir("gdelt")
    args.stories = args.stories or os.path.join(gdelt_dir, "gdelt_stories.jsonl")
    args.cache = args.cache or os.path.join(gdelt_dir, "gdelt_enrichment.json")

    with open(args.stories) as fh:
        stories = [json.loads(l) for l in fh if l.strip()]
    cache = {}
    if os.path.isfile(args.cache):
        with open(args.cache) as fh:
            cache = json.load(fh)

    def archive_inputs():
        """Snapshot cache + stories before an in-place rewrite."""
        stamp = time.strftime("%Y%m%d-%H%M%S")
        arch = paths.archive_dir("gdelt")
        os.makedirs(arch, exist_ok=True)
        for src in (args.cache, args.stories):
            dst = os.path.join(arch, f"{os.path.basename(src)}.{stamp}.bak")
            with open(src) as fh_in, open(dst, "w") as fh_out:
                fh_out.write(fh_in.read())
            print(f"  archived {os.path.relpath(dst, REPO_ROOT)}")

    def reattach_and_write():
        """Re-point every story at its (updated) cache record, then persist."""
        n = 0
        for s in stories:
            url = (s.get("enrichment") or {}).get("url")
            if url and url in cache and "error" not in cache[url]:
                s["enrichment"] = cache[url]
                n += 1
        with open(args.cache, "w") as fh:
            json.dump(cache, fh, ensure_ascii=False, indent=1)
        with open(args.stories, "w") as fh:
            for s in stories:
                fh.write(json.dumps(s, ensure_ascii=False) + "\n")
        return n

    if args.refetch_truncated:
        # Text past the old cap was never stored, so these need the outlet
        # again — but only these, not the whole corpus.
        stale = [u for u, r in cache.items()
                 if "error" not in r and (r.get("truncated")
                                          or len(r.get("body") or "") >= LEGACY_BODY_CAP)]
        print(f"{len(stale)} truncated records to refetch")
        archive_inputs()
        refetched = failed = 0
        for i, url in enumerate(stale, 1):
            rec = extract(url)
            if "error" in rec:
                failed += 1
                print(f"  [{i}/{len(stale)}] ERR {url[:70]} — {rec['error'][:60]}")
            else:
                rec["domain"] = cache[url].get("domain", "")
                old = len(cache[url].get("body") or "")
                cache[url] = rec
                refetched += 1
                print(f"  [{i}/{len(stale)}] ok  {rec['domain']:<22} "
                      f"{old:,} → {len(rec['body']):,} chars")
            if i % 25 == 0:
                with open(args.cache, "w") as fh:
                    json.dump(cache, fh, ensure_ascii=False, indent=1)
            time.sleep(FETCH_DELAY_S)
        attached = reattach_and_write()
        print(f"\nrefetched {refetched} ({failed} failed, kept as-is), "
              f"{attached} stories rewritten → {args.stories}")
        return

    if args.reclean:
        # Cleaning is line-based, so the stored body is enough to redo both
        # fields — no outlet gets hit again. Previous versions are archived
        # rather than overwritten in place.
        archive_inputs()
        changed = 0
        for rec in cache.values():
            if "error" in rec or not rec.get("body"):
                continue
            was_capped = len(rec["body"]) >= LEGACY_BODY_CAP
            body = clean_text(rec["body"])
            summary = lede(body)
            if body != rec.get("body") or summary != rec.get("summary"):
                changed += 1
            rec["body"], rec["summary"] = body, summary
            # cleaning shortens the body too, so truncation can only be judged
            # from the pre-clean length against the cap it was stored under
            rec["truncated"] = bool(rec.get("truncated")) or was_capped
        attached = reattach_and_write()
        print(f"\nrecleaned {changed} cached records, {attached} stories rewritten "
              f"→ {args.stories}")
        return

    fetches = 0
    attached = 0
    for s in sorted(stories, key=lambda s: -s["n_outlets"]):
        if s["n_outlets"] < args.min_outlets:
            continue
        art = pick_article(s)
        url = art["url"]
        # entries fetched before full-body support are stale — refetch them
        if url in cache and "error" not in cache[url] and "body" not in cache[url]:
            del cache[url]
        if url not in cache:
            if fetches >= args.limit:
                continue
            fetches += 1
            rec = extract(url)
            rec["domain"] = art["domain"]
            cache[url] = rec
            ok = "error" not in rec
            print(f"  [{fetches}/{args.limit}] {'ok ' if ok else 'ERR'} {art['domain']:<24}"
                  f" {(rec.get('summary') or rec.get('error', ''))[:60]!r}")
            if fetches % 25 == 0:  # crash/interrupt must not lose fetched work
                with open(args.cache, "w") as fh:
                    json.dump(cache, fh, ensure_ascii=False, indent=1)
            time.sleep(FETCH_DELAY_S)
        rec = cache[url]
        if "error" not in rec:
            s["enrichment"] = rec
            attached += 1

    with open(args.cache, "w") as fh:
        json.dump(cache, fh, ensure_ascii=False, indent=1)
    with open(args.stories, "w") as fh:
        for s in stories:
            fh.write(json.dumps(s, ensure_ascii=False) + "\n")
    print(f"\n{fetches} fetched this run, {attached} stories now enriched "
          f"({len(cache)} urls cached) → {args.stories}")

if __name__ == "__main__":
    main()
