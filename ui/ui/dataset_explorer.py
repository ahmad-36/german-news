"""
News Dataset Explorer — Streamlit App
=====================================
Story-centric explorer for the locally scraped news datasets. Every page works
off one unified-format JSONL (unify/unify.py — Ground News, GDELT, Event
Registry, AllSides, or the concatenated unified_all), so any dataset can be
browsed with the same UI; pick it in the sidebar.

Data locations all come from paths.py — nothing here builds a path of its own.

Launch:  uv run streamlit run ui/dataset_explorer.py
         uv run streamlit run ui/dataset_explorer.py -- --data <stories.jsonl>
         uv run streamlit run ui/dataset_explorer.py -- --data-dir <data root>
         NEWS_DATA_DIR=<data root> uv run streamlit run ui/dataset_explorer.py
"""

import argparse
import os
import sys

import streamlit as st

_UI_DIR = os.path.dirname(os.path.abspath(__file__))
# `streamlit run` puts the script's own dir on sys.path; other entry points
# (the app-testing harness, `python -m`) don't — so both are added explicitly.
for _p in (os.path.dirname(_UI_DIR), _UI_DIR):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import paths  # noqa: E402
from common import load_stories, sources_table  # noqa: E402

# ── CONFIGURATION ────────────────────────────────────────────────────────────

_ap = argparse.ArgumentParser()
_ap.add_argument("--data", default=None, help="unified-format stories JSONL to open")
paths.add_data_dir_arg(_ap)
_cli_args, _ = _ap.parse_known_args()
paths.use_data_dir(_cli_args.data_dir)


def _default_data_path() -> str:
    """Ground News first — the smallest complete story-level dataset — then
    whatever else exists. unified_all is sorted last by paths.unified_datasets()
    because it can be ~1 GB with Event Registry in it."""
    known = paths.unified_datasets()
    preferred = paths.unified_path("ground_news")
    if preferred in known:
        return preferred
    return known[0] if known else preferred


_DEFAULT_DATA_PATH = _cli_args.data or _default_data_path()

# ── PAGE CONFIG & CSS ────────────────────────────────────────────────────────

st.set_page_config(
    page_title="Ground News Dataset Explorer",
    page_icon="📰",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
[data-testid="stMetric"] {
    background: #f7f7f5; border: 1px solid #e2e2de;
    border-radius: 8px; padding: 10px 14px;
}
[data-testid="stMetric"] label { color: #555 !important; }
[data-testid="stMetric"] [data-testid="stMetricValue"] { color: #0b0b0b !important; font-size: 1.5rem; }
.block-container { padding-top: 0.8rem; max-width: 980px; }
div[data-testid="stExpander"] details { border: 1px solid #e1e4e8; border-radius: 8px; }

/* ── Masthead ─────────────────────────────────────────────────────────── */
.gn-masthead {
    display: flex; justify-content: space-between; align-items: baseline;
    padding: 2px 0 12px 0; border-bottom: 2px solid #0b0b0b; margin-bottom: 6px;
}
.gn-logo { font-size: 1.55rem; font-weight: 800; color: #0b0b0b; letter-spacing: -0.4px; }
.gn-logo .accent { color: #4869E8; }
.gn-edition { color: #6b6b6b; font-size: 0.82rem; }

/* ── Bias chips (7-tier, per-source rating) ──────────────────────────── */
.bias-chip {
    display: inline-block; min-width: 20px; text-align: center;
    border-radius: 4px; padding: 0 4px; margin-right: 3px;
    font-size: 0.68rem; font-weight: 700;
}

/* ── Left/Center/Right proportional bar (story-level bias split) ───────── */
.gn-lcr-bar { display: flex; width: 100%; height: 10px; border-radius: 6px; overflow: hidden; background: #eee; margin: 8px 0 6px 0; }
.gn-lcr-legend { display: flex; gap: 16px; font-size: 0.78rem; color: #52514e; flex-wrap: wrap; }
.gn-lcr-dot { display: inline-block; width: 9px; height: 9px; border-radius: 50%; margin-right: 5px; }

/* ── Feed cards (home-feed look) ─────────────────────────────────────── */
.gn-feed-card {
    border: 1px solid #e3e2dd; border-radius: 14px;
    padding: 16px 20px 14px 20px; margin-bottom: 4px;
    background: #ffffff;
}
.gn-feed-card .gn-meta { color: #6b6b6b; font-size: 0.78rem; margin-bottom: 6px; display:flex; align-items:center; gap:8px; flex-wrap: wrap; }
.gn-feed-card .gn-hl { font-weight: 700; color: #0b0b0b; font-size: 1.12rem; line-height: 1.35; margin-bottom: 8px; }
.gn-blindspot-badge {
    background: #fff4f3; color: #c0392b; border: 1px solid #f0c8c5;
    border-radius: 20px; padding: 1px 10px; font-size: 0.72rem; font-weight: 700;
}
.gn-source-count { font-weight: 600; color: #33383f; }

/* ── Topic pills ──────────────────────────────────────────────────────── */
.gn-topic-pill {
    display: inline-block; border: 1px solid #d8d8d3; border-radius: 20px;
    padding: 3px 12px; margin: 2px 6px 2px 0; font-size: 0.78rem;
    color: #33383f; background: #fafaf8;
}
.topic-chip { /* legacy alias kept for any cached references */ }

/* ── Article detail page ─────────────────────────────────────────────── */
.gn-insights {
    background: #f5f4fc; border-left: 4px solid #4869E8; border-radius: 8px;
    padding: 14px 18px; margin: 10px 0 18px 0; color: #2b2b2b;
}
.gn-insights b { color: #1a1a1a; }
.gn-insights p { margin: 0 0 6px 0; color: #33383f; }
.gn-source-card {
    border: 1px solid #e6e5e0; border-radius: 12px;
    padding: 14px 16px; margin-bottom: 12px; background: #fff;
    display: flex; gap: 12px; align-items: flex-start;
}
.gn-avatar {
    display: inline-flex; align-items: center; justify-content: center;
    width: 34px; height: 34px; border-radius: 50%; color: #fff;
    font-weight: 700; font-size: 0.95rem; flex-shrink: 0;
}
.gn-source-name { font-weight: 700; color: #0b0b0b; }
.gn-source-hl { font-weight: 600; color: #1a1a1a; margin: 4px 0 4px 0; }
.gn-source-excerpt { color: #52514e; font-size: 0.85rem; line-height: 1.4; margin-bottom: 6px; }
.gn-source-meta { color: #8a8a8a; font-size: 0.76rem; margin-top: 2px; }
.gn-source-url { color: #8a8a8a; font-size: 0.74rem; word-break: break-all; margin-top: 2px; }

/* Back-to-feed button, targeted by its Streamlit widget key */
div[class*="st-key-back_to_feed"] button {
    border: none !important; background: transparent !important;
    color: #4869E8 !important; font-weight: 600 !important; padding-left: 0 !important;
}
/* "Full coverage →" open-story buttons on feed cards */
div[class*="st-key-open_"] button {
    border: 1.5px solid #4869E8 !important; color: #4869E8 !important;
    background: transparent !important; border-radius: 20px !important;
    font-weight: 600 !important;
}
div[class*="st-key-open_"] button:hover {
    background: #eef1fd !important;
}
/* Random-story shuffle buttons (search-bar dice + feed header) */
div[class*="st-key-search_random_btn"] button,
div[class*="st-key-feed_random_btn"] button {
    border: 1.5px solid #9B8AC4 !important; color: #6b4f8c !important;
    background: transparent !important; border-radius: 20px !important;
    font-weight: 600 !important;
}
div[class*="st-key-search_random_btn"] button:hover,
div[class*="st-key-feed_random_btn"] button:hover {
    background: #f5f1fa !important;
}

/* ── Dark mode ────────────────────────────────────────────────────────────
   Streamlit's own "System" theme setting follows the browser/OS preference
   (this is what makes the app go dark without the user touching anything),
   but it doesn't expose a CSS variable or DOM attribute we can hook into —
   so this class-by-class override, keyed off the OS-level media query, is
   what keeps every custom card/box here readable when that happens. It
   won't catch someone who manually forces "Dark" while their OS itself is
   in light mode (Streamlit gives us no signal for that), but every text
   color throughout this file is set explicitly rather than inherited, so
   that mismatch is a mild aesthetic seam, not a repeat of the invisible-text
   bug this replaced. */
@media (prefers-color-scheme: dark) {
    [data-testid="stMetric"] { background: #1a1d24; border-color: #333844; }
    [data-testid="stMetric"] label { color: #9a9ba4 !important; }
    [data-testid="stMetric"] [data-testid="stMetricValue"] { color: #f5f5f5 !important; }
    div[data-testid="stExpander"] details { border-color: #333844; }

    .gn-masthead { border-bottom-color: #e8e8e8; }
    .gn-logo { color: #f5f5f5; }
    .gn-edition { color: #9a9ba4; }

    .gn-lcr-bar { background: #333844; }
    .gn-lcr-legend { color: #b5b6bd; }

    .gn-feed-card { border-color: #333844; background: #171a21; }
    .gn-feed-card .gn-meta { color: #9a9ba4; }
    .gn-feed-card .gn-hl { color: #f5f5f5; }
    .gn-blindspot-badge { background: #3a1f1f; color: #ff8a80; border-color: #5c2b2b; }
    .gn-source-count { color: #d5d6dc; }

    .gn-topic-pill { border-color: #3a3f4b; color: #d5d6dc; background: #23262e; }

    .gn-insights { background: #23212f; color: #e6e6e6; }
    .gn-insights b { color: #ffffff; }
    .gn-insights p { color: #d5d6dc; }

    .gn-source-card { border-color: #333844; background: #171a21; }
    .gn-source-name { color: #f0f0f0; }
    .gn-source-hl { color: #eaeaea; }
    .gn-source-hl a { color: #8fb2ff; }
    .gn-source-excerpt { color: #b5b6bd; }
    .gn-source-meta, .gn-source-url { color: #888a94; }

    div[class*="st-key-open_"] button:hover { background: #1c2540 !important; }
    div[class*="st-key-search_random_btn"] button:hover,
    div[class*="st-key-feed_random_btn"] button:hover { background: #2a2333 !important; }
}
</style>
""", unsafe_allow_html=True)

# ── PAGES ────────────────────────────────────────────────────────────────────

# Every page renders the unified format, so each one works on whichever
# dataset the sidebar has selected — no source-specific pages.
dataset_statistics = st.Page("dataset_statistics.py", title="Dataset Statistics", icon="📊")
story_viewer = st.Page("story_viewer.py", title="Story Feed", icon="📖")

st.markdown(
    '<div class="gn-masthead">'
    '<div class="gn-logo">📰 <span class="accent">News</span> Dataset Explorer</div>'
    '<div class="gn-edition">Ground News · GDELT · Event Registry · AllSides</div>'
    '</div>',
    unsafe_allow_html=True,
)

pg = st.navigation([story_viewer, dataset_statistics], position="top")

# ── SIDEBAR: DATA SOURCE ─────────────────────────────────────────────────

with st.sidebar:
    st.caption("Data source")
    _known = paths.unified_datasets()
    _options = _known + ["custom path …"]
    _initial = _options.index(_DEFAULT_DATA_PATH) if _DEFAULT_DATA_PATH in _known else len(_options) - 1
    _choice = st.selectbox(
        "Dataset", _options, index=_initial,
        format_func=lambda p: paths.label(p) if p != "custom path …" else p,
    )
    if _choice == "custom path …":
        data_path = st.text_input("Stories JSONL path", value=_DEFAULT_DATA_PATH)
    else:
        data_path = _choice
    st.caption(f"Data root: `{paths.data_dir()}`")

if not _known and not os.path.isfile(data_path):
    st.error(f"No unified datasets under `{paths.unified_dir()}`. Run a scraper, "
             "then `python unify/unify.py` — or point the app at another data root "
             f"with `${paths.DATA_DIR_ENV}` / `-- --data-dir`.")
    st.stop()

if not os.path.isfile(data_path):
    st.error(f"Data file not found: `{data_path}`")
    st.stop()

stories, by_slug = load_stories(data_path)
articles = sources_table(by_slug, data_path)

if stories.empty:
    st.warning("No stories found in the dataset yet — run a scraper first "
               "(e.g. `uv run python scrapers/ground_news/scraper.py`), then `python unify/unify.py`.")
    st.stop()

# Dominant bias rating per publisher
domain_bias = (
    articles.groupby("source_name")["source_bias"].agg(lambda s: s.mode().iloc[0]).to_dict()
    if not articles.empty else {}
)

# Switching datasets invalidates every filter: a source-count range or a topic
# list from Ground News is meaningless — and out of range — for GDELT or Event
# Registry. Drop the whole filter state so it re-defaults to the new dataset.
if st.session_state.get("data_path") != data_path:
    for _k in [k for k in st.session_state
               if k.startswith(("flt_", "search_", "source_side_"))
               or k in ("view_slug", "gdelt_view_id")]:
        del st.session_state[_k]

# Share data with the navigation pages
st.session_state["data_path"] = data_path
st.session_state["stories"] = stories
st.session_state["by_slug"] = by_slug
st.session_state["articles"] = articles
st.session_state["domain_bias"] = domain_bias

# Persist filter state across page switches
_FILTER_DEFAULTS = {
    "flt_sources": (int(stories["source_count"].min()), int(stories["source_count"].max())),
    "flt_topics": [],
    "flt_places": [],
    "flt_blindspot": ["left", "right", "none"],
    "flt_lang": "All",
    "search_fields": False,
}
for _k, _v in _FILTER_DEFAULTS.items():
    st.session_state[_k] = st.session_state.get(_k, _v)

pg.run()
