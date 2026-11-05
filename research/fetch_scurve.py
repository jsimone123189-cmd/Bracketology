"""Committee's official overall seed order (1-68), from published CBS lists. Facts for training only, stored locally, not committed."""
import html, json, re, sys, time, requests
sys.path.insert(0, "src")
from bracketology.features import build_year
from bracketology.sources import bracketmatrix as bm
from bracketology.teams import key
S = "https://www.cbssports.com/college-basketball/news/"
U = {2019: S + "march-madness-2019-official-ncaa-tournament-bracket-seeding-from-1-68", 2021: S + "march-madness-2021-committee-reveals-official-ncaa-tournament-bracket-seeding-from-1-68",
     2022: S + "march-madness-2022-committee-reveals-official-ncaa-tournament-bracket-seed-list-from-1-68/", 2023: S + "march-madness-2023-committee-reveals-official-ncaa-tournament-bracket-seed-list-from-1-68",
     2024: S + "march-madness-2024-committee-reveals-official-ncaa-tournament-bracket-seed-list-from-1-68", 2025: S + "march-madness-2025-committee-reveals-official-ncaa-tournament-bracket-seed-list-from-1-68",
     2026: S + "ncaa-tournament-2026-seeds-1-68-march-madness-bracket/"}
EXTRA = {"mississippi": ["Ole Miss", "Mississippi"], "southerncalifornia": ["USC", "Southern California", "Southern Cal"], "uconn": ["UConn", "Connecticut"], "miamifl": ["Miami (FL)", "Miami (Fla.)", "Miami"],
         "miamioh": ["Miami (OH)", "Miami (Ohio)", "Miami Ohio"], "loyolachicago": ["Loyola Chicago", "Loyola-Chicago", "Loyola (IL)", "Loyola"], "saintmarysca": ["Saint Mary's (CA)", "Saint Mary's", "St. Mary's", "St. Mary's (CA)"],
         "stjohnsny": ["St. John's (NY)", "St. John's"], "appstate": ["Appalachian State", "Appalachian St.", "App State"], "ncstate": ["NC State", "N.C. State", "North Carolina State"], "northcarolinastate": ["NC State", "N.C. State", "North Carolina State"],
         "nccentral": ["N.C. Central", "NC Central", "North Carolina Central"], "ncaandt": ["N.C. A&T", "North Carolina A&T"], "uni": ["Northern Iowa", "UNI"], "floridaatlantic": ["Florida Atlantic", "FAU", "Fla. Atlantic"], "floridagulfcoast": ["Florida Gulf Coast", "FGCU"], "fgcu": ["Florida Gulf Coast", "FGCU"],
         "fdu": ["Fairleigh Dickinson", "FDU"], "liu": ["Long Island", "LIU", "Long Island University"], "ucsb": ["UC Santa Barbara"], "uncw": ["UNCW", "UNC Wilmington", "NC-Wilmington"], "uncwilmington": ["UNCW", "UNC Wilmington"], "siue": ["SIUE", "SIU Edwardsville", "SIU-Edwardsville"],
         "saintfrancis": ["Saint Francis", "St. Francis (PA)", "Saint Francis (PA)", "St. Francis"], "prairieview": ["Prairie View", "Prairie View A&M"], "acollegeofcharleston": [], "colofcharleston": ["Charleston", "College of Charleston", "Col. of Charleston"], "akron": ["Akron"],
         "tamucc": [], "aandmcorpuschristi": ["Texas A&M-Corpus Christi", "Texas A&M-CC", "Texas A&M Corpus Christi", "A&M-Corpus Christi", "TAMU-CC"], "gramblingstate": ["Grambling"], "grambling": ["Grambling State", "Grambling St.", "Grambling"], "mcneese": ["McNeese", "McNeese State", "McNeese St."], "kennesawstate": ["Kennesaw State", "Kennesaw St."],
         "easternwashington": ["Eastern Washington", "Eastern Wash."], "northernkentucky": ["Northern Kentucky", "Northern Ky."], "southeastmissouristate": ["Southeast Missouri State", "Southeast Mo. St.", "SE Missouri State"], "californiabaptist": ["Cal Baptist", "California Baptist"], "calstatefullerton": ["Cal State Fullerton", "Cal St. Fullerton"], "calstfullerton": ["Cal State Fullerton", "Cal St. Fullerton"], "unc": [], "umbc": ["UMBC"], "penn": ["Penn", "Pennsylvania"], "wrightstate": ["Wright State", "Wright St."], "hawaii": ["Hawaii", "Hawai'i"], "omaha": ["Omaha", "Nebraska Omaha"], "stpeters": [], "saintpeters": ["Saint Peter's", "St. Peter's"], "northcarolinacentral": ["N.C. Central", "NC Central", "North Carolina Central"], "northcarolinaat": ["N.C. A&T"], "unca": [], "uncasheville": ["UNC Asheville", "NC-Asheville"], "uncgreensboro": ["UNC Greensboro", "UNCG"], "louisiana": ["Louisiana", "Louisiana-Lafayette", "Louisiana Lafayette"], "centralflorida": [], "ucf": ["UCF"]}
def variants(*names):
    v = set()
    for n in names:
        if not n: continue
        v |= {n, n.replace(" St.", " State"), n.replace(" State", " St."), n.replace("Saint ", "St. "), n.replace("St. ", "Saint ")}
    return v
out = {}
for y, u in U.items():
    r = requests.get(u, headers={"User-Agent": "Mozilla/5.0 (compatible; bracketology-research/0.1)"}, timeout=40)
    x = html.unescape(re.sub(r"\s+", " ", re.sub(r"<(script|style).*?</\1>|<[^>]+>", " ", r.text, flags=re.S))).replace("lowa", "Iowa").replace("lona", "Iona"); x = re.sub(r"\s+\.", ".", x)
    field = [t for t in build_year(y) if t["in_field"]]; off = {t["key"]: t["seed"] for t in field}
    mx = {key(t): t for t in bm.collect(y)["official"]}
    alias = []
    for t in field:
        for v in variants(t["team"], mx.get(t["key"]), *EXTRA.get(t["key"], [])):
            alias.append((v, t["key"]))
    alias.sort(key=lambda a: -len(a[0]))
    pat = re.compile(r"(?<![A-Za-z'\.-])(" + "|".join(re.escape(a) for a, _ in alias) + r")(?![A-Za-z'])")
    mp = {}
    for a, k in alias: mp.setdefault(a, k)
    hits = [mp[m[1]] for m in pat.finditer(x)]
    idx = range(max(1, len(hits) - 40)); best = max(len(set(hits[i:i + 68])) for i in idx)
    start = max(i for i in idx if len(set(hits[i:i + 68])) == best)   # the list = densest run of distinct field teams; latest start skips prose before it
    seq, seen = [], set()
    for k in hits[start:]:
        if k not in seen: seen.add(k); seq.append(k)
        if len(seq) == 68: break
    miss = [t["team"] for t in field if t["key"] not in seen]
    lines = [off[k] for k in seq]
    bad = sum(b < a for a, b in zip(lines, lines[1:]))
    print(y, r.status_code, "found", len(seq), "missing", miss, "out-of-order steps", bad, "max drop", max([a - b for a, b in zip(lines, lines[1:])] + [0]), seq[:3], seq[-1:], flush=True)
    out[y] = seq; time.sleep(3)
json.dump(out, open("data/history/scurve.json", "w"))
