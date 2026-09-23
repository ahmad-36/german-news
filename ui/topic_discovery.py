"""
Topic & Language Discovery — preview how much coverage exists on Ground News
before committing to a full scrape.

Cheap, live discovery signals (no full article scraping required):
  1. Trending topics + story counts, straight from the homepage.
  2. Place-tag hits on a listing page (e.g. how many stories on
     /interest/germany are actually tagged place=Germany).
  3. Known-outlet name/slug mentions on a listing page (a rough proxy for
     "how much coverage from these publishers shows up here").
  4. Scrape-by-publisher — Ground News has no per-publisher browse page
     (checked: /source/, /publisher/, /outlet/ all 404), so targeting one
     outlet means routing its name through search instead.

Ground News has no separate German (or other-language) edition or topic
set — it's a single English-labeled story graph. "German coverage" only
exists as (a) stories tagged place=Germany, or (b) individual German-
language sources cited inside otherwise English-labeled stories.
"""

import os
import subprocess
import sys

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from common import (
    PLOTLY_CONFIG,
    PLOTLY_LAYOUT,
    SEQ_BLUE,
    german_expansion_candidates,
    load_stories,
    outlet_color,
    sources_table,
)

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import paths  # noqa: E402

REPO_ROOT = paths.REPO_ROOT
GN_SCRAPER = os.path.join(REPO_ROOT, "scraper.py")
_GN_SCRAPER_DIR = os.path.dirname(GN_SCRAPER)
if _GN_SCRAPER_DIR not in sys.path:
    sys.path.insert(0, _GN_SCRAPER_DIR)

from scraper import (  # noqa: E402
    BASE,
    GERMAN_PUBLISHER_REGISTER,
    GERMAN_SEED_KEYWORDS,
    KNOWN_GERMAN_SOURCE_SLUGS,
    count_known_source_mentions,
    discover_trending_topics,
    extract_article_stubs,
    extract_flight_data,
    fetch,
    make_session,
    search_topic_preview,
)

stories = st.session_state["stories"]
articles = st.session_state["articles"]
data_path = st.session_state["data_path"]

st.title("🔎 Topic & Language Discovery")
st.caption(
    "Preview counts before scraping — nothing here fetches full article pages "
    "or writes to your dataset until you hit “Start scraping” at the bottom."
)


def _add_to_interests(slug: str) -> None:
    slug = (slug or "").strip()
    if not slug:
        return
    current = [s.strip() for s in st.session_state.get("interest_input_value", "").split(",") if s.strip()]
    if slug not in current:
        current.append(slug)
        st.session_state["interest_input_value"] = ", ".join(current)


def _add_to_queries(term: str) -> None:
    term = (term or "").strip()
    if not term:
        return
    current = [s.strip() for s in st.session_state.get("query_input_value", "").split(",") if s.strip()]
    if term not in current:
        current.append(term)
        st.session_state["query_input_value"] = ", ".join(current)


# ══════════════════════════════════════════════════════════════════════════════
#  SECTION 1 — Most-used topics right now
# ══════════════════════════════════════════════════════════════════════════════
st.markdown("## Most-used topics right now")
st.caption(
    "Pulled live from Ground News' homepage — each topic's `refCount` is how "
    "many stories it's attached to, site-wide. One request, no articles scraped."
)

if st.button("Fetch trending topics", key="fetch_topics_btn"):
    with st.spinner("Fetching the live topic list…"):
        session = make_session()
        st.session_state["discovered_topics"] = discover_trending_topics(session)

topics = st.session_state.get("discovered_topics", [])

if topics:
    tdf = pd.DataFrame(topics).sort_values("ref_count", ascending=False).reset_index(drop=True)
    fig = go.Figure(go.Bar(
        x=tdf["ref_count"], y=tdf["name"], orientation="h",
        marker=dict(color=SEQ_BLUE, cornerradius=4),
        hovertemplate="%{y}: %{x} stories<extra></extra>",
    ))
    fig.update_layout(**PLOTLY_LAYOUT, height=280, yaxis=dict(autorange="reversed"))
    st.plotly_chart(fig, width="stretch", config=PLOTLY_CONFIG)

    chosen_topic_slugs = st.multiselect(
        "Queue topics for scraping",
        options=tdf["slug"].tolist(),
        format_func=lambda s: f"{tdf.set_index('slug').loc[s, 'name']} ({tdf.set_index('slug').loc[s, 'ref_count']})",
        key="chosen_topics",
    )
    for slug in chosen_topic_slugs:
        _add_to_interests(slug)
else:
    st.caption("Click the button above to load it.")

st.divider()

# ══════════════════════════════════════════════════════════════════════════════
#  SECTION 2 — German-language coverage: compare discovery methods
# ══════════════════════════════════════════════════════════════════════════════
st.markdown("## German-language coverage: compare discovery methods")
st.caption(
    "No native German edition or topic set exists on Ground News, so “German "
    "news” only shows up two ways: stories tagged place=Germany, or individual "
    "German-language sources cited inside (still English-labeled) stories."
)

local_place_de = int(stories["place_names"].apply(lambda p: "Germany" in p).sum()) if not stories.empty else 0
local_lang_de = int((articles["lang"] == "de").sum()) if not articles.empty else 0
local_outlets_de = int(articles.loc[articles["lang"] == "de", "source_name"].nunique()) if not articles.empty else 0

st.markdown("**Already in your local dataset** (instant, zero requests)")
lcol1, lcol2, lcol3 = st.columns(3)
with lcol1:
    st.metric("Stories tagged place = Germany", local_place_de)
with lcol2:
    st.metric("German-language source mentions", local_lang_de)
with lcol3:
    st.metric("Distinct German outlets seen", local_outlets_de)

if local_lang_de:
    st.markdown("**Publisher contribution** — share of German-language source mentions by outlet")
    de_counts = articles.loc[articles["lang"] == "de", "source_name"].value_counts()
    top_n = 10
    top_pubs = de_counts.head(top_n)
    other_total = de_counts.iloc[top_n:].sum()
    legend_labels = [f"{name} — {count}" for name, count in top_pubs.items()]
    legend_labels += ([f"Other outlets — {other_total}"] if other_total > 0 else [])
    values = list(top_pubs.values) + ([other_total] if other_total > 0 else [])
    colors = [outlet_color(name) for name in top_pubs.index] + (["#c3c2b7"] if other_total > 0 else [])

    fig = go.Figure(go.Pie(
        labels=legend_labels, values=values, hole=0.45, sort=False,
        marker=dict(colors=colors, line=dict(color="#fcfcfb", width=2)),
        texttemplate="%{value}<br>(%{percent})", textfont=dict(size=11),
        hovertemplate="%{label}: %{value} mentions (%{percent})<extra></extra>",
    ))
    fig.update_layout(**PLOTLY_LAYOUT, height=360)
    st.plotly_chart(fig, width="stretch", config=PLOTLY_CONFIG)
    if other_total > 0:
        st.caption(
            f"Top {top_n} outlets shown individually; {len(de_counts) - top_n} smaller "
            f"outlets ({other_total} mentions total) grouped into “Other outlets”."
        )

st.markdown("**Seed keywords** — queue any of these for the next scrape")
st.caption(
    "Tested against Ground News' search (see conversation): proper nouns — "
    "people, parties, named laws — survive translation and find real hits in "
    "German. Generic concepts don't (titles are English), so those are kept "
    "in English instead of blindly translated."
)
for category, terms in GERMAN_SEED_KEYWORDS.items():
    kw_cols = st.columns(len(terms))
    for term, col in zip(terms, kw_cols):
        with col:
            if st.button(term, key=f"seed_kw_{category}_{term}", width="stretch"):
                _add_to_queries(term)

st.markdown("**Live probe** (2 page fetches, no articles scraped)")
if st.button("🇩🇪 Probe /interest/germany + /interest/german-politics", key="probe_de_btn"):
    with st.spinner("Checking live listing pages…"):
        session = make_session()
        stub_total = place_hits = outlet_hits = 0
        for islug in ("germany", "german-politics"):
            html = fetch(session, f"{BASE}/interest/{islug}")
            stubs = extract_article_stubs(html)
            stub_total += len(stubs)
            place_hits += sum(1 for s in stubs if s.get("place") == "Germany")
            outlet_hits += count_known_source_mentions(extract_flight_data(html), KNOWN_GERMAN_SOURCE_SLUGS)
        st.session_state["de_probe"] = {
            "stub_total": stub_total, "place_hits": place_hits, "outlet_hits": outlet_hits,
        }
        _add_to_interests("germany")
        _add_to_interests("german-politics")

probe = st.session_state.get("de_probe")
if probe:
    pcol1, pcol2, pcol3 = st.columns(3)
    with pcol1:
        st.metric("Stories visible on those 2 pages", probe["stub_total"])
    with pcol2:
        st.metric("...tagged place = Germany", probe["place_hits"])
    with pcol3:
        st.metric("...mentioning a known German outlet", probe["outlet_hits"])
    st.caption(
        "Undercounts real coverage on purpose — it's a cheap preview, not a full "
        "crawl. Each listing page only shows a batch of stories, and outlet "
        "matching only catches publishers already in the known-outlet list. "
        "\"germany\" and \"german-politics\" have been queued for scraping below."
    )
else:
    st.caption("Click the button above for a live count before scraping anything.")

st.divider()

# ══════════════════════════════════════════════════════════════════════════════
#  SECTION 3 — Candidate tags for expansion (Stage 5 — on demand, not a loop)
# ══════════════════════════════════════════════════════════════════════════════
st.markdown("## Candidate tags for expansion")
st.caption(
    "Topic/person/place tags that co-occur on stories already flagged as "
    "German coverage in your local dataset — e.g. once you've scraped some "
    "CDU stories, \"Friedrich Merz\" or \"AfD\" show up here if they ride "
    "along on the same stories. This is computed fresh each time you open "
    "this page (zero requests, pure local analysis) and does nothing on its "
    "own — nothing gets queued or searched until you click one. No "
    "auto-expanding loop."
)

already_known = {t.lower() for terms in GERMAN_SEED_KEYWORDS.values() for t in terms}
already_known |= {s.strip().lower() for s in st.session_state.get("interest_input_value", "").split(",") if s.strip()}
already_known |= {s.strip().lower() for s in st.session_state.get("query_input_value", "").split(",") if s.strip()}

candidates, n_de_stories = german_expansion_candidates(stories, articles, exclude=already_known, top_n=24)
st.caption(f"Based on {n_de_stories} locally-scraped stories currently flagged as German coverage.")

if candidates.empty:
    st.caption("No candidates yet — scrape some German coverage first (seed keywords or publisher search above), then check back here.")
else:
    cand_cols = st.columns(4)
    for i, row in enumerate(candidates.itertuples()):
        with cand_cols[i % 4]:
            if st.button(f"{row.name} ({row.count})", key=f"candidate_{i}_{row.name}"):
                _add_to_queries(row.name)

st.divider()

# ══════════════════════════════════════════════════════════════════════════════
#  SECTION 4 — Scrape by publisher
# ══════════════════════════════════════════════════════════════════════════════
st.markdown("## Scrape by publisher")
n_register = sum(len(v) for v in GERMAN_PUBLISHER_REGISTER.values())
st.caption(
    "Ground News has no page listing everything from one outlet (checked: "
    "/source/<slug>, /publisher/<slug>, /outlet/<slug> — all 404). Search by "
    "name is the only way in, so this is a keyword match against that "
    f"outlet's name, not a guaranteed \"articles authored by them\" filter. "
    f"The dropdown below draws from outlets already in your dataset plus a "
    f"register of {n_register} known German outlets (public broadcasters, "
    f"national dailies, regional press, business/tech press) — pick any of "
    f"those, or type a different name entirely."
)

scraped_de_outlets = (
    set(articles.loc[articles["lang"] == "de", "source_name"].dropna().unique())
    if not articles.empty else set()
)
register_names = {name for names in GERMAN_PUBLISHER_REGISTER.values() for name in names}
# Case-insensitive merge: prefer the casing Ground News itself uses for an
# outlet we've actually scraped over the register's casing for the same name.
seen_lower = {n.lower() for n in scraped_de_outlets}
known_de_outlets = sorted(scraped_de_outlets | {n for n in register_names if n.lower() not in seen_lower})

publisher_choice = st.selectbox(
    "Publisher name",
    options=known_de_outlets,
    accept_new_options=True,
    index=None,
    placeholder="Pick a German outlet (scraped-already or from the register), or type any publisher name…",
    key="publisher_choice",
)

if publisher_choice:
    local_mentions = int((articles["source_name"] == publisher_choice).sum()) if not articles.empty else 0
    st.metric(f"Already in local dataset for “{publisher_choice}”", local_mentions)

    pcol1, pcol2 = st.columns([1, 1])
    with pcol1:
        if st.button("🔎 Preview via search", key="publisher_preview_btn"):
            with st.spinner(f"Searching for “{publisher_choice}”…"):
                session = make_session()
                st.session_state["publisher_search_result"] = search_topic_preview(publisher_choice, session)
                st.session_state["publisher_search_term"] = publisher_choice
    with pcol2:
        if st.button("➕ Queue for scraping", key="publisher_queue_btn"):
            _add_to_queries(publisher_choice)

    pres = st.session_state.get("publisher_search_result")
    if pres and st.session_state.get("publisher_search_term") == publisher_choice:
        st.metric(f"Raw search hits for “{publisher_choice}”", len(pres["events"]))
        if pres["events"]:
            with st.expander(f"Sample matching stories ({len(pres['events'])})"):
                for e in pres["events"]:
                    st.markdown(f"- {e['title']} ({e['source_count']} sources){' — ' + e['place'] if e.get('place') else ''}")

st.divider()

# ══════════════════════════════════════════════════════════════════════════════
#  SECTION 5 — Confirm & scrape
# ══════════════════════════════════════════════════════════════════════════════
st.markdown("## Scrape selected")

interest_input = st.text_input(
    "Interest page slugs to scrape (comma-separated)",
    key="interest_input_value",
    help="e.g. germany, european-politics — topics/publishers queued above land here automatically.",
)
query_input = st.text_input(
    "Additional keyword searches (comma-separated, optional)",
    key="query_input_value",
    help="Free-text subjects/publishers — routed through Ground News' search instead of a known slug.",
)

interest_slugs = [s.strip() for s in interest_input.split(",") if s.strip()]
query_terms = [q.strip() for q in query_input.split(",") if q.strip()]

scrape_running = st.session_state.get("scrape_proc") is not None

start_col, _ = st.columns([1, 3])
with start_col:
    if st.button("🚀 Start scraping selected", type="primary", disabled=scrape_running):
        if not interest_slugs and not query_terms:
            st.warning("Pick at least one topic, interest slug, or query first.")
        else:
            cmd = [sys.executable, GN_SCRAPER, "--only"]
            for s in interest_slugs:
                cmd += ["--interest", s]
            for q in query_terms:
                cmd += ["--query", q]
            log_path = os.path.join(paths.source_dir("discovery"), ".topic_discovery_run.log")
            os.makedirs(os.path.dirname(log_path), exist_ok=True)
            log_file = open(log_path, "w")
            proc = subprocess.Popen(cmd, cwd=REPO_ROOT, stdout=log_file, stderr=subprocess.STDOUT, text=True)
            st.session_state["scrape_proc"] = proc
            st.session_state["scrape_log_path"] = log_path
            st.session_state["scrape_return_code"] = None
            st.session_state["scrape_cmd"] = " ".join(cmd)
            st.rerun()


@st.fragment(run_every=2)
def render_scrape_progress():
    # Only `scrape_log_path` needs to survive for this fragment to keep
    # rendering — `scrape_proc` gets cleared the moment we detect the run
    # finished, and that must NOT make the completion message disappear on
    # the next auto-refresh.
    log_path = st.session_state.get("scrape_log_path")
    if log_path is None:
        return

    proc = st.session_state.get("scrape_proc")
    return_code = proc.poll() if proc is not None else st.session_state.get("scrape_return_code")

    st.code(st.session_state.get("scrape_cmd", ""), language="bash")
    tail = ""
    if os.path.isfile(log_path):
        with open(log_path) as f:
            content = f.read()
        # tqdm writes progress as \r-separated updates on one line; keep only
        # the latest state of each line for a readable log view.
        lines = [ln for chunk in content.split("\n") for ln in chunk.split("\r") if ln.strip()]
        tail = "\n".join(lines[-25:])

    if proc is not None and return_code is None:
        st.info("⏳ Scraping in progress…")
        st.text(tail or "(starting up…)")
    else:
        if proc is not None:
            # First cycle after completion — clear the process handle and
            # remember the result, but keep log_path around so this branch
            # keeps rendering on later auto-refreshes.
            st.session_state["scrape_proc"] = None
            st.session_state["scrape_return_code"] = return_code
            load_stories.clear()
            sources_table.clear()
        if return_code == 0:
            st.success("✅ Scrape finished — dataset refreshed.")
        else:
            st.error(f"Scraper exited with code {return_code} — see log below.")
        st.text(tail)
        if st.button("Dismiss", key="reload_after_scrape"):
            st.session_state["scrape_log_path"] = None
            st.session_state["scrape_return_code"] = None
            st.rerun()


if st.session_state.get("scrape_proc") is not None or st.session_state.get("scrape_log_path"):
    render_scrape_progress()
