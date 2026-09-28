"""Build the clustering-eval set from the raw Event Registry pull (env: rag).

Gold labels = ER's own eventUri. Kept: German-anchored events (deu-*) covered by
2+ distinct sources. Each article gets
  * a time window, reproducing gdelt/gdelt_cluster_bulk.py with its default
    --span-days 1: the distinct crawl days, sorted, cut into consecutive pairs.
    Day = ER's crawl time (dateTime), the analogue of GDELT's seendate;
    dateTimePub has publisher-side day/month swaps (e.g. 2026-03-08 for 08-03).
  * a dev/test split by event (50/50, seeded), so thresholds are tuned on dev
    events and reported on unseen test events.

Output: data/clustering_eval/articles.jsonl
"""
import json
import os
import random
import sys
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "ui"))
from textlib import lede  # noqa: E402  same lede the unified files use

RAW = os.path.join(HERE, "..", "data", "eventregistry", "articles_germany.jsonl")
OUT_DIR = os.path.join(HERE, "..", "data", "clustering_eval")
SPAN_DAYS = 1
SEED = 13


def main():
    by_event, seen = defaultdict(list), set()
    with open(RAW) as f:
        for line in f:
            r = json.loads(line)
            ev = r.get("eventUri") or ""
            if not ev.startswith("deu-") or r["uri"] in seen:
                continue
            seen.add(r["uri"])
            by_event[ev].append(r)
    events = sorted(e for e, rs in by_event.items()
                    if len({r["source"]["uri"] for r in rs}) >= 2)

    rng = random.Random(SEED)
    shuffled = events[:]
    rng.shuffle(shuffled)
    split = {e: ("dev" if i < len(shuffled) // 2 else "test") for i, e in enumerate(shuffled)}

    days = sorted({r["dateTime"][:10] for e in events for r in by_event[e]})
    step = SPAN_DAYS + 1
    window_of = {d: i // step for i, d in enumerate(days)}

    os.makedirs(OUT_DIR, exist_ok=True)
    n = 0
    with open(os.path.join(OUT_DIR, "articles.jsonl"), "w") as out:
        for e in events:
            for r in sorted(by_event[e], key=lambda r: r["dateTime"]):
                body = r.get("body") or ""
                out.write(json.dumps({
                    "uri": r["uri"],
                    "event": e,
                    "split": split[e],
                    "source": r["source"]["uri"],
                    "crawl_time": r["dateTime"],
                    "window": window_of[r["dateTime"][:10]],
                    "title": (r.get("title") or "").strip(),
                    "lede": lede(body) if body else "",
                    "body": body,
                }, ensure_ascii=False) + "\n")
                n += 1
    print(f"{len(events)} events, {n} articles; windows:",
          {w: [d for d in days if window_of[d] == w] for w in sorted(set(window_of.values()))})
    print("split:", {s: sum(1 for e in events if split[e] == s) for s in ("dev", "test")}, "events")


if __name__ == "__main__":
    main()
