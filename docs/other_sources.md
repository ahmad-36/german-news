# Other Providers Checked

Nine providers beyond the four we use. Stage numbers refer to
[the pipeline](pipeline.md): ① collection ② filtering ③ topic clustering
④ article clustering ⑤ downstream tasks.

---

## The table

| provider | what it is | stages | German | stance labels | cost / access |
|---|---|---|---|---|---|
| **Ad Fontes Media** | article rating service — **the only one that rates individual articles**, ≥3 human analysts per article, mixed politics | ⑤ labels only | ❓ unlikely, US-focused — **needs confirming** | 🟢 **per article**, bias −42…+42 + reliability 0…64 | 🔴 commercial licence |
| **Media Cloud** | open academic news archive, 100+ countries, ~10 years | ① ② | 🟢 yes | 🔴 none | 🟢 **free API** for researchers |
| **CC-NEWS** | Common Crawl's news crawl — raw HTML, multilingual, back to 2016 | ① | 🟢 yes | 🔴 none | 🟢 **free, openly licensed** |
| **MBFC** | outlet bias + factuality ratings; already one of Ground News' three sources | ⑤ labels only | 🟢 rates German outlets | 🟡 **per outlet** | 🟡 API, paid tiers |
| **NewsGuard** | 0–100 trust scores, human-reviewed, good European coverage | ⑤ labels only | 🟢 yes | 🟡 credibility, **not political lean** | 🔴 commercial |
| **NELA-GT** | static research dataset, ~1.8M articles/yr, 519 sources, MBFC labels attached | ① ⑤ | 🔴 **English/US only** | 🟡 per outlet | 🟢 free |
| **NewsCatcher** | commercial API with **real Leiden event clustering** + dedup | ① ② ③ ④ | 🟢 yes | 🔴 none | 🔴 paid, trial available |
| **Perigon** | commercial API, story grouping but no event clustering | ① ② | 🟢 yes | 🔴 none | 🟡 free tier 150 req/month, then $250+/mo |
| **Webz.io** | commercial API, full text; dedup is your problem | ① | 🟢 yes | 🔴 none | 🔴 paid |

---

## The three worth acting on

**Ad Fontes** is the only provider found that rates **individual articles** rather than
outlets. Every stance-prediction problem we have traces back to that gap, so it is worth
asking about a research licence and whether any non-US coverage exists — even a US-only
article-level set would let us measure how far an outlet label sits from an article label.

**Media Cloud** is open, free and built for this kind of research. Worth testing its German
depth against our GDELT census; if comparable, it is a cleaner and publishable substitute
for part of that pipeline.

**CC-NEWS** is the obvious answer to Event Registry's licensing problem: German full text
we may actually republish.

---

## Rejected

**Europe Media Monitor (EMM/NewsBrief, JRC)** — would have been close to ideal: 20k sources,
80 languages, and the only service found doing **cross-lingual cluster linking** (cluster
per language, then link clusters describing the same event). That is exactly the
architecture [translation_problem.md](translation_problem.md) argues for.
🔴 **Permanently discontinued.** Cite the JRC papers as prior art; the service is gone.

**Static German corpora** — no ongoing collection, no clustering, so not providers:
`taz2024full` (1.8M articles, single outlet, 1980–2024), `One Million Posts` (DerStandard
comments, not articles), `MBIB` (bias benchmark collection — worth checking for a German
subset), `BABE`/`MBIC` (expert sentence-level bias, English, but the closest annotation
protocol to what we lack).

---

## What none of them fill

- **Article-level stance outside Ad Fontes.**
- **German full text that is legally republishable** — CC-NEWS is the only candidate.
- **Cross-lingual cluster linking**, now that EMM is gone.
