"""Audit Ground News machine translation for entity loss.

Ground News translates non-English articles into English and clusters the translation,
but keeps the pre-translation string in `original_title`. That lets us measure, directly,
what the translation destroys.

Two methodological rules, both learned the hard way:

1. **Count DISTINCT original titles, not records.** The same article recurs across
   stories; 5,224 German records hold only 4,167 distinct titles.
2. **A capitalised German surname is usually not a surname.** A naive
   `\bNeuer\b`-style regex reports 33 hits for the goalkeeper Manuel Neuer, of which
   26 are the ordinary adjective *neuer* ("new") in sentence-initial position
   ("Neuer Angriff auf Kiew" = "New attack on Kyiv", correctly translated). Likewise
   `Sommer` is almost always the season and `Kurz` almost always "shortly". Every
   surname claim below is therefore context-gated, and the script prints the matches
   so they can be eyeballed rather than trusted.

Reproduces every figure in docs/translation_problem.md.

    python scripts/translation_audit.py --data /path/to/ground_news.jsonl
"""

import argparse
import collections
import json
import re

# Surname erasure: require a context that rules out the adjectival reading.
# `Neuer-Nachfolge` / `Neuer-Abschied` are compounds that can only be the name;
# the others pin it to the Bayern goalkeeper story.
SURNAME_PATTERNS = {
    "Neuer (Manuel Neuer, goalkeeper)":
        re.compile(r"Neuer-(Nachfolge|Abschied)|Urbig soll Neuer|Neuer vor letzter"),
}

# German coalition shorthand: party colours, not colours.
COALITION = re.compile(r"Schwarz-(Rot|Grün|Gelb)|Rot-Rot-Grün|Rot-Grün|Jamaika-Koalition")

# Luxembourgish function words. rtl.lu publishes in lb but is tagged lang=de, so the
# translator is handed the wrong language and passes the text through untouched.
LUXEMBOURGISH = re.compile(r"\b(vun|engem|Zwee|gëtt|ouni|dreet|Pompjee|Bëschbrand)\b")

# "Bayern" is the club in a football context and the federal state otherwise; both
# render as "Bavaria", which is the point — the translation collapses the distinction.
FOOTBALL = re.compile(r"FC Bayern|Bundesliga|Trainer|Torwart|\bTor\b|Spieler|Saison|DFB")


def load(path):
    with open(path) as f:
        for line in f:
            yield json.loads(line)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True, help="ground_news.jsonl")
    ap.add_argument("--lang", default="de")
    ap.add_argument("--show", action="store_true", help="print every match")
    args = ap.parse_args()

    total = translated = 0
    by_lang = collections.Counter()
    translated_by_lang = collections.Counter()

    seen, titles = set(), []
    records = 0
    for story in load(args.data):
        for art in story.get("sources", []):
            total += 1
            lang = art.get("lang")
            by_lang[lang] += 1
            orig = art.get("original_title") or ""
            if not orig:
                continue
            translated += 1
            translated_by_lang[lang] += 1
            if lang != args.lang:
                continue
            records += 1
            if orig in seen:
                continue
            seen.add(orig)
            titles.append((orig, art["title"], art.get("source_name", "")))

    n = len(titles)
    print(f"Total articles           : {total:,}")
    print(f"Machine-translated       : {translated:,} ({100*translated/total:.1f}%)")
    print(f"Top languages            : {by_lang.most_common(10)}")
    print(f"Translated by language   : {translated_by_lang.most_common(10)}")
    print(f"\nlang={args.lang}: {records:,} records -> {n:,} DISTINCT original titles\n")

    def report(label, matches, denom=True):
        pct = f" ({100*len(matches)/n:.1f}%)" if denom else ""
        print(f"{label:52s} {len(matches):4d}{pct}")
        if args.show:
            for o, t in matches:
                print(f"     DE: {o[:92]}")
                print(f"     EN: {t[:92]}")
        return matches

    print("--- defect categories, counted on distinct titles ---")

    # 1. USA / US- collapsed into the English stopword "Us"
    us = [(o, t) for o, t, _ in titles
          if re.search(r"\bUSA?\b|\bUS-", o) and re.search(r"\b(the Us|Us|Usa|u\.s\.)\b", t)]
    report("USA / US- degraded to 'Us' / 'Usa'", us)

    # 2. Bayern -> Bavaria: club and state collapse to the same English string
    bay = [(o, t) for o, t, _ in titles
           if re.search(r"\bBayern\b", o) and re.search(r"\bBavaria\b", t)]
    club = [(o, t) for o, t in bay if FOOTBALL.search(o)]
    report("Bayern -> Bavaria (total)", bay)
    report("   ...of which football club (wrong)", club, denom=False)
    report("   ...of which federal state (right)", [x for x in bay if x not in club], denom=False)

    # 3. coalition colour shorthand translated as colours
    coal = [(o, t) for o, t, _ in titles if COALITION.search(o)]
    report("Coalition colour terms translated literally", coal)

    # 4. surname erased by translation (context-gated)
    for label, pat in SURNAME_PATTERNS.items():
        hits = [(o, t) for o, t, _ in titles if pat.search(o) and "Neuer" not in t]
        report(f"Surname erased: {label}", hits)

    # 5. wrong language tag -> translation does not run
    lux = [(o, t) for o, t, _ in titles if LUXEMBOURGISH.search(o)]
    report("Non-German text tagged lang=de (Luxembourgish)", lux)

    print("\nRun with --show to print every match for inspection.")


if __name__ == "__main__":
    main()
