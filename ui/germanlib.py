"""German publisher register and name matching.

Extracted from the Ground News scraper so the explorer UI can use it without
depending on the scraper. Vendored into each repo that needs it
(news-ground-news, news-explorer) — if you change one, change the other.
"""

import re

GERMAN_PUBLISHER_REGISTER = {
    "public_broadcasters": [
        "Tagesschau", "ZDF", "ZDFheute", "Deutschlandfunk", "Deutsche Welle",
        "WDR", "NDR", "BR", "SWR", "MDR", "rbb", "HR", "SR",
    ],
    "national_quality_dailies": [
        "Frankfurter Allgemeine Zeitung", "FAZ.NET", "Süddeutsche Zeitung",
        "Die Welt", "WELT", "Die Tageszeitung", "taz", "Der Tagesspiegel",
        "Frankfurter Rundschau", "NZZ Deutschland",
    ],
    "national_magazines_portals": [
        "Der Spiegel", "SPIEGEL Online", "Stern", "Focus", "FOCUS Online",
        "Die Zeit", "ZEIT ONLINE", "Cicero", "Blätter für deutsche und internationale Politik",
    ],
    "tabloids_mass_media": [
        "Bild", "BILD.de", "B.Z.", "Express", "Hamburger Morgenpost", "tz München",
    ],
    "business_finance": [
        "Handelsblatt", "WirtschaftsWoche", "Manager Magazin", "Boerse Frankfurt", "Finanzen.net",
    ],
    "tech_digital": [
        "Heise Online", "Golem.de", "Netzpolitik.org", "t3n",
    ],
    "major_regional_dailies": [
        "Rheinische Post", "Kölner Stadt-Anzeiger", "Stuttgarter Zeitung",
        "Münchner Merkur", "Hamburger Abendblatt", "Berliner Zeitung",
        "Berliner Morgenpost", "Hannoversche Allgemeine Zeitung", "Leipziger Volkszeitung",
        "Sächsische Zeitung", "Badische Zeitung", "Nürnberger Nachrichten", "Wetterauer Zeitung",
    ],
}

GERMAN_PUBLISHER_NAMES = {
    name.lower() for names in GERMAN_PUBLISHER_REGISTER.values() for name in names
}


# A handful of register entries are real outlet names that are ALSO plain
# English words or common name fragments in unrelated outlets — matching
# these as anything less than the full name produces real false positives
# (checked against this dataset): "Express" alone matches "Indian Express",
# "Daily Express", "Express Tribune"; "Focus" risks the same. These require
# an exact full-name match rather than the word-level matching below.
_AMBIGUOUS_GERMAN_NAMES = {"express", "focus"}


def _tokenize(s: str) -> list[str]:
    # \w is Unicode-aware in Python 3 str regexes, so accented letters
    # (e.g. "Brújula") stay part of their word instead of splitting into
    # fragments like "br" + "jula" — an earlier ASCII-only version of this
    # did exactly that and produced a false German-outlet match.
    return re.findall(r"\w+", s.lower())


def is_german_source_name(source_name: str) -> bool:
    """Whether a scraped source's name matches the German publisher
    register — case-insensitive, matched at the word level (not raw
    substring) so short register entries don't collide with unrelated
    names. A naive substring check makes "BR" (Bayerischer Rundfunk) match
    inside "Breitbart" and "CNN Brasil", and "stern" match inside "Western
    Journal" — both confirmed happening against this dataset before this
    fix. Word-level containment (register's token sequence must appear as
    a contiguous run of whole tokens in the name, or vice versa) avoids
    that while still matching real variants like "Spiegel" vs register's
    "Der Spiegel", or "focus.de" vs register's "Focus" (tokenizes to
    ["focus", "de"], still contains ["focus"] as a whole token).
    """
    n = (source_name or "").strip().lower()
    if not n:
        return False
    if n in GERMAN_PUBLISHER_NAMES:
        return True

    name_tokens = _tokenize(n)
    if not name_tokens:
        return False

    for reg in GERMAN_PUBLISHER_NAMES:
        if reg in _AMBIGUOUS_GERMAN_NAMES:
            continue  # exact-match only, already checked above
        reg_tokens = _tokenize(reg)
        if not reg_tokens:
            continue
        shorter, longer = sorted([name_tokens, reg_tokens], key=len)
        for i in range(len(longer) - len(shorter) + 1):
            if longer[i:i + len(shorter)] == shorter:
                return True
    return False
