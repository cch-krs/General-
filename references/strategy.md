# Strategic review — 2026-09-14

Written as the owner of the outcome, not the operator of the script. The goal is
the cheapest acceptable trip, not a well-run watcher.

## Correction to the 2026-09-14 multi-city finding

An earlier version of this file claimed the trip bought as one multi-city ticket
saved $64 in main cabin and $113 in basic. **That was wrong, and the error was
mine.** The one-way searches all pass `stops=1`; my first multi-city search did
not. So it was free to route HNL→SFO through Lihue — AS 1043 to LIH, a 4h52m
layover on Kauai, then AS 520 — turning a 5h30m nonstop into nearly 13 hours, and
violating the trip's own nonstop rule. The saving was mostly the connection.

Re-priced nonstop-only, the honest numbers:

| | Saver / basic | Main cabin |
|---|---|---|
| Six separate one-ways | $952 | $1,082 |
| One multi-city ticket, nonstop | $889 | $1,074 |
| **Saving** | **$63** | **$8** |

**In main cabin the restructuring is worth $8 — noise.** The multi-city idea is
not the lever; it only looked like one because of the Kauai detour. What survives
is that a single ticket puts misconnect risk on the airline rather than on
Cameron, which is worth something but not a line item.

## The lever that is real: fare class

On the nonstop multi-city ticket, Saver is $889 against $1,074 for Main — **$185**.
That is the largest number in this file. What Saver actually costs on this
itinerary, per the fare's own terms returned with it: **1 free carry-on included**,
first checked bag $135. Seat assignment and change rights are the other
restrictions and should be confirmed on the airline's own page before booking —
the Alaska policy URL tried here 404'd, so that is unverified rather than known.

## Ranked levers

| # | Lever | Worth | Whose call |
|---|---|---|---|
| 1 | Fare class: Saver vs Main on the nonstop multi-city | **$185** | Cameron |
| 2 | Wait for a dip toward the September low | **~$140 observed** | the watch |
| 3 | Buy as one multi-city ticket rather than six one-ways | $8 main / $63 Saver | Cameron |
| 4 | Stop weighting Option B equally | simplifies | already true |

### 2. What the main-cabin rule costs

The rule excludes Saver/Basic. On this itinerary that is **$179**. Worth an
explicit decision rather than an inherited default: on Alaska, Saver still carries
a carry-on and assigns a seat at check-in; what is lost is seat choice, changes and
refunds. For fixed dates booked three months out, that may be a fair trade — or
not. It is the second-largest number in this file either way.

### 3. The ceilings are dead tripwires

The $450 leg ceilings were set in September against **basic-economy** fares. In
main cabin, A1 and B3 have been $464 since the day main cabin was first priced —
permanently breached. So every run returns HOLD for the same reason, and a
tripwire that is always on carries no information. Either raise them to
main-cabin levels (~$500) or attach them explicitly to the headline fare.

### 4. Option B is settled

Option B is $85 behind and losing ground: B1 (JFK→SFO on Christmas Eve) is up $37
in a fortnight and dearer than 98% of its tracked readings. It will not recover.
Keep pricing it as a cheap sanity check, but the decision is Option A.

## What waiting is still worth — revised upward

An earlier line here put the remaining timing upside at $20–40, reasoning from A1
and B3 sitting near their own floors. That understated it, because the legs do not
bottom at the same time; the portfolio swings more than any single leg.

Reconstructing what Option A would have cost in Saver fares on each of the last 61
days:

| | |
|---|---|
| Today | **$897** |
| Cheapest seen | **$757** on 2026-09-03 |
| Dearest seen | $1,112 on 2026-08-15 |
| Median | $1,008 |
| July avg → September avg | $991 → **$832** |
| Last 21 days | $757–$897, 14 distinct values — **still moving** |

Today is cheap against July and August and **dear against the last three weeks**.
The same trip was $757 eleven days ago. The series has swung $140 inside three
weeks and has not gone flat, so a dip of that order before Oct 2 is not a
hypothetical — it happened this month.

**So timing is worth more than structure here: ~$140 of observed, recent
volatility against $8 of restructuring.** Booking today at $897 would be buying at
the top of the September range.

## Open recommendation

Teach the checker to price the multi-city itinerary as the primary number and keep
the six one-ways as the comparison. Until that lands, the page's totals are a
one-way comparison, not the best price available — the routine prompt now says so
explicitly so no run reports it as the cheapest option.
