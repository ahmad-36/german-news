"""Check whether top German outlets' article pages are scrapeable.

For each candidate domain, fetch 2 sample article URLs (from the GDELT sample)
with curl_cffi Chrome impersonation, then report per domain:
  - HTTP status / blocking
  - extracted text length via trafilatura (paywall pages yield stub text)
  - paywall markers in the HTML (CSS classes, JSON-LD isAccessibleForFree)
  - whether a lead image is predictably available (og:image / JSON-LD image)
"""
import json
import os
import re
import sys
from collections import defaultdict

import trafilatura
from bs4 import BeautifulSoup
from curl_cffi import requests as creq

import argparse

import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import paths  # noqa: E402

_ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
paths.add_data_dir_arg(_ap)
_ap.add_argument("--gdelt-dir", default=None,
                 help="directory holding gdelt_domain_counts.json (sample article URLs)")
_ap.add_argument("--out-dir", default=None,
                 help="directory for scrapeability_report.json")
_args, _ = _ap.parse_known_args()
paths.use_data_dir(_args.data_dir)
GDELT_DIR = _args.gdelt_dir or paths.source_dir("gdelt")
OUT_DIR = _args.out_dir or paths.source_dir("discovery")

PAYWALL_MARKERS = [
    "isAccessibleForFree\": false", "isAccessibleForFree\":false",
    "isAccessibleForFree': False",
    "paywall", "offerpage", "purchase-form", "premium-content",
    "plus-icon", "reduced-article", "article-teaser-paywall",
    "piano.io", "tinypass", "cxense", "sp-message",  # common paywall vendors
]

def check_url(url):
    try:
        r = creq.get(url, impersonate="chrome", timeout=25)
    except Exception as e:
        return {"url": url, "error": str(e)[:120]}
    html = r.text
    res = {"url": url, "status": r.status_code, "html_len": len(html)}
    if r.status_code != 200:
        return res

    text = trafilatura.extract(html, url=url) or ""
    res["text_len"] = len(text)
    res["text_head"] = text[:150].replace("\n", " ")

    low = html.lower()
    hits = sorted({m for m in PAYWALL_MARKERS if m.lower() in low})
    res["paywall_markers"] = hits

    # JSON-LD isAccessibleForFree — the most reliable paywall signal
    m = re.search(r'"isAccessibleForFree"\s*:\s*(true|false|"[^"]*")', html, re.I)
    if m:
        res["isAccessibleForFree"] = m.group(1).strip('"')

    soup = BeautifulSoup(html, "lxml")
    og = soup.find("meta", property="og:image")
    res["og_image"] = bool(og and og.get("content"))
    imgs = soup.select("article img[src], main img[src]")
    res["article_imgs"] = len(imgs)
    return res

def main():
    with open(f"{GDELT_DIR}/gdelt_domain_counts.json") as fh:
        data = json.load(fh)
    counts = data["domain_counts"]
    examples = data["domain_examples"]

    # If a curated domain list is passed on argv, use it; else top domains by count.
    domains = sys.argv[1:] or list(counts)[:14]

    report = {}
    for dom in domains:
        urls = examples.get(dom, [])[:2]
        if not urls:
            print(f"{dom}: no sample urls, skipping")
            continue
        print(f"\n=== {dom} ({counts.get(dom, '?')} articles in sample) ===")
        checks = []
        for u in urls:
            c = check_url(u)
            checks.append(c)
            if "error" in c:
                print(f"  FETCH ERROR: {c['error']}  <{u[:90]}>")
            else:
                print(f"  [{c['status']}] text={c.get('text_len', 0):>6} chars"
                      f"  og:image={c.get('og_image')}"
                      f"  imgs-in-article={c.get('article_imgs')}"
                      f"  free={c.get('isAccessibleForFree', '?')}"
                      f"  markers={c.get('paywall_markers', [])[:4]}")
                print(f"      {c.get('text_head', '')!r}")
        report[dom] = checks

    with open(f"{OUT_DIR}/scrapeability_report.json", "w") as fh:
        json.dump(report, fh, indent=2, ensure_ascii=False)
    print(f"\nSaved {OUT_DIR}/scrapeability_report.json")

if __name__ == "__main__":
    main()
