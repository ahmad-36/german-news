# German Keywords and Crawl Targets

Everything used to find German coverage: the **topic pages** the Ground News crawl walks,
the **86 search terms** used to reach what those pages miss, and the **publisher register**
that decides what counts as German. Plus how the terms were chosen, how they performed, and
how to extend them.

§1 is the honest answer to "what do we actually crawl with" — most stories arrive through
the topic pages, not through keywords at all.

**Machine-readable copies** live in
[news-ground-news/keywords/](../../news-ground-news/keywords)
and, identically, in
[news-gdelt/keywords/](../../news-gdelt/keywords):

| file | contents |
|---|---|
| `german_politics.txt` | 30 terms — parties, institutions, policy, recurring events |
| `german_all.txt` | 86 terms — the above plus companies, cities, sport, EU, US/geopolitics |
| `german_politics_themes.txt` | 13 GDELT GKG theme codes, empirically derived |
| `ground_news_interests.txt` | the 17 Ground News topic pages the crawl walks |
| `german_keywords.json` | all of the above with measured per-term yield |

Both `.txt` files are directly usable as a collection filter:

```bash
python gdelt_dump_pull.py --start 2026-01-05 --end 2026-01-12 \
    --keywords-file keywords/german_politics.txt
```

---

## 1. What Ground News is actually crawled with

Three separate mechanisms, and they use different vocabularies. Only the second is a
"keyword list" in the usual sense, but all three decide what ends up in the dataset.

### A. Listing pages — the default crawl

`scraper.py` walks a fixed set of pages on every run and keeps stories with 3+ sources.
**This is what produces the bulk of the 894 stories**; no keyword is involved.

Three generic listings:

`ground.news/` (homepage) · `/top` · `/blindspot`

Seventeen `/interest/<slug>` topic pages — the topic filter for discovery:

| | | |
|---|---|---|
| `us-politics` ⚠️ | `ai` | `business-and-markets` |
| `environment-and-climate` | `health-and-medicine` | `international` |
| `tech` | `science` | `education_fb8947` |
| `sports` | `entertainment` | `world` ⚠️ |
| `crime` ⚠️ | `economy` | `energy` ⚠️ |
| `law` ⚠️ | `media` ⚠️ | |

> ⚠️ **Six of these seventeen need verifying.** Ground News disambiguates topic slugs with
> a hash suffix, and the dataset only ever contains the suffixed form for five of them —
> `us-politics_3c3c3c`, `crime_a31cae`, `energy_f044a6`, `law_086880`, `media_5b9bd3` —
> while `world` never appears at all. The crawl list uses the bare slug for these but the
> *suffixed* form for `education_fb8947`, which is inconsistent. Either the bare slug
> redirects (harmless) or those pages return nothing and six of seventeen topic feeds are
> silently empty. Worth one manual check; it would be a quiet recall loss.

### B. Search terms — the keyword list

86 German seed terms, used by `--query` and the discovery pipeline to find coverage the
listing pages miss. This is the list in §3, and the one to extend.

```bash
python scraper.py --query "Heizungsgesetz"
python discovery/german_discovery_run.py     # runs the whole list
```

### C. German-outlet filter — deciding what counts as German

Neither of the above filters by language, so German stories are identified *after*
scraping, by matching the publisher name against a register in `germanlib.py`:

| group | names |
|---|---|
| public broadcasters | 13 — Tagesschau, ZDF, Deutschlandfunk, … |
| major regional dailies | 13 — Rheinische Post, Kölner Stadt-Anzeiger, … |
| national quality dailies | 10 — FAZ, Süddeutsche Zeitung, Die Zeit, … |
| national magazines/portals | 9 — Der Spiegel, Stern, Focus, … |
| tabloids / mass media | 6 — Bild, B.Z., … |
| business & finance | 5 — Handelsblatt, WirtschaftsWoche, … |
| tech / digital | 4 — Heise Online, Golem.de, Netzpolitik.org |
| **total** | **60 distinct names** |

Plus 23 `KNOWN_GERMAN_SOURCE_SLUGS` used for a faster slug-level check.

Matching is word-level, not substring — a naive substring check made "BR" (Bayerischer
Rundfunk) match inside *Breitbart* and "stern" inside *Western Journal*. Two register
entries, `Express` and `Focus`, require an exact full-name match because they collide with
*Indian Express*, *Daily Express* and similar.

**This register is the real ceiling on German coverage.** 60 outlets is a small slice of
the German press; anything outside it is not counted as German even when it is.

---

## 2. The rule the search terms are built on

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

## 3. The search-term list

86 terms. ⚠️ marks the four that returned nothing (§4).

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

The mixed languages are deliberate, not sloppiness — see §2.

## 4. How the terms performed

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
four zero-hit terms, just milder. This is the §2 rule showing up a second time in the data:
the closer a term is to a common noun, the worse it travels through translation. Every one
of these should be replaced by its English form qualified with "Germany".

### The four terms that returned nothing — and why

| Term | Why it failed |
|---|---|
| `Bundestagswahl` | No federal election in the window. Genuinely absent, not a bad term — keep it for a range that includes one. |
| `Frankreich` | Generic country name; the English index says "France". **Violates the rule in §2** — should be `France` or `French politics`. |
| `Republikaner` | Same failure: English coverage says "Republicans". Should be `Republicans`. |
| `Strompreis` | Generic compound noun; English says "electricity price". Should be `electricity price Germany`. |

Three of the four are the *same mistake* — a generic German word where the English form
was needed. That is a strong confirmation of the §2 rule, and the fix is mechanical.

---

## 5. Discovered interest tags — the cheapest way to extend

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

## 6. Extending the list

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
the translation problem in §2 entirely — an entity is language-independent, and you can
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

## 7. How the list is used now

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
