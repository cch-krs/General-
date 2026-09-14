# Flight watch — Dec 2026 NYC / Oahu / SF

A fork of the `flight-watch` skill's checker, carrying two changes the stock skill
does not make. The daily routine runs **this** copy; the skill's own copy is the
fallback and produces the older, thinner page.

Status page: https://claude.ai/code/artifact/e389354c-10fc-4dfe-8604-15a6aaa80728

## Why this fork exists

**1. It prices the fare class the rules actually allow.**
The trip rules say *"Nonstop, main cabin. Basic economy / Alaska Saver is not a
fare."* The stock checker takes Google's headline price, which on all six legs of
this trip is a Saver or Basic Economy fare — so every number on the page was for a
ticket that would not be bought. This fork makes a second SerpApi call per leg-date
(`booking_token`) to read the whole fare ladder, and decides on the cheapest true
main-cabin fare. Both numbers are tracked: main cabin drives every tripwire, the
headline fare stays on the page for context and because Google's price history is
built on it.

On 2026-09-11 that was a $185 difference on Option A ($882 headline vs $1,067 main
cabin) and enough to put two legs over their $450 ceilings.

**2. It links to the specific flight, not the route.**
The same booking call returns a Google Flights URL whose `tfs` parameter encodes the
exact flight (carrier, number, date), so the route code on each leg opens that
itinerary rather than a fresh search that may no longer show it.

**3. It says whether the fare still has room to fall.**
A ceiling breach alone is not an instruction to book, so each tripwire is judged
against the evidence for the fare that breached it. A breach expected to ease is
`HOLD`; a breach that is not is `BOOK_NOW`. The decision date is never softened —
once it arrives, the call is always `BOOK_NOW`.

### What the outlook is built from

Every signal is measured. Nothing is inferred from a model of how airfares behave.

| Signal | Source |
|---|---|
| low / typical / high | Google's own `price_level` for that exact route + date |
| position in the typical range | `typical_price_range`, as a percentile |
| direction of travel | ~60 days of Google's tracked `price_history` |
| how today compares to that history | share of readings below today's fare |
| time pressure | days to departure — holiday fares firm up inside six weeks |

Signals sum to a score: below zero leans against a further drop, at or above two
leans toward one. The bands are `drop unlikely` / `drop possible` / `drop likely`.
**No percentage is reported** — none of this is a calibrated probability, and a
number would imply more than the evidence supports.

The insights describe the cheapest fare on the flight, which is what moves the
main-cabin fare with it; the page says so rather than hiding the mismatch.

## Decision table

| Situation | Call |
|---|---|
| Decision date reached | `BOOK_NOW` — never softened |
| Ceiling or drift breached, that fare's outlook is `drop unlikely` | `BOOK_NOW` |
| Ceiling or drift breached, a drop is possible or likely | `HOLD` |
| An option's total fell by the drop alert | `GOOD_SIGN` |
| Nothing moved | `WAIT` — page timestamp is the only record |
| A leg could not be priced | `CHECK_FAILED` — never a guessed fare |

`HOLD` is new, and it notifies: a broken ceiling is news even when the answer is to
keep waiting.

## Schedule

Mon / Wed / Fri at 13:02 UTC, plus a one-shot on Nov 1 (the decision date, which
falls on a Sunday). `references/schedule.md` has the measurement behind that: there
is no cheap weekday to search — the spread across weekdays is smaller than 89% of
random shuffles — but fares are measurably less likely to fall over a weekend, so
the three-day gap is parked there. Budget settles the rest: 14 searches a check
against a free 250/month tier makes daily impossible and Mon/Wed/Fri comfortable.

## Layout

```
scripts/flight_watch.py       check | seed | render | init — stdlib only
assets/page.template.html     status page, with the "Will it drop?" section
assets/config.template.json
references/                   config guide + the routine prompt
```

Config gains `baseline_main` per leg and `baseline_total_main` per option, seeded on
the first run that reads main-cabin fares. Main-cabin baselines cannot be
back-derived from the September headline baselines, so drift is measured from the
day they were seeded.

## How the routine gets this code

A routine-fired session has no GitHub credentials, so it cannot clone this repo — on
2026-09-11 a rehearsal proved it: the run fell back to the skill's stock script and
republished basic-economy fares over the main-cabin page without erroring. So
`scripts/flight_watch.py` and `assets/page.template.html` are **published as
supporting files on the artifact itself**, and each run reads them exactly the way it
already reads `config.json`. The repo stays the source of truth for humans and
review; the artifact is the delivery channel for the run.

**When you change the script here, republish it to the artifact** — otherwise the
daily run keeps executing the old copy. The run's own republish omits those two files
from its `files` map, so they are preserved rather than overwritten.

## Running it by hand

```bash
cd site                     # holds config.json + history.json from the artifact
python3 scripts/flight_watch.py check --config config.json --out . --history history.json
```

Exit 0 priced, exit 2 `CHECK_FAILED`. `FLIGHT_WATCH_MOCK=wait|drop|tripwire|fail`
exercises every path without spending API calls; `FLIGHT_WATCH_NO_BOOKING=1` skips
the fare-ladder call and falls back to headline fares.

API cost is two SerpApi calls per leg-date — 16 per run for this trip.
