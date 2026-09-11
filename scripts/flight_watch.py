#!/usr/bin/env python3
"""
flight_watch.py — book-the-whole-trip-or-keep-waiting price monitor.

One trip = one config JSON. Each run:
  1. fetches the cheapest nonstop fare for every leg (trying each allowed date),
  2. totals each routing option,
  3. evaluates the tripwires,
  4. writes result.json + appends history.json + renders index.html.

The decision is one of:
  BOOK_NOW      a tripwire fired (leg ceiling, total drift, or decision date reached)
  GOOD_SIGN     an option's total dropped by >= price_drop_alert — keep waiting
  WAIT          nothing meaningful moved
  CHECK_FAILED  a leg could not be priced — never guess; say so

Providers (chosen by env, first match wins):
  SERPAPI_KEY                          -> SerpApi google_flights (Google Flights parity)
  AMADEUS_CLIENT_ID + AMADEUS_CLIENT_SECRET (+ AMADEUS_ENV=test|production)
  FLIGHT_WATCH_MOCK=wait|drop|tripwire|fail  -> deterministic mock for dry-runs

Stdlib only. Python 3.9+.

Usage:
  flight_watch.py check  --config config.json --out ./site [--history history.json]
  flight_watch.py render --result site/result.json --config config.json --out ./site
  flight_watch.py init   --out config.json      # writes the template
"""
from __future__ import annotations

import argparse
import datetime as dt
import html
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Optional

HERE = os.path.dirname(os.path.abspath(__file__))
UTC = dt.timezone.utc


# ----------------------------------------------------------------------------
# small helpers
# ----------------------------------------------------------------------------

def now_utc() -> dt.datetime:
    return dt.datetime.now(UTC).replace(microsecond=0)


def http_get_json(url: str, headers: Optional[dict] = None, data: Optional[bytes] = None,
                  timeout: int = 40) -> Any:
    req = urllib.request.Request(url, headers=headers or {}, data=data)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def google_flights_url(origin: str, dest: str, date: str) -> str:
    q = f"Flights from {origin} to {dest} on {date} one way"
    return "https://www.google.com/travel/flights?q=" + urllib.parse.quote(q)


def fmt_money(v: Optional[float], cur: str = "USD") -> str:
    if v is None:
        return "—"
    sym = {"USD": "$", "EUR": "€", "GBP": "£"}.get(cur, cur + " ")
    return f"{sym}{v:,.0f}"


def fmt_delta(v: Optional[float]) -> str:
    if v is None:
        return ""
    if abs(v) < 0.5:
        return "±0"
    return f"{'+' if v > 0 else '−'}{abs(v):,.0f}"


def hhmm(iso: Optional[str]) -> str:
    """'2026-12-16 07:45' or ISO -> '7:45a'"""
    if not iso:
        return "—"
    s = iso.replace("T", " ")[:16]
    try:
        t = dt.datetime.strptime(s, "%Y-%m-%d %H:%M")
    except ValueError:
        return iso
    h = t.hour % 12 or 12
    return f"{h}:{t.minute:02d}{'a' if t.hour < 12 else 'p'}"


def pretty_date(iso: str) -> str:
    d = dt.date.fromisoformat(iso)
    return d.strftime("%a %b ") + str(d.day)


# ----------------------------------------------------------------------------
# fare classes
#
# The trip rules exclude basic economy, so the fare the decision is made on is
# the cheapest true MAIN CABIN fare the operating airline sells — not the
# headline number, which on every one of these routes is a Saver/Basic fare.
# Both are tracked; only main cabin drives tripwires.
# ----------------------------------------------------------------------------

BELOW_MAIN = ("basic economy", "economy basic", "basic", "saver", "light", "blue basic")
ABOVE_MAIN = ("first", "business", "premium", "plus", "select", "refundable",
              "comfort", "extra", "flagship", "delta one", "mint", "flex")
MAIN_CABIN = ("main cabin", "main", "economy", "standard", "classic", "coach", "blue")


def fare_rank(title: Optional[str]) -> str:
    """'below' (basic/saver) | 'main' | 'above' (premium) | 'unknown' (OTA, no title)."""
    if not title:
        return "unknown"
    t = title.strip().lower()
    if any(k in t for k in BELOW_MAIN):
        return "below"
    if any(k in t for k in ABOVE_MAIN):
        return "above"
    if any(k in t for k in MAIN_CABIN):
        return "main"
    return "unknown"


def normalize_insights(pi: Any) -> Optional[dict]:
    """Google's own price analysis for this exact route+date, as SerpApi returns it."""
    if not isinstance(pi, dict):
        return None
    hist = []
    for row in pi.get("price_history") or []:
        try:
            hist.append((int(row[0]), float(row[1])))
        except (TypeError, ValueError, IndexError):
            continue
    return {"level": pi.get("price_level"), "lowest": pi.get("lowest_price"),
            "typical_range": pi.get("typical_price_range"), "history": hist}


# ----------------------------------------------------------------------------
# drop outlook — how much room is left for a fare to fall
#
# Every signal here is measured, never guessed: Google's price_insights for this
# exact route and date (its own low/typical/high call, the typical price range,
# and ~60 days of price history), plus how close departure is. A negative score
# leans against a further drop, positive leans toward one. No percentage is
# reported because nothing here is a calibrated probability.
#
# The insights describe the CHEAPEST fare on the route, so the outlook is scored
# on the headline price even when the decision is made on main cabin.
# ----------------------------------------------------------------------------

BANDS = {"UNLIKELY": "a drop is unlikely", "POSSIBLE": "a drop is possible",
         "LIKELY": "a drop looks likely"}


def drop_outlook(ins: Optional[dict], price: Optional[float], dep_date: Optional[str],
                 today: dt.date) -> dict:
    reasons: list = []
    score = 0
    pct = None
    if ins:
        lvl = (ins.get("level") or "").lower()
        if lvl == "low":
            score -= 2
            reasons.append("Google rates this fare low for the route")
        elif lvl == "high":
            score += 2
            reasons.append("Google rates this fare high for the route")
        elif lvl == "typical":
            reasons.append("Google rates this fare typical for the route")
        rng = ins.get("typical_range") or []
        if len(rng) == 2 and price is not None and rng[1] > rng[0]:
            pct = max(0.0, min(1.0, (price - rng[0]) / (rng[1] - rng[0])))
            band_txt = f"${rng[0]:,.0f}–${rng[1]:,.0f} typical range"
            if pct <= 0.25:
                score -= 2
                reasons.append(f"sits at the {pct:.0%} mark of the {band_txt} — little room below")
            elif pct >= 0.60:
                score += 2
                reasons.append(f"sits at the {pct:.0%} mark of the {band_txt} — room to fall")
            else:
                reasons.append(f"sits at the {pct:.0%} mark of the {band_txt}")
        hist = ins.get("history") or []
        if len(hist) >= 8:
            recent = [v for _, v in hist[-14:]]
            earlier = [v for _, v in hist[-42:-14]] or [v for _, v in hist[:len(hist) // 2]]
            if recent and earlier:
                ra, ea = sum(recent) / len(recent), sum(earlier) / len(earlier)
                if ra < ea * 0.96:
                    score += 1
                    reasons.append(f"still drifting down (${ea:,.0f} → ${ra:,.0f} over the tracked window)")
                elif ra > ea * 1.04:
                    score -= 1
                    reasons.append(f"already turning up (${ea:,.0f} → ${ra:,.0f} over the tracked window)")
                else:
                    reasons.append("flat over the tracked window")
            if price is not None:
                below = sum(1 for _, v in hist if v < price)
                share = below / len(hist)
                if share <= 0.15:
                    score -= 1
                    reasons.append(f"cheaper than {1 - share:.0%} of the last {len(hist)} readings")
                elif share >= 0.50:
                    score += 1
                    reasons.append(f"dearer than {share:.0%} of the last {len(hist)} readings")
    days = None
    if dep_date:
        try:
            days = (dt.date.fromisoformat(dep_date) - today).days
        except ValueError:
            days = None
    if days is not None:
        if days <= 45:
            score -= 2
            reasons.append(f"{days} days out — holiday fares firm up inside six weeks")
        elif days >= 90:
            score += 1
            reasons.append(f"{days} days out — still early enough for movement")
    if not reasons:
        reasons.append("no price history available for this route and date")
        band = "POSSIBLE"
    else:
        band = "LIKELY" if score >= 2 else ("POSSIBLE" if score >= 0 else "UNLIKELY")
    return {"band": band, "score": score, "reasons": reasons, "pct_in_range": pct,
            "days_out": days, "level": (ins or {}).get("level")}


def combine_outlooks(outlooks: list) -> dict:
    """An option is as bookable as its legs collectively allow."""
    real = [o for o in outlooks if o]
    if not real:
        return {"band": "POSSIBLE", "score": 0, "reasons": [], "legs": 0}
    total = sum(o["score"] for o in real)
    mean = total / len(real)
    band = "LIKELY" if mean >= 1.5 else ("POSSIBLE" if mean >= -0.5 else "UNLIKELY")
    return {"band": band, "score": round(mean, 2), "reasons": [], "legs": len(real)}

# ----------------------------------------------------------------------------
# providers — each returns the cheapest NONSTOP fare for one origin/dest/date
#   -> {"price": float, "airline": str, "flight": str, "dep": str, "arr": str,
#       "raw_count": int} or raises ProviderError
# ----------------------------------------------------------------------------

class ProviderError(Exception):
    pass


class SerpApiProvider:
    name = "serpapi"
    family = "google_flights"          # comparable with Google Flights baselines

    def __init__(self, key: str):
        self.key = key

    def _params(self, origin: str, dest: str, date: str, currency: str) -> dict:
        return {
            "engine": "google_flights", "departure_id": origin, "arrival_id": dest,
            "outbound_date": date, "type": "2",            # 2 = one way
            "stops": "1",                                   # 1 = nonstop only
            "travel_class": "1", "currency": currency, "hl": "en", "api_key": self.key,
        }

    def _get(self, params: dict, what: str) -> dict:
        url = "https://serpapi.com/search.json?" + urllib.parse.urlencode(params)
        try:
            data = http_get_json(url)
        except urllib.error.HTTPError as e:
            raise ProviderError(f"SerpApi HTTP {e.code} for {what}") from e
        except Exception as e:  # noqa: BLE001
            raise ProviderError(f"SerpApi request failed for {what}: {e}") from e
        if "error" in data:
            raise ProviderError(f"SerpApi: {data['error']}")
        return data

    def cheapest_nonstop(self, origin: str, dest: str, date: str, currency: str) -> dict:
        what = f"{origin}-{dest} {date}"
        params = self._params(origin, dest, date, currency)
        data = self._get(params, what)
        items = (data.get("best_flights") or []) + (data.get("other_flights") or [])
        cands = []
        for it in items:
            segs = it.get("flights") or []
            if len(segs) != 1 or it.get("price") is None:
                continue   # belt-and-braces nonstop filter
            s = segs[0]
            cands.append({
                "price": float(it["price"]),
                "airline": s.get("airline") or "",
                "flight": s.get("flight_number") or "",
                "dep": (s.get("departure_airport") or {}).get("time"),
                "arr": (s.get("arrival_airport") or {}).get("time"),
                "booking_token": it.get("booking_token"),
            })
        if not cands:
            raise ProviderError(f"no nonstop fares returned for {what}")
        best = min(cands, key=lambda c: c["price"])
        best["raw_count"] = len(cands)
        best["insights"] = normalize_insights(data.get("price_insights"))
        best.update(self._fare_ladder(params, best.pop("booking_token", None), what))
        return best

    def _fare_ladder(self, params: dict, token: Optional[str], what: str) -> dict:
        """Second call: every fare class sold on the chosen flight, plus a Google
        Flights link to that specific flight rather than the route search."""
        out: dict = {"fares": [], "main": None, "deep_link": None}
        if not token or os.environ.get("FLIGHT_WATCH_NO_BOOKING"):
            return out
        p = dict(params)
        p["booking_token"] = token
        try:
            b = self._get(p, what + " fare ladder")
        except ProviderError:
            return out          # a missing ladder must never fail the whole check
        out["deep_link"] = (b.get("search_metadata") or {}).get("google_flights_url")
        for x in b.get("booking_options") or []:
            t = x.get("together") or x.get("departing") or {}
            if t.get("price") is None:
                continue
            out["fares"].append({"seller": t.get("book_with") or "",
                                 "title": t.get("option_title"),
                                 "price": float(t["price"]),
                                 "rank": fare_rank(t.get("option_title"))})
        mains = [f for f in out["fares"] if f["rank"] == "main"]
        if mains:
            out["main"] = min(mains, key=lambda f: f["price"])
        return out


class AmadeusProvider:
    name = "amadeus"
    family = "amadeus"                 # GDS pricing; NOT comparable with Google baselines

    def __init__(self, cid: str, secret: str, env: str = "test"):
        self.base = "https://api.amadeus.com" if env == "production" else "https://test.api.amadeus.com"
        self.cid, self.secret = cid, secret
        self._token: Optional[str] = None
        self._carriers: dict = {}

    def _auth(self) -> str:
        if self._token:
            return self._token
        body = urllib.parse.urlencode({"grant_type": "client_credentials",
                                       "client_id": self.cid, "client_secret": self.secret}).encode()
        try:
            data = http_get_json(self.base + "/v1/security/oauth2/token",
                                 headers={"Content-Type": "application/x-www-form-urlencoded"}, data=body)
        except Exception as e:  # noqa: BLE001
            raise ProviderError(f"Amadeus auth failed: {e}") from e
        self._token = data["access_token"]
        return self._token

    def cheapest_nonstop(self, origin: str, dest: str, date: str, currency: str) -> dict:
        params = {"originLocationCode": origin, "destinationLocationCode": dest,
                  "departureDate": date, "adults": "1", "nonStop": "true",
                  "currencyCode": currency, "max": "50"}
        url = self.base + "/v2/shopping/flight-offers?" + urllib.parse.urlencode(params)
        try:
            data = http_get_json(url, headers={"Authorization": "Bearer " + self._auth()})
        except urllib.error.HTTPError as e:
            raise ProviderError(f"Amadeus HTTP {e.code} for {origin}-{dest} {date}") from e
        except Exception as e:  # noqa: BLE001
            raise ProviderError(f"Amadeus request failed for {origin}-{dest} {date}: {e}") from e
        self._carriers.update((data.get("dictionaries") or {}).get("carriers") or {})
        cands = []
        for off in data.get("data") or []:
            try:
                seg = off["itineraries"][0]["segments"]
                if len(seg) != 1:
                    continue
                s = seg[0]
                code = s.get("carrierCode", "")
                cands.append({
                    "price": float(off["price"]["grandTotal"]),
                    "airline": self._carriers.get(code, code).title() if code else "",
                    "flight": f"{code} {s.get('number', '')}".strip(),
                    "dep": s["departure"]["at"], "arr": s["arrival"]["at"],
                })
            except (KeyError, IndexError, ValueError):
                continue
        if not cands:
            raise ProviderError(f"no nonstop offers for {origin}-{dest} {date}")
        best = min(cands, key=lambda c: c["price"])
        best["raw_count"] = len(cands)
        return best


class MockProvider:
    """Deterministic fares for dry-runs. Scenario via FLIGHT_WATCH_MOCK."""
    name = "mock"
    family = "mock"

    def __init__(self, scenario: str, config: dict):
        self.scenario = scenario
        self.base = {}
        for opt in config["options"]:
            for leg in opt["legs"]:
                self.base[(leg["from"], leg["to"], leg["dates"][0])] = leg.get("baseline") or 300
                for extra in leg["dates"][1:]:
                    self.base[(leg["from"], leg["to"], extra)] = (leg.get("baseline") or 300) + 15

    def cheapest_nonstop(self, origin: str, dest: str, date: str, currency: str) -> dict:
        if self.scenario == "fail" and dest == "HNL":
            raise ProviderError("mock outage")
        p = float(self.base.get((origin, dest, date), 300))
        if self.scenario == "drop":
            p = round(p * 0.82)
        elif self.scenario == "tripwire":
            p = round(p * 1.35)
        return {"price": p, "airline": "Mock Air", "flight": "MK 100",
                "dep": f"{date}T08:05", "arr": f"{date}T13:40", "raw_count": 3}


def pick_provider(config: dict):
    if os.environ.get("FLIGHT_WATCH_MOCK"):
        return MockProvider(os.environ["FLIGHT_WATCH_MOCK"], config)
    if os.environ.get("SERPAPI_KEY"):
        return SerpApiProvider(os.environ["SERPAPI_KEY"])
    if os.environ.get("AMADEUS_CLIENT_ID") and os.environ.get("AMADEUS_CLIENT_SECRET"):
        return AmadeusProvider(os.environ["AMADEUS_CLIENT_ID"], os.environ["AMADEUS_CLIENT_SECRET"],
                               os.environ.get("AMADEUS_ENV", "test"))
    return None


# ----------------------------------------------------------------------------
# core: fetch + evaluate
# ----------------------------------------------------------------------------

def price_leg(provider, leg: dict, currency: str, today: dt.date) -> dict:
    """Try every allowed date; keep the cheapest. Record per-date results + errors.

    Two fares come back per date: the headline fare (cheapest of any class, which on
    these routes is Saver/Basic) and the cheapest main-cabin fare. The decision is
    made on main cabin, per the trip rules; the headline is kept for context and
    because the baselines and Google's price history are built on it."""
    per_date, errors = {}, {}
    for d in leg["dates"]:
        try:
            r = provider.cheapest_nonstop(leg["from"], leg["to"], d, currency)
            r["date"] = d
            r.setdefault("fares", [])
            r.setdefault("main", None)
            r.setdefault("insights", None)
            r["link"] = google_flights_url(leg["from"], leg["to"], d)
            r["flight_link"] = r.pop("deep_link", None) or r["link"]
            r["main_price"] = r["main"]["price"] if r.get("main") else None
            r["outlook"] = drop_outlook(r.get("insights"), r["price"], d, today)
            per_date[d] = r
        except ProviderError as e:
            errors[d] = str(e)
        time.sleep(float(os.environ.get("FLIGHT_WATCH_SLEEP", "0.6")))

    best = min(per_date.values(), key=lambda r: r["price"]) if per_date else None
    mains = [r for r in per_date.values() if r.get("main_price") is not None]
    best_main = min(mains, key=lambda r: r["main_price"]) if mains else None
    decide = best_main or best
    if best_main:
        decide_price, fare_class = best_main["main_price"], "main"
    elif best:
        decide_price, fare_class = best["price"], "headline"
    else:
        decide_price, fare_class = None, None

    return {"id": leg["id"], "label": leg.get("label") or f"{leg['from']}→{leg['to']}",
            "from": leg["from"], "to": leg["to"], "primary_date": leg["dates"][0],
            "baseline": leg.get("baseline"), "baseline_main": leg.get("baseline_main"),
            "max_price": leg.get("max_price"), "note": leg.get("note", ""),
            "best": best, "best_main": best_main, "decide_price": decide_price,
            "fare_class": fare_class, "outlook": decide["outlook"] if decide else None,
            "per_date": per_date, "errors": errors}


def evaluate(config: dict, legs_by_option: dict, today: dt.date, provider_family: str,
             rebaselined: bool) -> dict:
    tw = config.get("tripwires", {})
    drift_limit = float(tw.get("total_over_baseline", 100))
    drop_alert = float(tw.get("price_drop_alert", 40))
    decision_date = dt.date.fromisoformat(config["decision_date"]) if config.get("decision_date") else None

    fired, good_signs, failures = [], [], []
    options_out = []
    for opt in config["options"]:
        legs = legs_by_option[opt["id"]]
        missing = [l["id"] for l in legs if l["decide_price"] is None]
        total = None if missing else round(sum(l["decide_price"] for l in legs))
        head_missing = [l["id"] for l in legs if not l["best"]]
        total_headline = None if head_missing else round(sum(l["best"]["price"] for l in legs))
        base_total = opt.get("baseline_total_main")
        drift = (total - base_total) if (total is not None and base_total is not None) else None
        if missing:
            failures.append(f"Option {opt['id']}: could not price {', '.join(missing)}")

        # ceilings apply to the fare actually flown — main cabin. Each breach is
        # judged against the outlook for the thing that breached: a leg ceiling by
        # that leg's own fare, a total by the option as a whole.
        outlook = combine_outlooks([l.get("outlook") for l in legs])
        for l in legs:
            if l["decide_price"] is not None and l.get("max_price") is not None \
                    and l["decide_price"] > float(l["max_price"]):
                if l["fare_class"] == "main":
                    txt = (f"{l['id']} {l['label']} is {fmt_money(l['decide_price'])} in main cabin — "
                           f"above its {fmt_money(float(l['max_price']))} ceiling")
                else:
                    txt = (f"{l['id']} {l['label']} is {fmt_money(l['decide_price'])} — above its "
                           f"{fmt_money(float(l['max_price']))} ceiling (no main-cabin fare published)")
                fired.append({"text": txt, "band": (l.get("outlook") or {}).get("band", "POSSIBLE"),
                              "hard": False, "scope": l["id"]})
        if drift is not None and drift > drift_limit:
            fired.append({"text": f"Option {opt['id']} total {fmt_money(total)} is {fmt_money(drift)} over its "
                                  f"{fmt_money(base_total)} baseline (limit +{fmt_money(drift_limit)})",
                          "band": outlook["band"], "hard": False, "scope": opt["id"]})
        if drift is not None and -drift >= drop_alert:
            cheapest_leg = min((l for l in legs if l["decide_price"] is not None and l.get("baseline_main") is not None),
                               key=lambda l: l["decide_price"] - l["baseline_main"], default=None)
            detail = ""
            if cheapest_leg:
                detail = f" — {cheapest_leg['id']} {cheapest_leg['label']} dropped to {fmt_money(cheapest_leg['decide_price'])}"
            good_signs.append(f"Option {opt['id']} now {fmt_money(total)} ({fmt_delta(drift)}){detail}")

        options_out.append({"id": opt["id"], "label": opt.get("label", opt["id"]),
                            "total": total, "total_headline": total_headline,
                            "baseline_total": base_total,
                            "baseline_total_headline": opt.get("baseline_total"),
                            "drift": drift, "outlook": outlook, "legs": legs})

    decided = bool(decision_date and today >= decision_date)
    if decided:
        fired.insert(0, {"text": f"Decision date {decision_date.strftime('%b %-d')} has arrived — time to decide",
                         "band": "UNLIKELY", "hard": True, "scope": "date"})

    priced = [o for o in options_out if o["total"] is not None]
    better = min(priced, key=lambda o: o["total"])["id"] if priced else None

    # A breach that is not expected to ease is a reason to book. A breach the
    # evidence says will ease is a reason to keep watching — but it is still news.
    settled = [f for f in fired if f["hard"] or f["band"] == "UNLIKELY"]
    fired_text = [f["text"] for f in fired]

    if settled:
        decision = "BOOK_NOW"
        headline = settled[0]["text"]
        if not settled[0]["hard"]:
            headline += " — and that fare is not expected to fall further"
    elif fired:
        decision = "HOLD"
        headline = fired[0]["text"] + f" — but {BANDS[fired[0]['band']]} from here, so holding for now"
    elif failures and not priced:
        decision, headline = "CHECK_FAILED", failures[0]
    elif good_signs:
        decision, headline = "GOOD_SIGN", good_signs[0] + " — a good sign for continuing to wait, not a reason to book"
    else:
        parts = [f"Option {o['id']} {fmt_money(o['total'])}" for o in priced]
        decision, headline = "WAIT", "Still waiting — " + ", ".join(parts) + ", no tripwires"
        if failures:
            headline += f" ({failures[0]})"
    if rebaselined:
        headline = f"Baselines reset to today's main-cabin {provider_family} prices. " + headline

    return {"decision": decision, "headline": headline, "fired": fired_text,
            "fired_detail": fired, "good_signs": good_signs,
            "failures": failures, "better_option": better, "options": options_out,
            "decided_on": "main_cabin",
            "thresholds": {"total_over_baseline": drift_limit, "price_drop_alert": drop_alert,
                           "decision_date": config.get("decision_date")}}


def maybe_rebaseline(config: dict, provider_family: str, legs_by_option: dict) -> bool:
    """Baselines must describe the same thing the decision is made on. The original
    baselines were headline (basic-economy) fares, so main-cabin baselines are seeded
    the first time main-cabin fares are read. Also re-seeds if the price source family
    changed, or if any baseline is missing."""
    src = config.get("baseline_source")
    need = src is None or (src != provider_family and provider_family != "mock")
    if not need:
        need = any(l.get("baseline") is None for o in config["options"] for l in o["legs"])
    need_main = any(l.get("baseline_main") is None for o in config["options"] for l in o["legs"]) \
        or any(o.get("baseline_total_main") is None for o in config["options"])

    if not (need or need_main):
        return False
    changed = False
    for opt in config["options"]:
        legs = legs_by_option[opt["id"]]
        for cfg_leg, priced in zip(opt["legs"], legs):
            if need and priced["best"]:
                cfg_leg["baseline"] = round(priced["best"]["price"])
                priced["baseline"] = cfg_leg["baseline"]
                changed = True
            if need_main and priced["decide_price"] is not None:
                cfg_leg["baseline_main"] = round(priced["decide_price"])
                priced["baseline_main"] = cfg_leg["baseline_main"]
                changed = True
        if need and all(l["best"] for l in legs):
            opt["baseline_total"] = round(sum(l["best"]["price"] for l in legs))
        if need_main and all(l["decide_price"] is not None for l in legs):
            opt["baseline_total_main"] = round(sum(l["decide_price"] for l in legs))
    if changed:
        config["baseline_source"] = provider_family
        if need_main:
            config["baseline_main_set_at"] = now_utc().date().isoformat()
        if need:
            config["baseline_set_at"] = now_utc().date().isoformat()
    return changed


def run_check(config_path: str, out_dir: str, history_path: Optional[str]) -> dict:
    with open(config_path) as f:
        config = json.load(f)
    provider = pick_provider(config)
    os.makedirs(out_dir, exist_ok=True)
    history_path = history_path or os.path.join(out_dir, "history.json")
    history = []
    if os.path.exists(history_path):
        try:
            with open(history_path) as f:
                history = json.load(f)
        except json.JSONDecodeError:
            history = []

    ts = now_utc()
    if provider is None:
        result = {"checked_at": ts.isoformat(), "provider": None, "decision": "CHECK_FAILED",
                  "headline": "No price source configured — set SERPAPI_KEY or AMADEUS_CLIENT_ID/SECRET",
                  "fired": [], "good_signs": [], "failures": ["no provider"], "better_option": None,
                  "options": [], "config": config}
    else:
        currency = config.get("currency", "USD")
        legs_by_option = {o["id"]: [price_leg(provider, l, currency, ts.date()) for l in o["legs"]]
                          for o in config["options"]}
        rebased = maybe_rebaseline(config, provider.family, legs_by_option)
        if rebased:
            with open(config_path, "w") as f:
                json.dump(config, f, indent=2)
        ev = evaluate(config, legs_by_option, ts.date(), provider.family, rebased)
        result = {"checked_at": ts.isoformat(), "provider": provider.name,
                  "provider_family": provider.family, **ev, "config": config}

    # history: compact row per run
    history.append({
        "ts": ts.isoformat(), "decision": result["decision"], "provider": result.get("provider"),
        "totals": {o["id"]: o["total"] for o in result.get("options", [])},
        "totals_headline": {o["id"]: o.get("total_headline") for o in result.get("options", [])},
        "outlook": {o["id"]: (o.get("outlook") or {}).get("band") for o in result.get("options", [])},
    })
    history = history[-180:]
    with open(history_path, "w") as f:
        json.dump(history, f, indent=1)
    with open(os.path.join(out_dir, "result.json"), "w") as f:
        json.dump(result, f, indent=2)
    render(result, history, out_dir)
    return result


# ----------------------------------------------------------------------------
# render — status page (self-contained, theme-aware, phone-first)
# ----------------------------------------------------------------------------

DECISION_META = {
    "BOOK_NOW":     ("BOOK NOW", "critical", "A tripwire fired. Book the whole trip today."),
    "HOLD":         ("HOLD", "warn", "A tripwire fired, but the fare still has room to fall."),
    "GOOD_SIGN":    ("WAIT", "good", "Prices softened. Waiting is still the plan."),
    "WAIT":         ("WAIT", "neutral", "Nothing meaningful moved."),
    "CHECK_FAILED": ("CHECK FAILED", "warn", "Prices could not be read. No decision was made."),
    "PENDING":      ("WAIT", "neutral", "Baseline prices shown — no live check has run yet."),
}



BAND_META = {"UNLIKELY": ("drop unlikely", "critical"),
             "POSSIBLE": ("drop possible", "warn"),
             "LIKELY":   ("drop likely", "good")}

def seed_result(config: dict) -> dict:
    """A result built from the config's baselines, for publishing the page before the
    first live check. Every leg shows its baseline as the fare, with no carrier/times."""
    options = []
    for opt in config["options"]:
        legs = []
        for l in opt["legs"]:
            b = None
            base = l.get("baseline_main") if l.get("baseline_main") is not None else l.get("baseline")
            if base is not None:
                b = {"price": float(base), "airline": "", "flight": "", "dep": None, "arr": None,
                     "date": l["dates"][0], "link": google_flights_url(l["from"], l["to"], l["dates"][0]),
                     "flight_link": google_flights_url(l["from"], l["to"], l["dates"][0]),
                     "raw_count": 0, "fares": [], "main": None, "main_price": None,
                     "insights": None, "outlook": None}
            legs.append({"id": l["id"], "label": l.get("label") or f"{l['from']}→{l['to']}", "from": l["from"],
                         "to": l["to"], "primary_date": l["dates"][0], "baseline": l.get("baseline"),
                         "baseline_main": l.get("baseline_main"),
                         "max_price": l.get("max_price"), "note": l.get("note", ""), "best": b,
                         "best_main": None, "decide_price": float(base) if base is not None else None,
                         "fare_class": None, "outlook": None,
                         "per_date": {l["dates"][0]: b} if b else {}, "errors": {}})
        total = opt.get("baseline_total_main") or opt.get("baseline_total")
        options.append({"id": opt["id"], "label": opt.get("label", opt["id"]), "total": total,
                        "total_headline": opt.get("baseline_total"),
                        "baseline_total": total, "baseline_total_headline": opt.get("baseline_total"),
                        "drift": 0 if total is not None else None,
                        "outlook": {"band": "POSSIBLE", "score": 0, "reasons": [], "legs": 0},
                        "legs": legs})
    priced = [o for o in options if o["total"] is not None]
    better = min(priced, key=lambda o: o["total"])["id"] if priced else None
    tw = config.get("tripwires", {})
    return {"checked_at": now_utc().isoformat(), "provider": None, "provider_family": None,
            "decision": "PENDING", "headline": "Connect a price source (SerpApi or Amadeus key) and the daily check takes over from here.",
            "fired": [], "good_signs": [], "failures": [], "better_option": better, "options": options,
            "decided_on": "main_cabin",
            "thresholds": {"total_over_baseline": float(tw.get("total_over_baseline", 100)),
                           "price_drop_alert": float(tw.get("price_drop_alert", 40)),
                           "decision_date": config.get("decision_date")},
            "config": config}


def _leg_row(l: dict, cur: str) -> str:
    b, bm = l.get("best"), l.get("best_main")
    show = bm or b
    price = l.get("decide_price")
    if not show or price is None:
        err = "; ".join(l["errors"].values()) if l["errors"] else "no fare"
        return (f'<tr class="leg leg-missing"><td class="l-route"><span class="mono">{html.escape(l["from"])}→{html.escape(l["to"])}</span>'
                f'<span class="l-label">{html.escape(l["label"])}</span></td>'
                f'<td class="l-when" colspan="2">{html.escape(l["primary_date"])}</td>'
                f'<td class="l-price"><span class="pill warn">unpriced</span><span class="l-err">{html.escape(err)}</span></td></tr>')

    base = l.get("baseline_main") if l.get("fare_class") == "main" else l.get("baseline")
    delta = (price - base) if base is not None else None
    over = l.get("max_price") is not None and price > float(l["max_price"])
    dcls = "up" if (delta or 0) > 0 else ("down" if (delta or 0) < 0 else "flat")
    ceiling = f'<span class="l-ceiling">ceiling {fmt_money(float(l["max_price"]), cur)}</span>' if l.get("max_price") is not None else ""

    # the fare actually booked, and the cheap fare the rules exclude
    main_fare = show.get("main") or {}
    cls_label = main_fare.get("title") or ("main cabin" if l.get("fare_class") == "main" else "cheapest fare")
    seller = main_fare.get("seller") or (show.get("airline") or "")
    sub = f'<span class="l-class">{html.escape(cls_label)}{" · " + html.escape(seller) if seller else ""}</span>'
    basic = ""
    if b and b.get("price") is not None and abs(b["price"] - price) >= 1:
        basic_title = next((f["title"] for f in (b.get("fares") or []) if f.get("rank") == "below"), "basic")
        basic = f'<span class="l-basic">{html.escape(str(basic_title).lower())} {fmt_money(b["price"], cur)} — excluded by the rules</span>'

    alt = ""
    others = [d for d in l["per_date"] if d != show["date"]]
    if others:
        bits = []
        for d in sorted(others):
            r = l["per_date"][d]
            pv = r.get("main_price") if r.get("main_price") is not None else r.get("price")
            bits.append(f'{pretty_date(d)} {fmt_money(pv, cur)}')
        alt = f'<span class="l-alt">also: {html.escape("; ".join(bits))}</span>'

    ol = l.get("outlook") or {}
    chip = ""
    if ol.get("band"):
        txt, cls = BAND_META.get(ol["band"], (ol["band"].lower(), "neutral"))
        chip = f'<span class="pill {cls} chip">{html.escape(txt)}</span>'

    link = show.get("flight_link") or show.get("link") or ""
    return (f'<tr class="leg{" leg-over" if over else ""}">'
            f'<td class="l-route"><a class="mono" href="{html.escape(link)}" target="_blank" rel="noopener">{html.escape(l["from"])}→{html.escape(l["to"])}</a>'
            f'<span class="l-label">{html.escape(l["label"])}</span>{alt}</td>'
            f'<td class="l-when"><span class="mono">{pretty_date(show["date"])}</span><span class="l-times">{hhmm(show["dep"])}–{hhmm(show["arr"])}</span></td>'
            f'<td class="l-air">{html.escape(show["airline"] or "")}<span class="l-flight mono">{html.escape(show["flight"] or "")}</span></td>'
            f'<td class="l-price"><span class="mono price">{fmt_money(price, cur)}</span>'
            f'<span class="delta {dcls}">{fmt_delta(delta)}</span>{sub}{basic}{ceiling}{chip}</td></tr>')


def _option_panel(o: dict, better: Optional[str], cur: str) -> str:
    is_better = o["id"] == better and o["total"] is not None
    dcls = "up" if (o["drift"] or 0) > 0 else ("down" if (o["drift"] or 0) < 0 else "flat")
    rows = "".join(_leg_row(l, cur) for l in o["legs"])
    base = f'baseline {fmt_money(o["baseline_total"], cur)}' if o["baseline_total"] is not None else "no baseline yet"
    head = ""
    if o.get("total_headline") is not None and o.get("total") is not None and o["total_headline"] != o["total"]:
        head = f'<span class="opt-head-alt">basic-economy total {fmt_money(o["total_headline"], cur)}</span>'
    return f'''
<section class="option{" option-better" if is_better else ""}" aria-labelledby="opt-{o["id"]}">
  <header class="opt-head">
    <div>
      <div class="eyebrow">Option {html.escape(o["id"])}{' · <span class="pill good">cheapest</span>' if is_better else ''}</div>
      <h2 id="opt-{o["id"]}">{html.escape(o["label"])}</h2>
    </div>
    <div class="opt-total">
      <span class="mono total">{fmt_money(o["total"], cur)}</span>
      <span class="delta {dcls}">{fmt_delta(o["drift"])}</span>
      <span class="opt-base">{base}</span>
      {head}
    </div>
  </header>
  <div class="tablewrap"><table class="legs">
    <thead><tr><th>Leg</th><th>Date · times</th><th>Carrier</th><th class="num">Main cabin</th></tr></thead>
    <tbody>{rows}</tbody>
  </table></div>
</section>'''


def _tripwires(result: dict, cur: str) -> str:
    cfg = result["config"]
    th = result.get("thresholds", {})
    items = []
    today = dt.date.fromisoformat(result["checked_at"][:10])
    for o in result.get("options", []):
        for l in o["legs"]:
            if l.get("max_price") is None:
                continue
            p = l.get("decide_price")
            state = "critical" if (p is not None and p > float(l["max_price"])) else ("warn" if p is None else "good")
            txt = f'{l["id"]} {l["label"]} above {fmt_money(float(l["max_price"]), cur)}'
            now = f'now {fmt_money(p, cur)}' if p is not None else "unpriced"
            items.append((state, txt, now))
        if o["baseline_total"] is not None and th.get("total_over_baseline") is not None:
            lim = o["baseline_total"] + th["total_over_baseline"]
            state = "critical" if (o["drift"] is not None and o["drift"] > th["total_over_baseline"]) else ("warn" if o["total"] is None else "good")
            items.append((state, f'Option {o["id"]} total above {fmt_money(lim, cur)}',
                          f'now {fmt_money(o["total"], cur)}' if o["total"] is not None else "unpriced"))
    if cfg.get("decision_date"):
        dd = dt.date.fromisoformat(cfg["decision_date"])
        days = (dd - today).days
        state = "critical" if days <= 0 else "good"
        items.append((state, f'Decision date {dd.strftime("%b %-d, %Y")}', "arrived" if days <= 0 else f"{days} days away"))
    lis = "".join(f'<li><span class="dot {s}"></span><span class="tw-text">{html.escape(t)}</span><span class="tw-now mono">{html.escape(n)}</span></li>'
                  for s, t, n in items)
    return f'<ul class="tripwires">{lis}</ul>'


def _outlook(result: dict, cur: str) -> str:
    """Why the call is what it is — every line here is measured, not guessed."""
    opts = [o for o in result.get("options", []) if o.get("legs")]
    if not opts:
        return ""
    cards = []
    for o in opts:
        band = (o.get("outlook") or {}).get("band")
        if not band:
            continue
        txt, cls = BAND_META.get(band, (band.lower(), "neutral"))
        legs = []
        for l in o["legs"]:
            ol = l.get("outlook")
            if not ol:
                continue
            ltxt, lcls = BAND_META.get(ol["band"], (ol["band"].lower(), "neutral"))
            reasons = "; ".join(ol.get("reasons") or [])
            legs.append(f'<li><span class="dot {lcls}"></span><span class="tw-text">'
                        f'<strong class="mono">{html.escape(l["id"])}</strong> {html.escape(l["label"])} — '
                        f'{html.escape(ltxt)}<span class="ol-why">{html.escape(reasons)}</span></span></li>')
        cards.append(f'''<section class="outlook-card">
  <div class="opt-head"><div><div class="eyebrow">Option {html.escape(o["id"])} · {html.escape(o["label"])}</div>
  <h2>{html.escape(txt.capitalize())}</h2></div></div>
  <ul class="tripwires">{"".join(legs)}</ul>
</section>''')
    if not cards:
        return ""
    return ('<section style="margin-bottom:26px"><h3>Will it drop?</h3>'
            '<p class="ol-note">From Google\'s own price analysis for each route and date — its low/typical/high '
            'call, where today sits in the typical range, the tracked price history, and how close departure is. '
            'These describe the cheapest fare on the flight, which moves the main-cabin fare with it. '
            'No percentage is quoted because none of this is a calibrated probability.</p>'
            f'<div class="outlook-grid">{"".join(cards)}</div></section>')


def _history(history: list, options: list, cur: str) -> str:
    if len(history) < 1:
        return '<p class="rules" style="color:var(--muted);margin:0">No live checks yet.</p>'
    ids = [o["id"] for o in options] or sorted({k for h in history for k in h.get("totals", {})})
    rows = []
    for h in reversed(history[-14:]):
        d = h["ts"][:10]
        cells = "".join(f'<td class="num mono">{fmt_money(h.get("totals", {}).get(i), cur)}</td>' for i in ids)
        lab, cls, _ = DECISION_META.get(h["decision"], (h["decision"], "neutral", ""))
        rows.append(f'<tr><td class="mono">{d}</td>{cells}<td><span class="pill {cls}">{lab}</span></td></tr>')
    head = "".join(f'<th class="num">Option {i}</th>' for i in ids)
    return f'''<div class="tablewrap"><table class="hist"><thead><tr><th>Checked</th>{head}<th>Call</th></tr></thead>
<tbody>{"".join(rows)}</tbody></table></div>'''


def render(result: dict, history: list, out_dir: str) -> str:
    cfg = result["config"]
    cur = cfg.get("currency", "USD")
    label, cls, sub = DECISION_META.get(result["decision"], (result["decision"], "neutral", ""))
    checked = dt.datetime.fromisoformat(result["checked_at"]).strftime("%b %-d, %Y · %H:%M UTC")
    panels = "".join(_option_panel(o, result.get("better_option"), cur) for o in result.get("options", []))
    fired = "".join(f"<li>{html.escape(x)}</li>" for x in result.get("fired", []))
    fails = "".join(f"<li>{html.escape(x)}</li>" for x in result.get("failures", []))
    src = {"serpapi": "Google Flights via SerpApi", "amadeus": "Amadeus GDS", "mock": "mock data (dry run)"}.get(result.get("provider") or "", "no price source")
    rules = cfg.get("rules") or []
    rules_html = "".join(f"<li>{html.escape(r)}</li>" for r in rules)
    tpl_path = os.path.join(HERE, "..", "assets", "page.template.html")
    with open(tpl_path) as f:
        tpl = f.read()
    page = (tpl.replace("{{TITLE}}", html.escape(cfg.get("trip_name", "Flight watch")))
               .replace("{{DECISION_CLASS}}", cls)
               .replace("{{DECISION}}", label)
               .replace("{{DECISION_SUB}}", html.escape(sub))
               .replace("{{HEADLINE}}", html.escape(result.get("headline", "")))
               .replace("{{CHECKED}}", checked)
               .replace("{{SOURCE}}", html.escape(src))
               .replace("{{OPTIONS}}", panels)
               .replace("{{TRIPWIRES}}", _tripwires(result, cur) if result.get("options") else "")
               .replace("{{FIRED}}", f'<ul class="fired">{fired}</ul>' if fired else "")
               .replace("{{FAILURES}}", f'<ul class="fails">{fails}</ul>' if fails else "")
               .replace("{{OUTLOOK}}", _outlook(result, cur))
               .replace("{{HISTORY}}", _history(history, result.get("options", []), cur))
               .replace("{{RULES}}", f'<ul class="rules">{rules_html}</ul>' if rules_html else "")
               .replace("{{BASELINE_NOTE}}", html.escape(
                   "Baselines from " + {"google_flights": "Google Flights", "amadeus": "Amadeus",
                                        "mock": "mock data"}.get(cfg.get("baseline_source") or "", "manual entry")
                   + (f' on {cfg["baseline_set_at"]}' if cfg.get("baseline_set_at") else ""))))
    out = os.path.join(out_dir, "index.html")
    with open(out, "w") as f:
        f.write(page)
    return out


# ----------------------------------------------------------------------------
# cli
# ----------------------------------------------------------------------------

def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("check"); c.add_argument("--config", required=True); c.add_argument("--out", default="site"); c.add_argument("--history")
    r = sub.add_parser("render"); r.add_argument("--result", required=True); r.add_argument("--out", default="site"); r.add_argument("--history")
    i = sub.add_parser("init"); i.add_argument("--out", default="config.json")
    s = sub.add_parser("seed", help="render the page from baselines before any live check"); s.add_argument("--config", required=True); s.add_argument("--out", default="site")
    a = ap.parse_args(argv)

    if a.cmd == "seed":
        with open(a.config) as f:
            config = json.load(f)
        os.makedirs(a.out, exist_ok=True)
        result = seed_result(config)
        with open(os.path.join(a.out, "result.json"), "w") as f:
            json.dump(result, f, indent=2)
        hp = os.path.join(a.out, "history.json")
        if not os.path.exists(hp):
            with open(hp, "w") as f:
                f.write("[]")
        print(render(result, json.load(open(hp)), a.out))
        return 0

    if a.cmd == "init":
        with open(os.path.join(HERE, "..", "assets", "config.template.json")) as f:
            open(a.out, "w").write(f.read())
        print(f"wrote {a.out}")
        return 0
    if a.cmd == "render":
        with open(a.result) as f:
            result = json.load(f)
        hp = a.history or os.path.join(a.out, "history.json")
        history = json.load(open(hp)) if os.path.exists(hp) else []
        print(render(result, history, a.out))
        return 0
    result = run_check(a.config, a.out, a.history)
    print(json.dumps({k: result[k] for k in ("decision", "headline", "better_option", "provider")}, indent=2))
    return 0 if result["decision"] != "CHECK_FAILED" else 2


if __name__ == "__main__":
    sys.exit(main())
