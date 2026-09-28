import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from common import (
    BIAS_COLOR,
    BIAS_LABEL,
    BIAS_ORDER,
    BLINDSPOT_COLOR,
    LCR_COLOR,
    PLOTLY_CONFIG,
    PLOTLY_LAYOUT,
    SEQ_BLUE,
    bias_chip,
    gridline_color,
    ink_muted_color,
    topic_cluster_stats,
)

stories = st.session_state["stories"]
articles = st.session_state["articles"]
data_path = st.session_state["data_path"]
domain_bias = st.session_state["domain_bias"]

n_stories = len(stories)
n_articles = len(articles)
n_publishers = articles["source_name"].nunique() if not articles.empty else 0
dmin, dmax = stories["date_only"].min(), stories["date_only"].max()

st.markdown(f"""
## Dataset Statistics

Each row is one **story** — for Ground News and AllSides that's an event covered by multiple
outlets with per-publisher political-bias ratings; for GDELT it's a cross-outlet cluster built
by title similarity (no bias ratings); for Event Registry it's a single full-text article
(no clustering, no ratings). Bias-based charts below only carry signal for the rated datasets.

A story's **blindspot** flag (Ground News only) means the left or right side of the political
spectrum has no significant coverage of that story.

**Coverage window in this dataset:** {dmin} → {dmax}
""")

c1, c2, c3, c4 = st.columns(4)
c1.metric("Stories scraped", f"{n_stories:,}")
c2.metric("Source articles", f"{n_articles:,}")
c3.metric("Unique publishers", f"{n_publishers:,}")
c4.metric("Stories w/ blindspot", f"{(stories['blindspot'] != 'none').sum():,}")

if "source_dataset" in stories.columns and stories["source_dataset"].nunique() > 1:
    st.markdown("**Stories per collection strategy** — this file mixes several source datasets")
    ds_counts = stories["source_dataset"].value_counts()
    dcols = st.columns(len(ds_counts))
    for (ds_name, ds_n), col in zip(ds_counts.items(), dcols):
        col.metric(ds_name, f"{ds_n:,}")

st.divider()

ch1, ch2 = st.columns(2)
with ch1:
    st.markdown("**Stories per day**")
    daily = stories["date_only"].value_counts().sort_index()
    fig = go.Figure(go.Bar(
        x=[str(d) for d in daily.index], y=daily.values,
        marker=dict(color=SEQ_BLUE, cornerradius=4),
        hovertemplate="%{x}: %{y} stories<extra></extra>",
    ))
    fig.update_layout(**PLOTLY_LAYOUT, height=260, bargap=0.35)
    fig.update_yaxes(gridcolor=gridline_color(), zeroline=False)
    fig.update_xaxes(showgrid=False)
    st.plotly_chart(fig, width="stretch", config=PLOTLY_CONFIG)

with ch2:
    st.markdown("**Blindspot distribution** — stories with no coverage on one side")
    bcounts = stories["blindspot"].value_counts().reindex(["left", "none", "right"], fill_value=0)
    fig = go.Figure(go.Bar(
        x=[b.title() for b in bcounts.index], y=bcounts.values,
        marker=dict(color=[BLINDSPOT_COLOR.get(b, "#898781") for b in bcounts.index], cornerradius=4),
        width=0.55, text=[f"{v:,}" for v in bcounts.values], textposition="outside",
        textfont=dict(color=ink_muted_color()),
        hovertemplate="%{x} blindspot: %{y} stories<extra></extra>",
    ))
    fig.update_layout(**PLOTLY_LAYOUT, height=260, bargap=0.4)
    fig.update_yaxes(gridcolor=gridline_color(), zeroline=False)
    fig.update_xaxes(showgrid=False)
    st.plotly_chart(fig, width="stretch", config=PLOTLY_CONFIG)

st.markdown("**Story bias mix** — average share of Left / Center / Right sources across all scraped stories")
avg = stories[["left_pct", "center_pct", "right_pct"]].mean()
fig = go.Figure(go.Bar(
    x=["Left", "Center", "Right"], y=[avg["left_pct"], avg["center_pct"], avg["right_pct"]],
    marker=dict(color=[LCR_COLOR["left"], LCR_COLOR["center"], LCR_COLOR["right"]], cornerradius=4),
    width=0.5,
    text=[f"{v:.0%}" for v in [avg["left_pct"], avg["center_pct"], avg["right_pct"]]],
    textposition="outside", textfont=dict(color=ink_muted_color()),
    hovertemplate="%{x}: %{y:.0%} avg share<extra></extra>",
))
fig.update_layout(**PLOTLY_LAYOUT, height=240, bargap=0.5)
fig.update_yaxes(gridcolor=gridline_color(), zeroline=False, tickformat=".0%")
fig.update_xaxes(showgrid=False)
st.plotly_chart(fig, width="stretch", config=PLOTLY_CONFIG)

if not articles.empty:
    st.markdown("**Publishers by article count** — chip shows the publisher's dominant bias rating in this dataset")
    per_pub = articles["source_name"].value_counts().head(25).sort_values()
    fig = go.Figure(go.Bar(
        x=per_pub.values, y=per_pub.index, orientation="h",
        marker=dict(
            color=[BIAS_COLOR.get(domain_bias.get(p, ""), "#c3c2b7") for p in per_pub.index],
            cornerradius=4,
        ),
        width=0.6,
        text=[f" {v:,}" for v in per_pub.values], textposition="outside",
        textfont=dict(color=ink_muted_color()),
        customdata=[BIAS_LABEL.get(domain_bias.get(p, "unknown"), "Unrated") for p in per_pub.index],
        hovertemplate="%{y}: %{x} articles (%{customdata})<extra></extra>",
    ))
    fig.update_layout(**PLOTLY_LAYOUT, height=560, bargap=0.3)
    fig.update_xaxes(gridcolor=gridline_color(), zeroline=False)
    fig.update_yaxes(showgrid=False)
    st.plotly_chart(fig, width="stretch", config=PLOTLY_CONFIG)
    legend_bits = "&nbsp;&nbsp;".join(
        f'{bias_chip(b)} <span style="color:{ink_muted_color()};font-size:0.8rem;">{BIAS_LABEL[b]}</span>'
        for b in BIAS_ORDER
    )
    st.markdown(legend_bits, unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
#  TOPIC CLUSTERING
# ══════════════════════════════════════════════════════════════════════════════
st.divider()
st.markdown("""
## How topics are created

Topics are **not** something this pipeline computes — they come straight from Ground News.
Every scraped event embeds an `interests` list (see `event.get("interests")` in
`scraper.py::parse_article_page`), which Ground News' own editorial/tagging system attaches
server-side to the story. We split that list by its `type` field into three tag kinds and
store them verbatim in each record's `topics` field:

- **topic** — subject tags (e.g. "US Politics", "Crime", "AI")
- **place** — geographic tags (e.g. "Edinburgh", "Europe")
- **person** — named-person tags (e.g. a politician mentioned in the story)

A story's "cluster" for a given topic is simply *every scraped story that shares that tag* —
there's no similarity model or embedding step on our side, just a group-by on the tag name.
""")

tstats = topic_cluster_stats(stories, data_path)
topic_only = tstats[tstats["type"] == "topic"]

if topic_only.empty:
    st.info("No topic tags found in the current dataset.")
else:
    counts = topic_only["story_count"]
    top_topic_row = topic_only.iloc[0]
    tc1, tc2, tc3, tc4 = st.columns(4)
    tc1.metric("Distinct topics", f"{len(topic_only):,}")
    tc2.metric("Mean articles / topic", f"{counts.mean():.2f}")
    tc3.metric("Median articles / topic", f"{counts.median():.0f}")
    tc4.metric("Max articles / topic", f"{counts.max():,}", help=f"'{top_topic_row['name']}'")
    st.caption(
        f"Largest cluster: **{top_topic_row['name']}** with {top_topic_row['story_count']:,} stories. "
        "Most topic tags are small (median is often 1) — a few broad topics like "
        "\"Politics\" or \"World\" dominate the tail."
    )

    tcol1, tcol2 = st.columns(2)
    with tcol1:
        st.markdown("**Top topics** — how many stories each topic tag appears on")
        topic_counts = topic_only.set_index("name")["story_count"].head(20)
        fig = go.Figure(go.Bar(
            x=topic_counts.values[::-1], y=topic_counts.index[::-1], orientation="h",
            marker=dict(color=SEQ_BLUE, cornerradius=4), width=0.6,
            text=[f" {v:,}" for v in topic_counts.values[::-1]], textposition="outside",
            textfont=dict(color=ink_muted_color()),
            hovertemplate="%{y}: %{x} stories<extra></extra>",
        ))
        fig.update_layout(**PLOTLY_LAYOUT, height=440, bargap=0.3)
        fig.update_xaxes(gridcolor=gridline_color(), zeroline=False)
        fig.update_yaxes(showgrid=False)
        st.plotly_chart(fig, width="stretch", config=PLOTLY_CONFIG)

    with tcol2:
        st.markdown("**Topic cluster-size distribution** — how many topics fall in each size bucket")
        bins = [0, 1, 2, 5, 10, 20, 50, float("inf")]
        labels = ["1", "2", "3–5", "6–10", "11–20", "21–50", "50+"]
        bucketed = pd.cut(counts, bins=bins, labels=labels, right=True)
        bucket_counts = bucketed.value_counts().reindex(labels, fill_value=0)
        fig = go.Figure(go.Bar(
            x=labels, y=bucket_counts.values,
            marker=dict(color=SEQ_BLUE, cornerradius=4), width=0.55,
            text=[f"{v:,}" for v in bucket_counts.values], textposition="outside",
            textfont=dict(color=ink_muted_color()),
            hovertemplate="%{x} stories/topic: %{y} topics<extra></extra>",
        ))
        fig.update_layout(**PLOTLY_LAYOUT, height=440, bargap=0.35)
        fig.update_yaxes(gridcolor=gridline_color(), zeroline=False)
        fig.update_xaxes(showgrid=False, title="Stories per topic")
        st.plotly_chart(fig, width="stretch", config=PLOTLY_CONFIG)

    with st.expander("All topic tags, sorted by cluster size"):
        st.dataframe(
            topic_only[["name", "story_count"]].rename(
                columns={"name": "Topic", "story_count": "Stories"}
            ),
            hide_index=True, width="stretch",
        )
