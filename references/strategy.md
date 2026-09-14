# Strategic review — 2026-09-14

Written as the owner of the outcome, not the operator of the script. The goal is
the cheapest acceptable trip, not a well-run watcher.

## The finding that matters

**The watch has been optimising the wrong unit.** It prices six separate one-way
tickets. The same Option A itinerary bought as **one multi-city ticket** is
cheaper, measured today:

| | Basic / Saver | Main cabin |
|---|---|---|
| Six separate one-ways | $952 | **$1,082** |
| One multi-city ticket (Alaska AS 829 / AS 520 / AS 32) | $839 | **$1,018** |
| **Saving** | **$113** | **$64** |

Verified by walking the multi-city itinerary leg by leg to a complete price, then
pulling its fare ladder. It is one airline, one PNR — which also means a delay on
the first leg is Alaska's problem to re-accommodate, where three separate tickets
would leave that risk with Cameron. Note AS 520 is a different HNL→SFO flight than
the one-way search picks (UA 373), so it is not a pure like-for-like on timing.

Every other lever in this document is smaller than this one.

## Ranked levers

| # | Lever | Worth | Whose call |
|---|---|---|---|
| 1 | Buy as one multi-city ticket, not six one-ways | $64 main / $113 basic | Cameron |
| 2 | The main-cabin rule itself | $179 on the multi-city ($1,018 vs $839) | Cameron |
| 3 | Re-set the leg ceilings so the tripwire carries information | $0, restores signal | Cameron |
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

## What waiting is still worth

Pooled by days-to-departure, the fares have already done most of their falling:
A1 and B3 sit ~$20 above their own observed floors after coming down about $185
each. The remaining downside on the legs that drive the decision is small — call
it $20–40 across the trip — against a restructuring saving of $64 that is
available today and does not depend on the market moving at all.

**The structural win is larger than the remaining timing win.** That is the whole
strategic point: the question stopped being *when* to buy and became *how*.

## Open recommendation

Teach the checker to price the multi-city itinerary as the primary number and keep
the six one-ways as the comparison. Until that lands, the page's totals are a
one-way comparison, not the best price available — the routine prompt now says so
explicitly so no run reports it as the cheapest option.
