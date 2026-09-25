# The Five Downstream Tasks, Defined Separately

These have been run together as "the bias project". They are five distinct tasks with
different inputs, different outputs, different evaluation, and — critically — **different
data requirements**. Three of the five are blocked by the label-granularity problem; two
are not blocked at all and could start today.

Throughout: a **story** is a cluster of articles covering one event; a **topic** is a
group of stories on one subject; **stance** ∈ {left, center, right}.

---

## Task 1 — Article summarisation

| | |
|---|---|
| **Input** | one article (body text) |
| **Output** | a short abstractive summary of that article alone |
| **Unit** | article |
| **Evaluation** | ROUGE / BERTScore against a reference; faithfulness (NLI-based entailment of summary against source) |
| **Data needed** | body text. **No labels, no clustering.** |
| **Available now** | 🟢 **Yes.** Event Registry: 129,628 German articles at 100% body coverage. GDELT enrichment: 154,084 fetched German bodies. AllSides: 11,838 English bodies. |
| **Blocked by** | nothing |

The only task that needs neither clustering nor stance labels. It is also the only one
where Event Registry alone is sufficient — though the ToS forbids republishing the data,
so any release would be model-only.

---

## Task 2 — Topic summarisation

| | |
|---|---|
| **Input** | all articles in one **topic** (many stories, many events) |
| **Output** | a summary of the subject area over a period |
| **Unit** | topic × time window |
| **Evaluation** | coverage of constituent events; redundancy; factuality |
| **Data needed** | body text **+ topic clustering** (stage ③) |
| **Available now** | 🟡 **Partially.** AllSides and Ground News have human topics but thin/absent bodies. Event Registry has bodies but no topics collected. GDELT has machine themes of low precision. |
| **Blocked by** | no single provider has bodies *and* good topics — needs the cross-provider join on the 56 shared domains |

Distinct from Task 1 in that the input is a *set spanning multiple events*, so the failure
mode is not hallucination but **selection** — deciding which of 400 articles the summary
should be about.

---

## Task 3 — Stance summary

| | |
|---|---|
| **Input** | one story + one stance (e.g. all left-leaning articles about event X) |
| **Output** | *"here is how the left covered this"* — one summary per stance |
| **Unit** | (story, stance) pair — up to 3 outputs per story |
| **Evaluation** | faithfulness to that stance's subset only; must not leak content unique to the other stances |
| **Data needed** | body text + story clustering (④) + **stance partition** (④b) |
| **Available now** | 🟡 **Reference outputs exist, inputs do not.** Ground News ships `summary_left` / `summary_center` / `summary_right` for 441 of 894 stories — but it ships **no body text at all**, so the inputs those summaries were computed from are absent. |
| **Blocked by** | (a) no bodies on the only provider with stance summaries; (b) the stance partition is outlet-level |

Ground News's summaries are **LLM-generated**, so they are weak supervision or a baseline
to beat — not ground truth. `summary_right` is frequently the empty string even when left
and center are populated, which biases any study conditioning on all three being present.

---

## Task 4 — Stance comparison

| | |
|---|---|
| **Input** | one story + **all** its stance partitions |
| **Output** | *"the left framed it as A, the right as B, and they differ on C"* — one contrastive text per story |
| **Unit** | story (exactly one output) |
| **Evaluation** | are the asserted differences real and attributable? does it avoid inventing disagreement? |
| **Data needed** | everything Task 3 needs, **plus** ≥2 populated stances per story |
| **Available now** | 🟡 Ground News's `bias_comparison` field is exactly this output, LLM-generated, for the same 441 stories. Inputs again absent. |
| **Blocked by** | same as Task 3, and more tightly — needs *multiple* stances populated simultaneously |

**Not the same task as Task 3.** Task 3 summarises one side in isolation; Task 4 must
identify the *axis of disagreement*, which requires reading all sides jointly. A system
that does Task 3 three times and concatenates has not done Task 4.

---

## Task 5 — Stance prediction

| | |
|---|---|
| **Input** | one article (headline and/or body) |
| **Output** | a stance label ∈ {left, center, right} |
| **Unit** | article |
| **Evaluation** | accuracy / macro-F1 **under an outlet-disjoint split** |
| **Data needed** | body text + **article-level** stance labels |
| **Available now** | 🔴 **Blocked.** No provider surveyed offers article-level stance labels. |
| **Blocked by** | the label-granularity problem — see [stance_labels.md](stance_labels.md) |

This is the task the label problem hits hardest, and the only one where the problem is
*fatal rather than inconvenient*. With outlet-level labels the task silently becomes
publisher identification: deduplicated, a bag of bigrams scores **72.6%** on a random split
(baseline 38.9%) and **30.9%** when test outlets are held out — **indistinguishable from
that split's own 28.1% baseline**. It identifies outlets it has seen and carries none of it
to new ones.

**To unblock:** obtain article-level labels (Ad Fontes is the only provider offering
them), or reframe explicitly as outlet identification, or restrict to the minority of
articles where an LLM and the outlet label disagree and adjudicate those by hand.

---

## Summary

| # | Task | Unit | Needs clustering | Needs stance labels | Status |
|---|---|---|---|---|---|
| 1 | Article summarisation | article | 🔴 no | 🔴 no | 🟢 **can start now** |
| 2 | Topic summarisation | topic | 🟢 topic-level (③) | 🔴 no | 🟡 needs cross-provider join |
| 3 | Stance summary | (story, stance) | 🟢 story-level (④) | 🟢 yes | 🟡 no bodies where labels are |
| 4 | Stance comparison | story | 🟢 story-level (④) | 🟢 yes, ≥2 stances | 🟡 as Task 3, stricter |
| 5 | Stance prediction | article | 🔴 no | 🟢 **article-level** | 🔴 **blocked** |

The practical consequence: **Tasks 1 and 2 are the near-term work**; Tasks 3–5 all wait on
either article-level labels or a body-text join, and should not be planned as if they were
one deliverable.
