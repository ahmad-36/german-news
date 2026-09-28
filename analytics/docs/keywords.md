# Keywords

Only Ground News was pulled by keyword. **GDELT, Event Registry and AllSides were pulled
by date**, so they have no keyword list.

---

## 1. What we used

### Topic pages — this is where most stories came from

Ground News has no date endpoint, so the crawl walks fixed pages every run. Three general
ones — the **homepage**, **`/top`**, **`/blindspot`** — plus 17 `/interest/<topic>` pages:

| | | |
|---|---|---|
| us-politics | ai | business-and-markets |
| environment-and-climate | health-and-medicine | international |
| tech | science | education_fb8947 |
| sports | entertainment | world |
| crime | economy | energy |
| law | media | |

No keyword is involved here. These 20 pages produced the bulk of the 894 stories.

⚠️ Six of the 17 need one manual check — see [problems #11b](problems.md).

### Search terms — 86, to reach what the topic pages miss

Used by `--query` and the discovery run.

| group | n | terms |
|---|---|---|
| **Government and parties** | 17 | `AfD` `CDU` `CSU` `SPD` `FDP` `Grüne` `Die Linke` `Bundestag` `Bundesrat` `Bundesregierung` `Bundesverfassungsgericht` `Koalition Deutschland` `Merz` `Friedrich Merz` `Bundeskanzler Merz` `Robert Habeck` `Lars Klingbeil` |
| **Policy** | 8 | `Heizungsgesetz` `Bürgergeld` `Asylpolitik Deutschland` `Migrationspolitik Deutschland` `Klimapolitik Deutschland` `Mindestlohn Deutschland` `Rentenreform Deutschland` `Wehrpflicht Deutschland` |
| **National events** | 5 | `Bundestagswahl` `Landtagswahl` `Streik Deutschland` `Inflation Deutschland` `Energiekrise Deutschland` |
| **EU / international** | 5 | `EU-Kommission` `Europäisches Parlament` `Europäische Union` `Emmanuel Macron` `Frankreich` |
| **Companies** | 11 | `Volkswagen` `BMW` `Audi` `Mercedes-Benz` `Bosch` `Siemens` `SAP` `BASF` `Bayer AG` `Allianz` `Deutsche Bank` |
| **Cities** | 8 | `Berlin` `Hamburg` `München` `Köln` `Frankfurt` `Stuttgart` `Leipzig` `Dresden` |
| **Sport** | 8 | `Bundesliga` `DFB` `FIFA Deutschland` `Bayern München` `Borussia Dortmund` `RB Leipzig` `deutsche Nationalmannschaft` `Olympia Deutschland` |
| **US / geopolitics / tech / climate** | 24 | `Trump` `US-Wahl` `US-Präsident` `Weißes Haus` `Republikaner` `Ukraine` `Selenskyj` `Kreml` `Bundeswehr` `NATO summit Germany` `EZB` `German economy` `interest rate Germany` `tariffs Germany` `recession Germany` `Künstliche Intelligenz` `KI` `semiconductor Germany` `data protection Germany` `Energiewende` `climate change Germany` `E-Auto` `Strompreis` `Brandmauer` |

Machine-readable: [`german_all.txt`](../../news-ground-news/keywords/german_all.txt),
[`german_politics.txt`](../../news-ground-news/keywords/german_politics.txt),
[`ground_news_interests.txt`](../../news-ground-news/keywords/ground_news_interests.txt).

---

## 2. How we picked them

**By hand**, aiming at the biggest named things in each area — the parties actually in the
Bundestag, the DAX companies, the eight largest cities, the clubs and bodies people follow
(Bundesliga, DFB, FIFA, Bayern, Dortmund). Named entities, not concepts.

**One rule came out of testing, not guesswork.** Ground News translates articles into
English and indexes the translation. So:

- A German **proper noun** survives and is findable in German — `Bundeswehr` → 10 hits.
- A German **common word** does not; the English title uses the English word —
  `Leitzins` → **0 hits**, while `interest rate Germany` → 8.

So proper nouns stay German; general concepts are written in English with "Germany" added.

Four terms still returned nothing — `Bundestagswahl` (no election in the window),
`Frankreich`, `Republikaner`, `Strompreis`. The last three break the rule above and should
be `France`, `Republicans`, `electricity price Germany`.

---

## 3. Extending the list

Two routes, neither tried yet: **EventKG** entity URIs, which avoid the translation problem
because an entity is language-independent; and **GDELT GKG themes**, for which a usable
German-politics set is already derived in
[collection_policy.md §2b](collection_policy.md#2b-which-gkg-themes-to-filter-on).
