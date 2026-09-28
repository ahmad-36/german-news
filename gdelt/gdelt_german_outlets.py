"""Discover top German news outlets via GDELT DOC API.

Queries sourcecountry=Germany + sourcelang=German over a recent window
across several broad themes/keywords (the API requires a content filter),
then aggregates article counts per domain.
"""
import argparse
import json
import os
import time
from collections import Counter, defaultdict
from urllib.parse import urlparse

import pandas as pd
from gdeltdoc import Filters, GdeltDoc

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import paths  # noqa: E402

_ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
paths.add_data_dir_arg(_ap)
_ap.add_argument("--out-dir", default=None,
                 help="directory for gdelt_domain_counts.json / gdelt_articles_sample.csv")
_args = _ap.parse_args()
paths.use_data_dir(_args.data_dir)
OUT_DIR = _args.out_dir or paths.source_dir("gdelt")
os.makedirs(OUT_DIR, exist_ok=True)

# Broad, diverse probes so the domain ranking isn't biased by one topic.
THEME_PROBES = [
    "GENERAL_GOVERNMENT",
    "ECON_STOCKMARKET",
    "CRISISLEX_CRISISLEXREC",
    "SOC_POINTSOFINTEREST_SCHOOL",
    "TAX_FNCACT_POLICE",
]
KEYWORD_PROBES = [
    "Bundesregierung",
    "Fußball",
    "Wetter",
    "Polizei",
    "Wirtschaft",
    "Ukraine",
    "Gesundheit",
]

gd = GdeltDoc()
domain_counts = Counter()
domain_examples = defaultdict(list)
all_rows = []

def run_probe(label, **kw):
    f = Filters(timespan="7d", num_records=250, country="germany",
                language="german", **kw)
    try:
        df = gd.article_search(f)
    except Exception as e:
        print(f"  probe {label!r} FAILED: {e}")
        return
    if df is None or df.empty:
        print(f"  probe {label!r}: 0 articles")
        return
    print(f"  probe {label!r}: {len(df)} articles, {df['domain'].nunique()} domains")
    for _, row in df.iterrows():
        dom = row["domain"]
        domain_counts[dom] += 1
        if len(domain_examples[dom]) < 3:
            domain_examples[dom].append(row["url"])
        all_rows.append({"probe": label, "domain": dom, "url": row["url"],
                         "title": row["title"], "seendate": row["seendate"]})
    time.sleep(1)  # be polite to the API

print("Theme probes:")
for t in THEME_PROBES:
    run_probe(f"theme:{t}", theme=t)

print("Keyword probes:")
for k in KEYWORD_PROBES:
    run_probe(f"kw:{k}", keyword=k)

print(f"\nTotal articles collected: {len(all_rows)}")
print(f"Unique domains: {len(domain_counts)}\n")

print(f"{'rank':<5}{'domain':<40}{'articles':<10}")
for i, (dom, n) in enumerate(domain_counts.most_common(40), 1):
    print(f"{i:<5}{dom:<40}{n:<10}")

with open(f"{OUT_DIR}/gdelt_domain_counts.json", "w") as fh:
    json.dump({
        "domain_counts": dict(domain_counts.most_common()),
        "domain_examples": {d: domain_examples[d] for d, _ in domain_counts.most_common(40)},
    }, fh, indent=2, ensure_ascii=False)

pd.DataFrame(all_rows).to_csv(f"{OUT_DIR}/gdelt_articles_sample.csv", index=False)
print(f"\nSaved {OUT_DIR}/gdelt_domain_counts.json and {OUT_DIR}/gdelt_articles_sample.csv")
