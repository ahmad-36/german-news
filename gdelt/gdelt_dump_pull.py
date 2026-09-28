"""GDELT raw 15-minute dumps → German-language article dump (env: scrap2).

The no-credentials alternative to gdelt_bq_pull.py. Streams the translingual
GKG zips from data.gdeltproject.org, filters to German in memory, and keeps
only the extracted rows — the raw files are never written to disk, so the
172 GB of downloads for Jan–Aug 2026 cost bandwidth and time, not quota.

Coverage for that range is 20,446 of 20,448 expected slots, so this is
effectively a census of what GDELT saw, with no 250-result ceiling.

A full census is expensive (172 GB for Jan-Aug 2026) and usually not what you
want. Prefer a bounded run: a short date range plus a topic or keyword filter.

Usage:
  # bounded: one week, filtered to a keyword list  <- the default way to work
  python gdelt_dump_pull.py --start 2026-01-01 --end 2026-01-08 \
      --keywords-file keywords/german_politics.txt

  # bounded by GKG theme instead of keyword
  python gdelt_dump_pull.py --start 2026-01-01 --end 2026-01-08 \
      --themes ELECTION,DEMOCRACY,LEADER

  # census (no filter) - only when you really mean it
  python gdelt_dump_pull.py --start 2026-01-01 --end 2026-08-01

  python gdelt_dump_pull.py --resume          # continue an interrupted run

Filters are OR-ed: an article is kept if its title matches any keyword OR its
GKG themes match any theme. With no filter given, everything German is kept.
"""
import argparse
import csv
import html
import io
import json
import os
import re
import sys
import threading
import time
import urllib.request
import zipfile
from concurrent.futures import ThreadPoolExecutor
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import paths  # noqa: E402

REPO_ROOT = paths.REPO_ROOT


def default_out():
    """Resolved after --data-dir is parsed, so the flag actually takes effect."""
    return os.path.join(paths.source_dir("gdelt"), "gdelt_articles_de.jsonl")
MASTERLIST = "http://data.gdeltproject.org/gdeltv2/masterfilelist-translation.txt"

# GKG 2.1 is a 27-column TSV; these are the 0-indexed fields we keep.
C_DATE, C_SOURCE, C_DOCID, C_THEMES, C_IMAGE, C_TRANSINFO, C_EXTRAS = 1, 3, 4, 8, 18, 25, 26
TITLE_RE = re.compile(r"<PAGE_TITLE>(.*?)</PAGE_TITLE>", re.S)

_lock = threading.Lock()

# GKG's GCAM and Extras fields routinely exceed the default 128 KB csv limit.
csv.field_size_limit(sys.maxsize)


def fetch(url, retries=3, timeout=120):
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(url, timeout=timeout) as r:
                return r.read()
        except Exception as e:
            if attempt == retries - 1:
                print(f"  FAILED {url}: {e!r}", file=sys.stderr)
                return None
            time.sleep(2 ** attempt)
    return None


def load_terms(inline, path):
    """Terms from --x a,b,c and/or --x-file (one per line, # comments ok)."""
    terms = []
    if inline:
        terms += [t.strip() for t in inline.split(",")]
    if path:
        with open(path, encoding="utf-8") as fh:
            for line in fh:
                line = line.split("#", 1)[0].strip()
                if line:
                    terms.append(line)
    return [t for t in terms if t]


def build_keyword_re(keywords, whole_word=False):
    """Case-insensitive alternation over the keyword list.

    German needs care here. A plain substring check over-matches ("SPD" inside
    "SPDR"), but a strict word boundary on both sides under-matches badly,
    because German compounds and inflects: strict matching misses
    "Bundestag" in "Bundestagswahl" and "Grüne" in "Die Grünen" — both of
    which you certainly want.

    So the default anchors only the LEFT edge: the term must start a word, but
    may be continued by more word characters. That keeps "Bundestagswahl" and
    "Grünen" while still rejecting "Schafdorf" for "AfD". The cost is that
    "SPD" then also matches "SPDR"; pass whole_word=True if that matters more
    than recall for your term list.

    Multi-word phrases match with flexible whitespace, so "Friedrich  Merz"
    still hits.
    """
    if not keywords:
        return None
    parts = [r"\s+".join(re.escape(w) for w in k.split()) for k in keywords]
    tail = r"(?!\w)" if whole_word else ""
    return re.compile(r"(?<!\w)(?:" + "|".join(parts) + r")" + tail, re.IGNORECASE)


def build_theme_re(themes):
    """GKG V2Themes is a ';'-separated code list; match a code or its prefix."""
    if not themes:
        return None
    return re.compile("|".join(re.escape(t.strip().upper()) for t in themes))


def parse_slot(blob, kw_re=None, theme_re=None, stats=None):
    """Return German article dicts from one GKG zip blob.

    With kw_re/theme_re set, an article is kept only if its title matches a
    keyword or its themes match a theme. `stats` accumulates [seen, kept].
    """
    out = []
    try:
        z = zipfile.ZipFile(io.BytesIO(blob))
        raw = z.read(z.namelist()[0]).decode("utf-8", "replace")
    except Exception:
        return out
    reader = csv.reader(io.StringIO(raw), delimiter="\t", quoting=csv.QUOTE_NONE)
    while True:
        # A single malformed row must not abort a multi-hour run.
        try:
            r = next(reader)
        except StopIteration:
            break
        except csv.Error:
            continue
        if len(r) <= C_TRANSINFO or "srclc:deu" not in r[C_TRANSINFO]:
            continue
        url = r[C_DOCID]
        if not url:
            continue
        extras = r[C_EXTRAS] if len(r) > C_EXTRAS else ""
        m = TITLE_RE.search(extras)
        title = html.unescape(m.group(1)).strip() if m else ""
        themes = r[C_THEMES][:2000] if len(r) > C_THEMES else ""

        if stats is not None:
            stats[0] += 1
        if kw_re is not None or theme_re is not None:
            hit = (kw_re is not None and title and kw_re.search(title)) or \
                  (theme_re is not None and themes and theme_re.search(themes.upper()))
            if not hit:
                continue
        if stats is not None:
            stats[1] += 1

        out.append({
            "title": title,
            "url": url,
            "domain": r[C_SOURCE].lower(),
            "seendate": r[C_DATE],
            "sourcecountry": "",
            "language": "German",
            "socialimage": r[C_IMAGE] if len(r) > C_IMAGE else "",
            "probe": "dump:gkg-deu",
            "themes": themes,
        })
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--start", required=True, help="inclusive start date YYYY-MM-DD")
    ap.add_argument("--end", required=True, help="exclusive end date YYYY-MM-DD")
    paths.add_data_dir_arg(ap)
    ap.add_argument("--out", default=None)
    ap.add_argument("--workers", type=int, default=6,
                    help="parallel downloads; keep modest, GDELT throttles")
    ap.add_argument("--resume", action="store_true",
                    help="skip slots already recorded in the progress file")
    ap.add_argument("--keywords", default=None, metavar="A,B,C",
                    help="keep articles whose TITLE matches any of these terms")
    ap.add_argument("--keywords-file", default=None, metavar="PATH",
                    help="same, one term per line ('#' comments allowed)")
    ap.add_argument("--themes", default=None, metavar="A,B,C",
                    help="keep articles whose GKG V2Themes match any of these codes")
    ap.add_argument("--themes-file", default=None, metavar="PATH",
                    help="same, one theme code per line")
    ap.add_argument("--whole-word", action="store_true",
                    help="require keywords to match a whole word; default also "
                         "matches German compounds (Bundestag -> Bundestagswahl)")
    ap.add_argument("--max-slots", type=int, default=0, metavar="N",
                    help="stop after N slots - use to bound an exploratory run")
    args = ap.parse_args()
    paths.use_data_dir(args.data_dir)
    args.out = args.out or default_out()

    keywords = load_terms(args.keywords, args.keywords_file)
    themes = load_terms(args.themes, args.themes_file)
    kw_re = build_keyword_re(keywords, args.whole_word)
    theme_re = build_theme_re(themes)
    if kw_re is not None or theme_re is not None:
        print(f"filtering: {len(keywords)} keywords, {len(themes)} themes "
              f"(an article is kept if it matches any of either)")
    else:
        print("NO FILTER — this is a full German census for the date range. "
              "Pass --keywords/--themes to bound it.")

    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    progress_path = args.out + ".done"

    lo = date.fromisoformat(args.start).strftime("%Y%m%d") + "000000"
    hi = date.fromisoformat(args.end).strftime("%Y%m%d") + "000000"

    print("fetching master file list ...", flush=True)
    master = fetch(MASTERLIST, timeout=300)
    if master is None:
        sys.exit("could not fetch master file list")

    urls = []
    for line in master.decode("utf-8", "replace").splitlines():
        p = line.split()
        if len(p) < 3 or not p[2].endswith(".translation.gkg.csv.zip"):
            continue
        m = re.search(r"/(\d{14})\.", p[2])
        if m and lo <= m.group(1) < hi:
            urls.append(p[2])
    urls.sort()
    if args.max_slots:
        urls = urls[: args.max_slots]
        print(f"--max-slots {args.max_slots}: truncated to {len(urls)} slots")

    done = set()
    if args.resume and os.path.exists(progress_path):
        done = set(open(progress_path).read().split())
        urls = [u for u in urls if u not in done]
        print(f"resuming: {len(done)} slots already done")

    print(f"{len(urls)} GKG slots to fetch, {args.workers} workers", flush=True)
    mode = "a" if (args.resume and os.path.exists(args.out)) else "w"
    total = 0
    t0 = time.time()

    seen_kept = [0, 0]   # [German articles seen, kept after filtering]

    with open(args.out, mode) as fh, open(progress_path, "a") as pf:
        def work(url):
            try:
                blob = fetch(url)
                # None (not []) means "failed" — left unmarked so --resume retries it.
                return url, (parse_slot(blob, kw_re, theme_re, seen_kept) if blob else None)
            except Exception as e:
                print(f"  SKIP {url}: {e!r}", file=sys.stderr)
                return url, None

        failed = 0
        with ThreadPoolExecutor(max_workers=args.workers) as ex:
            for i, (url, arts) in enumerate(ex.map(work, urls), 1):
                with _lock:
                    if arts is None:
                        failed += 1
                        continue
                    for a in arts:
                        fh.write(json.dumps(a, ensure_ascii=False) + "\n")
                    pf.write(url + "\n")
                    total += len(arts)
                if i % 50 == 0:
                    el = time.time() - t0
                    rate = i / el
                    eta = (len(urls) - i) / rate / 3600 if rate else 0
                    fh.flush(); pf.flush()
                    print(f"  {i}/{len(urls)} slots | {total} articles | "
                          f"{rate*60:.0f} slots/min | ETA {eta:.1f}h", flush=True)

    seen, kept = seen_kept
    if kw_re is not None or theme_re is not None:
        rate = 100 * kept / seen if seen else 0
        print(f"\nFilter: {kept} kept of {seen} German articles seen ({rate:.2f}%)")
    print(f"\nWrote {total} German article records → {args.out}")
    if failed:
        print(f"{failed} slots failed and were left unmarked — re-run with --resume to retry them.")
    print(f"Next: python gdelt_cluster_bulk.py --articles {args.out}")


if __name__ == "__main__":
    main()
