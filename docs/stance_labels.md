# Stance Labels: Where They Come From, and Four Experiments On Them

**The short version.** Every stance label available from these providers is assigned to an
**outlet**, not to an article. Articles inherit their publisher's rating. This makes
article-level stance prediction a mislabelled task: what a model learns is which outlet
published the text. We establish this four ways below, and we correct two of our own
earlier numbers in the process.

---

## 1. How each provider's labels are made

| | **AllSides** | **Ground News** | **Ad Fontes** *(not yet used)* |
|---|---|---|---|
| **Human or AI?** | 🟢 Human | 🟢 Human (inherited) | 🟢 Human, AI-assisted at scale |
| **Experts or lay?** | 🟡 **Both, deliberately** | inherited from its three sources | 🟢 Trained analysts |
| **Per outlet or per article?** | 🔴 **Per outlet** | 🔴 **Per outlet** | 🟢 **Per article** |
| **Scale** | 7-point ordinal | 7-point ordinal | continuous, −42…+42 |
| **Inter-rater data published?** | 🔴 no | 🟡 three ratings retained, so computable | 🟢 panel design |

### AllSides

Four methods, in descending order of rigour:

1. **Blind Bias Surveys** — ordinary Americans across the political spectrum rate headlines
   and articles from an outlet *without being told which outlet it is*.
2. **Editorial Reviews** — a politically balanced panel of trained staff (equal numbers
   leaning left, right and center) reviews a source together.
3. **Independent review** — a single staffer's preliminary assessment; AllSides itself
   calls this "the lowest level of bias verification".
4. **Third-party data** — rarely, from universities and researchers.

**AllSides' own audit methodology confirms the outlet is the unit.** The
[AllSides Media Bias Audit example report (March 2022)](https://www.allsides.com/sites/default/files/AllSides-Media-Bias-Audit_Example-March-2022.pdf)
is a real audit with the outlet's identity redacted. It shows that article-level content
is only a *sample* used to produce one outlet-level number:

- **Sampling.** A Blind Bias Survey uses a small sample of content. One method takes the
  top 5 homepage headlines on each of two days, 10 in total. The other takes the outlet's
  most prominent article on each of two major stories, again on two days, showing the
  headline plus the first 50–100 words.
- **The outlet is what gets rated.** Respondents see an outlet's content together on one
  page and give *"an overall bias rating for the content"* on an 11-point scale. They
  are not asked to rate each headline separately.
- **One number per outlet.** Responses are averaged within each self-reported bias group
  and then across all groups into *"an overall weighted average"*, rescaled to −9…+9. The
  written and video ratings are averaged again into a single final rating: *"the average
  of both the written and video ratings."*
- **US-framed by design.** *"The AllSides patented media bias rating system reflects the
  average judgment of the American people."*

So 5–10 sampled headlines become one score, and every article the outlet publishes
inherits it. (The URL returns 403 to scripts; we read the copy archived on the
[Wayback Machine](https://web.archive.org/web/2024/https://www.allsides.com/sites/default/files/AllSides-Media-Bias-Audit_Example-March-2022.pdf).)

So: **human, a mix of experts and lay people by design, and assigned to the publication.**
AllSides does sometimes rate a source's sections separately, and sometimes separates news
from opinion — but the unit is still a section, never an article.

### Ground News

Ground News **does not rate anything itself**. It aggregates and averages three outside
agencies. In our 46,030-article dump:

| Rating agency | Articles carrying its rating |
|---|---|
| Media Bias/Fact Check | 25,435 |
| Ad Fontes Media | 19,034 |
| AllSides | 8,330 |

All three rate outlets. Ground News states the consequence outright:

> *"This rating does not measure the bias of specific news articles. The analysis is done
> at the publication level."*

**The three agencies disagree on 32.1% of rated articles** (9,244 of 28,833 where ≥2
agencies have rated the outlet). Ground News resolves this by averaging. A third of the
label set is therefore a contested rating presented as a single value.

**What *is* machine-generated on a Ground News page:** the per-stance summaries
(`summary_left` / `summary_center` / `summary_right`), the `bias_comparison` paragraph, and
`generated_headline`. Those are LLM outputs. The summaries and `bias_comparison` are GPT:
the page payload stores them in an object named `chatGptSummaries`. **The bias labels are
not.** This is worth stating because the opposite is often assumed.

The labels are also **US-framed**. All three agencies are US organisations that place
outlets on the American left–right axis, so a German outlet's label is its position on a
US spectrum.

---

## 2. Experiment 1 — Is the AllSides label outlet-level? (Yes, exactly.)

**Question:** does an outlet like Fox News always receive the same label? If so the labels
are outlet-level and the task is publisher identification.

**Method:** group the 11,779-article AllSides eval set by domain and count distinct labels.

**Result — every one of the 15 outlets has exactly one 3-class label. Purity is 100%.**

| outlet | articles | label | | outlet | articles | label |
|---|---|---|---|---|---|---|
| thehill.com | 2,227 | center | | foxbusiness.com | 435 | right |
| foxnews.com | 1,979 | right | | cnn.com | 433 | left |
| nypost.com | 1,078 | right | | theguardian.com | 339 | left |
| newsweek.com | 958 | center | | washingtonpost.com | 296 | left |
| bbc.com | 949 | center | | nytimes.com | 174 | left |
| washingtonexaminer.com | 766 | right | | reuters.com | 575 | center |
| nbcnews.com | 553 | left | | apnews.com | 512 | left |
| politico.com | 505 | left | | | | |

Across the full 37 source feeds, **36 of 37 carry exactly one label**. The single exception
is AP (59 `left` vs 453 `lean_left`) — a mid-scrape re-rating by AllSides, not article-level
variation. It is pinned to `lean left`.

**Conclusion: the ground truth *is* publisher identity.** Any classifier trained on it can
achieve a perfect score by recognising the outlet, and never model ideology at all.

---

## 3. Experiment 2 — The outlier check: how often does an LLM disagree with the label?

**Question:** if a model judges each article on its content alone, how often does it
contradict the outlet-level label? Concentrate on Fox News, with every other outlet as a
baseline.

**Method.** Qwen2.5-14B-Instruct, BF16, greedy. Prediction = argmax over the first
generated token restricted to `left` / `center` / `right`, which also yields a per-article
confidence. All Fox articles plus up to 250 per other outlet. 5,403 predictions on an
H100. Script: [`scripts/outlet_outlier_check.py`](../scripts/outlet_outlier_check.py).

**Deduplicated to unique URLs** — see §4 for why this matters. 1,465 unique articles.

### Result: disagreement rate by outlet

| outlet | label | unique articles | **disagrees with label** |
|---|---|---|---|
| thehill.com | center | 67 | **89.6%** |
| newsweek.com | center | 77 | 79.2% |
| reuters.com | center | 45 | 77.8% |
| bbc.com | center | 83 | 68.7% |
| politico.com | left | 53 | 67.9% |
| washingtonpost.com | left | 77 | 61.0% |
| theguardian.com | left | 82 | 59.8% |
| nbcnews.com | left | 50 | 58.0% |
| apnews.com | left | 107 | 57.9% |
| cnn.com | left | 102 | 57.8% |
| foxbusiness.com | right | 61 | 49.2% |
| nytimes.com | left | 19 | 42.1% |
| washingtonexaminer.com | right | 71 | 35.2% |
| nypost.com | right | 93 | 34.4% |
| **foxnews.com** | **right** | **478** | **28.9%** ← lowest |

**Overall agreement: 50.3%.**

### What this actually shows

**Fox News is not an outlier — it is the *least* outlying outlet in the set.** At 28.9%
disagreement it is the most internally consistent of all 15. The articles Fox publishes do
read as right-leaning to a model judging content alone, more reliably than any other
outlet's articles read as their assigned label.

The disagreement rate is **not** a property of the outlet. It is almost entirely a property
of **which label the outlet has**:

| gold label | unique articles | disagreement |
|---|---|---|
| right | 703 | 32.0% |
| left | 490 | 59.2% |
| **center** | **272** | **78.3%** |

Center collapses. The model almost never predicts `center`: The Hill (rated center) is
predicted `right` on the majority of its articles; Reuters likewise. This reproduces, in a
14B instruction-tuned LLM, the failure previously established for the fine-tuned encoder —
**`center` is negatively defined**. It means "absence of lean", and there are no positive
lexical markers for an absence.

### The disagreements are confident, not hedged

**77.7% of all disagreements are made at p > 0.95** (566 of 728). Mean confidence is 0.972
when agreeing and 0.940 when disagreeing — barely different. The model is not uncertain about the
articles it contradicts; it confidently asserts a different label.

### Inside Fox: where the 28.9% sits

| Fox section | unique articles | disagrees |
|---|---|---|
| opinion | 7 | **0.0%** |
| media | 53 | 24.5% |
| politics | 276 | 24.6% |
| world | 57 | 33.3% |
| us | 56 | 42.9% |

There is a mild gradient — explicitly opinionated and political content matches the label
best, general news least — but with 7 opinion articles the top row carries no weight. The
honest reading is that the label fits Fox's political coverage about three times in four,
and its general news coverage closer to three times in five.

### What the disagreeing articles look like

Fox `/politics/` articles the model confidently calls **left**:

- *"Ilhan Omar sprayed by unknown substance after man charges her at Minneapolis town hall"*
- *"Supreme Court blocks new deportations of Venezuelans in Texas under 18th century Alien Enemies Act"*
- *"Comey denies charges, declares 'I am not afraid'"*
- *"Dems erupt after report of Trump firing Librarian of Congress: 'A disgrace'"*

Fox `/politics/` articles the model confidently calls **right** (agreeing with the label):

- *"Socialist shockwave: Zohran Mamdani stuns NYC as voters hand power to Democrats' far-left flank"*
- *"Supreme Court blocks Colorado's so-called 'conversion therapy' ban on First Amendment grounds"*

The pattern is legible: **the model reads the article's *subject* as its stance.** A
straight report that centres a Democratic figure or quote is called left, regardless of
publisher; a piece carrying explicit editorial framing (*"Socialist shockwave"*, *"so-called
'conversion therapy'"*) is called right. This is the article-level analogue of the
outlet-level shortcut — the model has substituted topic for stance.

**Therefore the disagreement rate cannot be read as a label-error rate.** Both the label and
the prediction are measuring something other than the article's ideological stance. What the
experiment establishes is that the two disagree half the time, that the disagreement is
confident, and that it is structured by class rather than by outlet.

---

## 4. Experiment 3 — A correction: the eval set is 4.2× duplicated

While running the above we found a defect in our own evaluation set that changes a
previously reported headline number.

`data/unified_allsides/original.jsonl` holds **11,779 records but only 2,807 distinct
article texts** — a **4.20× inflation**. The cause is upstream: AllSides reuses the same
article across many story pages through its "More from the Left/Center/Right" sidebars
(68,352 article slots → 8,072 unique URLs), and `prepare_unified_allsides.py` keeps one
record per (story, slot) rather than per article. One article appears **300 times**.

The split is computed by hashing `article_id`, so identical texts scatter across train and
test:

- **256 of 2,807 distinct texts (9.1%) appear in both train and test.**
- **9,179 of 11,779 records (77.9%) are affected.**

### Impact, measured

[`scripts/dedup_impact.py`](../scripts/dedup_impact.py) — same TF-IDF + LogReg baseline,
as-is versus text-deduplicated with the split computed on the text hash:

| split | condition | accuracy | macro F1 |
|---|---|---|---|
| random | as-is (duplicates straddle) | **94.6%** | 94.3% |
| random | **deduplicated** | **72.6%** | 71.4% |
| outlet-disjoint | as-is | 27.3% ± 7.4 | 26.4% |
| outlet-disjoint | **deduplicated** | **30.9% ± 11.1** | 27.2% |

**22 of the 94.6 points were literal duplicate memorisation.** The outlet-disjoint number is
unaffected, as expected — different outlets never share a text.

### What survives, and what does not

**Does not survive:** the figure "94.6%" as a measure of the boilerplate shortcut. It was
two shortcuts stacked — duplicate leakage *and* outlet boilerplate — and we previously
attributed all of it to boilerplate.

**Survives, and is now cleaner:** the conclusion. Deduplicated, the random split still
scores **72.6%** against an outlet-disjoint **30.9%** — a 42-point gap, with the
outlet-disjoint score still **below the 38.9% majority-class baseline**. A bag of bigrams
that has seen an outlet during training identifies it easily and generalises to new outlets
*worse than guessing*. Outlet-disjoint remains the only protocol on this dataset that yields
an interpretable number.

Every random-split figure in our earlier write-ups (`RESULT2.md`, `FINDINGS_2026-08-11.md`)
carries this inflation and should be re-run deduplicated before being cited.

---

## 5. Experiment 4 — Earlier results, in context

From the July–August runs (full detail in
`muws-allsides-dataset/stance_detection_experiment/RESULT2.md`):

- **Headline alone reaches 87.6%** on the inflated random split — 93% of full-text
  performance from 1.7% of the characters. Outlet identity is carried by the title's house
  style before the body is read.
- **Publisher-name stripping costs 0.8pp.** The leakage is not the outlet's name, it is its
  template: Fox's URL scheme and app promo, AP's paywall notice, The Hill's section headers
  (*"Why it matters"*, *"What happens next"*).
- **Scrubbing fails.** Removing 9% of every character in the corpus moved the random split
  1.2 points. What remains is house style and naming convention — *"donald trump"* (left
  outlets) versus *"president trump"* (The Hill) — which cannot be removed without
  destroying the article.
- **A bug in the stripping itself:** `strip_publisher` substituted the constant string
  `"the news outlet"`, and because outlets differ in how often they name themselves, the
  *count* of that token re-identified the outlet. Delete names rather than substitute.
- **The fine-tuned encoder's `center` failure** has four mechanisms; calibrating two bias
  parameters on train lifts held-out macro-F1 from 0.607 to 0.731, with a zero
  generalisation gap.
- **All four zero-shot NLI models score below the majority-class baseline** (best 40.8% vs
  40.0%), with mean probability on the gold label ≈ 0.33 — uninformative rather than wrong.

---

## 6. What to do about it

1. **Stop reporting random-split numbers on this dataset.** They combine duplicate
   memorisation with outlet recognition. Report outlet-disjoint, deduplicated.
2. **Deduplicate `original.jsonl` by article text** and rebuild the splits on the text hash,
   not `article_id`. The usable set is ~2,807 articles, not 11,779 — and that smaller honest
   number should drive the modelling plan.
3. **Reframe or relabel.** Either state the task as *outlet identification* (defensible, and
   the numbers are interesting), or obtain article-level labels.
4. **Evaluate Ad Fontes Media.** It is the only provider found that rates **individual
   articles**, with panels of ≥3 trained human analysts of mixed self-reported politics, on
   a continuous −42…+42 bias scale plus a 0–64 reliability scale. See
   [other_sources.md](other_sources.md).
5. **A cheap high-value annotation task:** the ~50% of articles where the LLM and the outlet
   label disagree are a pre-filtered candidate pool for human adjudication. Hand-labelling a
   few hundred of those would establish, for the first time in this project, what the
   article-level ground truth actually looks like.
