# Config guide

One trip = one JSON file. Every number the script uses comes from here, so the check is the same from any machine.

```json
{
  "trip_name": "Dec 2026 · NYC · Oahu · SF",   // page title — short, specific
  "slug": "dec-2026-hawaii-sf",
  "currency": "USD",
  "decision_date": "2026-11-01",               // reaching this date is itself a tripwire
  "baseline_source": "google_flights",         // google_flights | amadeus | null (set on first run)
  "baseline_set_at": "2026-09-01",
  "rules": ["Must be in SF Dec 24–25", "..."], // shown on the page verbatim; the traveler's own words
  "tripwires": {
    "total_over_baseline": 100,                // option total drifts more than this above baseline → BOOK_NOW
    "price_drop_alert": 40                     // option total falls by at least this → GOOD_SIGN (notify, keep waiting)
  },
  "options": [
    {
      "id": "A", "label": "Hawaii first",
      "baseline_total": 837,                   // sum of the leg baselines on their primary dates
      "legs": [
        {
          "id": "A1", "label": "Out to Oahu",
          "from": "JFK", "to": "HNL",
          "dates": ["2026-12-16", "2026-12-14", "2026-12-15"],  // first = primary; cheapest across all wins
          "baseline": 379,
          "max_price": 450,                    // leg ceiling → BOOK_NOW when the cheapest date exceeds it; null = none
          "note": "Dec 17+ is $700+"           // why this leg matters; shown nowhere yet, kept for the reader
        }
      ]
    }
  ]
}
```

## Picking tripwires

- **Leg ceiling (`max_price`)** on the legs that make the routing work — usually the long-haul or the one with a hard date wall. Set it where the trip stops being worth the price at all, not where it becomes "a bit more". ~20% above baseline is typical.
- **Total drift** (`total_over_baseline`) catches slow creep across all legs. +$100 on an ~$850 trip is about 12%.
- **Drop alert** (`price_drop_alert`) is informational — it tells the traveler waiting is paying off. Don't set it so low it fires on noise; $40 on a multi-leg total is fine.
- **Decision date** is the backstop. Fares for peak dates rise steeply inside ~6 weeks; put the date where the traveler wants to be forced to choose.

## Alternate dates

`dates[1:]` are dates the traveler would accept equally. The script prices every one and takes the cheapest; the page shows the others as "also: Mon Dec 14 $369". Only list true alternates — a date that costs the traveler a night somewhere is not an alternate, it's a different option.

## Options

Two or three routings at most. Each is a complete trip; the page marks the cheapest. Legs must be independent one-ways (that is how the trip is booked and how the API prices them).
