"""GDELT GKG → German-language article dump via BigQuery (env: scrap2).

Replaces the DOC API's 250-results-per-query ceiling (see GDELT_NOTES.md) with
the full backend table `gdelt-bq.gdeltv2.gkg_partitioned`. One month per query,
filtered to German by TranslationInfo, written as article JSONL matching the
schema gdelt_collect.cluster_articles() already consumes.

Requires Google Cloud credentials and a project (BigQuery sandbox is enough):
    gcloud auth application-default login
    export GDELT_BQ_PROJECT=your-project-id

ALWAYS dry-runs first and prints the scanned-bytes estimate; the free sandbox
tier is 1 TB/month and the Extras column (which carries the article title) is
the expensive one. Use --yes to skip the confirmation prompt.

Usage:
  python gdelt_bq_pull.py --start 2026-01-01 --end 2026-08-01          # dry run
  python gdelt_bq_pull.py --start 2026-01-01 --end 2026-08-01 --yes    # execute
  python gdelt_bq_pull.py --start 2026-01-01 --end 2026-02-01 --no-titles
"""
import argparse
import html
import json
import os
import re
import sys
from datetime import date, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import paths  # noqa: E402

REPO_ROOT = paths.REPO_ROOT


def default_out():
    """Resolved after --data-dir is parsed, so the flag actually takes effect."""
    return os.path.join(paths.source_dir("gdelt"), "gdelt_articles_de.jsonl")

TITLE_RE = re.compile(r"<PAGE_TITLE>(.*?)</PAGE_TITLE>", re.S)

# GKG stores no title column; the page title lives in the Extras XML blob.
# Extras is also the largest column, so --no-titles makes the query far cheaper
# at the cost of losing the field the clusterer keys on.
SQL = """
SELECT
  DATE,
  SourceCommonName,
  DocumentIdentifier,
  V2Themes,
  SharingImage{extras_col}
FROM `gdelt-bq.gdeltv2.gkg_partitioned`
WHERE _PARTITIONTIME >= TIMESTAMP('{start}')
  AND _PARTITIONTIME <  TIMESTAMP('{end}')
  AND TranslationInfo LIKE '%srclc:deu%'
  AND DocumentIdentifier IS NOT NULL
"""


def month_windows(start, end):
    """Yield (start, end) date pairs on month boundaries, clipped to [start, end)."""
    cur = start
    while cur < end:
        nxt = (cur.replace(day=1) + timedelta(days=32)).replace(day=1)
        yield cur, min(nxt, end)
        cur = nxt


def extract_title(extras):
    if not extras:
        return ""
    m = TITLE_RE.search(extras)
    return html.unescape(m.group(1)).strip() if m else ""


def domain_of(url):
    m = re.match(r"https?://([^/]+)", url or "")
    return m.group(1).lower().lstrip("www.") if m else ""


def row_to_article(r, want_titles):
    url = r["DocumentIdentifier"]
    return {
        "title": extract_title(r.get("Extras")) if want_titles else "",
        "url": url,
        "domain": (r.get("SourceCommonName") or domain_of(url)).lower(),
        "seendate": str(r["DATE"]),
        "sourcecountry": "",          # GKG carries no outlet-country field
        "language": "German",
        "socialimage": r.get("SharingImage") or "",
        "probe": "bq:gkg-deu",
        "themes": (r.get("V2Themes") or "")[:2000],
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--start", required=True, help="inclusive start date YYYY-MM-DD")
    ap.add_argument("--end", required=True, help="exclusive end date YYYY-MM-DD")
    paths.add_data_dir_arg(ap)
    ap.add_argument("--out", default=None)
    ap.add_argument("--project", default=os.environ.get("GDELT_BQ_PROJECT"),
                    help="GCP project to bill the query to (or $GDELT_BQ_PROJECT)")
    ap.add_argument("--no-titles", action="store_true",
                    help="skip the Extras column — much cheaper, but no titles to cluster on")
    ap.add_argument("--yes", action="store_true", help="run for real instead of dry-run only")
    args = ap.parse_args()
    paths.use_data_dir(args.data_dir)
    args.out = args.out or default_out()

    if not args.project:
        sys.exit("No project. Set --project or $GDELT_BQ_PROJECT (a BigQuery sandbox works).")

    from google.cloud import bigquery

    client = bigquery.Client(project=args.project)
    start = date.fromisoformat(args.start)
    end = date.fromisoformat(args.end)
    want_titles = not args.no_titles
    extras_col = "" if args.no_titles else ",\n  Extras"

    windows = list(month_windows(start, end))
    queries = [SQL.format(start=a.isoformat(), end=b.isoformat(), extras_col=extras_col)
               for a, b in windows]

    # Dry-run every window first so one bad range can't silently eat the quota.
    dry = bigquery.QueryJobConfig(dry_run=True, use_query_cache=False)
    total = 0
    print(f"{len(windows)} monthly windows, {start} → {end}, titles={'yes' if want_titles else 'no'}\n")
    for (a, b), q in zip(windows, queries):
        job = client.query(q, job_config=dry)
        total += job.total_bytes_processed
        print(f"  {a} → {b}: {job.total_bytes_processed/1e9:7.1f} GB")
    print(f"\nTOTAL SCANNED: {total/1e12:.3f} TB  (free sandbox tier = 1 TB/month)")
    if total > 1e12:
        print("  WARNING: exceeds the free tier on its own. Consider --no-titles or a shorter range.")

    if not args.yes:
        print("\nDry run only. Re-run with --yes to execute.")
        return

    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    n = 0
    with open(args.out, "w") as fh:
        for (a, b), q in zip(windows, queries):
            print(f"querying {a} → {b} ...", flush=True)
            for r in client.query(q).result():
                fh.write(json.dumps(row_to_article(r, want_titles), ensure_ascii=False) + "\n")
                n += 1
            print(f"  cumulative articles: {n}", flush=True)
    print(f"\nWrote {n} German article records → {args.out}")
    print("Next: python gdelt_cluster_bulk.py --articles %s" % args.out)


if __name__ == "__main__":
    main()
