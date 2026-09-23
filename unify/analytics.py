#!/usr/bin/env python3
"""Analytics over the unified dataset: how much each collection strategy yields
and which publishers dominate, overall and per strategy — the numbers to look
at when deciding which strategy to invest in.

Reads unified_all.jsonl (see unify.py) and prints a report; --json / --markdown
also write machine-readable and doc-friendly copies next to the input.
"""
import argparse
import json
import os
import sys
from collections import Counter, defaultdict

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import paths  # noqa: E402

GERMAN_LANGS = {"de", "deu", "german"}


def analyze(path):
    per = defaultdict(lambda: {
        "stories": 0, "articles": 0, "with_body": 0, "with_bias_rating": 0,
        "german_lang_articles": 0, "publishers": Counter(), "dates": [],
    })
    overall_pubs = Counter()
    with open(path) as f:
        for line in f:
            if not line.strip():
                continue
            s = json.loads(line)
            d = per[s["source_dataset"]]
            d["stories"] += 1
            if s.get("date"):
                d["dates"].append(s["date"][:10])
            for a in s["articles"]:
                d["articles"] += 1
                if a.get("body_text"):
                    d["with_body"] += 1
                if a.get("bias_rating") and a["bias_rating"] != "unknown":
                    d["with_bias_rating"] += 1
                if (a.get("lang") or "").lower() in GERMAN_LANGS:
                    d["german_lang_articles"] += 1
                name = a.get("source_name") or "?"
                d["publishers"][name] += 1
                overall_pubs[name] += 1
    return per, overall_pubs


def fmt_pct(n, d):
    return f"{n / d:.0%}" if d else "–"


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    paths.add_data_dir_arg(ap)
    ap.add_argument("--data", default=None,
                    help="unified JSONL to analyze (default: unified_all.jsonl)")
    ap.add_argument("--top", type=int, default=15, help="publishers to list per table")
    ap.add_argument("--json", action="store_true",
                    help="also write analytics.json next to the input file")
    ap.add_argument("--markdown", action="store_true",
                    help="also write analytics.md next to the input file")
    args = ap.parse_args()

    paths.use_data_dir(args.data_dir)
    args.data = args.data or paths.unified_path("all")

    per, overall_pubs = analyze(args.data)

    lines = ["# Unified dataset analytics", ""]
    lines.append("## Yield per strategy")
    lines.append("")
    lines.append("| strategy | stories | articles | with body text | bias-rated | German-language | unique publishers | date range |")
    lines.append("|---|---|---|---|---|---|---|---|")
    for name, d in sorted(per.items(), key=lambda kv: -kv[1]["articles"]):
        dr = f"{min(d['dates'])} → {max(d['dates'])}" if d["dates"] else "–"
        lines.append(
            f"| {name} | {d['stories']:,} | {d['articles']:,} "
            f"| {d['with_body']:,} ({fmt_pct(d['with_body'], d['articles'])}) "
            f"| {d['with_bias_rating']:,} ({fmt_pct(d['with_bias_rating'], d['articles'])}) "
            f"| {d['german_lang_articles']:,} ({fmt_pct(d['german_lang_articles'], d['articles'])}) "
            f"| {len(d['publishers']):,} | {dr} |")
    lines.append("")

    lines.append(f"## Top {args.top} publishers — overall")
    lines.append("")
    lines.append("| publisher | articles |")
    lines.append("|---|---|")
    for name, n in overall_pubs.most_common(args.top):
        lines.append(f"| {name} | {n:,} |")
    lines.append("")

    for name, d in sorted(per.items(), key=lambda kv: -kv[1]["articles"]):
        lines.append(f"## Top {args.top} publishers — {name}")
        lines.append("")
        lines.append("| publisher | articles |")
        lines.append("|---|---|")
        for pub, n in d["publishers"].most_common(args.top):
            lines.append(f"| {pub} | {n:,} |")
        lines.append("")

    report = "\n".join(lines)
    print(report)

    out_dir = os.path.dirname(os.path.abspath(args.data))
    if args.json:
        payload = {
            name: {
                "stories": d["stories"], "articles": d["articles"],
                "with_body": d["with_body"], "with_bias_rating": d["with_bias_rating"],
                "german_lang_articles": d["german_lang_articles"],
                "unique_publishers": len(d["publishers"]),
                "date_range": [min(d["dates"]), max(d["dates"])] if d["dates"] else None,
                "top_publishers": d["publishers"].most_common(args.top),
            } for name, d in per.items()
        }
        payload["_overall_top_publishers"] = overall_pubs.most_common(args.top)
        with open(os.path.join(out_dir, "analytics.json"), "w") as f:
            json.dump(payload, f, ensure_ascii=False, indent=1)
        print(f"\nwrote {os.path.join(out_dir, 'analytics.json')}")
    if args.markdown:
        with open(os.path.join(out_dir, "analytics.md"), "w") as f:
            f.write(report + "\n")
        print(f"wrote {os.path.join(out_dir, 'analytics.md')}")


if __name__ == "__main__":
    main()
