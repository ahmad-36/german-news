"""
Ground News scraper.
Uses curl_cffi to impersonate Chrome and parses RSC flight data
from server-rendered Next.js pages.

Output: JSONL file with one story per line.
"""
import json
import time
import re
import os
import sys
import random
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock, Semaphore
from curl_cffi import requests
from bs4 import BeautifulSoup
from tqdm import tqdm

BASE = "https://ground.news"
SEARCH_API = "https://web-api-cdn.ground.news/api/public/search/url?includeInternalPages=true"
MAX_RETRIES = 4
RETRY_DELAY = 5
WORKERS = 4
MIN_REQUEST_DELAY = 1.5
MAX_REQUEST_DELAY = 4.0

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import paths  # noqa: E402

OUTPUT_DIR = paths.source_dir("ground_news")   # default; --output-dir overrides
OUTPUT_FILE_NAME = "ground_news.jsonl"

write_lock = Lock()
request_semaphore = Semaphore(WORKERS)
stats = {"completed": 0, "errors": 0, "skipped": 0}
stats_lock = Lock()

IMPERSONATE_PROFILES = [
    "chrome",
    "chrome110",
    "chrome116",
    "chrome120",
    "chrome124",
]


def random_delay():
    time.sleep(random.uniform(MIN_REQUEST_DELAY, MAX_REQUEST_DELAY))


def make_session():
    profile = random.choice(IMPERSONATE_PROFILES)
    return requests.Session(impersonate=profile)


def fetch(session, url: str) -> str:
    """Fetch a URL with retries and return the raw HTML text."""
    for attempt in range(MAX_RETRIES):
        try:
            with request_semaphore:
                r = session.get(url, timeout=30)
                random_delay()
            if r.status_code == 429:
                wait = RETRY_DELAY * (attempt + 2)
                print(f"  Rate limited on {url}, waiting {wait}s...")
                time.sleep(wait)
                continue
            if r.status_code == 502:
                time.sleep(RETRY_DELAY * (attempt + 1))
                continue
            r.raise_for_status()
            return r.text
        except Exception:
            if attempt < MAX_RETRIES - 1:
                time.sleep(RETRY_DELAY * (attempt + 1))
            else:
                raise
    raise RuntimeError(f"Failed after {MAX_RETRIES} retries: {url}")


_JS_ESCAPE_RE = re.compile(r"\\(.)")
_JS_ESCAPE_MAP = {
    '"': '"', "\\": "\\", "'": "'",
    "n": "\n", "t": "\t", "r": "\r",
    "/": "/", "b": "\b", "f": "\f",
}


def _js_unescape(s: str) -> str:
    """Unescape JS string escape sequences left-to-right."""
    return _JS_ESCAPE_RE.sub(
        lambda m: _JS_ESCAPE_MAP.get(m.group(1), m.group(0)), s
    )


def extract_flight_data(html: str) -> str:
    """Extract and unescape RSC flight data from the page HTML."""
    soup = BeautifulSoup(html, "html.parser")
    flight = ""
    for script in soup.find_all("script"):
        s = script.string or ""
        if "self.__next_f" in s:
            m = re.search(r'push\(\[1,"(.*)"\]\)', s, re.DOTALL)
            if m:
                flight += m.group(1)
    return _js_unescape(flight)


def extract_json_block(text: str, start_idx: int, open_char: str = "{") -> str:
    """Extract a balanced JSON block (object or array) from text."""
    close_char = "}" if open_char == "{" else "]"
    depth = 0
    in_string = False
    escape_next = False
    for i, c in enumerate(text[start_idx:]):
        if escape_next:
            escape_next = False
            continue
        if c == "\\":
            escape_next = True
            continue
        if c == '"' and not escape_next:
            in_string = not in_string
            continue
        if in_string:
            continue
        if c == open_char:
            depth += 1
        elif c == close_char:
            depth -= 1
        if depth == 0 and i > 0:
            return text[start_idx:start_idx + i + 1]
    return ""


# Next.js's React Server Components streaming protocol can hoist a large
# string to its own numbered chunk and reference it elsewhere as "$<hex
# id>" instead of inlining it directly. The chunk itself IS present in the
# same response (confirmed — a naive first attempt at this concluded it
# wasn't and just blanked these out; that was wrong): it's written as
# "<id>:T<hex-length>,<raw text>" — a length-prefixed raw-text row, not a
# quoted JSON string — so a plain json.loads() of the surrounding object
# never sees it, and a search for '<id>:"' (expecting JSON-string syntax)
# never finds it either. This resolves the reference by locating that row
# and reading its content directly.
_RSC_UNRESOLVED_REF_RE = re.compile(r"^\$([0-9a-fA-F]+)$")


def _resolve_flight_ref(flight: str, ref_id: str) -> str:
    """Look up a flight-stream row ("<ref_id>:T<hex-length>,<text>") and
    return its text. The length is an exact UTF-8 byte count declared by
    the protocol itself — used directly rather than guessing where the
    content ends by scanning for a boundary pattern (tried that first: row
    separators aren't reliably a newline once JS string escapes have been
    resolved, so it silently over-read into unrelated flight data past the
    real end on at least one real row)."""
    m = re.search(rf"(?:^|\n){re.escape(ref_id)}:", flight)
    if not m:
        return ""
    pos = m.end()
    type_m = re.match(r"T([0-9a-fA-F]+),", flight[pos:pos + 20])
    if not type_m:
        return ""
    length = int(type_m.group(1), 16)
    content_start = pos + type_m.end()
    remaining_bytes = flight[content_start:].encode("utf-8")
    return remaining_bytes[:length].decode("utf-8", errors="replace")


def _resolve_summary_field(flight: str, value: str) -> str:
    """Resolve a chatGptSummaries field that arrived as an unresolved
    reference instead of inline text. Falls back to blank (not the literal
    "$8e" placeholder) on the rare row that genuinely isn't in this
    response — e.g. a Suspense boundary that only resolves post-hydration."""
    if not value:
        return value
    m = _RSC_UNRESOLVED_REF_RE.match(value.strip())
    if not m:
        return value
    return _resolve_flight_ref(flight, m.group(1))


# Boilerplate/junk phrases that show up when a source site has no clean
# article excerpt and Ground News' own scraper fell back to raw page text
# — subscription paywalls, WordPress post metadata, etc. Confirmed against
# a real scraped source (quatrostrategies.ca): its "description" was
# literally "Posted by: ... Categories: ... Subscribe to unlock this
# insight ... START YOUR TRIAL NOW ... .vc_custom_1452662201783{margin...".
# That's page furniture, not the article — blanked out rather than shown.
_BOILERPLATE_MARKERS = (
    "subscribe to unlock", "start your trial", "already a member",
    "no comments", ".vc_custom_", "!important}",
)


def _blank_if_boilerplate(text: str) -> str:
    if not text:
        return text
    lowered = text.lower()
    if any(marker in lowered for marker in _BOILERPLATE_MARKERS):
        return ""
    return text


# ── Phase 1: Collect article slugs from the homepage ─────────────────────

def extract_article_stubs(html: str) -> list[dict]:
    """Extract event stubs (slug + title + sourceCount) from a page's HTML.

    Works on any server-rendered Ground News HTML — live or a Wayback Machine
    snapshot — since both embed the same RSC flight data in <script> tags
    (the Wayback crawler just saves the raw HTTP response, no JS execution
    needed for this data to be present).
    """
    flight = extract_flight_data(html)

    results = []
    seen_slugs = set()

    # Method 1: Extract from RSC flight data (sourceCount context)
    for m in re.finditer(r'"sourceCount":(\d+)', flight):
        ctx_start = max(0, m.start() - 600)
        ctx_end = min(len(flight), m.end() + 400)
        ctx = flight[ctx_start:ctx_end]

        slug_m = re.search(r'"slug":"([^"]+)"', ctx)
        title_m = re.search(r'"title":"([^"]*)"', ctx)
        # "place" sits right after sourceCount on listing/interest pages —
        # a story's country tag, free to read without opening its article.
        place_m = re.search(r'"place":\{"id":"[A-Z]{2}","name":"([^"]+)"', flight[m.end():m.end() + 200])

        if not slug_m:
            continue
        slug = slug_m.group(1)
        if slug in seen_slugs:
            continue
        # Skip non-article slugs: too short or no hyphens (source/interest names)
        if len(slug) < 10 or "-" not in slug:
            continue
        seen_slugs.add(slug)

        results.append({
            "slug": slug,
            "title": title_m.group(1) if title_m else "",
            "source_count": int(m.group(1)),
            "place": place_m.group(1) if place_m else "",
            "url": f"{BASE}/article/{slug}",
        })

    # Method 2: Extract from HTML href attributes (/article/slug links)
    for href_m in re.finditer(r'href="/article/([^"]+)"', html):
        slug = href_m.group(1)
        if slug in seen_slugs:
            continue
        if len(slug) < 10 or "-" not in slug:
            continue
        seen_slugs.add(slug)
        results.append({
            "slug": slug,
            "title": "",
            "source_count": 0,
            "place": "",
            "url": f"{BASE}/article/{slug}",
        })

    return results


def discover_trending_topics(session) -> list[dict]:
    """Fetch the Ground News homepage and read off its `trendingInterests`
    list — topic name, slug, and `refCount` (how many stories reference it).

    This is a cheap way to answer "what are the most-used topics right now"
    without scraping any article pages: the counts are already sitting in
    the homepage's own RSC flight data.
    """
    html = fetch(session, f"{BASE}/")
    flight = extract_flight_data(html)

    marker = '"trendingInterests":['
    idx = flight.find(marker)
    if idx < 0:
        return []
    start = idx + len('"trendingInterests":')
    raw = extract_json_block(flight, start, "[")
    if not raw:
        return []
    try:
        interests = json.loads(raw)
    except json.JSONDecodeError:
        return []

    return [
        {
            "name": i.get("name", ""),
            "slug": i.get("slug", ""),
            "type": i.get("type", "topic"),
            "ref_count": i.get("refCount", 0),
        }
        for i in interests
    ]


# A small seed list of German-language outlets, gathered from what this
# scraper has already picked up. Used only as a cheap pre-filter to spot
# likely German coverage in a listing page's source previews (name/slug are
# visible there; per-source `lang` is not — that's only known once the
# article page itself is parsed). Not exhaustive; scraping fills in the rest.
KNOWN_GERMAN_SOURCE_SLUGS = {
    "handelsblattcom", "zeit-online", "welt", "spiegel", "orfat-news",
    "focusde", "kurier", "tagesschau", "aachener-zeitungde",
    "sueddeutsche-zeitung", "frankfurter-allgemeine", "deutschlandfunk",
    "n-tvde", "die-presse", "bild", "sternde", "onetzde", "rndde",
    "zdfheutede", "faz", "taz", "dw", "ntv",
}


def count_known_source_mentions(flight: str, slugs: set[str]) -> int:
    """Count how many of the given source slugs appear in a page's flight
    data — a rough, cheap proxy for "how much coverage from these outlets
    shows up here", usable straight from a listing/interest page fetch."""
    return sum(1 for slug in slugs if f'"slug":"{slug}"' in flight)


# A broader German-outlet register, by name rather than slug. Unlike
# KNOWN_GERMAN_SOURCE_SLUGS above, these are NOT verified against real
# Ground News slugs — that would require seeing each outlet actually show
# up in scraped data first, which defeats the purpose of a register meant
# to cover outlets we haven't scraped yet. Instead this is matched directly
# against each source's own `source_name` (case-insensitive substring),
# which needs no slug guessing and works the moment an outlet appears in
# any scraped story, however it was discovered.
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


# Seed keywords for German/German-political coverage discovery via search.
# Tested empirically (see conversation) rather than assumed: proper nouns —
# people, parties, named laws/institutions — survive translation and appear
# verbatim even in Ground News' English-translated titles, so the German
# form finds real hits (e.g. "Bundeswehr" -> 10 events). Generic/abstract
# concepts do NOT survive translation — English titles use the English
# word, so the bare German term returns nothing (e.g. "Leitzins" -> 0
# events) while the English phrase, qualified with "Germany", does (e.g.
# "interest rate Germany" -> 8 events, 2 matched interests). So: keep
# proper nouns in German, translate generic concepts to English instead of
# to German.
GERMAN_SEED_KEYWORDS = {
    "us_politics": ["Trump", "US-Wahl", "Republikaner", "Weißes Haus", "US-Präsident"],
    "geopolitics": ["Ukraine", "Selenskyj", "Kreml", "Bundeswehr", "NATO summit Germany"],
    "economy": ["interest rate Germany", "German economy", "EZB", "tariffs Germany", "recession Germany"],
    "tech_ai": ["Künstliche Intelligenz", "KI", "semiconductor Germany", "data protection Germany"],
    "climate_energy": ["Energiewende", "climate change Germany", "E-Auto", "Strompreis", "Heizungsgesetz"],
    "domestic_politics": ["CDU", "AfD", "Merz", "Brandmauer", "Bundestag"],
}


def collect_article_slugs_from_page(url: str, session) -> list[dict]:
    """Fetch a live page and extract its event stubs."""
    html = fetch(session, url)
    return extract_article_stubs(html)


# ── Historical discovery via the Wayback Machine ──────────────────────────
# Ground News' listing pages only ever show what's *currently* trending, so
# there's no way to ask the live site "what was on /interest/ai on March 1st".
# But archive.org has independently crawled these same pages (often many
# times a day), and its snapshots are the same server-rendered HTML our
# extractor already understands. Article detail pages themselves are
# permanent on the live site (confirmed: a story discovered via a March
# snapshot still resolves live in July), so Wayback is only needed for
# *discovery* of what existed on a given day — the actual scrape still hits
# the fast, live /article/<slug> page.

CDX_API = "http://web.archive.org/cdx/search/cdx"
WAYBACK_RAW = "https://web.archive.org/web/{ts}id_/{url}"


def wayback_snapshot_timestamps(url: str, date_from: str, date_to: str, session) -> list[str]:
    """Return one archived snapshot timestamp per day for `url` within
    [date_from, date_to] (YYYYMMDD), via the CDX API."""
    params = {
        "url": url,
        "output": "json",
        "from": date_from,
        "to": date_to,
        "filter": "statuscode:200",
        "collapse": "timestamp:8",  # one snapshot per calendar day
    }
    for attempt in range(MAX_RETRIES):
        try:
            r = session.get(CDX_API, params=params, timeout=30)
            r.raise_for_status()
            rows = r.json()
            return [row[1] for row in rows[1:]] if len(rows) > 1 else []
        except Exception:
            if attempt < MAX_RETRIES - 1:
                time.sleep(RETRY_DELAY)
            else:
                raise


def collect_slugs_from_wayback(pages: list[str], date_from: str, date_to: str, session) -> list[dict]:
    """Discover article stubs that existed on Ground News listing pages
    sometime within [date_from, date_to], by replaying archived snapshots."""
    all_stubs = []
    seen = set()

    page_bar = tqdm(pages, desc="Wayback: scanning pages", unit="pg")
    for page_url in page_bar:
        try:
            timestamps = wayback_snapshot_timestamps(page_url, date_from, date_to, session)
        except Exception as e:
            print(f"\n  CDX error for {page_url}: {e}")
            continue

        for ts in timestamps:
            archive_url = WAYBACK_RAW.format(ts=ts, url=page_url)
            try:
                html = fetch(session, archive_url)
                stubs = extract_article_stubs(html)
            except Exception:
                continue
            new = 0
            for stub in stubs:
                if stub["slug"] not in seen:
                    seen.add(stub["slug"])
                    all_stubs.append(stub)
                    new += 1
            page_bar.set_postfix(total=len(all_stubs), snapshots=len(timestamps))
            random_delay()

    return all_stubs


def search_events(query: str, session) -> tuple[list[dict], list[str]]:
    """Query Ground News' public search-as-you-type API for a keyword.

    This is the same endpoint the site's search box calls (POST, JSON body
    `{"url": query}`). It returns a capped, mixed list of ~10 results: some
    are `type: "event"` (direct story matches — what we want) and some are
    `type: "interest"` (topic/person/place suggestions). There's no
    pagination param that changes the result count, so a single call is all
    a query gives us; the interest slugs it surfaces are still useful since
    following them via /interest/<slug> yields many more matching stories.

    Returns (event stubs in the same shape as collect_article_slugs_from_page,
    discovered interest slugs).
    """
    try:
        r = session.post(
            SEARCH_API,
            json={"url": query},
            headers={"content-type": "application/json", "x-gn-v": "web", "referer": f"{BASE}/"},
            timeout=20,
        )
        random_delay()
        r.raise_for_status()
        data = r.json()
    except Exception as e:
        print(f"  Search error for '{query}': {e}")
        return [], []

    events, interests = [], []
    for item in data.get("searchResults", []):
        slug = item.get("slug", "")
        if not slug:
            continue
        if item.get("type") == "event":
            events.append({
                "slug": slug,
                "title": item.get("title", ""),
                "source_count": item.get("sourceCount", 0),
                "url": f"{BASE}/article/{slug}",
            })
        elif item.get("type") == "interest":
            interests.append(slug)
    return events, interests


def search_topic_preview(query: str, session) -> dict:
    """Same search endpoint as `search_events`, but for discovery/preview UI
    rather than scraping: keeps the full interest objects (name, subtype,
    site-wide `refCount`) instead of discarding everything but the slug, and
    keeps event stubs' place string too. One request, no article pages
    fetched — used by the Topic Discovery page's "search any topic" and
    "scrape by publisher" panels to answer "how much is out there" before
    committing to a scrape.
    """
    try:
        r = session.post(
            SEARCH_API,
            json={"url": query},
            headers={"content-type": "application/json", "x-gn-v": "web", "referer": f"{BASE}/"},
            timeout=20,
        )
        random_delay()
        r.raise_for_status()
        data = r.json()
    except Exception as e:
        return {"interests": [], "events": [], "error": str(e)}

    interests, events = [], []
    for item in data.get("searchResults", []):
        if item.get("type") == "interest":
            interests.append({
                "name": item.get("title", ""),
                "slug": item.get("slug", ""),
                "sub_type": item.get("subType", ""),
                "ref_count": item.get("refCount") or 0,
            })
        elif item.get("type") == "event":
            events.append({
                "title": item.get("title", ""),
                "slug": item.get("slug", ""),
                "source_count": item.get("sourceCount", 0),
                "place": item.get("placeString", ""),
            })
    return {"interests": interests, "events": events}


LISTING_PAGES = [
    f"{BASE}/top",
    f"{BASE}/blindspot",
    BASE,
    f"{BASE}/interest/us-politics",
    f"{BASE}/interest/ai",
    f"{BASE}/interest/business-and-markets",
    f"{BASE}/interest/environment-and-climate",
    f"{BASE}/interest/health-and-medicine",
    f"{BASE}/interest/international",
    f"{BASE}/interest/tech",
    f"{BASE}/interest/science",
    f"{BASE}/interest/education_fb8947",
    f"{BASE}/interest/sports",
    f"{BASE}/interest/entertainment",
    f"{BASE}/interest/world",
    f"{BASE}/interest/crime",
    f"{BASE}/interest/economy",
    f"{BASE}/interest/energy",
    f"{BASE}/interest/law",
    f"{BASE}/interest/media",
]


def collect_all_slugs(
    queries: list[str] | None = None,
    date_range: tuple[str, str] | None = None,
    interests: list[str] | None = None,
    only_specified: bool = False,
):
    """Collect article slugs.

    - Default: crawl the live listing pages (today's trending snapshot).
    - date_range=(from, to) (YYYYMMDD): instead replay archived Wayback
      Machine snapshots of those same listing pages within the window, since
      the live pages only ever show "now" and can't answer a historical
      question.
    - queries: optional keyword searches, layered on top of either mode.
    - interests: optional explicit /interest/<slug> pages to crawl directly
      (e.g. a country page like "germany"), skipping search discovery.
    - only_specified: when True, skip the default LISTING_PAGES crawl (and
      Wayback replay) entirely and use ONLY `queries`/`interests` as the
      discovery source — for a targeted run instead of the usual broad one.
    """
    session = make_session()
    all_stubs = []
    seen = set()

    if only_specified:
        pass
    elif date_range:
        date_from, date_to = date_range
        all_stubs = collect_slugs_from_wayback(LISTING_PAGES, date_from, date_to, session)
        seen = {s["slug"] for s in all_stubs}
    else:
        pbar = tqdm(LISTING_PAGES, desc="Phase 1: Collecting article slugs", unit="pg")
        for page_url in pbar:
            try:
                stubs = collect_article_slugs_from_page(page_url, session)
                new = 0
                for stub in stubs:
                    if stub["slug"] not in seen:
                        seen.add(stub["slug"])
                        all_stubs.append(stub)
                        new += 1
                pbar.set_postfix(total=len(all_stubs), new=new)
            except Exception as e:
                print(f"\n  Error on {page_url}: {e}")
            random_delay()

    if queries:
        discovered_interests: set[str] = set()
        qbar = tqdm(queries, desc="Phase 1b: Searching subjects", unit="query")
        for q in qbar:
            events, interests = search_events(q, session)
            new = 0
            for stub in events:
                if stub["slug"] not in seen:
                    seen.add(stub["slug"])
                    all_stubs.append(stub)
                    new += 1
            discovered_interests.update(interests)
            qbar.set_postfix(total=len(all_stubs), new=new)

        if discovered_interests:
            ibar = tqdm(sorted(discovered_interests), desc="Phase 1c: Discovered interest pages", unit="pg")
            for islug in ibar:
                try:
                    stubs = collect_article_slugs_from_page(f"{BASE}/interest/{islug}", session)
                    new = 0
                    for stub in stubs:
                        if stub["slug"] not in seen:
                            seen.add(stub["slug"])
                            all_stubs.append(stub)
                            new += 1
                    ibar.set_postfix(total=len(all_stubs), new=new)
                except Exception as e:
                    print(f"\n  Error on interest/{islug}: {e}")
                random_delay()

    if interests:
        xbar = tqdm(interests, desc="Phase 1d: Explicit interest pages", unit="pg")
        for islug in xbar:
            try:
                stubs = collect_article_slugs_from_page(f"{BASE}/interest/{islug}", session)
                new = 0
                for stub in stubs:
                    if stub["slug"] not in seen:
                        seen.add(stub["slug"])
                        all_stubs.append(stub)
                        new += 1
                xbar.set_postfix(total=len(all_stubs), new=new)
            except Exception as e:
                print(f"\n  Error on interest/{islug}: {e}")
            random_delay()

    return all_stubs


# ── Phase 2: Scrape each article detail page ──────────────────────────────

def parse_article_page(html: str) -> dict | None:
    """Parse an article detail page and extract event + sources data."""
    flight = extract_flight_data(html)

    # --- Event data ---
    event_marker = '"event":{"biasSourceCount"'
    idx = flight.find(event_marker)
    if idx < 0:
        return None

    event_start = idx + 8  # skip '"event":'
    event_raw = extract_json_block(flight, event_start, "{")
    if not event_raw:
        return None

    try:
        event = json.loads(event_raw)
    except json.JSONDecodeError:
        return None

    # Skip articles with fewer than 3 sources
    if event.get("sourceCount", 0) < 3:
        return None

    # --- Article sources ---
    sources = []
    src_marker = '"articleSources":[{'
    idx2 = flight.find(src_marker)
    if idx2 >= 0:
        src_start = idx2 + len('"articleSources":')
        src_raw = extract_json_block(flight, src_start, "[")
        if src_raw:
            try:
                sources = json.loads(src_raw)
            except json.JSONDecodeError:
                pass

    # --- Per-bias-side AI summaries + bias-comparison analysis ---
    # Ground News generates up to three separate bullet-point summaries per
    # story — one written from what left-leaning, center, and right-leaning
    # coverage each emphasize — plus a short "analysis" paragraph comparing
    # how the sides frame the story. All four live together in the event's
    # own `chatGptSummaries` object, so no extra fetch/parsing is needed
    # beyond what `event` (parsed above) already contains. A side's summary
    # is simply absent when that story has too little coverage from that
    # side to generate one (e.g. a near-unanimous-center story may have no
    # "right" entry at all).
    chatgpt_summaries = event.get("chatGptSummaries") or {}

    # --- Build output record ---
    interests = event.get("interests", [])

    record = {
        "id": event.get("id", ""),
        "slug": event.get("slug", ""),
        "title": event.get("title", ""),
        "generated_headline": event.get("generatedHeadline", ""),
        "description": event.get("description", ""),
        "dek": event.get("dek", ""),
        "summary_left": _resolve_summary_field(flight, chatgpt_summaries.get("left", "")),
        "summary_center": _resolve_summary_field(flight, chatgpt_summaries.get("center", "")),
        "summary_right": _resolve_summary_field(flight, chatgpt_summaries.get("right", "")),
        "bias_comparison": _resolve_summary_field(flight, chatgpt_summaries.get("analysis", "")),
        "date": event.get("start", ""),
        "source_count": event.get("sourceCount", 0),
        "bias_source_count": event.get("biasSourceCount", 0),
        "left_pct": event.get("leftSrcPercent", 0),
        "center_pct": event.get("cntrSrcPercent", 0),
        "right_pct": event.get("rightSrcPercent", 0),
        "overall_bias": event.get("overallBias", ""),
        "blindspot": event.get("blindspot"),
        "topics": [
            {"name": i.get("name", ""), "slug": i.get("slug", ""), "type": i.get("type", "")}
            for i in interests
        ],
        "place": event.get("place", []),
        "share_url": event.get("shareUrl", ""),
        "sources": [],
    }

    for src in sources:
        si = src.get("sourceInfo", {})
        bias_ratings = si.get("biasRatings", [])
        factuality = si.get("factuality", [])

        record["sources"].append({
            "title": src.get("title", ""),
            "original_title": src.get("originalTitle") or "",
            "url": src.get("url", ""),
            "date": src.get("date", ""),
            "description": _blank_if_boilerplate(src.get("description", "")),
            "original_description": _blank_if_boilerplate(src.get("originalDescription") or ""),
            "lang": src.get("lang", ""),
            "paywall": src.get("paywall", ""),
            "source_name": si.get("name", ""),
            "source_bias": si.get("bias", ""),
            "source_slug": si.get("slug", ""),
            "source_place": [
                {"id": p.get("id", ""), "name": p.get("name", "")}
                for p in (si.get("place") or [])
            ],
            "is_german_publisher": is_german_source_name(si.get("name", "")),
            "bias_ratings": [
                {
                    "reviewer": br.get("reviewer", {}).get("name", ""),
                    "rating": br.get("politicalBias", ""),
                }
                for br in bias_ratings
            ],
            "factuality": [
                {
                    "reviewer": fr.get("reviewer", {}).get("name", ""),
                    "rating": fr.get("factualityLabel", ""),
                }
                for fr in factuality
            ] if isinstance(factuality, list) else [],
        })

    return record


def process_and_write(stub: dict, output_path: str):
    """Fetch an article page, parse it, and write the result."""
    session = make_session()

    try:
        html = fetch(session, stub["url"])
    except Exception as e:
        with stats_lock:
            stats["errors"] += 1
        return None

    record = parse_article_page(html)
    if record is None:
        with stats_lock:
            stats["skipped"] += 1
        return None

    with write_lock:
        with open(output_path, "a") as f:
            json.dump(record, f)
            f.write("\n")

    with stats_lock:
        stats["completed"] += 1

    return record


def parse_args():
    import argparse
    p = argparse.ArgumentParser(description="Ground News scraper")
    p.add_argument(
        "--query", action="append", default=[], dest="queries",
        help="Keyword/subject to search for (repeatable), in addition to the "
             "standard topic/top/blindspot pages. Example: --query 'ukraine' --query 'ai regulation'",
    )
    p.add_argument(
        "--interest", action="append", default=[], dest="interests",
        help="Interest-page slug to crawl directly (repeatable), e.g. "
             "--interest germany --interest european-politics. Bypasses "
             "search discovery — use this when you already know the slug "
             "(see discover_trending_topics() / the Topic Discovery UI page).",
    )
    p.add_argument(
        "--only", action="store_true",
        help="Skip the default listing-page crawl and use ONLY --query/--interest "
             "as the discovery source, for a small targeted run instead of the "
             "usual broad one. Requires at least one --query or --interest.",
    )
    p.add_argument(
        "--fresh", action="store_true",
        help="Overwrite the output file instead of merging with previously scraped stories.",
    )
    p.add_argument(
        "--from-date", dest="from_date", default=None, metavar="YYYY-MM-DD",
        help="Discover stories via Wayback Machine snapshots of the listing pages "
             "starting from this date, instead of crawling the live (present-day) pages. "
             "Requires --to-date.",
    )
    p.add_argument(
        "--to-date", dest="to_date", default=None, metavar="YYYY-MM-DD",
        help="End of the historical discovery window (see --from-date).",
    )
    paths.add_data_dir_arg(p)
    p.add_argument(
        "--output-dir", default=None,
        help="Directory for the accumulated JSONL and range exports "
             "(default: <data root>/ground_news).",
    )
    p.add_argument(
        "--refresh-existing", action="store_true",
        help="Skip discovery and re-fetch every story already in the output file "
             "instead. Use this to pick up parser fixes/new fields, or to refresh "
             "stale bias percentages and source counts, on stories no longer "
             "reachable via the live listing pages. Requires an existing output file.",
    )
    args = p.parse_args()
    if bool(args.from_date) != bool(args.to_date):
        p.error("--from-date and --to-date must be given together")
    if args.refresh_existing and args.fresh:
        p.error("--refresh-existing re-fetches stories already in the output file; "
                 "--fresh would discard them first, so the two can't be combined")
    if args.only and not (args.queries or args.interests):
        p.error("--only requires at least one --query or --interest")
    if args.only and args.refresh_existing:
        p.error("--only and --refresh-existing are two different discovery modes; pick one")
    return args


# ── Main ──────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    args = parse_args()
    paths.use_data_dir(getattr(args, "data_dir", None))
    OUTPUT_DIR = args.output_dir or paths.source_dir("ground_news")
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    output_path = os.path.join(OUTPUT_DIR, OUTPUT_FILE_NAME)
    start_time = time.time()

    print(f"\n{'=' * 60}")
    print(f"Ground News Scraper")
    print(f"Output: {output_path}")
    print(f"Workers: {WORKERS} threads")
    print(f"Delay: {MIN_REQUEST_DELAY}-{MAX_REQUEST_DELAY}s per request")
    if args.queries:
        print(f"Subject queries: {args.queries}")
    if args.interests:
        print(f"Explicit interest pages: {args.interests}")
    if args.only:
        print("Mode: targeted (--only) — skipping the default listing-page crawl")
    date_range = None
    if args.from_date:
        date_range = (args.from_date.replace("-", ""), args.to_date.replace("-", ""))
        print(f"Historical window: {args.from_date} to {args.to_date} (via Wayback Machine discovery)")
    print(f"{'=' * 60}\n")

    # Load stories from previous runs so this run accumulates history instead
    # of overwriting it (Ground News' listing pages only ever show what's
    # currently trending, so each run is a snapshot of "right now").
    previous_records: dict[str, dict] = {}
    if not args.fresh and os.path.isfile(output_path):
        with open(output_path) as f:
            for line in f:
                if line.strip():
                    rec = json.loads(line)
                    slug = rec.get("slug") or rec.get("id")
                    if slug:
                        previous_records[slug] = rec
        print(f"Loaded {len(previous_records)} stories from previous runs.\n")

    if args.refresh_existing:
        # No discovery — re-fetch every already-known slug so parser fixes,
        # new fields, and updated bias/source-count data land on stories
        # that may no longer show up on the live listing pages.
        if not previous_records:
            print(f"--refresh-existing given but {output_path} has no stories to refresh. Exiting.")
            exit(1)
        stubs = [
            {"slug": slug, "title": rec.get("title", ""),
             "source_count": rec.get("source_count", 0), "url": f"{BASE}/article/{slug}"}
            for slug, rec in previous_records.items()
        ]
        print(f"Refreshing {len(stubs)} previously-scraped stories (skipping discovery).\n")
    else:
        # Phase 1: collect slugs
        stubs = collect_all_slugs(
            queries=args.queries, date_range=date_range,
            interests=args.interests, only_specified=args.only,
        )
        t1 = time.time() - start_time
        print(f"\nFound {len(stubs)} unique articles this run. ({t1:.0f}s)\n")

    if not stubs:
        print("No articles found. Exiting.")
        exit(1)

    # Phase 2: scrape each article into a scratch file, then merge below
    run_output_path = output_path + ".run"
    with open(run_output_path, "w"):
        pass

    with ThreadPoolExecutor(max_workers=WORKERS) as executor:
        futures = {
            executor.submit(process_and_write, stub, run_output_path): stub
            for stub in stubs
        }
        pbar = tqdm(
            as_completed(futures),
            total=len(futures),
            desc=f"Phase 2: Scraping articles ({WORKERS} threads)",
            unit="article",
        )
        for future in pbar:
            try:
                future.result()
            except Exception:
                with stats_lock:
                    stats["errors"] += 1
            pbar.set_postfix(
                done=stats["completed"],
                skip=stats["skipped"],
                err=stats["errors"],
            )

    # Merge this run's stories into the accumulated set (freshest data wins
    # per slug), then sort by date and write the combined result.
    with open(run_output_path) as f:
        new_records = [json.loads(line) for line in f if line.strip()]
    os.remove(run_output_path)

    n_new = sum(1 for r in new_records if (r.get("slug") or r.get("id")) not in previous_records)
    n_updated = len(new_records) - n_new

    merged = dict(previous_records)
    for rec in new_records:
        slug = rec.get("slug") or rec.get("id")
        if slug:
            merged[slug] = rec

    records = sorted(merged.values(), key=lambda r: r.get("date", ""), reverse=True)
    with open(output_path, "w") as f:
        for rec in records:
            json.dump(rec, f)
            f.write("\n")

    t2 = time.time() - start_time
    dates = sorted(r["date"] for r in records if r.get("date"))

    print(f"\n{'=' * 60}")
    print(f"DONE in {t2 / 60:.1f} minutes")
    print(f"This run: {n_new} new stories, {n_updated} refreshed, {stats['skipped']} skipped, {stats['errors']} errors")
    print(f"Total accumulated: {len(records)} stories in {output_path}")
    if dates:
        print(f"  Date range: {dates[0][:10]} to {dates[-1][:10]}")

    # If a date range was requested, also produce a filtered export of just
    # that window, drawn from the FULL accumulated set (not just this run) —
    # earlier runs may already have relevant stories in range.
    if date_range:
        lo, hi = args.from_date, args.to_date
        in_range = [r for r in records if r.get("date") and lo <= r["date"][:10] <= hi]
        range_path = os.path.join(OUTPUT_DIR, f"range_{args.from_date}_to_{args.to_date}.jsonl")
        with open(range_path, "w") as f:
            for rec in in_range:
                json.dump(rec, f)
                f.write("\n")
        print(f"\nDate-range export ({lo} to {hi}): {len(in_range)} stories -> {range_path}")
        print("Note: coverage of the requested window depends on how densely Wayback Machine")
        print("archived Ground News' listing pages during that period — it is a best-effort")
        print("reconstruction, not a guaranteed-complete historical archive.")
    print(f"{'=' * 60}")
