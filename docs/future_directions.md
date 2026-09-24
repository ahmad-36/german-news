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
- **Clustering:** Ground News' own pipeline, run after translating everything into
  English, with an error mode we measured. 41.2% of articles are machine-translated into
  English before they are clustered and tagged. The translation deletes entities (*Manuel
  **Neuer*** → "new", *FC **Bayern*** → "Bavaria", `USA` → "Us"). One Bundesliga
  goalkeeper cluster ends up tagged "Mohammed Bin Salman". See
  [translation_problem.md](translation_problem.md).

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
- A bag of bigrams scores **94.6%** on a random split but **27.3%** with held-out outlets,
  below the 46.8% majority baseline.
- The eval set is also **4.2× duplicated**. After deduplication, the random-split number
  drops to 72.6%.

**What would change the decision:**

- Article-level human labels, such as Baly et al.'s AllSides article annotations, BASIL,
  or our own annotation of the articles where an LLM and the outlet label disagree (see
  [tasks.md](tasks.md)).
- Always evaluating on a **media-based split**.
- For German outlets, a rating scheme that isn't built on the US political spectrum.

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
