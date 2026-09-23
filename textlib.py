"""Shared article-text helpers: cleaning extractions and taking a lede.

Used by the enrichment scraper (which produces article text), unify.py (which
copies it into the unified format) and the UI (which renders it) — so a
"summary" means the same thing everywhere and no consumer invents its own
character slice. Deliberately dependency-free: the scrapers run in a conda env
with trafilatura/curl_cffi, the UI in a uv venv without them.
"""
import re

# Lines an extractor keeps that are page furniture, not article prose: share /
# follow CTAs, reading-time badges, teaser bullet lists, comment counters. They
# sit right at the top of the extraction on many outlets, so an unfiltered
# "first N chars" summary was mostly this.
_DROP_LINE_RES = [re.compile(p, re.I) for p in (
    r"^uns auf \w+ folgen$",
    r"^(folgen sie uns|jetzt folgen|hier folgen)\b",
    r"^(teilen|drucken|merken|speichern|feedback|kommentare?)( \(\d+\))?$",
    r"^(anzeige|werbung|sponsored|gesponsert)$",
    r"^\d+\s*min(\.|uten)?\s*lesezeit$",
    r"\blese(dauer|zeit)\s*[:•]\s*\d+\s*min",
    r"^(lesen sie auch|mehr zum thema|auch interessant|das könnte sie auch interessieren)\b",
    r"^(newsletter|zum newsletter|jetzt kostenlos|jetzt abonnieren|abo)\b",
    r"^(datenschutz|impressum|cookies?|alle rechte vorbehalten)\b",
    r"^-\s",                       # teaser bullet lists ("- Alle Transfer-News …")
)]

SENTENCE_END = ('.', '!', '?', '"', '“', '”', '«', '»', '…', ':')


def clean_text(text: str) -> str:
    """Drop page-furniture lines from an extraction, keeping the article's own
    paragraphs and subheads in order."""
    kept = [l.strip() for l in (text or "").split("\n")]
    kept = [l for l in kept if l and not any(r.search(l) for r in _DROP_LINE_RES)]
    return "\n".join(kept)


def lede(text: str, target: int = 600) -> str:
    """The article's opening *prose*, not its first N characters.

    Takes whole lines that read like article paragraphs — long enough, and
    ending on (or containing) sentence punctuation — so headlines, subheads,
    dateline stubs and ticker separators are skipped rather than becoming the
    summary. Never cuts mid-word or mid-sentence; falls back to the cleaned
    head if the page yielded no prose at all (paywalled pages often extract to
    a bare table of contents)."""
    lines = [l for l in clean_text(text).split("\n") if l]
    prose = [l for l in lines
             if len(l) >= 80 and not l.startswith("+++")
             and (l.endswith(SENTENCE_END) or ". " in l)]
    if not prose:
        head = "\n".join(lines)[:target]
        return head.rsplit(" ", 1)[0] + "…" if len(head) == target else head
    out = []
    for line in prose:
        out.append(line)
        if sum(len(l) for l in out) >= target:
            break
    summary = "\n\n".join(out)
    if len(summary) > target * 1.8:  # one very long paragraph: end on a sentence
        cut = summary.rfind(". ", 0, int(target * 1.8))
        if cut > target // 2:
            summary = summary[:cut + 1]
    return summary
