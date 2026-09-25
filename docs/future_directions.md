# Future Directions

Candidate tasks that were considered for this dataset. For each one: what the task is,
and whether we are pursuing it and why.

---

## 1. Bias / leaning classification

| | |
|---|---|
| **Input** | One article |
| **Output** | `left` / `center` / `right` |
| **Ground truth (candidate)** | AllSides (human, but check the granularity); Ground News |
| **Nature of the task** | A property of the *text*, independent of any particular claim |

### Status: not pursued — the available labels do not measure what the task asks

The task needs a label for each **article**. Every label we can get is for the **outlet**,
and the other signals Ground News provides are either machine-generated or built on
machine-translated text. What each part of a Ground News record actually is:

- **Bias labels:** human, outlet-level, averaged from AllSides / Ad Fontes / MBFC, and
  US-framed. Ground News rates nothing itself. All three agencies are US organisations
  that place outlets on the American left–right axis, and they **disagree on 32.1%** of
  rated articles (9,244 of 28,833). Ground News averages that disagreement into one value.
  So "Ground News" is not a separate source of ground truth. Its labels are the same
  human outlet ratings, averaged.
- **Summaries and bias comparison:** GPT output, story-level, partial coverage. The page
  payload stores `summary_left/center/right` and `bias_comparison` in an object named
  `chatGptSummaries`. Only 441 of 894 stories have any side summary, and only 209 have all
  three. These are GPT's reading of the coverage, so they are weak supervision at best,
  not ground truth.
- **Clustering: mechanism unknown.** Ground News does not document how it groups articles
  into stories, and nothing in the scraped record reveals it — no algorithm, no
  similarity score, no indication of which text the clustering key is built from. Treat
  its clusters as a black box.

  What we *can* measure is that **41.2% of articles are machine-translated into English**
  and that the translation deletes entities (*Manuel **Neuer*** → "new", *FC **Bayern***
  → "Bavaria", `USA` → "Us"), and that at least one cluster's **topic tags** are wrong in
  a way consistent with being derived from that translated text — a Bundesliga goalkeeper
  story tagged "Mohammed Bin Salman". Whether the *clustering* also runs on the
  translation is **not established**; see [translation_problem.md](translation_problem.md)
  for what the evidence does and does not support.

**AllSides rates the outlet, not the article.**
AllSides' audit methodology
([Media Bias Audit example report, March 2022](https://www.allsides.com/sites/default/files/AllSides-Media-Bias-Audit_Example-March-2022.pdf))
explains that they sample 5 to 10 headlines, or the top article on specific major stories.
Those samples are then aggregated into **a single overall score for the publication**.
Survey respondents rate the outlet's sampled content as a whole on an 11-point scale. The
responses are averaged across bias groups into *"an overall weighted average"*, and the
written and video ratings are averaged again into one final rating. The report also says
the system *"reflects the average judgment of the American people."* Every article the
outlet publishes then inherits that one number. Details:
[stance_labels.md §1](stance_labels.md).

**The literature names the same failure.**

- **Baly et al. (EMNLP 2020)**, *"We Can Detect Your Bias: Predicting the Political
  Ideology of News Articles"*
  ([PDF](https://aclanthology.org/2020.emnlp-main.404.pdf); mirror:
  [research.unipd.it](https://www.research.unipd.it/retrieve/e14fb26d-c6fc-3de1-e053-1705fe0ac030/2020.emnlp-main.404.pdf)).
  - Earlier article-level work *"typically used distant supervision, assuming that all
    articles from a given medium should share its overall bias, which is not always the
    case."*
  - On Kulkarni et al. (2018), which built its data from AllSides outlet labels: *"their
    training and test sets contain articles from the same media, and thus models could
    easily learn to predict the article's source rather than its bias."* That is a
    source-identity leak.
  - Their fix is a **media-based split**, where test articles come from outlets never
    seen in training, plus adversarial media adaptation and a triplet loss.
  - Their own AllSides article-level labels differ from the outlet's label for only 3.11%
    of articles (1,080 / 34,737). The outlet label is usually *right*, which is exactly
    why a model can score well by learning the outlet.
- **Fan et al. (EMNLP 2019)**, *"In Plain Sight: Media Bias Through the Lens of Factual
  Reporting"* ([ACL Anthology](https://aclanthology.org/D19-1664/), BASIL dataset).
  - They annotate bias at the article and span level for the same event covered by Fox,
    NYT and HuffPost. This contrasts with prior work that *"uses all articles published
    by a news outlet to estimate their ideology."*
  - In **17 of 100** event triplets, annotators ranked the articles in the opposite order
    to the outlets' known leanings: Fox marked more liberal, or HuffPost more
    conservative. Outlet leaning therefore does not reliably transfer to a given article.
- **Spinde et al. (Findings of EMNLP 2021)**, *"Neural Media Bias Detection Using Distant
  Supervision With BABE"* ([ACL Anthology](https://aclanthology.org/2021.findings-emnlp.101/)).
  - They label text by outlet (partisan outlet → biased, high-standards outlet → neutral)
    and call these *"noisy yet abundantly available labels"*.
  - They use that corpus only for pre-training, because it *"is not suitable for
    evaluation purposes due to its noisy nature"*. Evaluation uses expert
    sentence-level annotations (BABE).

**Our own data shows it.** See [stance_labels.md](stance_labels.md):

- All 15 outlets in the AllSides eval set have **100% label purity**.
- Deduplicated, a bag of bigrams scores **72.6%** on a random split (baseline 38.9%) but
  **30.9%** with held-out outlets — indistinguishable from that split's own 28.1% baseline.
  (The often-quoted 94.6% / 27.3% are the *pre-deduplication* figures and should not be
  cited — see [stance_labels.md §4](stance_labels.md#4-experiment-3--a-correction-the-eval-set-is-42-duplicated).)
- The eval set is **4.2× duplicated**, with the same article text on both sides of the
  split for 77.9% of records — which is where the 22-point drop comes from.

**What would change the decision:**

- Article-level human labels, such as Baly et al.'s AllSides article annotations, BASIL,
  or our own annotation of the articles where an LLM and the outlet label disagree (see
  [tasks.md](tasks.md)).
- Always evaluating on a **media-based split**.
- For German outlets, a rating scheme that isn't built on the US political spectrum.

### What actually ran: publisher-name reliance in political-leaning classifiers

Code and full tables: `~/muws-allsides-dataset/stance_detection_experiment/`, mainly
`publisher_sensitivity.py`, `analyze_publisher_sensitivity.py`, `baly_data.py`,
`train_baly.py` and `compare_models.py`. Outputs are in
`analysis/publisher_sensitivity/`, including `COMPARISON.md`.

#### Motivation

AllSides labels articles by outlet, not by article. In the **full scrape** — 411 outlets,
68,352 article slots — **408 of 411** outlets
carry one label on every article. The other three (AP, Daily Mail, The American
Conservative) changed rating on a clean date, and in the 3-class setup each change stays
on the same side. So a classifier trained on AllSides labels can score well just by
recognizing the outlet. The question: **how much do classifiers rely on the publisher's
name in the text, and where does that reliance come from?**

#### Prior work

- **Baly et al. (EMNLP 2020)** identified the same problem (see above).
  - They compared a random split with a media-based split, where each outlet appears in
    only one of train or test.
  - BERT: **79.8%** accuracy on the random split vs **36.8%** on unseen outlets.
  - Adversarial adaptation and triplet loss reduce the outlet signal; triplet loss lifts
    unseen-outlet accuracy to **51.4%**.
- **LLMs.** GPT-4o without examples reached 0.50 accuracy on AllSides. GPT-3.5 with a
  structured prompt reached 59.8% on the de-biased test set. Giving LLMs the source name
  raises their accuracy, so they use names too. *(Citations to be added.)*
- **Model choice.** A 2025 benchmark (Volf & Simko) found premsa's DeBERTa the best
  available political-leaning classifier, which is why it became the main model.
  *(Full citation to be added.)*

#### Stage 1: first stance experiments

- **Tested:** the premsa encoder, NLI models and open-source LLMs, in 3-class and 5-class
  setups.
- **Encoder:** 65.7% on the 15-outlet scrape and 52.7% on the 465-source AllSides set.
  NLI models and LLMs were near chance.
- **Center** was the weak class (The Hill at 17.5%).
- **First swap test.**
  - 58.4% of articles mention their publisher; a later, more thorough name search raised
    this to 63.4%.
  - Stripping names cost the encoder 3.8 points.
  - A cross-side swap dropped left-article accuracy from 81% to 58%.
- **Problems found:**
  - Label flips depend on the 0.5 threshold.
  - Articles without a name mention diluted every number.
  - Center articles weren't cross-swapped, which made the flip-rate comparison unfair.

#### Stage 2: publisher-name sensitivity test

**Setup**

| | |
|---|---|
| Model | premsa, 3-class |
| Data | 2,823 articles after deduplication; 1,789 (63.4%) mention their own publisher |
| Conditions | original, stripped, invented neutral name, same-side swap, cross-side swap |
| Metric | change in softmax probability per article; bootstrap CIs and Wilcoxon tests |
| Chunking | chunk boundaries fixed on the original text; reported for the whole article and for the chunk containing the name |
| Swap targets | from the data: the name with the highest share of mentioning articles on one side (≥30 mentions, ranked by Wilson lower bound). Final run: **Politico** (left), **The BBC** (center), **Fox News** (right). A first run used NBC News / Newsweek / Washington Examiner and was redone — see the centre-control note below |

**Results** — change in softmax probability, percentage points, **whole article**
(mean over all chunks). Per-class columns show where the probability mass actually moves.

> **ΔP(true class)** = the change in the probability the model puts on the article's *gold*
> label. Negative means the edit pushed the model away from the right answer. It is the
> single headline number per condition; the per-class columns say *where* that mass went.

| Condition | n | ΔP(left) | ΔP(center) | ΔP(right) | ΔP(true class) |
|---|---:|---:|---:|---:|---:|
| Stripped | 1,790 | +4.7 | −4.9 | +0.2 | **−8.4** |
| Neutral name | 1,790 | −3.6 | −2.5 | +6.1 | **−9.4** |
| Same-side swap | 1,790 | +3.5 | −4.0 | +0.5 | **+3.3** |
| Cross-side swap | 1,234 | −5.3 | −0.6 | +5.9 | **−23.5** |

The cross-swap row looks small only because it averages two opposite interventions.
Split by the article's own side, the effect is large **and strongly asymmetric**:

| Cross-swap | n | ΔP(left) | ΔP(center) | ΔP(right) | ΔP(swapped-in side) |
|---|---:|---:|---:|---:|---:|
| **left** article, name → right-leaning outlet | 483 | **−34.4** | −6.3 | **+40.7** | +40.7 [37.8, 43.7] |
| **right** article, name → left-leaning outlet | 751 | **+13.4** | +3.1 | **−16.5** | +13.4 [12.0, 14.9] |
| both, pooled | 1,234 | | | | +24.1 [22.5, 25.7] |

**Centre articles are the cleanest test**, because they have no "opposite" side, so both
directions were run on the *same* 556 articles. Only the inserted name differs:

| Centre article, name → | n | ΔP(left) | ΔP(center) | ΔP(right) |
|---|---:|---:|---:|---:|
| The Hill *(center control)* | 556 | +0.9 | −5.5 | +4.6 |
| **Politico** *(left)* | 556 | **+19.5** | −21.0 | +1.5 |
| **Fox News** *(right)* | 556 | −19.0 | **−32.1** | **+51.1** |

Identical articles, identical procedure — inserting "Fox News" moves them **+51.1 points
toward right**, while inserting "Politico" moves them only **+19.5 toward left**. The model
does not weigh outlet names symmetrically: a right-coded name is worth roughly **2.6×** a
left-coded one. This is the tightest controlled comparison in the experiment, and the
strongest single piece of evidence that the model is reading the byline rather than the
article.

- **The name works as a side signal**, and it is worth ~3× more when it points right.
  Renaming a left-leaning article to a right-leaning outlet moves **+40.7 points** toward
  right; the reverse move buys only **+13.4**. Paired against the same-side control on the
  same articles, cross − same is **−49.0** for left articles and **−19.1** for right
  (both p < 1e−80).
- **Stripping ≈ neutral name.** The drop comes from losing the name, not from broken
  sentences. AP is the exception: deleting "(AP)" *raises* P(left) by 17 points.
- **Long articles dilute the effect.** Restricted to the chunk containing the name, the
  pooled cross-swap effect rises from **+24.1** to **+31.0**, and the left-article case
  from +40.7 to **+52.2**.

> **Correction.** An earlier version of this table reported −0.8 for same-side swap,
> −32.4 / +31.2 for cross-side swap, and "−35 for right". Those mixed three different
> rows of the source report: −32.1 is `cross_right` (swaps *to a right name*, not the
> `cross` condition), +31.0 is the **name-chunk** scope rather than the whole article, and
> the right-side paired contrast is −19.1, not −35. Same-side swap is **+3.3**, not −0.8.
> All figures above are the whole-article block of
> `analysis/publisher_sensitivity/premsa/REPORT.md`, with brackets showing 95% bootstrap
> CIs.
- **The center control was broken in the first run**, which is why the targets changed.
  Newsweek looked 99% center only because 207 of its 210 mentions come from its own
  articles. The model doesn't read "Newsweek" as center, so the centre same-side control
  failed. The final run uses the BBC. Both runs are kept:
  `analysis/publisher_sensitivity/premsa/` (final) and `premsa_v1_newsweek/` (first).

#### Stage 3: where the effect comes from

**premsa's model card.**

- DeBERTa-v3-base, trained on Baly's dataset with the *random* split, so the outlets it is
  tested on were seen in training. It reports F1 0.9427.
- The cleaning rules are undocumented.
- Baly's processed text masks most outlet names but not all: in a sample, 34 of 178
  name-mentioning articles still had the name. So premsa saw at least some names during
  training.

**Models trained** (both with premsa's hyperparameters):

- **A:** outlet split (test outlets unseen), names kept.
- **B:** outlet split, all news-outlet names stripped from the training text.

Swap targets for this run were counted over all AllSides data (Baly + test), which gave
Politico (left), BBC (center) and Fox News (right). Center articles are cross-swapped to
both the left and the right target.

| | premsa | A | B |
|---|---|---|---|
| Cross-swap Δ P(swapped-in side) | +24.1 | +7.6 | +19.0 |
| Center → Politico | +19.5 | −2.8 | +1.5 (n.s.) |
| Center → Fox News | +51.1 | +22.8 | +25.2 |
| Same-swap Δ (control) | +3.3 | +1.3 | −1.0 |
| Accuracy, original text | 66.6% | 52.0% | 53.8% |
| Accuracy, stripped text | 61.8% | 50.3% | 47.2% |

- **Seen outlets drive most of the effect.** Leaving the test outlets out of training cuts
  the effect by about two-thirds (24.1 → 7.6). Politico shows pure memorization: premsa
  reacts to it, A and B don't.
- **premsa's accuracy was inflated by seen outlets.** It drops to about 52–54% on unseen
  outlets, matching the literature.
- **Stripping names in training made the shortcut worse** (B +19.0 vs A +7.6). A likely
  learned from mixed-label mentions that names are unreliable. B never saw names, so it
  falls back on what the base model already knows. Both react strongly to Fox News, a
  well-known name, but not to Politico.
  - **Confound:** B's best checkpoint is from **epoch 1** (valid loss 1.15). A's is from
    **epoch 3** (valid loss 0.81). B barely moved from the base model, which alone could
    make it lean on base-model name associations. The A vs B gap is not yet attributable
    to name stripping (`logs/train_A.log`, `logs/train_B.log`).

#### Main conclusion

The best available AllSides classifier relies heavily on publisher names. Most of that
comes from training on the same outlets it's tested on. Removing names from the training
data doesn't fix it, because the base model already links well-known outlets to political
sides. That last point is subject to the epoch confound above.

#### Dropped or unproductive

| Idea | Why dropped |
|---|---|
| 5-class setup | Doesn't fit NLI models, which are built around 3 answers |
| NLI and open-source LLMs without examples | Near chance, so they told us nothing about name reliance |
| Few-shot or fine-tuned LLMs | Not pursued; encoders answered the question at lower cost |
| Outlet-recognition classifier | Just a standard classifier; only confirms what Baly already showed |
| Rater disagreement (AllSides vs Ad Fontes vs MBFC) | Needed new scraping, which Eric ruled out |
| Fox News outlier analysis | Dropped **with an AllSides-trained classifier** (circular — it learned the same outlet labels). Ran **zero-shot with an LLM instead**: see [stance_labels.md §3](stance_labels.md#3-experiment-2--the-outlier-check-how-often-does-an-llm-disagree-with-the-label) |
| Center and length fixes (summaries, long-context models) | Raising accuracy against outlet-level labels doesn't measure article leaning |
| Name-only test for choosing swap targets | Depends on the model, not the data |
| Target choice by the outlet's own articles | Every outlet is 100% one side, so it can't rank anything |
| Newsweek as center target | Broke the center control because of self-mentions |
| Label flip rate as main metric | Replaced by change in probability |
| Stripping names in training (Model B) | Did not remove the shortcut |

#### Left open

- **Seeds.** A and B were trained once each. Three seeds would confirm the A vs B gap.
- **Epochs.** Compare A and B at the same epoch as well as at the best checkpoint (see the
  confound above).
- **Leftover names.** Check B's training text for remaining names such as "( CNN )".
- **Model C.** Names randomly swapped across sides during training. This is the likely
  fix, but it's untested.
- **premsa's cleaning rules.** Ask the author (Premtim Sahitaj, DFKI).
- **The 97% claim.** Likely source: Baly et al. (2020) report that 1,080 of 34,737
  articles (3.11%) have a label different from their outlet's, i.e. 96.9% agree. Confirm
  this is the claim being cited.
- **Multiple comparisons.** p-values are uncorrected. The swap targets differ between
  Stage 2 and Stage 3, so don't combine those tables.

---

## 2. Stance detection

| | |
|---|---|
| **Input** | An article (news body) plus a **target**: a claim, entity, or policy |
| **Output** | `favor` / `against` / `neutral` toward that target |
| **Ground truth** | None available. No provider gives this, so it needs annotation |
| **Nature of the task** | A relation between the text and a specific target, not a property of the text alone |

**How it differs from #1.** Direction 1 asks where an article sits overall. Stance detection
asks what the article says about one particular thing. The two can diverge: an article can
be left-leaning overall and still argue *against* a left-favored policy. An outlet-level
label cannot capture that, even in principle.

Compact form of the same task: **input** = news body + a stance statement; **output** =
`right` / `wrong` / `neutral`. Here `right` means the article supports the statement,
`wrong` means it opposes it, and `neutral` means it takes no position.

### Status: open — the problem is that we need to create the dataset ourselves

None of the four providers labels an article's position toward a target:

- **AllSides / Ground News** give outlet-level left/center/right (see #1). That is the
  wrong granularity and the wrong question.
- **Ground News' `summary_left/center/right` and `bias_comparison`** describe how each
  side framed a *story*. They are GPT-generated, cover only 441 / 894 stories, and do not
  name a target or give a per-article position.
- **GDELT / Event Registry** carry no stance signal at all.

So the labels have to be made. What we have to build on:

- **Bodies.** The task needs full text, not headlines. Event Registry has 100% bodies, and
  our GDELT enrichment crawl has 154,084 German bodies. Ground News has none (headline +
  dek only). Bodies for AllSides are scraped, at 17.3% coverage. Details:
  [sources.md](sources.md).
- **Targets.** Same-story clusters (GDELT stories with 3+ outlets, Ground News stories)
  give many articles on one event. That makes a natural unit: fix one target per cluster,
  then label each article's position toward it.

What creating the dataset involves:

1. **Target selection.** Pick claims, entities or policies per cluster, and write each one
   as a short statement.
2. **Annotation guidelines.** Define `favor` / `against` / `neutral`, including how to
   treat reported speech. Quoting someone who opposes a policy is not the article opposing
   it.
3. **Annotation.** Multiple annotators per item, with inter-annotator agreement reported.
   LLM pre-labelling can speed this up, but the gold labels must be human.
4. **Evaluation.** Use a split that holds out outlets and events, so the model cannot win
   by learning the publisher (the lesson from #1).

### Proposed experiment: train an NLI model for stance

The compact form of this task — *article + stance statement → supports / opposes /
neutral* — **is** natural language inference: the article is the premise, the statement is
the hypothesis, and the three labels are entailment / contradiction / neutral. That makes
NLI the obvious modelling route, and it has one property the rest of this project lacks:
**it does not need outlet labels**, so it sidesteps the granularity problem in #1 entirely.

**Why train rather than use off-the-shelf.** We already ran four NLI encoders zero-shot on
the AllSides set (`run_unified_nli.py`: `snli_only`, `mnli_only`, `combined`,
`strong_encoder`). **All four scored below the majority-class baseline** — best 40.8%
against 40.0% — and their mean probability on the gold label was ≈0.33 across every class.
They were not wrong so much as *uninformative*. Two reasons to expect training to help:

1. Those runs asked an out-of-domain question. Generic NLI hypotheses ("This text is
   right-wing") are not the entailment relations MNLI was trained on, and the models had
   never seen news-length premises with political targets.
2. The scoring was ad hoc. The original `run_nli.py` argmaxed **raw entailment logits
   across hypotheses**, which is not comparable between hypothesis strings — the
   "right-wing" hypothesis sat ~3.5 nats above the others, which alone explains the
   observed right-skew. `run_unified_nli.py` fixed this with `zeroshot_norm`, but the
   conclusion was unchanged.

**Setup.**

| | |
|---|---|
| Premise | article body, sentence-aligned 400-token chunks at 35% overlap (`semantic_chunk_overlap`, already implemented) |
| Hypothesis | one short statement per target, from the target-selection step above |
| Labels | entail / contradict / neutral ↔ favor / against / neutral |
| Init | an NLI-pretrained encoder (DeBERTa-v3-large-MNLI) rather than a bare LM, so the entailment head is already shaped |
| Training | fine-tune on the human-annotated set; MNLI/ANLI as auxiliary data if the annotated set is small |
| Aggregation | per-chunk probabilities pooled to an article decision — compare max-entailment vs mean |
| **Split** | **outlet- *and* event-disjoint**, for the reason in #1 |

**Controls, which matter more than the headline score.**

- **Name-swap control.** Run the Stage-2 intervention above on the trained model. If
  swapping the publisher name moves its prediction the way it moved premsa's (+40.7 for
  left articles), the model has learned the outlet again and the score is not about stance.
- **Hypothesis-only baseline.** Train on the hypothesis with no premise. NLI datasets are
  notorious for hypothesis-only artefacts; if this scores well, the targets leak the label.
- **Premise-shuffle baseline.** Pair each hypothesis with a random article from a different
  event. Should collapse to chance.

**What would make it worth doing.** A trained NLI model that beats the outlet-disjoint
baseline *and* survives the name-swap control would be the first result in this project
that measures article content rather than publisher identity. That is a stronger claim than
any accuracy number.

**What blocks it.** The annotated set from the four steps above — this cannot start before
there are human labels. Everything else (chunking, the NLI roster, the swap harness) is
already written.

---

## 3. Event / topic clustering

| | |
|---|---|
| **Input** | A set of articles |
| **Output** | Groups, one per real-world event |
| **Ground truth** | Event Registry and Ground News both do this natively |
| **Nature of the task** | A property of a *set* of articles, not of one article |

### Three ways to handle multiple languages

| | Method | Who does it this way | Where it can break |
|---|---|---|---|
| **A** | **Translate → cluster**: machine-translate everything into one language, then cluster once | *no confirmed example* — Ground News translates, but whether it clusters on the translation is undocumented | Translation errors would become clustering errors: entities are deleted (*Neuer* → "new", *Bayern* → "Bavaria"); see [translation_problem.md](translation_problem.md) |
| **B** | **Cluster per language → link clusters**: cluster within each language, then join the clusters across languages | Event Registry | Needs a cross-lingual linking step, and a missed link splits one event into several |
| **C** | **Multilingual embed → cluster once**: embed all articles in one shared multilingual space, cluster once, no translation | Ours (proposed) | Embedding quality varies by language; the distance threshold has to be tuned |

### Dataset we are using: Event Registry

Event Registry assigns each article an `eventUri`. Articles that share one are ER's own
cluster, which is method B's output. Our pull contains:

| | |
|---|---|
| Articles | 129,628, from 2026-07-30 to 2026-08-07 |
| Articles with an `eventUri` | 21,416 (16.5%) |
| Distinct events | 2,729 |
| Events with 2+ articles | 2,392 (holding 21,079 articles) |
| Events with 3+ articles | 2,169 |

That is enough to sample 100 events.

**Dataset problem: our copy is German-only, not multilingual.** The pull used
`lang="deu"`. So every event holds only its German members, and the non-German members of
~9.5% of events were never fetched. The comparison this direction is actually about is how
A, B and C handle *cross-lingual* events. Our data can't test that, because it contains
one language. Getting a multilingual version is blocked by the Event Registry account:

- **Tokens.** Expanding the events we already have, or pulling a new multilingual
  dataset, costs API tokens. The free plan gives **2,000 tokens that never renew**. The
  German pull used ~1,540, leaving **461**. One 7-day German window alone costs ~1,790.
  A multilingual pull at useful scale needs a **paid account**.
- **30-day limit.** The free tier only serves content from the last 30 days. Our pull
  (2026-07-30 → 08-07) is already outside that window, so the free tier can't fetch the
  missing non-German members of those events. Any new pull on the free tier is also
  limited to one recent month.
- **Terms.** The free plan is for "evaluation and testing" only, and ER's terms prohibit
  redistributing its data. The labelled set would be for internal evaluation, not a
  public release.

On German-only data, method B reduces to "cluster within one language", and there is no
translation step for A to get wrong. So the evaluation below would measure clustering
quality in general, not the multilingual question. That still works for a first pass,
but it doesn't answer the main question.

### What needs to be done

Event Registry's clusters are its own algorithm's output, not human truth. So the
comparison needs our own judgements. Two options:

1. **Sample and judge.** Sample 100 ER events and judge each one yourself: is it one
   real-world event, are any articles wrongly included, are any obviously missing?
   This gives an absolute error rate for ER's clusters.
2. **Pool the disagreements.** Run methods A, B and C over the same articles. Take only
   the cases where the methods disagree (one method groups two articles, another
   separates them). Judge only those, and report **which method is right more often**.
   Cases where all methods agree are assumed correct and cost no annotation time. This is
   cheaper per useful label, but it only gives a *relative* ranking of the methods, and
   it can't detect errors that all three make.

### What actually ran

**Only the third method (C).** We clustered each article set once, with no translation
step, and scored the result against Event Registry's method-B output (its `eventUri`).
Every article we hold is German, because the pull requested German only. So methods A and
B could not be compared cross-lingually:

- ER's free tier serves only the last 30 days, and our events are 48+ days old.
- The remaining 461 non-renewing tokens can't fetch the other-language articles.

The cross-lingual comparison can't be built retroactively. It would have to be collected
going forward, starting from the day collection begins.

So what we have is a **German-only model comparison, evaluated against ER's own event
IDs**: 2,117 events and 17,810 articles, split 50/50 into dev and test by event.
Thresholds were tuned on dev and are reported on test. Code, full tables and bootstrap
CIs are in
[news-eventregistry/clustering_eval](../../news-eventregistry/clustering_eval/README.md).

### Results, with a caveat that undercuts them

| representation (test, dev-tuned) | BCubed P | R | **F1** |
|---|---|---|---|
| *window oracle: perfect clustering inside each 2-day block* | 1.000 | 0.793 | *0.884* |
| BGE-M3, full body | 0.847 | 0.737 | **0.788** |
| TF-IDF word, title + lede | 0.841 | 0.731 | 0.782 |
| mE5-large, title + lede | 0.810 | 0.738 | 0.772 |
| BGE-M3, title + lede | 0.842 | 0.712 | 0.772 |
| gbert-large (German), title + lede | 0.778 | 0.712 | 0.743 |
| SequenceMatcher, title, **production t=0.65** (GDELT clusterer) | 0.981 | 0.293 | 0.451 |

- **TF-IDF ties the best neural model, which is suspicious.** TF-IDF on title + lede
  scored **0.782** BCubed F1. That is statistically tied with the best neural model,
  BGE-M3 on full bodies (**0.788**; difference +0.006, CI [−0.005, 0.016]). On equal
  input (title + lede), TF-IDF is slightly *ahead* of BGE-M3 (+0.010, CI [0.002, 0.021]).
  That looks like a finding, but the likelier explanation is that ER's own clustering is
  bag-of-words-based. If so, TF-IDF scores well because it resembles the labeler, not
  because it clusters well, and the metric may be rewarding similarity to the annotator.
  **This needs human verification before any claim is made.** That is exactly what the
  sample-and-judge or disagreement-pooling step above provides.
- **The German-specific model (gbert) brought no benefit** over the multilingual ones. It
  is 0.02–0.03 F1 worse than BGE-M3 and mE5, and all CIs exclude 0.
- **The GDELT clusterer misses most same-event pairs.** Our production SequenceMatcher at
  threshold 0.65 scored **0.45** F1, with recall **0.29**, so it loses roughly two-thirds
  of the articles that belong together. That is expected, since it compares characters
  rather than meaning, but the size matters: the delivered GDELT file was built with it.
  Tuning the threshold only reaches 0.51. The same caveat applies: this was measured
  against a ground truth that may favour word-overlap methods.
- **Windowing is the biggest limit.** The 2-day non-overlapping blocks cap *every*
  method at **0.884** F1, because about half the events (53%) span longer than a block.
  The best system already reaches 89% of that ceiling. Fixing the windowing would gain
  more than any model change.
