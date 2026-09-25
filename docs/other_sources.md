# Other Providers Checked

Ten providers beyond the four we use. **None of these are in our pipeline** — this is a
shortlist of what we could add, and what each would buy us.

Columns: **multilingual** = does it cover languages beyond English · **clustering** = does
it group articles into same-event stories itself, or would we have to · **stance labels** =
political lean, and at what granularity.

---

## The table

| provider | what it is | multilingual | clustering | German | stance labels | cost / access |
|---|---|---|---|---|---|---|
| **EMM** (JRC) | EU Commission's media monitor — 20k sites, 500k pages/day | 🟢 **80 languages** | 🟢 **cross-lingual linking** — clusters per language, then links clusters across them | 🟢 yes | 🟡 "framing and persuasion" detection, not left/right | 🟡 public tools; researcher access unclear — **ask** |
| **Ad Fontes Media** | article rating service, ≥3 human analysts per article | 🔴 English | 🔴 none | ❓ unlikely, US-focused — **confirm** | 🟢 **per article**, bias −42…+42 + reliability 0…64 | 🔴 commercial licence |
| **Media Cloud** | open academic news archive, 100+ countries, ~10 years | 🟢 ~20 languages with proper support | 🔴 searchable archive, not a story graph | 🟢 yes | 🔴 none | 🟢 **free API** for researchers |
| **CC-NEWS** | Common Crawl's news crawl — raw HTML, back to 2016 | 🟢 yes | 🔴 none | 🟢 yes | 🔴 none | 🟢 **free, openly licensed** |
| **NewsCatcher** | commercial news API | 🟢 yes | 🟢 **Leiden event clustering** + dedup | 🟢 yes | 🔴 none | 🔴 paid, trial available |
| **Perigon** | commercial news API | 🟢 yes | 🟡 story grouping, no event clustering | 🟢 yes | 🔴 none | 🟡 150 req/month free, then $250+/mo |
| **Webz.io** | commercial news API, full text | 🟢 yes | 🔴 dedup is your problem | 🟢 yes | 🔴 none | 🔴 paid |
| **MBFC** | outlet bias + factuality ratings (one of Ground News' three sources) | 🟢 rates international outlets | — labels only | 🟢 rates German outlets | 🟡 **per outlet** | 🟡 API, paid tiers |
| **NewsGuard** | 0–100 trust scores, human-reviewed | 🟢 good European coverage | — labels only | 🟢 yes | 🟡 credibility, **not** political lean | 🔴 commercial |
| **NELA-GT** | static research dataset, ~1.8M articles/yr, 519 sources | 🔴 **English/US only** | 🔴 none | 🔴 none | 🟡 per outlet, from MBFC | 🟢 free |

---

## The ones worth acting on

**EMM** is the most interesting. It is the only system
found doing **cross-lingual cluster linking** — clustering within each language, then
linking clusters that describe the same event. That is exactly the architecture
[translation_problem.md](translation_problem.md) argues for. (Ground News translates and
then publishes English, but whether it clusters on the translation is undocumented, so it
is not a confirmed contrast case.) It also does framing/persuasion detection, which is
bias-adjacent even though it is not a left/right label. **Next step: email
`JRC-EMM-INFO@ec.europa.eu`** and ask what researchers can get.

**Ad Fontes** is the only provider that rates **individual articles** rather than outlets.
Every stance-prediction problem we have traces back to that gap, so it is worth asking
about a research licence — even a US-only article-level set would let us measure how far an
outlet label sits from an article label.

**CC-NEWS** is the answer to Event Registry's licensing problem: German full text we may
actually republish.

**NewsCatcher** is the only commercial API doing real event clustering, so it is the one
useful benchmark against our own `SequenceMatcher` approach.


---


## What none of them fill

- **Article-level stance outside Ad Fontes.**
- **German full text that is legally republishable** — CC-NEWS is the only candidate.
