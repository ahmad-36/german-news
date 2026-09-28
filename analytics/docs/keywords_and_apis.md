# Keywords, API Filters and Bounded Collection

What was used to select articles from each provider, and which filters each API offers.
The machine-readable keyword files are in the `gdelt/` and `ground-news/` folders, under
`keywords/`.

---

## 1. How each provider was selected

| provider | selected by | keyword list? |
|---|---|---|
| Ground News | 20 fixed pages + 86 search terms | ✅ below |
| GDELT | date range + 30-term keyword filter, or GKG themes | ✅ below |
| Event Registry | date range + `lang="deu"` + publisher in Germany | ❌ |
| AllSides | date range | ❌ (no search endpoint) |

---

## 2. Ground News

### Topic pages (most stories came from these)

The homepage, `/top`, `/blindspot`, plus 17 `/interest/` pages: `us-politics`, `ai`,
`business-and-markets`, `environment-and-climate`, `health-and-medicine`, `international`,
`tech`, `science`, `education_fb8947`, `sports`, `entertainment`, `world`, `crime`,
`economy`, `energy`, `law`, `media`.

⚠️ Six of these slugs may be silently empty. The data only contains hash-suffixed variants
(`us-politics_3c3c3c`), and `world` never appears. This needs one manual check.

### Search terms (86, `german_all.txt`)

| group | n | terms |
|---|---|---|
| Government, parties | 17 | AfD, CDU, CSU, SPD, FDP, Grüne, Die Linke, Bundestag, Bundesrat, Bundesregierung, Bundesverfassungsgericht, Koalition Deutschland, Merz, Friedrich Merz, Bundeskanzler Merz, Robert Habeck, Lars Klingbeil |
| Policy | 8 | Heizungsgesetz, Bürgergeld, Asylpolitik / Migrationspolitik / Klimapolitik / Mindestlohn / Rentenreform / Wehrpflicht Deutschland |
| National events | 5 | Bundestagswahl, Landtagswahl, Streik / Inflation / Energiekrise Deutschland |
| EU, international | 5 | EU-Kommission, Europäisches Parlament, Europäische Union, Emmanuel Macron, Frankreich |
| Companies | 11 | Volkswagen, BMW, Audi, Mercedes-Benz, Bosch, Siemens, SAP, BASF, Bayer AG, Allianz, Deutsche Bank |
| Cities | 8 | Berlin, Hamburg, München, Köln, Frankfurt, Stuttgart, Leipzig, Dresden |
| Sport | 8 | Bundesliga, DFB, FIFA Deutschland, Bayern München, Borussia Dortmund, RB Leipzig, deutsche Nationalmannschaft, Olympia Deutschland |
| US, geopolitics, tech, climate | 24 | Trump, US-Wahl, US-Präsident, Weißes Haus, Republikaner, Ukraine, Selenskyj, Kreml, Bundeswehr, NATO summit Germany, EZB, German economy, interest rate Germany, tariffs Germany, recession Germany, Künstliche Intelligenz, KI, semiconductor Germany, data protection Germany, Energiewende, climate change Germany, E-Auto, Strompreis, Brandmauer |

**How they were picked.** The terms were chosen by hand, targeting the largest named
entities in each area. Testing produced one rule. Ground News searches its English
translation, so **proper nouns stay German** (`Bundeswehr` → 10 hits) while **general
concepts must be English** (`Leitzins` → 0 hits, `interest rate Germany` → 8).

**Four terms returned nothing:** `Bundestagswahl` (there was no election in the window),
plus `Frankreich`, `Republikaner` and `Strompreis`. The last three break the rule and should
become `France`, `Republicans` and `electricity price Germany`.

---

## 3. GDELT

### Keyword filter (30 terms, `german_politics.txt`)

These are the German-politics subset of the list above, matched against article **titles**.
Matching is anchored only at the start of a word, because German compounds words:

| term | title | default | `--whole-word` |
|---|---|---|---|
| Bundestag | Bundestag**swahl** 2026 | ✅ | ❌ missed |
| Koalition | Koalition**svertrag** steht | ✅ | ❌ missed |
| SPD | SPDR ETF steigt | ⚠️ false positive | ✅ |

This trades precision for recall on purpose: a false positive is cheap to drop later, but
a missed article is gone.

### Theme filter (`german_politics_themes.txt`)

The theme set was derived by running the keyword filter for one week and keeping the GKG
themes that co-occur with it:

- **Use:** `USPEC_POLITICS_GENERAL1`, `GENERAL_GOVERNMENT`, `EPU_POLICY_GOVERNMENT`,
  `LEADER`, `USPEC_POLICY1`, `TAX_FNCACT_MINISTER`, `TAX_FNCACT_CHANCELLOR`, `ELECTION`,
  `EPU_POLICY_POLICY`, `EPU_POLICY_POLITICAL`, `LEGISLATION`, `EPU_POLICY_LAW`.
- **Avoid:** `TAX_ETHNICITY_GERMAN` and `TAX_WORLDLANGUAGES_GERMAN` (side effects of our own
  language filter), `ALLIANCE` (fires on almost everything), `CRISISLEX_*` and
  `UNGP_FORESTS_RIVERS_OCEANS` (low precision).

### Access routes and filters

| route | used? | filters | limit |
|---|---|---|---|
| **Raw 15-min dumps** | ✅ all our data | none on the server; we filter locally (`--keywords-file`, `--themes-file`, `--max-slots`) | bandwidth |
| BigQuery | no | full SQL | 1 TB/month free; the `Extras` column holds titles and is the expensive one |
| DOC 2.0 API | tried, abandoned | `sourcelang`, `sourcecountry`, `domain`, `theme`, `tone`, `near20:`, `repeat3:`, boolean, plus image filters (`imagetag`, `imageocrmeta`, `imagenumfaces`) | **250 results, no pagination, last 3 months** |

GDELT cannot filter on bias, paywall or body text. On the dump route it also cannot filter
on publisher country.

---

## 4. Event Registry

**What we used:** `lang="deu"`, `sourceLocationUri=Germany`, `dateStart` / `dateEnd`, and
optionally `sourceUri`, plus `allowUseOfArchive=False`.

**Available but unused:**

| filter | what it would fix |
|---|---|
| `conceptUri`, `categoryUri` (and adding them to `returnInfo`) | we collected **zero topics** |
| `startSourceRankPercentile` | drops the finance wires and local networks that cluster worst |
| `eventFilter=skipArticlesWithoutEvent` | removes singletons, but also the wire stories ER wrongly flags as duplicates |
| `keywords` + `keywordsLoc`, `authorUri`, `locationUri`, `dataType`, `ignore*` | keyword search, event location, excluding press releases |

⚠️ Setting `minSentiment` or `maxSentiment` silently restricts results to English.

**Cost:** 1 token per 100-article page. The free tier has 2,000 non-renewing tokens and a
30-day window. The archive costs 5 tokens per searched year.

---

## 5. Bounded collection (Sept 2026)

The Jan–Aug 2026 GDELT census cost **172 GB** of bandwidth for 1.4M articles with no text
and no labels, and 91% of the clusters were discarded afterwards. GDELT collection now
takes a date range plus a keyword or theme filter, and prints a warning before running
without one.

**Measured on one week** (2026-01-05 → 01-12, 30-term filter): 4,220 of 127,705 German
articles kept (3.3%), giving **273 stories with 3+ outlets** (median 4 outlets, max 48) in
about **10 minutes**. The six largest clusters are all genuine federal or state political
stories.

| range | est. articles | est. stories | run time |
|---|---|---|---|
| 1 week | 4,220 | 273 | 10 min |
| 3 months | ~55,000 | ~3,500 | ~2 h |
| Jan 2025 → now (~21 months) | ~384,000 | ~25,000 | ~15 h |

The run time scales with the date range, not with the filter, because every 15-minute file
still has to be downloaded. **Agree on the keyword list before a long run.**
