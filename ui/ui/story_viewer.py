import html
import json
import random
import re

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from streamlit_searchbox import st_searchbox

from common import (
    BIAS_COLOR,
    BIAS_ORDER,
    LCR_BUCKET,
    LCR_COLOR,
    LCR_LABEL,
    PLOTLY_CONFIG,
    PLOTLY_LAYOUT,
    bias_chip,
    ink_strong_color,
    langs_by_slug,
    lcr_bar_html,
    outlet_avatar_html,
    render_article,
)

stories = st.session_state["stories"]
by_slug = st.session_state["by_slug"]
articles = st.session_state["articles"]
domain_bias = st.session_state["domain_bias"]
data_path = st.session_state["data_path"]

# ══════════════════════════════════════════════════════════════════════════════
#  SIDEBAR — filters + distribution (kept off the main feed, like the real
#  site's own trending/filter rail is separate from the story list itself)
# ══════════════════════════════════════════════════════════════════════════════
with st.sidebar:
    st.subheader("🔎 Filters")

    sc_min, sc_max = int(stories["source_count"].min()), int(stories["source_count"].max())
    if sc_min == sc_max:
        # Event Registry has no clustering — every story is a single article,
        # so there is no range to pick from.
        st.caption(f"All stories have {sc_min} source{'s' if sc_min != 1 else ''}")
        f_sources = (sc_min, sc_max)
    else:
        # Clamp a range carried over from a dataset with a wider spread.
        _lo, _hi = st.session_state.get("flt_sources", (sc_min, sc_max))
        st.session_state["flt_sources"] = (min(max(_lo, sc_min), sc_max),
                                           min(max(_hi, sc_min), sc_max))
        f_sources = st.slider(
            "Source count (min / max)", sc_min, sc_max, key="flt_sources",
            help="How many outlets this story groups together.",
        )

    all_topics = sorted({t for row in stories["topic_names"] for t in row})
    st.session_state["flt_topics"] = [t for t in st.session_state["flt_topics"] if t in all_topics]
    f_topics = st.multiselect(
        "Topics (any match)", options=all_topics, key="flt_topics",
        help="Show stories tagged with at least one of the selected topics.",
    )

    all_places = sorted({p for row in stories["place_names"] for p in row})
    st.session_state["flt_places"] = [p for p in st.session_state.get("flt_places", []) if p in all_places]
    f_places = st.multiselect(
        "Places (any match)", options=all_places, key="flt_places",
        help="Show stories tagged with at least one of the selected places — e.g. pick "
             "\"Germany\" to see everything the topic-discovery scrapes brought in.",
    )

    f_blindspot = st.multiselect(
        "Blindspot side", options=["left", "right", "none"], key="flt_blindspot",
        format_func=lambda b: {"left": "Left blindspot", "right": "Right blindspot", "none": "No blindspot"}[b],
    )

    f_lang = st.radio(
        "Source language", options=["All", "German only", "English only", "English + German"],
        key="flt_lang", horizontal=True,
        help="Based on the language of each story's cited sources. \"German only\" means "
             "none of its sources are in English (other languages may still be present); "
             "\"English + German\" means both are present.",
    )

    st.markdown("**Date range**")
    valid_dates = stories["date_only"].dropna()
    dmin, dmax = valid_dates.min(), valid_dates.max()
    if dmin == dmax:
        st.caption(f"All stories on {dmin}")
        f_dates = (dmin, dmax)
    else:
        _lo, _hi = st.session_state.get("flt_dates", (dmin, dmax))
        st.session_state["flt_dates"] = (min(max(_lo, dmin), dmax), min(max(_hi, dmin), dmax))
        f_dates = st.slider(
            "Date range", min_value=dmin, max_value=dmax, key="flt_dates",
            format="YYYY-MM-DD",
        )

    # ── APPLY FILTERS ────────────────────────────────────────────────────
    mask = stories["source_count"].between(f_sources[0], f_sources[1])
    if f_topics:
        mask &= stories["topic_names"].apply(lambda ts: any(t in f_topics for t in ts))
    if f_places:
        mask &= stories["place_names"].apply(lambda ps: any(p in f_places for p in ps))
    if f_blindspot:
        mask &= stories["blindspot"].isin(f_blindspot)
    if f_lang != "All" and not articles.empty:
        lang_by_slug = langs_by_slug(articles, data_path)
        _empty: set = set()
        has_de = stories["slug"].map(lambda s: "de" in lang_by_slug.get(s, _empty))
        has_en = stories["slug"].map(lambda s: "en" in lang_by_slug.get(s, _empty))
        if f_lang == "German only":
            mask &= has_de & ~has_en
        elif f_lang == "English only":
            mask &= has_en & ~has_de
        elif f_lang == "English + German":
            mask &= has_de & has_en
    mask &= stories["date_only"].between(f_dates[0], f_dates[1])
    filtered = stories[mask].sort_values("date_parsed", ascending=False)
    f_articles = articles[articles["slug"].isin(filtered["slug"])] if not articles.empty else articles

    st.divider()
    st.markdown("**Data Coverage**")
    n_stories_total, n_articles_total = len(stories), len(articles)
    st.progress(
        len(filtered) / n_stories_total if n_stories_total else 0,
        text=f"Stories matching filter — {len(filtered):,} / {n_stories_total:,}"
             if n_stories_total else "Stories matching filter",
    )
    st.progress(
        len(f_articles) / n_articles_total if n_articles_total else 0,
        text=f"Source articles in those stories — {len(f_articles):,} / {n_articles_total:,}"
             if n_articles_total else "Source articles in those stories",
    )

    st.divider()
    st.markdown("**Bias / Publisher Distribution**")
    st.caption("Source articles in the current filter")
    if f_articles.empty:
        st.caption("No source articles in the current filter.")
    else:
        counts = f_articles.groupby(["source_bias", "source_name"]).size()
        ids, labels, parents, sb_values, colors = [], [], [], [], []
        for bias in BIAS_ORDER:
            if bias not in counts.index.get_level_values(0):
                continue
            sub = counts[bias].sort_values(ascending=False)
            ids.append(bias)
            labels.append(bias)
            parents.append("")
            sb_values.append(int(sub.sum()))
            colors.append(BIAS_COLOR[bias])
            for dom, val in sub.items():
                ids.append(f"{bias}/{dom}")
                labels.append(dom)
                parents.append(bias)
                sb_values.append(int(val))
                colors.append(BIAS_COLOR[bias])
        fig = go.Figure(go.Sunburst(
            ids=ids, labels=labels, parents=parents, values=sb_values,
            branchvalues="total",
            marker=dict(colors=colors, line=dict(color="#fcfcfb", width=2)),
            insidetextorientation="radial",
            textfont=dict(size=11, color="#1a1a2e"),
            hovertemplate="%{label}: %{value} articles (%{percentRoot:.0%})<extra></extra>",
        ))
        fig.update_layout(**PLOTLY_LAYOUT, height=320)
        fig.update_layout(margin=dict(l=0, r=0, t=10, b=0))
        st.plotly_chart(fig, width="stretch", config=PLOTLY_CONFIG)

if filtered.empty:
    st.info("No stories match the current filters.")
    st.stop()


def _lcr_legend(lp: float, cp: float, rp: float) -> str:
    bits = []
    for key, pct in [("left", lp), ("center", cp), ("right", rp)]:
        bits.append(
            f'<span><span class="gn-lcr-dot" style="background:{LCR_COLOR[key]};"></span>'
            f'{LCR_LABEL[key]} {pct:.0%}</span>'
        )
    return f'<div class="gn-lcr-legend">{"".join(bits)}</div>'


def _strip_numbering(line: str) -> str:
    """Ground News' per-side summaries are numbered ("0. ...", "1. ..."),
    which reads oddly once we're rendering them as our own bullet list."""
    return re.sub(r"^\s*\d+\.\s*", "", line.strip())


# ══════════════════════════════════════════════════════════════════════════════
#  SEARCH — type a few words, pick the matching story from the dropdown
# ══════════════════════════════════════════════════════════════════════════════
view_slug = st.session_state.get("view_slug")

search_row1, search_row2 = st.columns([11, 1], gap="small")


def search_stories(q: str) -> list:
    words = q.strip().lower().split()
    if not words:
        return []
    hits = []
    for _, row in filtered.iterrows():
        hay = f"{row['title']} {row['generated_headline']} {row['dek']} {row['description']}".lower()
        if all(w in hay for w in words):
            date_str = row["date"][:10] if row["date"] else "—"
            hits.append((f"{date_str} · {row['title']}", row["slug"]))
            if len(hits) >= 30:
                break
    return hits


_default_term = ""
if view_slug and view_slug in set(filtered["slug"]):
    _default_term = filtered.loc[filtered["slug"] == view_slug, "title"].iloc[0]

with search_row1:
    picked = st_searchbox(
        search_stories,
        label=None,
        placeholder="Search stories — type a few words to see related stories to pick from …",
        default_searchterm=_default_term,
        key=f"story_searchbox_{view_slug}",
    )
with search_row2:
    if st.button("🎲", help="Jump to a random story", key="search_random_btn"):
        st.session_state["view_slug"] = random.choice(filtered["slug"].tolist())
        st.rerun()

if picked:
    st.session_state["view_slug"] = picked
    view_slug = picked

st.divider()

# ══════════════════════════════════════════════════════════════════════════════
#  ARTICLE DETAIL — Ground News' own article-page layout: headline, key
#  insights, a bias donut, then a single-column list of source articles.
# ══════════════════════════════════════════════════════════════════════════════
if view_slug and view_slug in by_slug:
    record = by_slug[view_slug]

    if st.button("← Back to feed", key="back_to_feed"):
        st.session_state["view_slug"] = None
        st.rerun()

    st.markdown(f"# {record.get('title', '')}")
    if record.get("generated_headline") and record["generated_headline"] != record.get("title"):
        st.caption(f"AI-generated headline: {record['generated_headline']}")
    if record.get("dek"):
        st.markdown(f"##### {record['dek']}")

    date_str = record.get("date", "")[:10] if record.get("date") else "—"
    meta_bits = [date_str, f"{record.get('source_count', 0)} sources"]
    if record.get("blindspot") in ("left", "right"):
        meta_bits.append(f'<span class="gn-blindspot-badge">🕳 {record["blindspot"].title()} Blindspot</span>')
    # Cluster facts sources other than Ground News carry instead of bias data
    # (GDELT: independent-outlet count, countries, last seen).
    meta_bits += record.get("source_facts") or []
    st.markdown(" · ".join(meta_bits), unsafe_allow_html=True)

    # Always offer a way through to the source. Ground News stories have their
    # own story page; the other datasets don't, so they link the original
    # article — the only route out for a story whose text failed to extract.
    # `story_url` means something different per dataset: a Ground News story
    # page, an AllSides story page, or — for Event Registry — the article's
    # own URL, which the "read the original" link already covers.
    _STORY_PAGE = {"ground_news": "View on Ground News", "allsides": "View on AllSides"}
    links = []
    share_url = record.get("share_url", "")
    primary_url = record.get("primary_url", "")
    story_page_label = _STORY_PAGE.get(record.get("source_dataset", ""))
    if share_url and story_page_label and share_url != primary_url:
        links.append(f"🔗 [↗ {story_page_label}]({share_url})")
    if primary_url:
        origin = record.get("primary_source") or "the original"
        links.append(f"📰 [↗ Read the original on {origin}]({primary_url})")
    elif share_url and not links:
        links.append(f"🔗 [↗ Open the story page]({share_url})")
    if links:
        st.markdown(" &nbsp;·&nbsp; ".join(links), unsafe_allow_html=True)

    # Lead image: fetched from the outlet by the enrichment step, else the
    # source's own social-preview image.
    if record.get("lead_image"):
        st.image(record["lead_image"], width=560,
                 caption=record.get("lead_image_caption") or None)

    # Coverage split — shown right up top, like the real site's own
    # prominent "X% Left / Y% Center / Z% Right" breakdown.
    lp = record.get("left_pct", 0) or 0
    cp = record.get("center_pct", 0) or 0
    rp = record.get("right_pct", 0) or 0
    if lp or cp or rp:
        donut_col, legend_col = st.columns([1, 1.3], gap="medium")
        with donut_col:
            fig = go.Figure(go.Pie(
                labels=["Left", "Center", "Right"], values=[lp, cp, rp], hole=0.62, sort=False,
                marker=dict(colors=[LCR_COLOR["left"], LCR_COLOR["center"], LCR_COLOR["right"]]),
                textinfo="percent", textfont=dict(size=12, color="#ffffff"),
                hovertemplate="%{label}: %{percent}<extra></extra>",
            ))
            fig.add_annotation(
                text=f"{record.get('source_count', 0)}<br>sources",
                x=0.5, y=0.5, showarrow=False, font=dict(size=14, color=ink_strong_color()),
            )
            fig.update_layout(**PLOTLY_LAYOUT, height=190, showlegend=False)
            fig.update_layout(margin=dict(l=0, r=0, t=0, b=0))
            st.plotly_chart(fig, width="stretch", config=PLOTLY_CONFIG)
        with legend_col:
            st.markdown(f"**Coverage breakdown** — {record.get('bias_source_count', 0)} bias-rated sources")
            st.markdown(_lcr_legend(lp, cp, rp), unsafe_allow_html=True)

    # When the dataset carries the article itself (GDELT enrichment, Event
    # Registry, AllSides bodies), show it in full and inline — the story
    # summary is only its opening, so leading with that and hiding the rest in
    # an expander made every story look truncated. Ground News has no bodies,
    # so it keeps showing its own story summary.
    primary_url = record.get("primary_url", "")
    sources = record.get("sources") or []
    main = next((s for s in sources if s.get("url") == primary_url and s.get("body_text")), None)
    main = main or next((s for s in sources if s.get("body_text")), None)

    if main:
        st.markdown(
            f"### Article  <span class='gn-source-meta'>· {main['source_name']} · "
            f"{len(main['body_text']):,} chars</span>",
            unsafe_allow_html=True,
        )
        render_article(main["body_text"])
    elif record.get("description"):
        st.markdown(record["description"].replace("$", "\\$"))
    elif not any(s.get("description") for s in sources):
        # Extraction can come back empty — paywalls, or a page that yields only
        # navigation. Say so instead of rendering a blank gap; the link above
        # is then the only way to read the story.
        st.caption("No article text could be extracted for this story — open the "
                   "original above to read it.")

    # Per-side AI summaries — how left-, center-, and right-leaning coverage
    # each frame the story. Ground News generates these per-story; a side
    # with too little coverage may simply have none.
    perspectives = [
        ("left", "Left", record.get("summary_left", "")),
        ("center", "Center", record.get("summary_center", "")),
        ("right", "Right", record.get("summary_right", "")),
    ]
    perspectives = [(k, label, txt) for k, label, txt in perspectives if txt and txt.strip()]
    if perspectives:
        st.markdown("**Perspectives**")
        persp_cols = st.columns(len(perspectives), gap="small")
        for (side, label, text), col in zip(perspectives, persp_cols):
            bullet_lines = [_strip_numbering(ln) for ln in text.split("\n") if ln.strip()]
            body_html = "".join(f"<p>• {html.escape(b)}</p>" for b in bullet_lines)
            with col:
                st.markdown(
                    f'<div class="gn-insights" style="border-left-color:{LCR_COLOR[side]};">'
                    f'<b style="color:{LCR_COLOR[side]};">{label}</b>{body_html}</div>',
                    unsafe_allow_html=True,
                )

    bias_comparison = record.get("bias_comparison", "")
    if bias_comparison and bias_comparison.strip():
        comparison_lines = [_strip_numbering(ln) for ln in bias_comparison.split("\n") if ln.strip()]
        comparison_html = "".join(f"<p>{html.escape(b)}</p>" for b in comparison_lines)
        st.markdown(
            f'<div class="gn-insights"><b>Bias comparison</b>{comparison_html}</div>',
            unsafe_allow_html=True,
        )

    st.divider()
    srcs = record.get("sources") or []

    @st.fragment
    def render_sources(srcs: list, view_slug: str) -> None:
        """Isolated fragment: the side-filter toggle reruns only this block
        (not the whole page — no re-fetching, no scroll jump, no re-drawing
        the header/donut/sidebar above it)."""
        st.markdown(f"### Sources ({len(srcs)})")
        side_choice = st.segmented_control(
            "Filter sources by side",
            options=["All", "Left", "Center", "Right"],
            default="All",
            key=f"source_side_{view_slug}",
            label_visibility="collapsed",
        ) or "All"

        if side_choice == "All":
            visible_srcs = srcs
        else:
            wanted = side_choice.lower()
            visible_srcs = [s for s in srcs if LCR_BUCKET.get(s.get("source_bias") or "unknown", "unknown") == wanted]

        if not visible_srcs:
            st.caption(f"No {side_choice.lower()} sources for this story.")

        for s in visible_srcs:
            bias = s.get("source_bias") or "unknown"
            url = s.get("url", "")
            paywall_note = {"yes": " · 🔒 paywalled", "sometimes": " · 🔒 sometimes paywalled"}.get(s.get("paywall"), "")
            src_date = (s.get("date") or "")[:10]

            # Ground News stores both an English machine-translation
            # (title/description) and the true original-language text
            # (original_title/original_description — null on their side,
            # so empty here, when the source already is English). Show the
            # original as the headline when we have one, with the English
            # translation underneath for readers who don't read the source
            # language — rather than only ever showing the translation.
            translated_title = s.get("title", "")
            original_title = s.get("original_title", "")
            has_translation = bool(original_title) and original_title != translated_title
            headline = original_title if has_translation else translated_title

            translated_desc = s.get("description", "") or ""
            original_desc = s.get("original_description", "") or ""
            excerpt = original_desc if original_desc else translated_desc

            translation_line = (
                f'<div class="gn-source-meta">🌐 Translated: {html.escape(translated_title)}</div>'
                if has_translation else ""
            )

            st.markdown(
                f'<div class="gn-source-card">'
                f'{outlet_avatar_html(s.get("source_name",""))}'
                f'<div style="flex:1;min-width:0;">'
                f'<div class="gn-source-name">{bias_chip(bias)} {html.escape(s.get("source_name",""))}</div>'
                f'<div class="gn-source-hl"><a href="{html.escape(url)}" target="_blank">'
                f'{html.escape(headline or url)}</a></div>'
                f'{translation_line}'
                f'<div class="gn-source-excerpt">{html.escape(excerpt[:280])}</div>'
                f'<div class="gn-source-meta">{src_date}{paywall_note}</div>'
                f'<div class="gn-source-url">{html.escape(url)}</div>'
                f'</div></div>',
                unsafe_allow_html=True,
            )

            # Other outlets' full texts stay collapsed here; the main article
            # is already rendered inline above, so it isn't repeated.
            body = "" if s is main else (s.get("body_text") or "")
            if body.strip():
                with st.expander(f"📄 Full article text ({len(body):,} chars)"):
                    render_article(body)

    render_sources(srcs, view_slug)

    topics = record.get("topics") or []
    if topics:
        st.divider()
        st.markdown("**Related topics**")
        chips = "".join(f'<span class="gn-topic-pill">{html.escape(t.get("name",""))}</span>' for t in topics)
        st.markdown(chips, unsafe_allow_html=True)

    with st.expander("🔍 Raw JSON for this story"):
        st.code(json.dumps(record, indent=2, default=str), language="json")

# ══════════════════════════════════════════════════════════════════════════════
#  FEED — vertical list of full-width story cards, Ground News home-feed style
# ══════════════════════════════════════════════════════════════════════════════
else:
    feed_cap_col, feed_rand_col = st.columns([5, 1.4], gap="small", vertical_alignment="center")
    with feed_cap_col:
        st.caption(f"Showing {min(len(filtered), 40)} of {len(filtered):,} stories, newest first.")
    with feed_rand_col:
        if st.button("🎲 Random story", key="feed_random_btn", width="stretch",
                      help="Jump to a random story from the current filter"):
            st.session_state["view_slug"] = random.choice(filtered["slug"].tolist())
            st.rerun()

    for _, row in filtered.head(40).iterrows():
        date_str = row["date"][:10] if row["date"] else "—"
        topics_html = "".join(f'<span class="gn-topic-pill">{html.escape(t)}</span>' for t in row["topic_names"][:4])
        blindspot_html = (
            f'<span class="gn-blindspot-badge">🕳 {row["blindspot"].title()} Blindspot</span>'
            if row["blindspot"] in ("left", "right") else ""
        )
        st.markdown(
            f'<div class="gn-feed-card">'
            f'<div class="gn-meta"><span class="gn-source-count">🗞 {row["source_count"]} sources</span>'
            f' · {date_str}{blindspot_html}</div>'
            f'<div class="gn-hl">{html.escape(row["title"])}</div>'
            f'{lcr_bar_html(row["left_pct"], row["center_pct"], row["right_pct"])}'
            f'{topics_html}'
            f'</div>',
            unsafe_allow_html=True,
        )
        bcol1, bcol2 = st.columns([5, 1])
        with bcol2:
            if st.button("Full coverage →", key=f"open_{row['slug']}", width="stretch"):
                st.session_state["view_slug"] = row["slug"]
                st.rerun()
        st.markdown("<div style='height:10px;'></div>", unsafe_allow_html=True)
