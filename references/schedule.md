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

Nov 1 2026 — the planned decision date, and the one unconditional BOOK_NOW
tripwire — is a **Sunday**, and Oct 31 is a Saturday. Under Mon/Wed/Fri the last
run before it is Fri Oct 30 and the next is Mon Nov 2, so the tripwire would fire a
day late. A one-shot routine (`trig_01MWQTpTpYo8iy7cKbVHxbMQ`) runs on Nov 1 at
13:02 UTC to close that gap.

## Reproducing this

The analysis needs one search per leg (6 total) to pull `price_insights.price_history`,
then groups by the weekday of each observation. Worth re-running if the schedule is
ever questioned, or closer to departure when the booking curve steepens and the
weekend effect may sharpen.
