# Generates sources.json. Edit lists here, rerun.
import json
G = "https://news.google.com/rss/search?hl=en-US&gl=US&ceid=US:en&q="
def gn(q): return G + q.replace(" ", "+")
S = []
def add(name, url, lean, cat, state=""): S.append(dict(name=name, url=url, lean=lean, cat=cat, state=state))

# Ground-level
for n,u in [("Votebeat","https://www.votebeat.org/arc/outboundfeeds/rss/?outputType=xml"),
            ("Bolts","https://boltsmag.org/feed/"),
            ("Texas Tribune", gn("site:texastribune.org when:1d")),
            ("Bridge Michigan","https://www.bridgemi.com/rss.xml"),
            ("Spotlight PA","https://www.spotlightpa.org/feeds/full.xml"),
            ("Gothamist","https://gothamist.com/feed"),
            ("THE CITY","https://www.thecity.nyc/feed/"),
            ("City & State NY","https://www.cityandstateny.com/rss/all/"),
            ("Hell Gate","https://hellgatenyc.com/all-posts/rss/"),
            ("Stateline","https://stateline.org/feed/"),
            ("Mississippi Today","https://mississippitoday.org/feed/"),
            ("CalMatters","https://calmatters.org/feed/"),
            ("Votebeat (Google News)", gn("site:votebeat.org when:1d")),]:
    add(n,u,"ground","news")
SN = [("Alabama Reflector","alabamareflector.com","AL"),("Alaska Beacon","alaskabeacon.com","AK"),
 ("Arizona Mirror","azmirror.com","AZ"),("Arkansas Advocate","arkansasadvocate.com","AR"),
 ("Colorado Newsline","coloradonewsline.com","CO"),("Daily Montanan","dailymontanan.com","MT"),
 ("Florida Phoenix","floridaphoenix.com","FL"),("Georgia Recorder","georgiarecorder.com","GA"),
 ("Idaho Capital Sun","idahocapitalsun.com","ID"),("Indiana Capital Chronicle","indianacapitalchronicle.com","IN"),
 ("Iowa Capital Dispatch","iowacapitaldispatch.com","IA"),("Kansas Reflector","kansasreflector.com","KS"),
 ("Kentucky Lantern","kentuckylantern.com","KY"),("Louisiana Illuminator","lailluminator.com","LA"),
 ("Maine Morning Star","mainemorningstar.com","ME"),("Maryland Matters","marylandmatters.org","MD"),
 ("Michigan Advance","michiganadvance.com","MI"),("Minnesota Reformer","minnesotareformer.com","MN"),
 ("Missouri Independent","missouriindependent.com","MO"),("Nebraska Examiner","nebraskaexaminer.com","NE"),
 ("Nevada Current","nevadacurrent.com","NV"),("New Hampshire Bulletin","newhampshirebulletin.com","NH"),
 ("New Jersey Monitor","newjerseymonitor.com","NJ"),("Source NM","sourcenm.com","NM"),
 ("NC Newsline","ncnewsline.com","NC"),("North Dakota Monitor","northdakotamonitor.com","ND"),
 ("Ohio Capital Journal","ohiocapitaljournal.com","OH"),("Oklahoma Voice","oklahomavoice.com","OK"),
 ("Oregon Capital Chronicle","oregoncapitalchronicle.com","OR"),("Pennsylvania Capital-Star","penncapital-star.com","PA"),
 ("Rhode Island Current","rhodeislandcurrent.com","RI"),("SC Daily Gazette","scdailygazette.com","SC"),
 ("South Dakota Searchlight","southdakotasearchlight.com","SD"),("Tennessee Lookout","tennesseelookout.com","TN"),
 ("Utah News Dispatch","utahnewsdispatch.com","UT"),("Virginia Mercury","virginiamercury.com","VA"),
 ("Washington State Standard","washingtonstatestandard.com","WA"),("West Virginia Watch","westvirginiawatch.com","WV"),
 ("Wisconsin Examiner","wisconsinexaminer.com","WI"),("Mississippi Free Press","mississippifreepress.org","MS")]
for n,d,st in SN: add(n, f"https://{d}/feed/", "ground", "news", st)
# Public radio (Google News per-site, election-scoped: robust to unknown feed paths)
PR = [("NPR Politics","npr.org",""),("WUNC","wunc.org","NC"),("WHYY","whyy.org","PA"),
 ("WESA","wesa.fm","PA"),("Michigan Public","michiganpublic.org","MI"),("WPR","wpr.org","WI"),
 ("GPB","gpb.org","GA"),("WABE","wabe.org","GA"),("KJZZ","kjzz.org","AZ"),("KUNR / Nevada Public Radio","knpr.org","NV"),
 ("KQED","kqed.org","CA"),("LAist","laist.com","CA"),("WNYC","wnyc.org","NY"),("WBUR","wbur.org","MA"),
 ("NHPR","nhpr.org","NH"),("Maine Public","mainepublic.org","ME"),("MPR News","mprnews.org","MN"),
 ("KUT","kut.org","TX"),("Texas Standard","texasstandard.org","TX"),("Iowa Public Radio","iowapublicradio.org","IA"),
 ("Ohio Public Radio / Statehouse News","statenews.org","OH"),("VPM","vpm.org","VA"),("WAMU","wamu.org","DC"),
 ("Colorado Public Radio","cpr.org","CO"),("OPB","opb.org","OR"),("Alaska Public Media","alaskapublic.org","AK"),
 ("Montana Free Press","montanafreepress.org","MT"),("Nebraska Public Media","nebraskapublicmedia.org","NE"),
 ("WFAE","wfae.org","NC"),("WMFE / Central Florida Public Media","cfpublic.org","FL")]
for n,d,st in PR:
    add(n, d if d.startswith("http") else gn(f"site:{d} election when:1d"), "ground", "radio", st)
# County / state election offices (no RSS; Google News on official-source phrasing)
for n,q in [("County election offices", '"county elections" OR "board of elections" OR "county clerk" results when:1d'),
            ("Secretaries of State", '"secretary of state" election results 2026 when:1d'),
            ("Election administration problems", '(polling place OR ballots OR "voting machines") delay OR extended OR problem when:1d')]:
    add(n, gn(q), "ground", "offices")
# Left
for n,u in [("TPM","https://talkingpointsmemo.com/feed"),("The Downballot","https://www.the-downballot.com/feed"),
            ("MS NOW", gn("site:ms.now when:1d")),("Mother Jones","https://www.motherjones.com/feed/"),
            ("Daily Kos Elections", gn("site:dailykos.com election when:1d"))]:
    add(n,u,"left","news")
# Right
for n,u in [("National Review","https://www.nationalreview.com/feed/"),("Washington Examiner","https://www.washingtonexaminer.com/feed/"),
            ("The Dispatch","https://thedispatch.com/feed/"),("Free Beacon","https://freebeacon.com/feed/"),
            ("Daily Wire","https://www.dailywire.com/feeds/rss.xml"),
            ("Washington Examiner (GN)", gn("site:washingtonexaminer.com election when:1d"))]:
    add(n,u,"right","news")
# Calls & data
for n,u in [("AP", gn("site:apnews.com election when:1d")),("AP race calls", gn('"AP" "race call" OR "projected winner" OR "wins election" when:1d')),
            ("DDHQ (GN)", gn("decision desk HQ projects when:1d")),
            ("Reuters", gn("site:reuters.com election when:1d")),("Split Ticket","https://split-ticket.org/feed/"),
            ("Cook Political", gn("site:cookpolitical.com when:2d")),("Sabato's Crystal Ball", gn("site:centerforpolitics.org when:3d")),
            ("NYT Elections", gn("site:nytimes.com election results when:1d")),("Politico Elections", gn("site:politico.com election when:1d"))]:
    add(n,u,"wire","calls")
json.dump(S, open("sources.json","w"), indent=1)
print(len(S), "sources")
