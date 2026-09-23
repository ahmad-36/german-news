# Collection Policy: Bounded, Not Census

**Decision (Sept 2026): stop collecting at scale.** The default is now a short date range
plus a topic or keyword filter. This documents why, what changed in the code, and a
measured end-to-end test of the new mode.

---

## 1. Why the census was the wrong default

| | Census (Jan–Aug 2026) | Bounded week (2026-01-05 → 01-12) |
|---|---|---|
| Bandwidth | **172 GB** | a few GB |
| Wall clock | ~5 h at 8 workers | **~10 minutes** |
| GKG slots | 20,350 | 672 |
| German articles kept | 1,408,753 | **4,220** |
| Stories (3+ outlets) | 173,388 | **273** |
| On-disk output | ~5 GB raw, 2.6 GB clustered | 3.6 MB |

The census produced 1.4M German articles with **no body text and no bias labels**, of
which a small fraction has ever been used. It also produced 2,015,373 raw clusters that
had to be cut to 173,388 by a `--min-outlets 3` filter — i.e. 91% was discarded after
paying full price for it.

Nothing about the research questions required a census. Every task in
[tasks.md](tasks.md) operates on stories within a topic; none needs exhaustive coverage of
all German news.

---

## 2. What changed

`gdelt_dump_pull.py` gained filtering. Previously the only knobs were `--start`, `--end`
and `--workers`; the German-language filter was hard-coded and nothing else was
selectable.

```bash
# the new default way to run it
python gdelt_dump_pull.py --start 2026-01-05 --end 2026-01-12 \
    --keywords-file keywords/german_politics.txt

# by GKG theme instead
python gdelt_dump_pull.py --start 2026-01-05 --end 2026-01-12 \
    --themes-file keywords/german_politics_themes.txt

# bound an exploratory run
python gdelt_dump_pull.py --start ... --end ... --max-slots 20 --keywords-file ...
```

| flag | effect |
|---|---|
| `--keywords`, `--keywords-file` | keep articles whose **title** matches any term |
| `--themes`, `--themes-file` | keep articles whose **GKG V2Themes** match any code |
| `--whole-word` | strict word matching (default allows German compounds) |
| `--max-slots N` | stop after N 15-minute slots |

Filters are OR-ed. **With no filter the script prints a warning** that it is about to run
a full census, so the expensive mode can no longer be entered by accident.

### German matching is not the obvious thing

Strict word-boundary matching under-matches German badly, because the language compounds
and inflects. The default therefore anchors only the **left** edge of a term.

| term | title | default | `--whole-word` |
|---|---|---|---|
| `Bundestag` | Bundestagswahl 2026 | ✅ | ❌ missed |
| `Grüne` | Die Grünen fordern | ✅ | ❌ missed |
| `Koalition` | Koalitionsvertrag steht | ✅ | ❌ missed |
| `SPD` | SPDR ETF steigt | ⚠️ false positive | ✅ rejected |
| `AfD` | Schafdorf brennt | ✅ rejected | ✅ rejected |

The trade is recall for precision, and German compounding makes recall the right side to
favour for a collection filter — a false positive is cheap to drop later, a missed article
is gone.

---

## 3. Measured end-to-end test

One week, 2026-01-05 → 2026-01-12, filtered with the 30-term
[`german_politics.txt`](keywords.md):

```
672 GKG slots, 8 workers
Filter: 4,220 kept of 127,705 German articles seen (3.30%)
Clustered: 273 stories with >=3 independent outlets
```

### Cluster quality

| | |
|---|---|
| Outlets per story | median **4**, mean 7.6, max **48** |
| Articles per story | median 6, mean 9.3, max 62 |
| Stories with ≥5 outlets | 132 (48%) |
| Stories with ≥10 outlets | 66 (24%) |

Top outlets: welt.de (90) · zeit.de (78) · merkur.de (67) · az-online.de (62) ·
finanznachrichten.de (59) · hna.de (56) · rga.de (55) · n-tv.de (55).

### The largest clusters, as a precision check

| outlets | story |
|---|---|
| 48 | CSU für Autoführerschein ab 16 Jahren |
| 38 | Nach Bruch der Koalition — BSW-Fraktion wird AfD-Antrag für Neuwahl zustimmen |
| 34 | Mission Stimmungswechsel — welche Sorgen die CSU 2026 plagen |
| 33 | Kinder: CSU-Papier: Auch kriminelle Kinder unter 14 vor Gericht stellen |
| 32 | Brandenburger Landtag lehnt Neuwahl ab — BSW stimmt mit AfD |
| 32 | Übergibt Haseloff an Schulze? CDU setzt vor Wahl auf Wechsel |

All six are genuine German federal/state political stories with real cross-outlet
coverage. **A single filtered week produces 273 usable multi-outlet stories** — enough to
prototype every task in [tasks.md](tasks.md) that does not need bias labels.

---

## 4. What this implies for scope

The organisers will set the final date range and topic list; the plan mentioned possibly
starting from **January 2025**. Extrapolating the measured week linearly:

| range | weeks | est. articles | est. stories (3+ outlets) |
|---|---|---|---|
| 1 week | 1 | 4,220 | 273 |
| 1 month | ~4.3 | ~18,000 | ~1,200 |
| 3 months | 13 | ~55,000 | ~3,500 |
| **Jan 2025 → now (~21 months)** | ~91 | **~384,000** | **~25,000** |

Caveats on the extrapolation: news volume is not flat (election periods spike), and GDELT
coverage before 2026 may be thinner. Treat these as an order of magnitude.

Even the full 21-month range under a topic filter is **~27% of the census article count**
and far more usable, because every article in it is on-topic. The cost driver is bandwidth
per slot, which does not fall with filtering — **672 slots must still be downloaded per
week regardless of how few articles survive**. So wall-clock scales with the date range,
not the filter: ~21 months is roughly 91 × 10 min ≈ **15 hours**, which should be run
deliberately and once, with `--resume`.

### Recommended before committing to a long range

1. **Agree the keyword list first** — see [keywords.md](keywords.md) §5 for the four
   broken terms and the extension routes. Re-running a long pull because the term list was
   wrong is the expensive mistake to avoid.
2. **Run one week per candidate topic area**, not one long range per topic. A week is
   ~10 minutes and tells you the yield and the cluster quality for that vocabulary.
3. **Decide whether bodies are needed.** GDELT gives no text; enrichment is a second crawl
   against the outlets and is the real cost driver for anything text-based.
