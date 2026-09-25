# Ground News' Translation Loses Entities

**Summary.** Ground News machine-translates non-English articles into English. The
translation systematically destroys proper nouns: person surnames that are homographs of
common German words, club names that collide with place names, and the token `USA`. We can
measure this because Ground News stores the pre-translation string in `original_title`
alongside the translated `title`.

> ### What this does and does not show
>
> **Established.** 41.2% of articles are machine-translated; the translation deletes the
> entities listed in §3; and at least one story's **topic tags** are wrong in a way that
> only makes sense if the tagger read the translated text (§2).
>
> **Not established: that Ground News clusters on the translation.** Ground News does not
> document how it groups articles into stories, and nothing in the scraped record reveals
> it. The order of translate and cluster is unknown.
>
> **There is even mild counter-evidence.** The worked example in §2 is a *coherent*
> 15-article cluster whose English titles are badly mangled. If the clustering key were
> the translated title, that cluster should have fragmented. It did not — which is what
> you would expect if clustering ran on the original language, on URLs, or on a vendor's
> event IDs.
>
> So the finding is about **translation quality and its effect on the published record and
> on downstream tagging**, not a proven indictment of translate-then-cluster. The
> architectural argument in §4 is a hypothesis this data motivates, not one it confirms.

---

## 1. Scale of translation in the corpus

| | articles |
|---|---|
| Total articles | 46,030 |
| **Machine-translated** (`original_title` non-empty) | **18,969 (41.2%)** |
| German-tagged and translated | 5,224 records → **4,167 distinct titles** |

Top source languages by translated count: `de` 5,224 · `es` 4,330 · `fr` 1,884 ·
`pt` 925 · `nl` 657 · `it` 504 · `ro` 466 · `hu` 385 · `ru` 381 · `el` 342.

So translation is not an edge case in this corpus — it touches **two articles in five**,
and it is the majority condition for every non-English language.

---

## 2. The worked example — one cluster, four compounding failures

Story: **"Not at All Noticed: Urbig Avoids Questions About the New Succession at FC Bayern
and in the DFB Team"** — 15 sources, all German. The story is about Bayern Munich
goalkeeper **Jonas Urbig** succeeding **Manuel Neuer**.

| German original | Ground News English |
|---|---|
| Urbig soll **Neuer** schon diese Saison mehr und mehr beerben | Urbig Should **Newer** Inherit More and More This Season |
| Urbig weicht Fragen zur **Neuer-Nachfolge** beim FC Bayern | Urbig Avoids Questions About the **New Succession** at FC Bayern |
| Urbig überrascht mit Aussage zum **Neuer-Abschied** | Urbig Surprises with a Statement About the **New Farewell** |
| **Neuer** vor letzter Saison? Urbig reagiert überraschend | **New** Before Last Season? Urbig Reacts Surprisingly |
| **Bayern** und DFB-**Tor**: Urbig überrascht … | **Bavaria** and DFB **Gate**: Urbig Surprises … |
| **Thronwechsel bei Bayern?** Urbig hat "kein Modell ausgearbeitet" | **Change of Throne in Bavaria?** Urbig Has "No Model Worked Out" |
| Chancen auf Platz im **Nationaltor**? | Chances at the **National Gate**? |

Four distinct failures, compounding:

1. **`Neuer` → "new" / "newer".** The surname of the person the story is *about* is read
   as the German comparative adjective *neuer* and translated away. In four of the seven
   titles above, the central entity has been deleted from the English text entirely.
2. **`Bayern` → "Bavaria".** The football club becomes the federal state.
3. **`Tor` → "Gate".** The goal (football) becomes a gate; `DFB-Tor` → "DFB Gate",
   `Nationaltor` → "National Gate".
4. **Downstream topic tagging is poisoned.** This cluster's topic tags are
   **`Mohammed Bin Salman`**, `Bayern Munich`, `Munich`. A Bundesliga goalkeeper story is
   tagged with the Saudi crown prince — a tagging decision made on text in which the
   subject's name no longer appears.

The cluster survived only because `Urbig` is not a German word. Had the goalkeeper been
named Weber or Koch, there would be no cluster left to inspect.

---

## 3. Quantification

**Counting rule.** All counts below are on **distinct original titles**, not records — the
same article recurs across stories, so 5,224 German records hold only **4,167 distinct
titles**. Percentages are of those 4,167.

**A caveat that matters.** A naive regex badly overcounts surname loss. Searching
`\bNeuer\b` returns 33 hits, but **26 of them are the ordinary German adjective** *neuer*
("new") in sentence-initial position — *"Neuer Angriff auf Kiew"* → "New Attack on Kyiv",
correctly translated. The same trap catches `Sommer` (almost always the season) and `Kurz`
(almost always "shortly"). Every figure below is context-gated, and
[`scripts/translation_audit.py --show`](../scripts/translation_audit.py) prints every match
for inspection rather than asking you to trust the count.

### Measured defect rates

| Defect | Distinct titles | % of 4,167 |
|---|---|---|
| **`USA` / `US-` degraded to `Us` / `Usa`** | **96** | **2.3%** |
| `Bayern` → `Bavaria` (total) | 18 | 0.4% |
| — of which the **football club** (wrong) | 3 | |
| — of which the federal state (correct) | 15 | |
| Coalition colour shorthand translated as colours | 5 | 0.1% |
| Surname `Neuer` erased | 4 | 0.1% |
| Luxembourgish tagged `lang=de`, left untranslated | 4 | 0.1% |

**These are small numbers, and should be presented as such.** The corpus has only 4,167
distinct German titles to begin with. What the audit establishes is the *existence and
mechanism* of each defect, verified case by case — not that translation failure is
statistically dominant in this dataset. The claim to make in a paper is architectural, not
epidemiological.

### 3a. `USA` / `US-` → `Us` — the most frequent defect

96 titles (2.3%) degrade `USA` or the prefix `US-` into `Us`, `Usa` or `u.s.`. After
title-casing, the highest-salience geopolitical token in the headline becomes an English
stopword pronoun.

| German | Ground News English |
|---|---|
| **US**-Militär: Kuwait schießt versehentlich drei **US**-Kampfjets ab | **Us** Military: Kuwait Accidentally Shoots Down Three **Us** Fighter Jets |
| **USA**-Iran-Krieg: Kuwait soll **US**-Kampfjets versehentlich abgeschossen haben | **Usa**-Iran War: Kuwait Reportedly Shot Down **Us** Fighter Jets |
| Insider der **US**-Regierung zweifeln an Regimewechsel | Insiders of the **Us** Government Doubt Regime Changes |

### 3b. `Bayern` → `Bavaria` — a collapsed distinction

18 titles render `Bayern` as `Bavaria`. In **15 of those the translation is correct** —
they are about Bavarian state politics (*"Dritter AfD-Abgeordneter in Bayern wird vom
Verfassungsschutz beobachtet"*). In **3 it is wrong**: the football club becomes the
federal state.

| German | Ground News English |
|---|---|
| **Bayern** und DFB-**Tor**: Urbig überrascht mit Aussage zum Neuer-Abschied | **Bavaria** and DFB **Gate**: Urbig Surprises with a Statement About the New Farewell |
| Fußball-Rekordmeister: DFB-Stars starten in **Bayern**-Vorbereitung | Football Record Champions: DFB Stars Start in **Bavaria** Preparation |

The interesting failure is not the 3 errors but the collapse: club stories and state
stories become **lexically indistinguishable** to the clusterer, because both produce the
token "Bavaria".

### 3c. Surname `Neuer` erased — 4 titles, all in one cluster

All four are the Urbig story in §2. Small, but it is the cleanest demonstration available
that the translation can delete the article's central entity, and it is verified by hand.

### 3d. Coalition colour shorthand — 5 titles

German coalition names are party colours. Translated literally, they stop referring to
anything:

| German | Ground News English | Actually means |
|---|---|---|
| **Schwarz-Rot** ist ein Projekt für acht Jahre | **Black-Red** Is a Project for Eight Years | CDU/CSU–SPD coalition |
| Erfolg für **Schwarz-Rot** | Success for **Black and Red** | as above |
| Spekuliert Merz … auf **Schwarz-Grün**? | Speculate on **Black and Green**? | CDU/CSU–Greens |
| Bedingung für **Rot-Rot-Grün** in Berlin | Condition for **Red-Red-Green** in Berlin | SPD–Linke–Greens |

An English-language clusterer has no way to connect "Black-Red" to a German governing
coalition, so these headlines cannot cluster with English-language coverage of the same
government.

### 3e. Language misidentification → translation does not run

`rtl.lu` publishes in **Luxembourgish**, which Ground News tags `lang: de`. The translator,
handed Luxembourgish as German, passes most of it through untouched. 4 distinct titles:

| Original (Luxembourgish) | Ground News "English" |
|---|---|
| **Op Kreta: Zwee Pompjeeë stierwe** bei Bekämpfung vun engem **Bëschbrand** | **Op Crete: Zwee Pompjeeë Stierwe** in the Fight Against **Strong Fire** |
| **Futtball WM ouni europäesch Ekippen?** UEFA **dreet** der FIFA **mat** Boykott | **Futtball World Cup Ouni European Tipping?** UEFA **Dreet** the FIFA **Mat** Boycott |

*Zwee Pompjeeë stierwe* = "two firefighters die"; *Bëschbrand* = "forest fire", rendered
"Strong Fire". The English title contains neither "firefighters" nor "wildfire" — yet the
story it sits in is titled *"2 firefighters die in a wildfire on the southern Greek island
of Crete"*, with which it shares **no content words at all**. Only 4 articles, but the
mechanism generalises to every minority language mis-tagged as a major one.

## 4. Why this matters beyond Ground News

*This section is the hypothesis the measurements motivate — see the box at the top for
which parts are established.*

**If** a pipeline is ordered **translate → cluster → tag → label**, each stage consumes the
previous stage's output, so a translation error is never corrected downstream — it is
amplified:

```
translate     Neuer ──────────► "new"
cluster       clustering key loses the story's central entity   ← unverified for Ground News
tag           topic tagger, reading "new", assigns Mohammed Bin Salman   ← observed
label         stance labels attach to a cluster that may be the wrong cluster
```

Only the *tag* step is directly evidenced here. Three consequences worth stating in a
paper, if the architecture is confirmed:

1. **Recall loss is invisible.** We can see the articles that were wrongly *kept together*
   because we have `original_title`. We cannot see the articles that were wrongly *split
   apart*, and there is no reason to think that number is smaller.
2. **The loss is concentrated on named entities**, which is precisely the signal that
   cross-lingual event clustering relies on most.
3. **Cluster-then-translate would not have this failure mode.** Clustering in the source
   language and translating only for presentation preserves `Neuer` as an unmatched token
   — unglamorous, but correct. This is a directly testable architectural claim, and it is
   the architecture the JRC's Europe Media Monitor (EMM) uses: cluster within each
   language, then link clusters across languages. EMM is live and covers 80 languages —
   see [other_sources.md](other_sources.md).

### Honest limits of this evidence

- **We never observe the clustering step.** Everything here is measured on the published
  record — titles and tags. The clustering mechanism is a black box, so any claim about
  *when* translation happens relative to clustering is inference.
- **The rates are low** — the largest single defect is 2.3% of distinct German titles.
  This is a demonstration of a mechanism, not a claim that Ground News clustering is
  broadly broken.
- **Only titles are auditable.** `original_description` exists too, but body text does
  not, so we cannot measure translation quality on the text that matters most.
- **We can only see one direction of the error.** Wrongly-merged clusters are visible;
  wrongly-split ones are not, and are probably more numerous.
- **Only German was audited in depth.** Spanish (4,330 translated records), French
  (1,884) and the other 40+ languages are unexamined and would likely show
  language-specific analogues.

---

## 5. Reproducing these numbers

All figures come from `data/ground_news/ground_news.jsonl` in
[`ahmad-36/news`](https://github.com/ahmad-36/news) (894 stories, 46,030 articles,
scraped 2025-05 → 2026-08). Each article carries both `title` (translated) and
`original_title` (source language, empty when no translation occurred).

```bash
python scripts/translation_audit.py --data data/ground_news/ground_news.jsonl
```

See [`scripts/translation_audit.py`](../scripts/translation_audit.py) in this repo.
