"""Draw the charts in assets/ from the numbers reported in docs/experiments.md.

    python scripts/figures.py
"""
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

OUT = Path(__file__).resolve().parent.parent / "assets"

BLUE, ORANGE, RED = "#2a78d6", "#eb6834", "#e34948"
GREY, LIGHT_GREY = "#8f8e88", "#d6d5d0"
INK, INK_2, GRID = "#0b0b0b", "#52514e", "#e6e5e0"

plt.rcParams.update({
    "font.family": "DejaVu Sans",
    "font.size": 10.5,
    "svg.fonttype": "none",
    "axes.edgecolor": GRID,
    "axes.labelcolor": INK_2,
    "xtick.color": INK_2,
    "ytick.color": INK,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "axes.spines.left": False,
    "figure.facecolor": "white",
    "axes.facecolor": "white",
})


def finish(fig, ax, name, title, subtitle):
    ax.set_axisbelow(True)
    ax.xaxis.grid(True, color=GRID, linewidth=0.8)
    ax.tick_params(axis="y", length=0)
    ax.tick_params(axis="x", length=0)
    step = 0.26 / fig.get_figheight()
    fig.text(0.012, 0.99, title, fontsize=13, fontweight="bold", color=INK, va="top")
    fig.text(0.012, 0.99 - step, subtitle, fontsize=10, color=INK_2, va="top")
    fig.savefig(OUT / name, bbox_inches="tight", pad_inches=0.15)
    plt.close(fig)


def label(ax, bar, text, color=INK, inside=False):
    x = bar.get_width()
    y = bar.get_y() + bar.get_height() / 2
    if inside:
        ax.text(x - 1, y, text, ha="right", va="center", color="white", fontsize=9.5, fontweight="bold")
    else:
        pad = 1 if x >= 0 else -1
        ax.text(x + pad, y, text, ha="left" if x >= 0 else "right", va="center", color=color, fontsize=9.5)


def dedup():
    """§1: accuracy on random vs unseen-outlet splits, as-is vs deduplicated vs baseline."""
    groups = ["random split", "unseen outlets"]
    series = [
        ("as-is (with duplicates)", [94.6, 27.3], LIGHT_GREY),
        ("deduplicated", [72.6, 30.9], BLUE),
        ("majority baseline", [38.9, 28.1], GREY),
    ]
    fig, ax = plt.subplots(figsize=(7.6, 3.4))
    h = 0.24
    for i, (name, vals, color) in enumerate(series):
        ys = [g + (i - 1) * (h + 0.03) for g in range(len(groups))]
        bars = ax.barh(ys, vals, height=h, color=color, label=name)
        for b, v in zip(bars, vals):
            label(ax, b, f"{v}%")
    ax.set_yticks(range(len(groups)), groups)
    ax.invert_yaxis()
    ax.set_xlim(0, 105)
    ax.set_xlabel("accuracy (TF-IDF + logistic regression)")
    ax.legend(frameon=False, loc="lower right", fontsize=9.5)
    fig.subplots_adjust(top=0.78)
    finish(fig, ax, "exp1_dedup.svg",
           "On unseen outlets the classifier is no better than the baseline",
           "AllSides eval set, 3-class stance")


def name_swap():
    """§2: change in P(gold) per condition, and the directional swaps."""
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(10, 3.4), gridspec_kw={"wspace": 0.9})

    conds = ["name stripped", "neutral invented name", "same-side outlet", "opposite-side outlet"]
    vals = [-8.4, -9.4, 3.3, -23.5]
    bars = a1.barh(conds, vals, height=0.55, color=[RED if v < 0 else BLUE for v in vals])
    for b, v in zip(bars, vals):
        label(a1, b, f"{v:+.1f}")
    a1.axvline(0, color=INK_2, linewidth=0.8)
    a1.invert_yaxis()
    a1.set_xlim(-30, 10)
    a1.set_xlabel("Δ P(gold label), points")
    a1.set_title("Every name edit, by condition", loc="left", fontsize=10.5, color=INK)

    swaps = ["left article → right name", "right article → left name",
             'centre article → "Fox News"', 'centre article → "Politico"']
    svals = [40.7, 13.4, 51.1, 19.5]
    bars = a2.barh(swaps, svals, height=0.55, color=[ORANGE, BLUE, ORANGE, BLUE])
    for b, v in zip(bars, svals):
        label(a2, b, f"+{v}")
    a2.invert_yaxis()
    a2.set_xlim(0, 75)
    a2.set_xlabel("Δ P(swapped-in side), points")
    a2.set_title("Swaps toward right move it more", loc="left", fontsize=10.5, color=INK)
    a2.legend(handles=[plt.Rectangle((0, 0), 1, 1, color=ORANGE), plt.Rectangle((0, 0), 1, 1, color=BLUE)],
              labels=["toward right", "toward left"], frameon=False, loc="lower right", fontsize=9.5)

    for ax in (a1, a2):
        ax.set_axisbelow(True)
        ax.xaxis.grid(True, color=GRID, linewidth=0.8)
        ax.tick_params(length=0)
    fig.subplots_adjust(top=0.72)
    finish(fig, a2, "exp2_name_swap.svg",
           "Swapping in another outlet's name moves the prediction",
           "premsa (DeBERTa-v3), 2,823 deduplicated AllSides articles")


def llm_disagreement():
    """§3: LLM vs outlet label, disagreement by label."""
    labels = ["right", "left", "center"]
    vals = [32.0, 59.2, 78.3]
    fig, ax = plt.subplots(figsize=(7.6, 2.6))
    bars = ax.barh(labels, vals, height=0.55, color=BLUE)
    for b, v in zip(bars, vals):
        label(ax, b, f"{v}%")
    ax.axvline(49.7, color=INK_2, linewidth=1, linestyle=(0, (4, 3)))
    ax.text(49.7, -0.62, " overall 49.7%", color=INK_2, fontsize=9, va="bottom")
    ax.invert_yaxis()
    ax.set_xlim(0, 100)
    ax.set_xlabel("articles where Qwen2.5-14B disagrees with the outlet label")
    fig.subplots_adjust(top=0.70)
    finish(fig, ax, "exp3_llm_disagreement.svg",
           "The LLM almost never predicts centre",
           "1,465 AllSides articles, zero-shot, content only")


def clustering():
    """§5: BCubed F1 against Event Registry's eventUri (test set)."""
    methods = ["BGE-M3, full body", "TF-IDF, title + lede", "mE5-large, title + lede",
               "BGE-M3, title + lede", "gbert-large (German-only)", "our GDELT clusterer"]
    f1 = [0.79, 0.78, 0.77, 0.77, 0.74, 0.45]
    fig, ax = plt.subplots(figsize=(7.6, 3.4))
    bars = ax.barh(methods, f1, height=0.6, color=[BLUE] * 5 + [ORANGE])
    for b, v in zip(bars, f1):
        ax.text(v + 0.01, b.get_y() + b.get_height() / 2, f"{v:.2f}", va="center", fontsize=9.5, color=INK)
    ax.axvline(0.88, color=INK_2, linewidth=1, linestyle=(0, (4, 3)))
    ax.text(0.88, -0.75, " ceiling 0.88\n (2-day windows)", color=INK_2, fontsize=9, va="bottom")
    ax.invert_yaxis()
    ax.set_xlim(0, 1)
    ax.set_xlabel("BCubed F1")
    fig.subplots_adjust(top=0.74)
    finish(fig, ax, "exp5_clustering.svg",
           "Our production clusterer misses most same-event pairs",
           "German, 2,117 events / 17,810 articles, scored against Event Registry eventUri")


if __name__ == "__main__":
    OUT.mkdir(exist_ok=True)
    dedup()
    name_swap()
    llm_disagreement()
    clustering()
    print("wrote", sorted(p.name for p in OUT.glob("exp*.svg")))
