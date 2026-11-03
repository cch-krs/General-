"""Heuristic tagging: estimated outlet bias, race references, competitive flag, Silver/poll flags."""
import re

# Estimated bias buckets (approximate, AllSides/Ad Fontes-style; label as estimates in UI)
BIAS_RULES = [  # (substring of outlet name or url, bias)
 ("silver bulletin","Center"),("natesilver","Center"),("split ticket","Center"),("cook political","Center"),("cookpolitical","Center"),
 ("sabato","Center"),("centerforpolitics","Center"),("inside elections","Center"),("decision desk","Center"),("ddhq","Center"),
 ("votehub","Center"),("kalshi","Center"),("polymarket","Center"),("elliott morris","Lean Left"),("gelliottmorris","Lean Left"),
 ("slow boring","Lean Left"),("realclear","Lean Right"),
 ("associated press","Center"),("ap news","Center"),("apnews","Center"),("reuters","Center"),("the hill","Center"),("thehill","Center"),
 ("semafor","Center"),("bloomberg","Center"),("wall street journal","Center"),("wsj","Center"),("usa today","Center"),("newsnation","Center"),
 ("bbc","Center"),("forbes","Center"),("stateline","Center"),("votebeat","Center"),("texas tribune","Center"),("calmatters","Center"),
 ("spotlight pa","Center"),("bridge michigan","Center"),("bridgemi","Center"),("city & state","Center"),("mississippi today","Center"),
 ("the city","Lean Left"),("gothamist","Lean Left"),("hell gate","Left"),("bolts","Lean Left"),("mississippi free press","Lean Left"),
 ("new york times","Lean Left"),("nytimes","Lean Left"),("nyt ","Lean Left"),("washington post","Lean Left"),("cnn","Lean Left"),
 ("nbc","Lean Left"),("abc news","Lean Left"),("cbs","Lean Left"),("politico","Lean Left"),("axios","Lean Left"),("npr","Lean Left"),
 ("guardian","Lean Left"),("atlantic","Lean Left"),("bulwark","Lean Left"),("time magazine","Lean Left"),("los angeles times","Lean Left"),("the onion","Unrated"),("newsweek","Center"),
 ("mother jones","Left"),("huffpost","Left"),("daily kos","Left"),("ms now","Left"),("msnbc","Left"),("ms.now","Left"),("downballot","Left"),
 ("tpm","Left"),("talking points memo","Left"),("vox","Left"),("the nation","Left"),("jacobin","Left"),("democracy docket","Left"),("slate","Left"),
 ("washington examiner","Lean Right"),("the dispatch","Lean Right"),("new york post","Lean Right"),("ny post","Lean Right"),("reason","Lean Right"),
 ("washington times","Right"),("national review","Right"),("free beacon","Right"),("daily wire","Right"),("fox news","Right"),("foxnews","Right"),
 ("breitbart","Right"),("newsmax","Right"),("daily caller","Right"),("federalist","Right"),("blaze","Right"),("townhall","Right"),("oann","Right"),
 ("epoch times","Right"),("pbs","Center"),("daily beast","Left"),("yahoo","Center"),("the independent","Lean Left"),("wbur","Lean Left"),("wuwm","Lean Left"),
 ("multistate","Center"),("covers.com","Center"),("oddschecker","Center"),("action network","Center"),("daily signal","Right"),("just the news","Right"),
]
SN_AND_RADIO_DEFAULT = {"ground": "Lean Left", "left": "Left", "right": "Right", "wire": "Center", "data": "Center", "national": "Center"}

def bias(outlet, feed, url, lean, cat):
    gn = "news.google.com" in url
    hay = (outlet if gn else f"{outlet} | {url.split()[0]}").lower()  # never match on Google News's encoded links
    for k, b in BIAS_RULES:
        if k in hay:
            return b
    if outlet != feed and re.match(r"^(K|W)[A-Z]{2,3}\b|.*\b(News First|FOX ?\d+|NBC ?\d+|CBS ?\d+|ABC ?\d+|Herald|Dispatch|Gazette|Tribune|Journal|Courier|Register|Star|Observer|Times)\b", outlet):
        return "Local/Unrated"
    if outlet != feed:  # Google News item from an outlet we don't have rated
        return "Local/Unrated" if cat in ("radio", "offices") or lean == "ground" else "Unrated"
    if cat == "radio": return "Lean Left"
    return SN_AND_RADIO_DEFAULT.get(lean, "Unrated")

STATES = {"Alabama":"AL","Alaska":"AK","Arizona":"AZ","Arkansas":"AR","California":"CA","Colorado":"CO","Connecticut":"CT","Delaware":"DE",
 "Florida":"FL","Georgia":"GA","Hawaii":"HI","Idaho":"ID","Illinois":"IL","Indiana":"IN","Iowa":"IA","Kansas":"KS","Kentucky":"KY",
 "Louisiana":"LA","Maine":"ME","Maryland":"MD","Massachusetts":"MA","Michigan":"MI","Minnesota":"MN","Mississippi":"MS","Missouri":"MO",
 "Montana":"MT","Nebraska":"NE","Nevada":"NV","New Hampshire":"NH","New Jersey":"NJ","New Mexico":"NM","New York":"NY",
 "North Carolina":"NC","North Dakota":"ND","Ohio":"OH","Oklahoma":"OK","Oregon":"OR","Pennsylvania":"PA","Rhode Island":"RI",
 "South Carolina":"SC","South Dakota":"SD","Tennessee":"TN","Texas":"TX","Utah":"UT","Vermont":"VT","Virginia":"VA","Washington State":"WA",
 "West Virginia":"WV","Wisconsin":"WI","Wyoming":"WY"}
ABBR = set(STATES.values())
STATE_RE = re.compile(r"\b(" + "|".join(sorted(map(re.escape, STATES), key=len, reverse=True)) + r")\b")
# Distinctive candidate surnames -> race (only unambiguous names)
CANDIDATES = {"Peltola":"AK-SEN","Talarico":"TX-SEN","Paxton":"TX-SEN","Cornyn":"TX-SEN","Ossoff":"GA-SEN","Husted":"OH-SEN",
 "Sherrod Brown":"OH-SEN","El-Sayed":"MI-SEN","el Sayed":"MI-SEN","El Sayed":"MI-SEN","McMorrow":"MI-SEN","Hinson":"IA-SEN","Roger Marshall":"KS-SEN","Susan Collins":"ME-SEN",
 "Platner":"ME-SEN","Troy Jackson":"ME-SEN","Turek":"IA-SEN","Haley Stevens":"MI-SEN","Mike Rogers":"MI-SEN","Mary Peltola":"AK-SEN","Dan Sullivan":"AK-SEN","Roy Cooper":"NC-SEN","Whatley":"NC-SEN","Pappas":"NH-SEN","Osborn":"NE-SEN","Ricketts":"NE-SEN",
 "Ramaswamy":"OH-GOV","Amy Acton":"OH-GOV","Lombardo":"NV-GOV","Aaron Ford":"NV-GOV","Keisha Lance Bottoms":"GA-GOV",
 "Rick Jackson":"GA-GOV","Holscher":"KS-GOV","Masterson":"KS-GOV","Hobbs":"AZ-GOV","Biggs":"AZ-GOV","Duggan":"MI-GOV",
 "Benson":"MI-GOV","Hochul":"NY-GOV","Stefanik":"NY-GOV","Blakeman":"NY-GOV","Shapiro":"PA-GOV","Mastriano":"PA-GOV","Garrity":"PA-GOV"}
CAND_RE = re.compile(r"\b(" + "|".join(map(re.escape, CANDIDATES)) + r")\b")
COMPETITIVE = {"AK-SEN","IA-SEN","KS-SEN","OH-SEN","TX-SEN","MI-SEN","GA-SEN","ME-SEN","NC-SEN","NH-SEN","NE-SEN","MN-SEN",
 "GA-GOV","KS-GOV","NV-GOV","OH-GOV","AZ-GOV","MI-GOV","WI-GOV","PA-GOV","AK-GOV","NE-GOV","IA-GOV","NY-GOV","ME-GOV",
 "US-HOUSE","US-SENATE",
 # House watch list (approximate battlegrounds)
 "AZ-01","AZ-06","CA-13","CA-22","CA-45","CO-05","CO-08","IA-01","IA-03","ME-02","MI-07","MI-10","NE-02","NJ-07","NM-02",
 "NY-04","NY-17","NC-01","OH-09","OH-13","PA-01","PA-07","PA-08","PA-10","SC-01","TX-28","TX-34","VA-02","WA-03","WI-03","NV-03","NV-04"}
ORD = re.compile(r"\b(%s)'s (\d{1,2})(?:st|nd|rd|th) (?:Congressional )?District" % "|".join(map(re.escape, STATES)))
CODE = re.compile(r"\b([A-Z]{2})-(\d{1,2})\b")
SEN = re.compile(r"\bSenat(e|or|orial)\b", re.I)
STATE_LEG = re.compile(r"\b(state senate|state senator|state house|legislat|assembly|senate district|house district \d)", re.I)
GOV = re.compile(r"\b(governor|gubernatorial|governor's race)\b", re.I)
HOUSE_CTRL = re.compile(r"\b(House (control|majority|balance)|control of the House|House Republicans|House Democrats|Speaker)\b", re.I)
SEN_CTRL = re.compile(r"\b(Senate (control|majority|balance)|control of the Senate)\b", re.I)
COMP_WORDS = re.compile(r"\b(toss-?up|battleground|swing (state|district|seat)|competitive|bellwether|flip(ped|s)?)\b", re.I)
SILVER = re.compile(r"\b(Nate Silver|Silver Bulletin)\b", re.I)
POLL = re.compile(r"\b(poll(s|ing|ster)?|forecast|averages?|odds|Kalshi|Polymarket|exit poll|model|projection|projects|projected|needle)\b", re.I)

def races(title, blurb, src_state):
    text = f"{title} {blurb}"
    out = []
    def add(r):
        if r not in out: out.append(r)
    for m in CODE.finditer(text):
        if m.group(1) in ABBR: add(f"{m.group(1)}-{int(m.group(2)):02d}")
    for m in ORD.finditer(text): add(f"{STATES[m.group(1)]}-{int(m.group(2)):02d}")
    for m in CAND_RE.finditer(text): add(CANDIDATES[m.group(1)])
    states = [STATES[m.group(1)] for m in STATE_RE.finditer(title)] or [STATES[m.group(1)] for m in STATE_RE.finditer(blurb)]
    if not states and src_state: states = [src_state]
    leg = STATE_LEG.search(text)
    for st in dict.fromkeys(states):
        if SEN.search(title) and not leg: add(f"{st}-SEN")
        if GOV.search(title): add(f"{st}-GOV")
    if not out and STATE_RE.search(blurb):  # blurb-only office mention needs an explicit state in the blurb
        for st in dict.fromkeys(STATES[m.group(1)] for m in STATE_RE.finditer(blurb)):
            if SEN.search(blurb) and not leg: add(f"{st}-SEN")
            if GOV.search(blurb): add(f"{st}-GOV")
    if HOUSE_CTRL.search(text): add("US-HOUSE")
    if SEN_CTRL.search(text): add("US-SENATE")
    return out

def tag(item, src):
    t, b = item["title"], item["blurb"]
    item["bias"] = bias(item["outlet"], src["name"], src["url"] + " " + item["link"], src["lean"], src["cat"])
    rs = races(t, b, src.get("state", ""))
    item["races"] = rs
    item["comp"] = any(r in COMPETITIVE for r in rs) or bool(COMP_WORDS.search(t))
    item["silver"] = bool(SILVER.search(f"{t} {b} {item['outlet']}")) or "natesilver" in src["url"]
    item["poll"] = item["silver"] or src["cat"] == "polls" or bool(POLL.search(t))
    return item
