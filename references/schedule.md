# Why the watch runs Mon / Wed / Fri

Measured on 2026-09-14 from Google's own `price_history` for all six legs of this
trip: **368 daily observations, 2026-07-16 to 2026-09-14**, six independent
route/date series, each normalised by its own median so legs at different price
levels pool fairly.

## There is no cheap day to search

| Observed on | Rel. price (1.00 = median) | vs avg | P(cheaper than previous day) | Avg move |
|---|---|---|---|---|
| Mon | 0.963 | −3.7% | 17% | −$8.7 |
| Tue | 0.959 | −4.1% | 12% | +$2.4 |
| Wed | 0.975 | −2.5% | 17% | +$1.2 |
| Thu | 0.958 | −4.2% | 22% | −$1.8 |
| Fri | 0.971 | −2.9% | 15% | +$1.8 |
| Sat | 0.992 | −0.8% | 6% | +$4.8 |
| Sun | 0.988 | −1.2% | 11% | −$2.0 |

The spread between the best and worst weekday is 3.4% of the median fare — and a
spread that large **appears in 89% of 4,000 random shuffles** of the weekday
labels. So the "book on a Tuesday" folklore does not survive contact with this
trip's data. Tuesday is not meaningfully cheaper than Thursday here, and any
schedule built on that premise is built on noise.

## Weekends are worse, weakly

One contrast does separate from noise. Pooling Sat+Sun against Mon–Fri:

- Relative price: **+2.5%** on weekends, p = 0.15 — not significant
- **P(cheaper than previous day): −8.2 points** on weekends, p = 0.046

A fare is meaningfully less likely to *fall* over a weekend. That agrees with the
mechanism — airlines file fare changes through ATPCO on weekdays, so weekend
movement is thin — and a finding that matches a known mechanism is worth more than
one that only shows up in the numbers. It is still weak evidence (p = 0.046, and
it was one of several contrasts tested), so it justifies a mild preference, not a
strong claim.

## What the schedule actually optimises

Weekday choice is close to free, so the schedule is set by the things that do
matter:

- **Coverage.** Fares changed on 34% of day-transitions, median move $14 when they
  move, and a price holds for a median of 1 day (mean 2.9). Prices move often
  enough that long gaps risk missing a dip.
- **Budget.** The account is on SerpApi's free 250-searches/month tier and one
  check costs 14. Daily is 420/month and runs dry mid-month. Mon/Wed/Fri is ~13
  runs/month = 182, which fits with room.
- **Where to put the gap.** Mon→Wed and Wed→Fri are two days; the three-day gap
  falls Fri→Mon, across exactly the window where fares are least likely to drop.

That is the whole argument: no weekday is cheaper, weekends are the deadest, so
run on weekdays and let the long gap land on the weekend.

## The decision date

Moved up to **Oct 2 2026** (from Nov 1) on 2026-09-14. Oct 2 is a **Friday**,
already a scheduled run day, so no one-shot is needed — the decision-date
tripwire fires on the day itself. (An Oct 1 one-shot existed briefly when the
date was Oct 1, a Thursday; moving to Oct 2 made it redundant and it was
deleted.)

### What the data says about that date

Pooling all six legs by days-to-departure widens the observed booking curve to
175→93 days out. Within that window the fares have mostly been falling, and the
two legs that matter most are close to their observed floors:

| Leg | Departs | Days out | First seen | Now | Its floor | Above floor | Last 14d |
|---|---|---|---|---|---|---|---|
| A1 | Dec 16 | 93 | $574 | $389 | $369 | +$20 | **−$84** |
| A2 | Dec 23 | 100 | $157 | $229 | $157 | +$72 | −$2 |
| A3 | Dec 28 | 105 | $224 | $279 | $200 | +$79 | −$40 |
| B1 | Dec 24 | 101 | $274 | $397 | $190 | +$207 | **+$37** |
| B2 | Dec 29 | 106 | $243 | $229 | $157 | +$72 | −$4 |
| B3 | Jan 6 | 114 | $574 | $389 | $369 | +$20 | −$33 |

(Headline fares, which is what Google's history tracks; main cabin sits ~$55–75
above each.)

Two things follow. **Most of the fall has already happened** — A1 and B3 are $20
off their own floors after coming down ~$185 — so the remaining downside on the
legs that drive the decision is small. And **B1 is going the wrong way**, up $37
in a fortnight and dearer than 98% of its readings, which is why Option B keeps
losing ground to Option A.

### The limit of this analysis

The series only reaches 93 days before departure. **There is no measurement here
of what happens inside 90 days** — the stretch that actually decides whether
waiting pays. The general shape of holiday booking curves puts the turn upward
somewhere inside the last six weeks, which for a Dec 16 departure is roughly
Nov 4, but that is a prior about airfares in general, not something measured from
this trip. Oct 2 sits comfortably before any plausible run-up; a later date in
October would capture more of a decline that is visibly still in progress, at the
cost of holding exposure longer. See `strategy.md` — the remaining timing upside
($20–40) is now smaller than the structural saving available today ($64).

## Reproducing this

The analysis needs one search per leg (6 total) to pull `price_insights.price_history`,
then groups by the weekday of each observation. Worth re-running if the schedule is
ever questioned, or closer to departure when the booking curve steepens and the
weekend effect may sharpen.
