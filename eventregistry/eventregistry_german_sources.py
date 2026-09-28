"""Discover German news providers via Event Registry (newsapi.ai).

Token-frugal by design (free plan = 2,000 non-renewing tokens):
  - suggestSourcesAtPlace(Germany) — autosuggest call, does not consume search tokens
  - one QueryArticles over a recent window (recent search = 1 token) with a
    sourceAggr result: top sources by article volume, Germany + German only
  - allowUseOfArchive=False so a typo'd date can never trigger a 5-token/yr
    historical search
  - prints the remaining-token counter after every call

Key lookup order: --key flag, EVENTREGISTRY_API_KEY env var, ~/.eventregistry_key file.

Usage (env scrap2):
    python eventregistry_german_sources.py [--days 7] [--sample]
"""
import argparse
import datetime as dt
import json
import os
import sys
from pathlib import Path

from eventregistry import (
    EventRegistry,
    QueryArticles,
    QueryArticlesIter,
    QueryItems,
    RequestArticlesInfo,
    RequestArticlesSourceAggr,
)

sys.path.insert(0, str(Path(__file__).resolve().parent))
import paths  # noqa: E402

OUT_DIR = Path(paths.source_dir("eventregistry"))  # rebound in main() after --data-dir


def get_api_key(cli_key):
    if cli_key:
        return cli_key
    if os.environ.get("EVENTREGISTRY_API_KEY"):
        return os.environ["EVENTREGISTRY_API_KEY"]
    key_file = Path.home() / ".eventregistry_key"
    if key_file.exists():
        return key_file.read_text().strip()
    sys.exit(
        "No API key. Register at https://newsapi.ai, then either:\n"
        "  export EVENTREGISTRY_API_KEY=<key>   or   echo <key> > ~/.eventregistry_key"
    )


def print_tokens(er, label):
    print(f"[tokens] after {label}: {er.getRemainingAvailableRequests()} remaining "
          f"(also watch https://newsapi.ai dashboard)")


def main():
    ap = argparse.ArgumentParser()
    paths.add_data_dir_arg(ap)
    ap.add_argument("--key", help="API key (overrides env/file)")
    ap.add_argument("--days", type=int, default=7,
                    help="recent window length; keep <=30 (free plan hard limit)")
    ap.add_argument("--sample", action="store_true",
                    help="also fetch 10 sample articles (one search, ~5 tokens)")
    ap.add_argument("--pull", type=int, default=0, metavar="N",
                    help="scrape up to N articles to JSONL; 1 token per 100 "
                         "articles (measured; aggregate queries cost ~5)")
    ap.add_argument("--pull-sources", nargs="*", default=None, metavar="URI",
                    help="restrict --pull to these source uris (e.g. zeit.de faz.net)")
    ap.add_argument("--skip-discovery", action="store_true",
                    help="skip the suggest + sourceAggr steps (no tokens spent on them)")
    args = ap.parse_args()

    global OUT_DIR
    paths.use_data_dir(args.data_dir)
    OUT_DIR = Path(paths.source_dir("eventregistry"))
    if args.days > 30:
        sys.exit("--days > 30 exceeds the free plan's content window; refusing.")

    er = EventRegistry(apiKey=get_api_key(args.key), allowUseOfArchive=False)
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    germany_uri = er.getLocationUri("Germany")
    print(f"Germany location URI: {germany_uri}")
    date_end = dt.date.today()
    date_start = date_end - dt.timedelta(days=args.days)

    if not args.skip_discovery:
        # --- 1. Providers known to Event Registry for Germany (no search tokens) ---
        suggested = er.suggestSourcesAtPlace(germany_uri, count=200)
        (OUT_DIR / "suggested_sources_germany.json").write_text(
            json.dumps(suggested, ensure_ascii=False, indent=2))
        print(f"suggestSourcesAtPlace: {len(suggested)} sources "
              f"-> {OUT_DIR/'suggested_sources_germany.json'}")
        for s in suggested[:25]:
            print(f"  {s.get('title'):<45} {s.get('uri')}")
        print_tokens(er, "suggest calls")

        # --- 2. Top sources by actual article volume, recent window (~5 tokens) ---
        q = QueryArticles(
            sourceLocationUri=germany_uri,
            lang="deu",
            dateStart=date_start.isoformat(),
            dateEnd=date_end.isoformat(),
        )
        q.setRequestedResult(RequestArticlesSourceAggr(sourceCount=100))
        res = er.execQuery(q)
        (OUT_DIR / "source_aggr_germany.json").write_text(
            json.dumps(res, ensure_ascii=False, indent=2))
        aggr_res = res.get("sourceAggr") or {}
        aggr = aggr_res.get("countsPerSource", [])
        print(f"\nsourceAggr {date_start}..{date_end}: "
              f"{aggr_res.get('totalResults')} matching articles, {len(aggr)} sources "
              f"-> {OUT_DIR/'source_aggr_germany.json'}")
        for s in aggr[:25]:
            src = s.get("source", {})
            counts = s.get("counts", {})
            print(f"  {src.get('title'):<45} {src.get('uri'):<30} "
                  f"in-window={counts.get('frequency'):<7} total={counts.get('total')}")
        print_tokens(er, "sourceAggr query")

    # --- 3. Article pull: N articles -> JSONL, merging on article uri ---
    if args.pull:
        out_path = OUT_DIR / "articles_germany.jsonl"
        seen = set()
        if out_path.exists():
            with open(out_path) as f:
                seen = {json.loads(line)["uri"] for line in f if line.strip()}
        est_searches = -(-args.pull // 100)
        print(f"\npulling up to {args.pull} articles "
              f"(~{est_searches} searches, ~{est_searches} tokens), "
              f"{len(seen)} already in {out_path}")
        qi = QueryArticlesIter(
            sourceUri=QueryItems.OR(args.pull_sources) if args.pull_sources else None,
            sourceLocationUri=None if args.pull_sources else germany_uri,
            lang="deu",
            dateStart=date_start.isoformat(),
            dateEnd=date_end.isoformat(),
        )
        n_new = 0
        with open(out_path, "a") as f:
            for art in qi.execQuery(er, sortBy="date", maxItems=args.pull):
                if art["uri"] in seen:
                    continue
                f.write(json.dumps(art, ensure_ascii=False) + "\n")
                seen.add(art["uri"])
                n_new += 1
        print(f"wrote {n_new} new articles -> {out_path} ({len(seen)} total)")
        print_tokens(er, "article pull")

    # --- 4. Optional: eyeball a few articles (~5 tokens) ---
    if args.sample:
        q2 = QueryArticles(
            sourceLocationUri=germany_uri,
            lang="deu",
            dateStart=date_start.isoformat(),
            dateEnd=date_end.isoformat(),
        )
        q2.setRequestedResult(RequestArticlesInfo(count=10))
        res2 = er.execQuery(q2)
        (OUT_DIR / "sample_articles_germany.json").write_text(
            json.dumps(res2, ensure_ascii=False, indent=2))
        arts = (res2.get("articles") or {}).get("results", [])
        print(f"\nsample articles -> {OUT_DIR/'sample_articles_germany.json'}")
        for a in arts:
            print(f"  [{a.get('source', {}).get('title')}] {a.get('title')}")
        print_tokens(er, "sample articles")


if __name__ == "__main__":
    main()
