# Providers Beyond the Four

Nine further sources, assessed against what this project actually needs: **German
coverage**, **full text**, **cross-outlet clustering**, and **article-level stance labels**.

Ranked by how much they would change the plan.

---

## Tier 1 — evaluate these

### 1. Ad Fontes Media — the only article-level stance labels found

| | |
|---|---|
| **Why it matters** | 🟢 **Rates individual articles, not outlets.** This is the one gap nothing else fills. |
| Method | Each article assessed by **≥3 human analysts**, deliberately a mix of self-reported left, right and center |
| Analysts | 40+, trained: 30 h initial + 40 h/year ongoing; academics, journalists, librarians, lawyers, veterans |
| Scales | Bias **−42…+42** (continuous); Reliability **0…64** |
| Dimensions | Bias: Political Position, Language, Comparison. Reliability: Expression, Veracity, Headline/Graphic |
| Scale-up | Now human-plus-AI; top daily stories still rated by balanced human panels |
| German | 🔴 Unlikely — US-focused. **Needs confirming.** |
| Access | Commercial licence; already an upstream input to Ground News |

**Action:** ask about (a) a research licence, (b) whether any non-US/German coverage
exists, (c) whether the continuous score and per-analyst ratings are exposed or only the
aggregate. Even a US-only article-level set would let us measure how far an outlet-level
label is from an article-level one — the central open question in
[stance_labels.md](stance_labels.md).

### 2. Media Cloud — open, academic, multilingual

| | |
|---|---|
| **Why it matters** | 🟢 Open source and open data, built for exactly this kind of research |
| Coverage | Collections for **100+ countries**; a decade of crawling |
| Language | ~20 languages with proper stopword support; German included |
| Clustering | 🟡 Not event clustering — it is a searchable archive, not a story graph |
| Labels | 🔴 No bias labels |
| Full text | 🟡 Varies by source |
| Access | 🟢 **Free API** for researchers |

**Action:** test German collection depth against our GDELT census. If comparable, Media
Cloud is a cleaner, better-documented, openly licensed substitute for part of the GDELT
pipeline — and unlike Event Registry, publishable.

---

## Tier 2 — useful, with caveats

### 3. Common Crawl News (CC-NEWS)

Massive multilingual news crawl with **full HTML**, openly licensed, free, back to 2016.
No clustering, no labels, no topic metadata — but it is the only source of German full text
with no redistribution restriction. **The obvious substitute for Event Registry** if
licensing is what blocks a public release.

### 4. Media Bias/Fact Check (MBFC)

Already reaching us indirectly (it is Ground News's largest label source, 25,435 articles).
Outlet-level, covers **international outlets including German ones** — better German
coverage than AllSides, which is US-only. Has an API. Worth pulling directly so German
outlet ratings can attach to GDELT clusters without going through Ground News's tiny
corpus.

### 5. NewsGuard

0–100 trust scores, human-reviewed, transparent criteria, **good European coverage**. Rates
*credibility*, not political lean — complementary to a bias label, not a substitute.
Commercial.

### 6. NELA-GT (2018–2022)

Academic, free, well-documented: ~1.8M articles/year from ~519 sources with source-level
MBFC labels. 🔴 **English/US only.** Useful as a methodological template and as a
pre-existing benchmark; contributes nothing German.

---

## Tier 3 — commercial APIs

| Provider | Clustering | Full text | Free tier | Note |
|---|---|---|---|---|
| **NewsCatcher** | 🟢 **Leiden-based event clustering + dedup** | 🟢 | trial | The only commercial API found doing real event clustering |
| **Perigon** | 🟡 story grouping, no event clustering | 🟢 | 150 req/month | Measured 22.2% duplicate rate |
| **Webz.io** | 🔴 dedup is your problem | 🟢 | limited | Measured 13.0% duplicate rate |

All three carry **the same redistribution problem as Event Registry**. They solve
convenience, not licensing. Perigon's paid tiers start at $250–550/month.

If clustering quality is the bottleneck, **NewsCatcher's Leiden clustering is worth a trial
run against our `SequenceMatcher` baseline** — a direct, cheap comparison of a proper
community-detection clustering against our greedy title-similarity approach.

---

## Assessed and rejected

### Europe Media Monitor (EMM / NewsBrief) — JRC

Would have been close to ideal: 20,000 sources, ~500k pages/day, 80 languages, 150
countries, and **the only service found doing cross-lingual cluster linking** — clustering
in 60 languages and then linking clusters across languages that describe the same event.
That is precisely the architecture [translation_problem.md](translation_problem.md) argues
for, and German is fully supported.

🔴 **EMM NewsBrief has been permanently discontinued.** Cite the JRC publications as prior
art for cluster-then-link; the service is not available.

### German-specific corpora

Static research datasets, not providers — no ongoing collection, no clustering:

- **taz2024full** — 1,834,370 articles from *taz*, 1980–2024. Single outlet, so no
  multi-perspective structure, but an excellent single-outlet longitudinal resource.
- **One Million Posts Corpus** — *DerStandard* (AT) user comments, professionally
  moderated labels. Comments, not articles.
- **MBIB** (Media Bias Identification Benchmark) — a collection of bias datasets; worth
  checking for any German subset.
- **BABE / MBIC** — expert sentence-level bias annotation. **English**, but the closest
  existing analogue to the article-level labels we lack, and a usable annotation-protocol
  template.

---

## Summary against our requirements

| Provider | German | Full text | Clustering | **Article-level stance** | Publishable |
|---|---|---|---|---|---|
| *GDELT* (current) | 🟢 | 🟠 own crawl | 🟠 ours | 🔴 | 🟢 |
| *Event Registry* (current) | 🟢 | 🟢 | 🔴 | 🔴 | 🔴 |
| *Ground News* (current) | 🟡 12% | 🔴 | 🟢 | 🔴 outlet | 🟡 |
| *AllSides* (current) | 🔴 | 🟡 17% | 🟢 | 🔴 outlet | 🟡 |
| **Ad Fontes** | ❓ verify | — | 🔴 | 🟢 **yes** | 🔴 commercial |
| **Media Cloud** | 🟢 | 🟡 | 🔴 | 🔴 | 🟢 **open** |
| **CC-NEWS** | 🟢 | 🟢 | 🔴 | 🔴 | 🟢 **open** |
| **MBFC** | 🟢 outlets | — | — | 🔴 outlet | 🟡 |
| **NewsCatcher** | 🟢 | 🟢 | 🟢 **Leiden** | 🔴 | 🔴 |
| **NewsGuard** | 🟢 outlets | — | — | 🔴 credibility | 🔴 |
| **NELA-GT** | 🔴 | 🟢 | 🔴 | 🔴 outlet | 🟢 |
| ~~EMM NewsBrief~~ | 🟢 | — | 🟢 **cross-lingual** | 🔴 | — **discontinued** |

**The three gaps that remain unfilled by any single provider:** article-level stance labels
outside Ad Fontes; German full text that is legally republishable (CC-NEWS is the best
candidate); and cross-lingual cluster linking now that EMM is gone.
