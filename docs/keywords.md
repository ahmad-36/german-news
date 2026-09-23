# The German Keyword List

The seed terms used to discover German coverage on Ground News, how they were chosen,
how they performed, and how to extend them.

**Machine-readable copies** live in
[news-ground-news/keywords/](https://github.com/ahmad-36/news-ground-news/tree/main/keywords)
and, identically, in
[news-gdelt/keywords/](https://github.com/ahmad-36/news-gdelt/tree/main/keywords):

| file | contents |
|---|---|
| `german_politics.txt` | 30 terms — parties, institutions, policy, recurring events |
| `german_all.txt` | 86 terms — the above plus companies, cities, sport, EU, US/geopolitics |
| `german_politics_themes.txt` | 13 GDELT GKG theme codes, empirically derived |
| `german_keywords.json` | all of the above with measured per-term yield |

Both `.txt` files are directly usable as a collection filter:

```bash
python gdelt_dump_pull.py --start 2026-01-05 --end 2026-01-12 \
    --keywords-file keywords/german_politics.txt
```

---

## 1. The rule the list is built on

This is the part worth carrying over to any extension, because it was established
empirically rather than assumed:

> **Proper nouns survive translation. Generic concepts do not.**
>
> Ground News translates non-English articles into English and indexes the translation.
> A German *proper noun* — a person, party, named law or institution — appears verbatim in
> the English title, so searching the German form finds it: `Bundeswehr` → 10 events.
>
> A German *generic or abstract* word does not survive: the English title uses the English
> word. `Leitzins` → **0 events**. The English phrase, qualified with "Germany", does work:
> `interest rate Germany` → 8 events, 2 matched interests.

**So: keep proper nouns in German; translate generic concepts into English and qualify
them with "Germany".** That is why the list mixes languages — `Heizungsgesetz` and
`Bundesverfassungsgericht` sit next to `interest rate Germany` and `German economy`.

This is the same translate-then-index architecture documented in
[translation_problem.md](translation_problem.md), seen from the query side rather than
the clustering side.

---

## 2. The list

86 terms. ⚠️ marks the four that returned nothing (§3).

| group | n | terms |
|---|---|---|
| **Government, parties, institutions** | 17 | `AfD` · `Bundeskanzler Merz` · `Bundesrat` · `Bundesregierung` · `Bundestag` · `Bundesverfassungsgericht` · `CDU` · `CSU` · `Die Linke` · `FDP` · `Friedrich Merz` · `Grüne` · `Koalition Deutschland` · `Lars Klingbeil` · `Merz` · `Robert Habeck` · `SPD` |
| **Public policy and legislation** | 8 | `Asylpolitik Deutschland` · `Bürgergeld` · `Heizungsgesetz` · `Klimapolitik Deutschland` · `Migrationspolitik Deutschland` · `Mindestlohn Deutschland` · `Rentenreform Deutschland` · `Wehrpflicht Deutschland` |
| **Recurring national events** | 5 | `Bundestagswahl` ⚠️ · `Energiekrise Deutschland` · `Inflation Deutschland` · `Landtagswahl` · `Streik Deutschland` |
| **EU and international** | 5 | `EU-Kommission` · `Emmanuel Macron` · `Europäische Union` · `Europäisches Parlament` · `Frankreich` ⚠️ |
| **Companies and industry** | 11 | `Allianz` · `Audi` · `BASF` · `BMW` · `Bayer AG` · `Bosch` · `Deutsche Bank` · `Mercedes-Benz` · `SAP` · `Siemens` · `Volkswagen` |
| **Cities** | 8 | `Berlin` · `Dresden` · `Frankfurt` · `Hamburg` · `Köln` · `Leipzig` · `München` · `Stuttgart` |
| **Sport** | 8 | `Bayern München` · `Borussia Dortmund` · `Bundesliga` · `DFB` · `FIFA Deutschland` · `Olympia Deutschland` · `RB Leipzig` · `deutsche Nationalmannschaft` |
| **US, geopolitics, tech, climate** | 24 | `Brandmauer` · `Bundeswehr` · `E-Auto` · `EZB` · `Energiewende` · `German economy` · `KI` · `Kreml` · `Künstliche Intelligenz` · `NATO summit Germany` · `Republikaner` ⚠️ · `Selenskyj` · `Strompreis` ⚠️ · `Trump` · `US-Präsident` · `US-Wahl` · `Ukraine` · `Weißes Haus` · `climate change Germany` · `data protection Germany` · `interest rate Germany` · `recession Germany` · `semiconductor Germany` · `tariffs Germany` |

The mixed languages are deliberate, not sloppiness — see §1.

## 3. How the terms performed

From the discovery run of 2026-08-06/07 (`german_discovery_candidates.jsonl`, 880
candidate stories):

| | |
|---|---|
| Terms searched | 86 |
| **Terms that returned results** | **82 (95%)** |
| Terms that returned nothing | 4 |
| Candidate stories found | 880 |
| Ground News *interest tags* discovered | 77 |

**Yield per term is not a useful ranking signal**, because Ground News' search preview
caps at **10 results**, and **76 of the 82 productive terms hit that ceiling exactly**.
Only `AfD` and `CDU` exceeded it (20 each, via a second route). So the informative signal
is close to binary: did the term return anything at all?

The four terms that returned results but stayed *below* the cap are the only ones where
the count carries information — they are genuinely thin rather than truncated:

| term | hits | literal meaning | what English coverage says instead |
|---|---|---|---|
| `Bundesregierung` | 1 | federal government | "German government" |
| `Landtagswahl` | 3 | state election | "state election" / "regional election" |
| `Bürgergeld` | 7 | citizen's income | "unemployment benefit", "welfare reform" |
| `Bundesverfassungsgericht` | 9 | Federal Constitutional Court | "Constitutional Court" |

**All four are generic German compounds, not proper nouns** — the same failure mode as the
four zero-hit terms, just milder. This is the §1 rule showing up a second time in the data:
the closer a term is to a common noun, the worse it travels through translation. Every one
of these should be replaced by its English form qualified with "Germany".

### The four terms that returned nothing — and why

| Term | Why it failed |
|---|---|
| `Bundestagswahl` | No federal election in the window. Genuinely absent, not a bad term — keep it for a range that includes one. |
| `Frankreich` | Generic country name; the English index says "France". **Violates the rule in §1** — should be `France` or `French politics`. |
| `Republikaner` | Same failure: English coverage says "Republicans". Should be `Republicans`. |
| `Strompreis` | Generic compound noun; English says "electricity price". Should be `electricity price Germany`. |

Three of the four are the *same mistake* — a generic German word where the English form
was needed. That is a strong confirmation of the §1 rule, and the fix is mechanical.

---

## 4. Discovered interest tags — the cheapest way to extend

The discovery run also surfaced **77 Ground News interest tags** attached to matched
stories. These are the platform's own topic vocabulary and are the most natural source of
additional terms:

`alternative-for-germany-afd` (11) · `far-right` (3) · `cdu` · `deutsche-welle` ·
`european-union` · `german-politics` · `united-states-economy` · `us-immigration` ·
`fifa` · `bayern-munich` · `borussia-dortmund` · `die-linke` · `friedrich-merz` ·
`emmanuel-macron` · `kremlin` · `nato` · `g7-summit` · `inflation` · `formula-1` · …

### ⚠️ They need filtering before use

The tag matcher disambiguates badly on place names. Real tags returned for German city
terms include:

`berlin-maryland` · `dresden-ontario` · `hamburg-new-york` · `san-german-san-german` ·
`kiribati` · `inflation-reduction-act` · `a-and-e` · `e-news`

So `Berlin`, `Hamburg` and `Dresden` all pull in US/Canadian namesakes. Any extension
from this list should either (a) drop bare city names in favour of
`Berlin Germany`-style qualified forms, or (b) post-filter on the story's `place` field,
which the discovery pipeline already records.

---

## 5. Extending the list

### From GDELT GKG themes — concrete, already derived

The supervisor's suggestion to source topics from GDELT categories works, but the raw
theme vocabulary is noisy and needs curation. We derived a usable set empirically: run
the keyword filter over one week, then take the themes that co-occur with it.

**Recommended** (share of keyword-matched articles carrying the theme):

| theme | share |
|---|---|
| `USPEC_POLITICS_GENERAL1` | 162% |
| `GENERAL_GOVERNMENT` | 146% |
| `EPU_POLICY_GOVERNMENT` | 142% |
| `LEADER` | 88% |
| `TAX_FNCACT_MINISTER` | 74% |
| `TAX_FNCACT_CHANCELLOR` | 71% |
| `ELECTION` | 60% |
| `EPU_POLICY_POLICY` | 59% |
| `EPU_POLICY_POLITICAL` | 35% |
| `LEGISLATION` | 29% |

(Themes are multi-valued, so shares exceed 100%.)

**Do not use**, despite high frequency:

| theme | why |
|---|---|
| `TAX_ETHNICITY_GERMAN`, `TAX_WORLDLANGUAGES_GERMAN` | artefacts of the German-language filter itself, not subject matter |
| `ALLIANCE` | fires on 183% of articles — no discriminative value |
| `CRISISLEX_CRISISLEXREC`, `CRISISLEX_C07_SAFETY` | generic crisis lexicon, very low precision |
| `UNGP_FORESTS_RIVERS_OCEANS` | fires at 62% on political text; miscalibrated |

Shipped as `keywords/german_politics_themes.txt`.

### From EventKG

Not yet tried. EventKG would give entity URIs rather than surface strings, which sidesteps
the translation problem in §1 entirely — an entity is language-independent, and you can
render whichever surface form each provider indexes. Worth a trial specifically for the
three terms that failed for surface-form reasons.

The same argument applies to Event Registry's `conceptUri`, which is an entity-level
filter we are not currently using ([api_filters.md](api_filters.md)).

### Mechanical next steps

1. **Fix the three broken terms**: `Frankreich` → `France`, `Republikaner` → `Republicans`,
   `Strompreis` → `electricity price Germany`.
2. **Qualify the bare city names** to stop the `berlin-maryland` class of match.
3. **Fold in the discovered interest tags**, after filtering per §4.
4. **Extend per topic area as the organisers decide the scope** — the list is currently
   heavy on federal politics and light on regional politics, courts, and health.

---

## 6. How the list is used now

Originally a Ground News *search* input. It is now also a GDELT *collection filter*, which
is how GDELT collection is bounded instead of run as a census:

```bash
python gdelt_dump_pull.py --start 2026-01-05 --end 2026-01-12 \
    --keywords-file keywords/german_politics.txt
```

Measured selectivity over 2026-01-05 → 2026-01-12: **1.9% of German articles kept**.

**One caveat on matching.** German compounds and inflects, so strict word-boundary
matching under-matches — it misses `Bundestag` inside *Bundestagswahl* and `Grüne` inside
*Die Grünen*. The matcher therefore anchors only the left edge of a term by default: it
must start a word but may continue. The cost is that `SPD` also matches *SPDR*.
`--whole-word` restores strict matching.
