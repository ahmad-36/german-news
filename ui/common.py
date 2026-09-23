"""
Shared constants, styling, and cached data loaders for the Ground News dataset
explorer pages.
"""

import html
import json
import os
import sys

import pandas as pd
import streamlit as st

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import paths  # noqa: E402
from textlib import lede  # noqa: E402

from germanlib import GERMAN_PUBLISHER_NAMES, is_german_source_name  # noqa: E402

# ── CONFIGURATION ────────────────────────────────────────────────────────────

BIAS_ORDER = ["farLeft", "left", "leanLeft", "center", "leanRight", "right", "farRight", "unknown"]
BIAS_LABEL = {
    "farLeft": "Far Left", "left": "Left", "leanLeft": "Lean Left", "center": "Center",
    "leanRight": "Lean Right", "right": "Right", "farRight": "Far Right", "unknown": "Unrated",
}
# Diverging bias scale (blue <-> red, neutral gray center).
BIAS_COLOR = {
    "farLeft": "#0b3d91", "left": "#1c5cab", "leanLeft": "#86b6ef", "center": "#898781",
    "leanRight": "#e58f83", "right": "#c0392b", "farRight": "#7a1f14", "unknown": "#c3c2b7",
}
BIAS_SHORT = {
    "farLeft": "FL", "left": "L", "leanLeft": "L", "center": "C",
    "leanRight": "R", "right": "R", "farRight": "FR", "unknown": "?",
}
BIAS_TEXT = {  # chip text color per background
    "farLeft": "#ffffff", "left": "#ffffff", "leanLeft": "#0b0b0b", "center": "#ffffff",
    "leanRight": "#0b0b0b", "right": "#ffffff", "farRight": "#ffffff", "unknown": "#0b0b0b",
}
BLINDSPOT_COLOR = {"left": BIAS_COLOR["left"], "right": BIAS_COLOR["right"], "none": "#898781"}

# Collapse the 7-tier per-source rating down to the 3-way Left/Center/Right
# buckets Ground News' own "All / Left / Center / Right" source-list toggle
# uses.
LCR_BUCKET = {
    "farLeft": "left", "left": "left", "leanLeft": "left",
    "center": "center",
    "leanRight": "right", "right": "right", "farRight": "right",
    "unknown": "unknown",
}

# 3-way Left/Center/Right palette, approximating Ground News' own bias-bar and
# coverage-donut colors (their exact brand hex values aren't exposed to us —
# we don't have their stylesheet — so these are a close visual match, not a
# literal color-pick from their CSS).
LCR_COLOR = {"left": "#4869E8", "center": "#9B8AC4", "right": "#E1524B"}
LCR_LABEL = {"left": "Left", "center": "Center", "right": "Right"}

_AVATAR_PALETTE = [
    "#4869E8", "#9B8AC4", "#E1524B", "#2A9D8F", "#E76F51",
    "#457B9D", "#8D5A97", "#C9184A", "#3D8361", "#B5651D",
]


def outlet_color(name: str) -> str:
    """Deterministic color for a publisher name — same mapping used for its
    avatar badge, so a given outlet reads as the same color everywhere
    (source cards, publisher charts, etc.)."""
    label = (name or "?").strip()
    return _AVATAR_PALETTE[sum(ord(c) for c in label) % len(_AVATAR_PALETTE)]


def outlet_avatar_html(name: str) -> str:
    """Small colored initials 'logo' placeholder for a publisher (we don't
    scrape actual outlet logos, so this stands in for the real site's
    publication thumbnails)."""
    label = (name or "?").strip()
    initial = label[0].upper() if label else "?"
    return (f'<span class="gn-avatar" style="background:{outlet_color(name)};">'
            f'{html.escape(initial)}</span>')


def lcr_bar_html(left_pct: float, center_pct: float, right_pct: float) -> str:
    """Proportional Left/Center/Right segmented bar, in the style of Ground
    News' own story-level bias bar."""
    parts = []
    for key, pct in [("left", left_pct), ("center", center_pct), ("right", right_pct)]:
        if pct and pct > 0:
            parts.append(
                f'<div style="width:{pct*100:.2f}%;background:{LCR_COLOR[key]};" '
                f'title="{LCR_LABEL[key]}: {pct:.0%}"></div>'
            )
    return f'<div class="gn-lcr-bar">{"".join(parts)}</div>'

# Chart chrome (light surface)
INK_MUTED = "#898781"
GRIDLINE = "#e1e0d9"
GRIDLINE_DARK = "#3a3f4b"
SEQ_BLUE = "#2a78d6"

PLOTLY_LAYOUT = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(family='system-ui, -apple-system, "Segoe UI", sans-serif', color=INK_MUTED, size=12),
    margin=dict(l=8, r=8, t=28, b=8),
)
PLOTLY_CONFIG = {"displayModeBar": False}


def is_dark_theme() -> bool:
    """Whether Streamlit's *actually active* theme is dark — reflects the
    real rendered state (OS preference AND a manual Light/Dark override from
    the app menu), unlike a CSS `prefers-color-scheme` media query, which
    only ever sees the OS setting. Chart elements (Plotly SVG/canvas) can't
    be reached by our CSS overrides at all, so this is the only way to pick
    a readable color for e.g. a donut-chart annotation.
    """
    try:
        return st.context.theme.type == "dark"
    except Exception:
        return False


def gridline_color() -> str:
    return GRIDLINE_DARK if is_dark_theme() else GRIDLINE


def ink_strong_color() -> str:
    """Near-max-contrast ink for chart text that sits directly on the page
    background (e.g. a donut-chart center label) rather than on one of our
    own colored surfaces."""
    return "#f5f5f5" if is_dark_theme() else "#0b0b0b"


def ink_muted_color() -> str:
    """Muted ink for secondary chart text (bar value labels, legend
    captions) that sits directly on the page background — same idea as
    `ink_strong_color()` but for text that shouldn't be full-contrast."""
    return "#b5b6bd" if is_dark_theme() else "#52514e"


def bias_chip(rating: str) -> str:
    r = rating or "unknown"
    bg = BIAS_COLOR.get(r, "#c3c2b7")
    fg = BIAS_TEXT.get(r, "#0b0b0b")
    return (f'<span class="bias-chip" style="background:{bg};color:{fg};" '
            f'title="{html.escape(BIAS_LABEL.get(r, r))}">{BIAS_SHORT.get(r, "?")}</span>')


def render_article(text: str, headline: bool = True) -> None:
    """Render an extracted article body with its paragraph structure intact.

    Extractions store one paragraph per line; markdown collapses single
    newlines, so writing the string as-is turns a whole article into one
    run-on block. Each line is emitted separately instead, with the outlet's
    headline and its section subheads (short lines that don't end a sentence)
    styled as such rather than reading like body prose."""
    lines = [l for l in (text or "").split("\n") if l.strip()]
    for i, line in enumerate(lines):
        is_head = len(line) < 110 and not line.rstrip().endswith((".", "!", "?", "”", "«", "»", "…"))
        if i == 0 and headline and is_head:
            st.markdown(f"##### {line}")
        elif is_head:
            st.markdown(f"**{line}**")
        else:
            st.write(line)


# ── DATA LOADING ─────────────────────────────────────────────────────────────

# unified bias vocabulary (see unify/unify.py) -> the Ground News camelCase
# vocabulary every page in this UI renders with
_UNIFIED_TO_GN_RATING = {
    "far_left": "farLeft", "left": "left", "lean_left": "leanLeft",
    "center": "center",
    "lean_right": "leanRight", "right": "right", "far_right": "farRight",
    "unknown": "unknown",
}


def _unified_to_gn_record(r: dict) -> dict:
    """Adapt one unified-format story (unify/unify.py schema, any source
    dataset) into the Ground News raw-record shape the rest of this UI was
    built around — so the same feed/detail/statistics pages work for Ground
    News, GDELT, Event Registry, and AllSides data alike."""
    meta = r.get("meta") or {}
    articles = r.get("articles") or []

    sources = []
    for a in articles:
        am = a.get("meta") or {}
        body = a.get("body_text") or ""
        paywall_raw = am.get("paywall_raw")
        if paywall_raw is None and a.get("paywall") is not None:
            paywall_raw = "yes" if a["paywall"] else "no"
        sources.append({
            "source_name": a.get("source_name") or "",
            "source_bias": _UNIFIED_TO_GN_RATING.get(a.get("bias_rating") or "unknown", "unknown"),
            "url": a.get("url") or "",
            "title": a.get("headline") or "",
            "date": a.get("date") or "",
            "description": a.get("description") or (lede(body) if body else ""),
            "original_title": am.get("original_title") or "",
            "original_description": am.get("original_description") or "",
            "body_text": a.get("body_text"),
            "lang": "de" if (a.get("lang") or "").lower() in ("de", "deu", "german") else (a.get("lang") or ""),
            "paywall": paywall_raw,
            "source_slug": am.get("source_slug", ""),
            "bias_ratings": am.get("bias_ratings") or [],
            "factuality": am.get("factuality") or [],
            "source_place": am.get("source_place") or [],
            "is_german_publisher": am.get("is_german_publisher"),
        })

    # Sources without bias ratings carry their own descriptive extras instead:
    # GDELT's enrichment (lead image + caption fetched from the outlet, see
    # gdelt_enrich.py) and its cluster stats, Event Registry's article image.
    # These used to be shown by source-specific pages; they ride along in the
    # unified record's meta, so every page can render them for any dataset.
    enrichment = meta.get("enrichment") or {}
    lead_image = enrichment.get("image") or meta.get("image") or ""
    if not lead_image:  # Event Registry's own image, else GDELT's social preview
        lead_image = next((am.get("image") or am.get("socialimage") or ""
                           for am in ((a.get("meta") or {}) for a in articles)
                           if am.get("image") or am.get("socialimage")), "")
    # The story's primary article, so there is always a way through to the
    # original: the one the enrichment was extracted from, else the first
    # article carrying a URL. Ground News stories link to Ground News itself;
    # GDELT and Event Registry have no story page of their own, so without
    # this a story whose text failed to extract would show no link at all.
    primary_url = enrichment.get("url") or ""
    primary_source = ""
    for a in articles:
        if primary_url and a.get("url") == primary_url:
            primary_source = a.get("source_name") or ""
            break
    if not primary_url:
        primary = next((a for a in articles if a.get("url")), None)
        if primary:
            primary_url = primary["url"]
            primary_source = primary.get("source_name") or ""

    facts = []
    if meta.get("n_outlets"):
        facts.append(f"{meta['n_outlets']} independent outlets")
    if meta.get("countries"):
        facts.append("countries: " + ", ".join(meta["countries"]))
    if meta.get("last_seen"):
        facts.append(f"last seen {str(meta['last_seen'])[:16].replace('T', ' ')}")

    dist = r.get("bias_distribution") or {}
    lp, cp, rp = dist.get("left"), dist.get("center"), dist.get("right")
    if lp is None and cp is None and rp is None:
        rated = [a for a in articles if a.get("stance") in ("left", "center", "right")]
        if rated:
            n = len(rated)
            lp = sum(1 for a in rated if a["stance"] == "left") / n
            cp = sum(1 for a in rated if a["stance"] == "center") / n
            rp = sum(1 for a in rated if a["stance"] == "right") / n

    topics = meta.get("topics_typed") or [
        {"name": t, "type": "topic"} for t in (r.get("topics") or []) if t
    ]
    summaries = r.get("stance_summaries") or {}
    return {
        "slug": r.get("story_id", ""),
        "source_dataset": r.get("source_dataset", ""),
        "date": r.get("date") or "",
        "title": r.get("title") or "",
        "generated_headline": meta.get("generated_headline") or "",
        "dek": meta.get("dek") or "",
        "description": r.get("story_summary") or "",
        "summary_left": summaries.get("left") or "",
        "summary_center": summaries.get("center") or "",
        "summary_right": summaries.get("right") or "",
        "bias_comparison": meta.get("bias_comparison") or "",
        "source_count": meta.get("source_count") or len(articles),
        "bias_source_count": meta.get("bias_source_count")
            or sum(1 for a in articles if (a.get("bias_rating") or "unknown") != "unknown"),
        "left_pct": lp or 0, "center_pct": cp or 0, "right_pct": rp or 0,
        "blindspot": meta.get("blindspot"),
        "place": meta.get("place") or [],
        "topics": topics,
        "share_url": r.get("story_url") or "",
        "lead_image": lead_image,
        "lead_image_caption": enrichment.get("image_caption") or "",
        "source_facts": facts,
        "primary_url": primary_url,
        "primary_source": primary_source,
        "sources": sources,
    }


@st.cache_resource(show_spinner="Loading stories …")
def load_stories(path: str):
    """Returns (stories DataFrame, {slug: record}) for a stories JSONL.

    Accepts either the raw Ground News scraper output or the unified format
    from unify/unify.py (any source dataset) — unified records are detected
    per line by their `source_dataset` field and adapted to the same shape.
    """
    rows, by_slug = [], {}
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            r = json.loads(line)
            if "source_dataset" in r and "articles" in r:
                r = _unified_to_gn_record(r)
            slug = r.get("slug") or r.get("id", "")
            if not slug or slug in by_slug:
                continue
            by_slug[slug] = r
            topics = r.get("topics") or []
            # Ground News carries place info in two separate spots that
            # don't always agree: the event's own top-level `place` field
            # (country/region, e.g. a Bavaria story might list both
            # "Bavaria" and "Germany") and its `topics` list's type=="place"
            # entries (interest tags, e.g. sometimes just "Bavaria" alone,
            # with no redundant "Germany"). Using only one undercounts —
            # confirmed against this dataset, ~100 genuinely-German stories
            # had "Germany" in `place` but not in their place-type topic
            # tags — so this merges both into one set.
            place_names = {t.get("name", "") for t in topics if t.get("type") == "place"}
            place_names |= {p.get("name", "") for p in (r.get("place") or [])}
            place_names.discard("")
            rows.append({
                "slug": slug,
                "source_dataset": r.get("source_dataset", "ground_news"),
                "date": r.get("date", ""),
                "title": r.get("title", ""),
                "generated_headline": r.get("generated_headline", ""),
                "dek": r.get("dek", ""),
                "description": r.get("description", ""),
                "source_count": r.get("source_count", 0),
                "bias_source_count": r.get("bias_source_count", 0),
                "left_pct": r.get("left_pct", 0) or 0,
                "center_pct": r.get("center_pct", 0) or 0,
                "right_pct": r.get("right_pct", 0) or 0,
                "blindspot": r.get("blindspot") or "none",
                "topic_names": [t.get("name", "") for t in topics if t.get("type") == "topic"],
                "person_names": [t.get("name", "") for t in topics if t.get("type") == "person"],
                "place_names": sorted(place_names),
                "share_url": r.get("share_url", ""),
            })
    df = pd.DataFrame(rows)
    df["date_parsed"] = pd.to_datetime(df["date"], errors="coerce", utc=True)
    df["date_only"] = df["date_parsed"].dt.date
    return df, by_slug


@st.cache_resource(show_spinner=False)
def sources_table(_by_slug: dict, cache_key: str = "") -> pd.DataFrame:
    """One row per (story, source) pair — used for publisher-level stats.

    `_by_slug` is underscore-prefixed so Streamlit does NOT hash it: on the
    GDELT dataset that dict holds 173k nested records, and hashing it to build
    the cache key took ~78s on *every* rerun — far longer than the work itself.
    `cache_key` (the dataset path) identifies the entry instead; callers must
    pass it or every dataset shares one cache slot.
    """
    # Built column-wise rather than as a list of per-row dicts: on GDELT this
    # table is ~1.4M rows, and DataFrame(list-of-dicts) has to re-derive the
    # schema from every one of them.
    cols: dict[str, list] = {k: [] for k in (
        "slug", "story_title", "source_name", "source_bias", "url", "title",
        "date", "paywall", "lang", "source_place_names", "is_german_publisher",
        "factuality")}
    c_slug, c_stitle = cols["slug"], cols["story_title"]
    c_name, c_bias = cols["source_name"], cols["source_bias"]
    c_url, c_title, c_date = cols["url"], cols["title"], cols["date"]
    c_pw, c_lang = cols["paywall"], cols["lang"]
    c_place, c_de, c_fact = (cols["source_place_names"], cols["is_german_publisher"],
                             cols["factuality"])
    de_cache: dict[str, bool] = {}

    for slug, r in _by_slug.items():
        story_title = r.get("title", "")
        for s in r.get("sources", ()):
            name = s.get("source_name", "") or ""
            # `is_german_publisher` is only present on sources scraped after
            # this flag was added; fall back to computing it fresh (same
            # register, same logic) for anything scraped earlier so older
            # records don't just silently read as False. Memoised — the same
            # few hundred outlets recur across every story.
            is_de_pub = s.get("is_german_publisher")
            if is_de_pub is None:
                is_de_pub = de_cache.get(name)
                if is_de_pub is None:
                    is_de_pub = de_cache[name] = is_german_source_name(name)
            places = s.get("source_place") or ()
            fact = s.get("factuality") or ()
            c_slug.append(slug)
            c_stitle.append(story_title)
            c_name.append(name)
            c_bias.append(s.get("source_bias") or "unknown")
            c_url.append(s.get("url", ""))
            c_title.append(s.get("title", ""))
            c_date.append(s.get("date", ""))
            c_pw.append(s.get("paywall", ""))
            c_lang.append(s.get("lang", ""))
            c_place.append([p.get("name", "") for p in places] if places else [])
            c_de.append(bool(is_de_pub))
            c_fact.append(", ".join(f"{fr.get('reviewer', '')}: {fr.get('rating', '')}"
                                    for fr in fact) if fact else "")
    return pd.DataFrame(cols)


@st.cache_resource(show_spinner=False)
def langs_by_slug(_articles: pd.DataFrame, cache_key: str = "") -> dict:
    """slug -> set of article languages.

    Cached because story_viewer's language filter needs it on every rerun and
    the group-by runs over ~1.4M article rows (~3s) on the GDELT dataset.
    """
    if _articles.empty:
        return {}
    return _articles.groupby("slug")["lang"].apply(set).to_dict()


@st.cache_resource(show_spinner=False)
def topic_cluster_stats(_stories: pd.DataFrame, cache_key: str = "") -> pd.DataFrame:
    """One row per distinct interest tag (topic/person/place), with how many
    scraped stories it's attached to — i.e. its "cluster size" in this dataset.

    These tags are NOT computed by us: Ground News attaches them server-side
    to each event as `interests` (see `scraper.py::parse_article_page`, the
    `topics` field), already split into `type: "topic" | "person" | "place"`.
    We just count how many scraped stories share each tag.
    """
    # Column-wise, not iterrows(): at 173k stories iterrows materialises a
    # Series per row and dominates the cost.
    counts: dict[tuple[str, str], int] = {}
    for kind, col in (("topic", "topic_names"),
                      ("person", "person_names"),
                      ("place", "place_names")):
        if col not in _stories.columns:
            continue
        for names in _stories[col].to_numpy():
            for name in names or ():
                key = (kind, name)
                counts[key] = counts.get(key, 0) + 1
    if not counts:
        return pd.DataFrame(columns=["type", "name", "story_count"])
    out = pd.DataFrame(
        [{"type": k[0], "name": k[1], "story_count": v} for k, v in counts.items()]
    )
    return out.sort_values("story_count", ascending=False).reset_index(drop=True)


def german_expansion_candidates(
    stories: pd.DataFrame, articles: pd.DataFrame, exclude: set[str], top_n: int = 25,
) -> tuple[pd.DataFrame, int]:
    """Stage 5 of the German discovery pipeline, computed on demand (not as
    an automatic loop): topic/person/place tags that co-occur on stories
    ABOUT Germany in the local dataset, ranked by how often they show up —
    a candidate list for what to search/scrape next, for you to act on
    whenever you want rather than the pipeline acting on it itself.

    Scoped to place=Germany specifically, not "has any German source" —
    tried the broader version first and it was wrong: a story with 50+
    sources only needs ONE of them to be a German outlet to qualify, which
    pulls in whatever that outlet happened to cover (confirmed against this
    dataset: Marc Anthony's baby news, Champions League riots in Paris —
    neither about Germany, both had some German source). place=Germany is
    a real editorial judgment Ground News already made about the story
    itself, so it's a much more precise "this is actually about Germany"
    signal than source language ever is.

    `exclude` is checked case-insensitively so tags you've already queued
    or that are already in the seed keyword bank don't clutter the list.

    Returns (candidates DataFrame with name/count, number of local stories
    tagged place=Germany).
    """
    if stories.empty:
        return pd.DataFrame(columns=["name", "count"]), 0

    matched = stories[stories["place_names"].apply(lambda p: "Germany" in p)]
    if matched.empty:
        return pd.DataFrame(columns=["name", "count"]), 0

    # "Germany" itself is tautological here (it's the scoping criterion,
    # not a discovery), so it's always excluded regardless of `exclude`.
    exclude_lower = {e.strip().lower() for e in exclude} | {"germany"}
    counts: dict[str, int] = {}
    for _, row in matched.iterrows():
        for name in row["topic_names"] + row["person_names"] + row["place_names"]:
            if not name or name.strip().lower() in exclude_lower:
                continue
            counts[name] = counts.get(name, 0) + 1
    if not counts:
        return pd.DataFrame(columns=["name", "count"]), len(matched)

    out = pd.DataFrame([{"name": k, "count": v} for k, v in counts.items()])
    out = out.sort_values("count", ascending=False).head(top_n).reset_index(drop=True)
    return out, len(matched)
