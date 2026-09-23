"""
One-shot execution of the German & Regional News Discovery pipeline
(Stages 1-5 from the earlier planning conversation) — run once end-to-end,
not an unbounded auto-loop.

Phase A — Search & document: run every seed term through Ground News'
    search endpoint, log EVERY candidate link found (event or matched
    interest) to data/discovery/german_discovery_candidates.jsonl, regardless of
    whether it ends up getting scraped. This is the "document the links at
    the very least so we can get back to them" step.

Phase B — Scrape: feed the same term list into the real scraper
    (scraper.py --only --query ...), which does the actual language/source
    determination — each source's real `lang` and the story's `place` only
    become known once the article page itself is parsed, not from search
    results alone. This is the existing, already-tested scrape pipeline;
    nothing new here.

Phase C — Bounded tag expansion (ONE round, not a loop): after Phase B,
    look at what's newly in the dataset that's actually about Germany
    (place=Germany, not just "cites a German source" — that broader
    definition was tried and produced false positives, see conversation),
    pull the top newly-discovered tags not already in the seed list, and
    run ONE more Phase A + Phase B pass with just those. Stops there —
    doesn't recurse further, to keep the request volume against
    ground.news bounded and auditable.
"""

import argparse
import json
import os
import re
import subprocess
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import paths  # noqa: E402

REPO_ROOT = paths.REPO_ROOT
sys.path.insert(0, REPO_ROOT)
sys.path.insert(0, os.path.join(REPO_ROOT, "ui"))

from scraper import make_session, search_topic_preview, GERMAN_SEED_KEYWORDS  # noqa: E402

def candidates_log():
    return os.path.join(paths.source_dir("discovery"), "german_discovery_candidates.jsonl")


def output_jsonl():
    return os.path.join(paths.source_dir("ground_news"), "ground_news.jsonl")

# ── Seed term list ───────────────────────────────────────────────────────
# Categorized per the brief: government, public policy, sport/football/
# olympics/FIFA, business, EU/international, cities, big events — mixing
# plain English and German terms, biased toward proper nouns since that's
# what was empirically shown to actually return hits (see conversation:
# German generic/abstract words return ~0 results, proper nouns return
# real hits even in Ground News' English-translated titles).
SEED_TERMS = {
    "government": [
        "Bundesregierung", "Bundeskanzler Merz", "Bundestag", "Bundesrat",
        "CDU", "CSU", "SPD", "AfD", "Die Linke", "Grüne", "FDP",
        "Friedrich Merz", "Merz", "Robert Habeck", "Lars Klingbeil",
        "Koalition Deutschland", "Bundesverfassungsgericht",
    ],
    "public_policy": [
        "Heizungsgesetz", "Rentenreform Deutschland", "Mindestlohn Deutschland",
        "Wehrpflicht Deutschland", "Asylpolitik Deutschland", "Migrationspolitik Deutschland",
        "Klimapolitik Deutschland", "Bürgergeld",
    ],
    "sport_football_olympics_fifa": [
        "Bundesliga", "DFB", "FIFA Deutschland", "Bayern München",
        "Borussia Dortmund", "RB Leipzig", "deutsche Nationalmannschaft",
        "Olympia Deutschland",
    ],
    "cities": [
        "Berlin", "Frankfurt", "München", "Hamburg", "Köln", "Stuttgart",
        "Leipzig", "Dresden",
    ],
    "business": [
        "Deutsche Bank", "Audi", "BMW", "Bosch", "Siemens", "Volkswagen",
        "SAP", "Mercedes-Benz", "Allianz", "Bayer AG", "BASF",
    ],
    "eu_international": [
        "Europäisches Parlament", "EU-Kommission", "Frankreich",
        "Emmanuel Macron", "Europäische Union",
    ],
    "big_events_general": [
        "Bundestagswahl", "Landtagswahl", "Streik Deutschland",
        "Inflation Deutschland", "Energiekrise Deutschland",
    ],
}

# Merge in the (already tested, already in use) seed keyword bank too, and
# dedupe.
for terms in GERMAN_SEED_KEYWORDS.values():
    SEED_TERMS.setdefault("previously_seeded", []).extend(terms)

ALL_TERMS = sorted({t for terms in SEED_TERMS.values() for t in terms})


def log_candidates(term: str, result: dict) -> int:
    n = 0
    with open(candidates_log(), "a") as f:
        for e in result.get("events", []):
            f.write(json.dumps({"searched_term": term, "kind": "event", **e}) + "\n")
            n += 1
        for it in result.get("interests", []):
            f.write(json.dumps({"searched_term": term, "kind": "interest", **it}) + "\n")
            n += 1
    return n


def phase_a_search(terms: list[str]) -> tuple[set[str], set[str]]:
    """Search every term, log every candidate link. Returns (query terms
    worth feeding to the real scraper, interest slugs discovered)."""
    session = make_session()
    interest_slugs: set[str] = set()
    total_events = total_interests = 0
    print(f"\n=== PHASE A: searching {len(terms)} terms, documenting candidates ===")
    for i, term in enumerate(terms, 1):
        try:
            result = search_topic_preview(term, session)
        except Exception as e:
            print(f"  [{i}/{len(terms)}] {term!r} -> ERROR: {e}")
            continue
        if result.get("error"):
            # search_topic_preview swallows its own exceptions into this
            # field — surface it instead of silently reporting "0 results",
            # which looks identical to "genuinely nothing found" otherwise.
            print(f"  [{i}/{len(terms)}] {term!r} -> REQUEST FAILED: {result['error']}")
            continue
        n = log_candidates(term, result)
        n_events, n_interests = len(result.get("events", [])), len(result.get("interests", []))
        total_events += n_events
        total_interests += n_interests
        for it in result.get("interests", []):
            interest_slugs.add(it["slug"])
        print(f"  [{i}/{len(terms)}] {term!r} -> {n_events} events, {n_interests} interests logged ({n} lines)")
    print(f"  Phase A total: {total_events} events, {total_interests} interests across {len(terms)} terms")
    return set(terms), interest_slugs


def phase_b_scrape(query_terms: set[str], interest_slugs: set[str]) -> bool:
    """Returns True if the scrape ran (even if it found nothing new to
    write), False if there was nothing to search at all."""
    if not query_terms and not interest_slugs:
        print("\n=== PHASE B: skipped — no query terms or interests to scrape ===")
        return False
    print(f"\n=== PHASE B: scraping — {len(query_terms)} query terms, {len(interest_slugs)} discovered interests ===")
    cmd = [sys.executable, os.path.join(REPO_ROOT, "scrapers", "ground_news", "scraper.py"), "--only"]
    for t in sorted(query_terms):
        cmd += ["--query", t]
    for s in sorted(interest_slugs):
        cmd += ["--interest", s]
    result = subprocess.run(cmd, cwd=REPO_ROOT)
    if result.returncode != 0:
        # scraper.py exits 1 when discovery finds zero stubs at all — a
        # legitimate "nothing here" outcome (e.g. every search call above
        # got rate-limited), not a crash. Don't let it kill this script;
        # just report it and move on so a bad round doesn't lose earlier
        # rounds' already-written progress.
        print(f"  scraper.py exited with code {result.returncode} — treating as "
              f"'nothing found this round' and continuing.")
        return False
    return True


def count_dataset() -> tuple[int, int]:
    with open(output_jsonl()) as f:
        rows = [json.loads(l) for l in f if l.strip()]
    de_place = sum(1 for r in rows if "Germany" in [p.get("name") for p in (r.get("place") or [])])
    return len(rows), de_place


# Tags too broad to be useful search seeds on their own — they'd just
# re-match a huge, generic slice of Ground News rather than anything
# specifically German. Excluded from Phase C's candidate list outright.
_GENERIC_TAG_DENYLIST = {
    "politics", "europe", "economy", "business", "sports", "international",
    "military", "world", "science", "technology", "health & medicine",
    "entertainment", "crime", "law", "media", "education",
}


def _refine_candidate_term(name: str) -> str | None:
    """Turn a raw topic-tag display name into something worth searching:
    pull the short form out of a parenthetical abbreviation (e.g.
    "Alternative For Germany (AfD)" -> "AfD" — both were confirmed to work
    fine as search terms individually, but keeping the short form matches
    how the rest of the seed list is written), and drop anything on the
    generic-tag denylist. Returns None if the tag should be skipped.
    """
    if name.strip().lower() in _GENERIC_TAG_DENYLIST:
        return None
    m = re.search(r"\(([^)]+)\)\s*$", name)
    if m:
        return m.group(1).strip()
    return name.strip()


def phase_c_expand(already_used: set[str], top_n: int = 15) -> set[str]:
    """One bounded round: find new candidate tags from what's now in the
    dataset (place=Germany stories specifically — see module docstring for
    why), not already in `already_used`."""
    from common import load_stories, sources_table, german_expansion_candidates

    print("\n=== PHASE C: computing tag-expansion candidates from freshly scraped data ===")
    stories, by_slug = load_stories(output_jsonl())
    articles = sources_table(by_slug)
    candidates, n_de = german_expansion_candidates(stories, articles, exclude=already_used, top_n=top_n)
    print(f"  {n_de} place=Germany stories in dataset now; top new candidates:")
    new_terms = set()
    for row in candidates.itertuples():
        refined = _refine_candidate_term(row.name)
        status = f"-> {refined!r}" if refined and refined != row.name else ("-> skipped (too generic)" if refined is None else "")
        print(f"    {row.name} ({row.count}) {status}")
        if refined:
            new_terms.add(refined)
    return new_terms


def parse_args():
    p = argparse.ArgumentParser(description="German discovery pipeline runner")
    paths.add_data_dir_arg(p)
    p.add_argument(
        "--phase-c-only", action="store_true",
        help="Skip round 1 (seed-term search + scrape) and go straight to the "
             "bounded tag-expansion round using whatever's already in the "
             "dataset. Use this to retry round 2 without redoing round 1.",
    )
    p.add_argument(
        "--cooldown", type=int, default=30, metavar="SECONDS",
        help="Pause before the tag-expansion round's search calls, to let any "
             "rate-limiting from the round-1 scrape settle first (default: 30s).",
    )
    return p.parse_args()


if __name__ == "__main__":
    args = parse_args()
    paths.use_data_dir(args.data_dir)
    os.makedirs(os.path.dirname(candidates_log()), exist_ok=True)
    start = time.time()
    before_total, before_de = count_dataset()
    print(f"Dataset before: {before_total} stories total, {before_de} tagged place=Germany")

    if not args.phase_c_only:
        print(f"Seed term count: {len(ALL_TERMS)}")
        query_terms, interest_slugs = phase_a_search(ALL_TERMS)
        phase_b_scrape(query_terms, interest_slugs)
        after_r1_total, after_r1_de = count_dataset()
        print(f"\nAfter round 1: {after_r1_total} stories total ({after_r1_total - before_total:+d}), "
              f"{after_r1_de} tagged place=Germany ({after_r1_de - before_de:+d})")
    else:
        print("--phase-c-only: skipping round 1, using dataset as-is.")

    # Round 2 — bounded tag expansion, one hop only
    if args.cooldown:
        print(f"\nCooling down {args.cooldown}s before round 2's search calls...")
        time.sleep(args.cooldown)

    used_lower = {t.lower() for t in ALL_TERMS}
    new_terms = phase_c_expand(used_lower, top_n=15)
    if new_terms:
        query_terms2, interest_slugs2 = phase_a_search(sorted(new_terms))
        phase_b_scrape(query_terms2, interest_slugs2)
    else:
        print("  No new candidate terms found — skipping round 2.")

    after_final_total, after_final_de = count_dataset()
    elapsed = time.time() - start
    print(f"\n{'=' * 60}")
    print(f"DONE in {elapsed / 60:.1f} minutes")
    print(f"Dataset: {before_total} -> {after_final_total} stories total ({after_final_total - before_total:+d})")
    print(f"place=Germany: {before_de} -> {after_final_de} ({after_final_de - before_de:+d})")
    print(f"Candidate links documented (all rounds): see {candidates_log()}")
