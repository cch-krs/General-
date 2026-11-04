"""Election-night firehose: fetch every feed in sources.json, merge into docs/data.json."""
import json, re, html, time, hashlib, sys, os, urllib.parse
from concurrent.futures import ThreadPoolExecutor
from urllib.request import Request, urlopen
import feedparser
from classify import tag
from gnews import decode, RateLimited
GN_BUDGET = int(os.environ.get("GN_BUDGET", "25"))  # max Google News links resolved per run

ROOT = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(ROOT, "..", "docs", "data.json")
WINDOW_H = 24          # drop anything published more than 24h ago
RESURFACE_H = 6        # first seen >6h after its publish time => old article reposted/resurfaced
MAX_ITEMS = 4000
UA = "Mozilla/5.0 (compatible; election-firehose/1.0; RSS reader)"
ELEX = re.compile(r"\b(elect|vote|voter|voting|ballot|poll|races?\b|wins\b|won\b|defeats?\b|concede|result|"
                  r"senat|house|congress|governor|gubernat|mayor|primary|runoff|recount|precinct|turnout|"
                  r"democrat|republican|gop|dnc|rnc|campaign|candidate|measure|proposition|amendment|referend|"
                  r"ap |decision desk|ddhq|projected|midterm)", re.I)
TAG = re.compile(r"<[^>]+>")

def clean(s, n=320):
    s = html.unescape(TAG.sub(" ", s or ""))
    s = re.sub(r"\s+", " ", s).strip()
    return s[:n] + ("…" if len(s) > n else "")

def ts(e):
    for k in ("published_parsed", "updated_parsed"):
        if e.get(k):
            return int(time.mktime(e[k]) - time.timezone)  # struct is UTC
    return None

def fetch(src):
    t0 = time.time()
    try:
        raw = urlopen(Request(src["url"], headers={"User-Agent": UA}), timeout=20).read()
        f = feedparser.parse(raw)
        items = []
        for e in f.entries[:60]:
            link = e.get("link") or ""
            title = clean(e.get("title"), 300)
            if not (link and title):
                continue
            outlet = src["name"]
            if "news.google.com" in src["url"] and e.get("source", {}).get("title"):
                outlet = f'{e["source"]["title"]}'
                title = re.sub(r"\s+-\s+" + re.escape(outlet) + r"$", "", title)
            blurb = "" if "news.google.com" in src["url"] else clean(e.get("summary"))
            pub = (e.get("source") or {}).get("href", "") if "news.google.com" in src["url"] else ""
            items.append(dict(
                id=hashlib.sha1(link.encode()).hexdigest()[:16], title=title, link=link, blurb=blurb,
                outlet=outlet, feed=src["name"], lean=src["lean"], cat=src["cat"], state=src.get("state", ""),
                t=ts(e), elex=bool(ELEX.search(title + " " + blurb)), pub=pub))
            tag(items[-1], src)
        return src, items, dict(ok=True, n=len(items), ms=int((time.time()-t0)*1000))
    except Exception as ex:
        return src, [], dict(ok=False, err=str(ex)[:160])

def main():
    sources = json.load(open(os.path.join(ROOT, "sources.json")))
    now = int(time.time())
    try:
        old = json.load(open(OUT))
    except Exception:
        old = {"items": []}
    seen = {i["id"]: i for i in old.get("items", [])}
    resolved = {i["id"]: i["link"] for i in old.get("items", []) if i.get("gn")}  # id -> publisher URL
    status = []
    skip_gn = os.environ.get("SKIP_GN") == "1"  # fast loop: spare Google News, refresh direct feeds only
    old_status = {x["name"]: x for x in old.get("sources", [])}
    todo = [x for x in sources if not (skip_gn and "news.google.com" in x["url"])]
    for x in sources:
        if x not in todo and x["name"] in old_status:
            status.append(old_status[x["name"]])
    with ThreadPoolExecutor(24) as ex:
        for src, items, st in ex.map(fetch, todo):
            status.append(dict(name=src["name"], lean=src["lean"], cat=src["cat"], **st))
            for it in items:
                prev = seen.get(it["id"])
                it["first_seen"] = prev["first_seen"] if prev else now
                if it["races"] or it["silver"]: it["elex"] = True
                it["undated"] = it["t"] is None
                if it["t"] is None or it["t"] > now + 600:
                    it["t"] = prev["t"] if prev else it["first_seen"]
                it["resurfaced"] = (it["first_seen"] - it["t"]) > RESURFACE_H * 3600
                seen[it["id"]] = it
    srcmap = {x["name"]: x for x in sources}
    for it in seen.values():  # retag everything so classifier changes apply to kept items
        src = srcmap.get(it.get("feed"))
        if src:
            tag(it, src)
            if it["races"] or it["silver"]: it["elex"] = True
    cutoff = now - WINDOW_H * 3600
    fresh = [i for i in seen.values() if i["t"] >= cutoff and not (i.get("undated") and now - i["first_seen"] > 6 * 3600)]
    # collapse reposts: same headline across outlets / Google News copies -> one item, others listed in "also"
    groups = {}
    for i in fresh:
        groups.setdefault(re.sub(r"[^a-z0-9 ]", "", i["title"].lower())[:70], []).append(i)
    items = []
    for g in groups.values():
        g.sort(key=lambda i: ("news.google.com" in i["link"], i["t"]))  # direct feed first, then earliest
        keep = dict(g[0])
        keep.setdefault("undated", False)
        keep["also"] = sorted({x["outlet"] for x in g[1:] if x["outlet"] != keep["outlet"]})
        keep["first_seen"] = min(x["first_seen"] for x in g)
        keep["resurfaced"] = (keep["first_seen"] - keep["t"]) > RESURFACE_H * 3600
        items.append(keep)
    items = sorted(items, key=lambda i: -i["t"])[:MAX_ITEMS]
    # swap Google News redirect links for the publisher's own URL (cached; newest first; capped per run)
    budget, n_ok = GN_BUDGET, 0
    for it in items:
        if "news.google.com" not in it["link"]:
            continue
        if it["id"] in resolved:
            it["gn"], it["link"] = it["link"], resolved[it["id"]]
            continue
        if budget <= 0:
            continue
        budget -= 1
        try:
            real = decode(it["link"])
            it["gn"], it["link"] = it["link"], real
            resolved[it["id"]] = real
            n_ok += 1
            time.sleep(0.4)
        except RateLimited:
            print("  Google News rate-limited; resolving the rest next run")
            budget = 0
        except Exception:
            pass
    # anything still on a Google redirect: send the click straight to the publisher via a first-result search
    for it in items:
        if "news.google.com" in it["link"]:
            dom = urllib.parse.urlparse(it.get("pub") or "").netloc.replace("www.", "")
            q = f'\\{it["title"]}' + (f" site:{dom}" if dom else "")
            it["out"] = "https://duckduckgo.com/?q=" + urllib.parse.quote(q)
        else:
            it.pop("out", None)
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    json.dump(dict(updated=now, sources=status, items=items), open(OUT, "w"), separators=(",", ":"))
    ok = sum(s["ok"] for s in status)
    left = sum("news.google.com" in i["link"] for i in items)
    print(f"{ok}/{len(status)} feeds ok, {len(items)} items; resolved {n_ok} Google News links this run, {left} still pending")
    for s in status:
        if not s["ok"]:
            print("  FAIL", s["name"], s["err"])

if __name__ == "__main__":
    main()
