"""Resolve news.google.com/rss/articles/... redirect links to the publisher's own URL."""
import json, re, urllib.parse as up, urllib.request as r

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36"}


class RateLimited(Exception):
    pass


def decode(url, timeout=12):
    gid = up.urlparse(url).path.rstrip("/").split("/")[-1]
    try:
        html = r.urlopen(r.Request(f"https://news.google.com/rss/articles/{gid}?hl=en-US&gl=US&ceid=US:en", headers=UA),
                         timeout=timeout).read().decode("utf-8", "replace")
    except r.HTTPError as e:
        if e.code == 429:
            raise RateLimited
        raise
    sig = re.search(r'data-n-a-sg="([^"]+)"', html).group(1)
    ts = re.search(r'data-n-a-ts="([^"]+)"', html).group(1)
    inner = json.dumps(["garturlreq", [["X", "X", ["X", "X"], None, None, 1, 1, "US:en", None, 1, None, None, None, None, None, 0, 1],
                                       "X", "X", 1, [1, 1, 1], 1, 1, None, 0, 0, None, 0], gid, int(ts), sig])
    body = "f.req=" + up.quote(json.dumps([[["Fbv4je", inner, None, "generic"]]]))
    try:
        resp = r.urlopen(r.Request("https://news.google.com/_/DotsSplashUi/data/batchexecute", data=body.encode(),
                                   headers={**UA, "Content-Type": "application/x-www-form-urlencoded;charset=UTF-8"}),
                         timeout=timeout).read().decode()
    except r.HTTPError as e:
        if e.code == 429:
            raise RateLimited
        raise
    real = json.loads(json.loads(resp.split("\n\n")[1])[0][2])[1]
    if not real.startswith("http"):
        raise ValueError("bad decode")
    return real
