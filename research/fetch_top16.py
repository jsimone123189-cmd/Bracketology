"""NCAA in-season Top-16 reveal (official, published about a month before Selection Sunday). Used only as a pre-selection feature."""
import html, json, re, sys, time, requests
sys.path.insert(0, "src")
from bracketology.features import build_year
from bracketology.teams import key
B = "https://www.ncaa.com/news/basketball-men/article/"
U = {2019: B + "2019-02-09/march-madness-top-16-teams-revealed-season-look-ncaa", 2021: B + "2021-02-13/division-i-mens-basketball-committee-unveils-top-16-teams-bracket-preview-show",
     2022: B + "2022-02-19/gonzaga-auburn-arizona-kansas-no-1-seeds-ncaa-mens-basketball-committee-top-16", 2023: B + "2023-02-18/division-i-mens-basketball-committee-reveals-top-16-seeds-three-weeks-selection",
     2024: B + "2024-02-17/purdue-tops-season-division-i-mens-basketball-committee-rankings", 2025: B + "2025-02-15/division-i-mens-basketball-committee-reveals-top-16-seeds-one-month-selection",
     2026: B + "2026-02-21/michigan-duke-arizona-and-iowa-st-lead-division-i-mens-basketball-top-16-reveal"}
for y, u in U.items():
    r = requests.get(u, headers={"User-Agent": "bracketology-bot/0.1 (free open bracketology project)"}, timeout=40)
    t = r.text; cells = [re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", x))).strip() for x in re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", t, re.S)]
    x = html.unescape(re.sub(r"\s+", " ", re.sub(r"<(script|style).*?</\1>|<[^>]+>", " ", t, flags=re.S)))
    print(y, r.status_code, len(t), "cells", len(cells), cells[:14]); i = max(x.find("overall"), 0); print("   ", x[i - 100:i + 500]); time.sleep(2)
print("=====")
out={}
for y,u in U.items():
    t=requests.get(u,headers={"User-Agent":"bracketology-bot/0.1 (free open bracketology project)"},timeout=40).text
    x=html.unescape(re.sub(r"\s+"," ",re.sub(r"<(script|style).*?</\1>|<[^>]+>"," ",t,flags=re.S)))
    i=[m.start() for m in re.finditer(r"(Top 16|top 16|seed list|Region)",x)]
    cand=re.findall(r"(?<![\d-])(\d{1,2})[\.\)]\s+([A-Z][A-Za-z\.'& ]{2,24}?)(?=\s+\(|\s*\d{1,2}[\.\)]|\s*[,;]|\s{2}|\s+[A-Z]{2,})",x)
    print(y,[c for c in cand if int(c[0])<=16][:22])
    j=x.find("South Region") if "South Region" in x else x.find("Region")
    print("   ",x[max(0,j-80):j+520])
    time.sleep(2)
