"""Retry the GDELT probes that failed (rate-limited) and merge domain counts."""
import argparse
import json
import os
import time
from collections import Counter, defaultdict

import pandas as pd
from gdeltdoc import Filters, GdeltDoc

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import paths  # noqa: E402

_ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
paths.add_data_dir_arg(_ap)
_ap.add_argument("--out-dir", default=None,
                 help="directory holding gdelt_domain_counts.json / gdelt_articles_sample.csv")
_args = _ap.parse_args()
paths.use_data_dir(_args.data_dir)
OUT_DIR = _args.out_dir or paths.source_dir("gdelt")

FAILED = [
    ("theme:GENERAL_GOVERNMENT", {"theme": "GENERAL_GOVERNMENT"}),
    ("theme:ECON_STOCKMARKET", {"theme": "ECON_STOCKMARKET"}),
    ("theme:CRISISLEX_CRISISLEXREC", {"theme": "CRISISLEX_CRISISLEXREC"}),
    ("kw:Bundesregierung", {"keyword": "Bundesregierung"}),
    ("kw:Fußball", {"keyword": "Fußball"}),
    ("kw:Wetter", {"keyword": "Wetter"}),
    ("kw:Polizei", {"keyword": "Polizei"}),
    ("kw:Wirtschaft", {"keyword": "Wirtschaft"}),
    ("kw:Gesundheit", {"keyword": "Gesundheit"}),
]

with open(f"{OUT_DIR}/gdelt_domain_counts.json") as fh:
    prev = json.load(fh)
domain_counts = Counter(prev["domain_counts"])
domain_examples = defaultdict(list, {k: v for k, v in prev["domain_examples"].items()})
all_rows = pd.read_csv(f"{OUT_DIR}/gdelt_articles_sample.csv").to_dict("records")

gd = GdeltDoc()
for label, kw in FAILED:
    f = Filters(timespan="7d", num_records=250, country="germany",
                language="german", **kw)
    for attempt in range(3):
        try:
            df = gd.article_search(f)
            break
        except Exception as e:
            print(f"  probe {label!r} attempt {attempt+1} failed: {e!r}")
            time.sleep(10)
    else:
        continue
    if df is None or df.empty:
        print(f"  probe {label!r}: 0 articles")
        time.sleep(6)
        continue
    print(f"  probe {label!r}: {len(df)} articles, {df['domain'].nunique()} domains")
    for _, row in df.iterrows():
        dom = row["domain"]
        domain_counts[dom] += 1
        if len(domain_examples[dom]) < 3:
            domain_examples[dom].append(row["url"])
        all_rows.append({"probe": label, "domain": dom, "url": row["url"],
                         "title": row["title"], "seendate": row["seendate"]})
    time.sleep(6)

print(f"\nTotal articles: {len(all_rows)}, unique domains: {len(domain_counts)}\n")
print(f"{'rank':<5}{'domain':<40}{'articles':<10}")
for i, (dom, n) in enumerate(domain_counts.most_common(40), 1):
    print(f"{i:<5}{dom:<40}{n:<10}")

with open(f"{OUT_DIR}/gdelt_domain_counts.json", "w") as fh:
    json.dump({
        "domain_counts": dict(domain_counts.most_common()),
        "domain_examples": {d: domain_examples[d] for d, _ in domain_counts.most_common(60)},
    }, fh, indent=2, ensure_ascii=False)
pd.DataFrame(all_rows).to_csv(f"{OUT_DIR}/gdelt_articles_sample.csv", index=False)
print("\nMerged and saved.")
