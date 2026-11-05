from __future__ import annotations
"""Team identity normalization across sources. Canonical key = lowercase alnum of a cleaned name.
Explicit ALIASES cover known cross-source differences; anything unmatched is reported, never silently dropped."""
import re

ALIASES = {  # source variant (already key-normalized) -> canonical key
    "connecticut": "uconn", "stjohnsny": "stjohns", "saintjohns": "stjohns",
    "miamifl": "miamifl", "miamifla": "miamifl", "miamiflorida": "miamifl", "miamioh": "miamioh", "miamiohio": "miamioh",
    "nccharlotte": "charlotte", "unclarlotte": "charlotte", "loyolachi": "loyolachicago", "loyolaillinois": "loyolachicago",
    "unc": "northcarolina", "ncstate": "northcarolinastate", "pittsburgh": "pitt", "ole miss": "mississippi",
    "olemiss": "mississippi", "usc": "southerncalifornia", "ucfloridacentral": "ucf", "centralflorida": "ucf",
    "lsu": "lsu", "smu": "smu", "byu": "byu", "vcu": "vcu", "unlv": "unlv", "utsa": "utsa", "uab": "uab",
    "stmarysca": "stmarys", "saintmarys": "stmarys", "stmaryscalifornia": "stmarys", "saintmaryscalifornia": "stmarys",
    "stbonaventure": "stbonaventure", "saintbonaventure": "stbonaventure", "stlouis": "saintlouis",
    "sanjosest": "sanjosestate", "sdsu": "sandiegostate", "utahst": "utahstate", "bostoncollege": "bostoncollege",
    "texasam": "texasam", "texasamcc": "texasamcorpuschristi", "tamucc": "texasamcorpuschristi",
    "etsu": "easttennesseestate", "umbc": "umbc", "liu": "liu", "liubrooklyn": "liu", "longislandu": "liu",
    "uic": "illinoischicago", "uiuc": "illinois", "queens": "queensnc", "queensnc": "queensnc",
    "southernmiss": "southernmississippi", "fau": "floridaatlantic", "fiu": "floridainternational",
    "nebraskaomaha": "omaha", "uncwilmington": "uncwilmington", "uncw": "uncwilmington",
    "uncgreensboro": "uncgreensboro", "uncg": "uncgreensboro", "uncasheville": "uncasheville", "unca": "uncasheville",
    "pennsylvania": "penn", "bethunecookman": "bethunecookman", "cspolo": "calpoly", "calpoly": "calpoly",
}

# NCAA.com abbreviates ("Ill.", "Ky.", "Mich."); expand tokens so they equal full names used elsewhere.
ABBREV = {"ark": "arkansas", "ill": "illinois", "mich": "michigan", "ky": "kentucky", "conn": "connecticut",
          "colo": "colorado", "ariz": "arizona", "fla": "florida", "ga": "georgia", "mo": "missouri",
          "tenn": "tennessee", "wash": "washington", "ind": "indiana", "la": "louisiana", "caro": "carolina",
          "mass": "massachusetts", "miss": "mississippi", "ala": "alabama", "pa": "pennsylvania", "okla": "oklahoma"}

# Torvik / game-log name -> NCAA.com name (NCAA list is the canonical D-I universe). Verified 41/41 against 2026 data.
TORVIK_TO_NCAA = {'Albany': 'UAlbany', 'Alcorn St.': 'Alcorn', 'Appalachian St.': 'App State', 'Arkansas Pine Bluff': 'Ark.-Pine Bluff', 'Army': 'Army West Point', 'Boston University': 'Boston U.', 'Cal Baptist': 'California Baptist', 'Cal St. Bakersfield': 'CSU Bakersfield', 'Cal St. Northridge': 'CSUN', 'Central Connecticut': 'Central Conn. St.', 'Charleston': 'Col. of Charleston', 'Charleston Southern': 'Charleston So.', 'Fairleigh Dickinson': 'FDU', 'Florida Gulf Coast': 'FGCU', 'Grambling St.': 'Grambling', 'Incarnate Word': 'UIW', 'Lamar': 'Lamar University', 'Louisiana Monroe': 'ULM', 'Loyola MD': 'Loyola Maryland', 'Loyola Marymount': 'LMU (CA)', 'Maryland Eastern Shore': 'UMES', 'McNeese St.': 'McNeese', 'Mississippi': 'Ole Miss', 'Mississippi Valley St.': 'Mississippi Val.', 'Nicholls St.': 'Nicholls', 'North Carolina A&T': 'N.C. A&T', 'North Carolina Central': 'N.C. Central', 'Northern Illinois': 'NIU', 'Northern Iowa': 'UNI', 'Prairie View A&M': 'Prairie View', 'SIU Edwardsville': 'SIUE', "Saint Mary's": "Saint Mary's (CA)", 'Sam Houston St.': 'Sam Houston', 'Seattle': 'Seattle U', 'Southern': 'Southern U.', 'St. Thomas': 'St. Thomas (MN)', 'Stephen F. Austin': 'SFA', 'Tennessee Martin': 'UT Martin', 'Texas A&M Corpus Chris': 'A&M-Corpus Christi', 'UMKC': 'Kansas City', 'UT Rio Grande Valley': 'UTRGV'}

# Bracket Matrix / older spellings -> NCAA.com name.
# Warren Nolan spellings, verified 20/20 against the 2026 NCAA list.
WARRENNOLAN_TO_NCAA = {"Saint Mary's College": "Saint Mary's (CA)", 'Saint Thomas': 'St. Thomas (MN)', 'Sam Houston State': 'Sam Houston', 'Seattle University': 'Seattle U', 'UTA': 'UT Arlington', 'Loyola-Marymount': 'LMU (CA)', 'Cal State Northridge': 'CSUN', 'UMass': 'Massachusetts', 'Tennessee-Martin': 'UT Martin', 'Southeast Missouri': 'Southeast Mo. St.', 'Presbyterian College': 'Presbyterian', "Mount Saint Mary's": "Mount St. Mary's", 'South Carolina Upstate': 'USC Upstate', 'Grambling State': 'Grambling', 'Arkansas-Pine Bluff': 'Ark.-Pine Bluff', 'IU Indianapolis': 'IU Indy', 'Cal State Bakersfield': 'CSU Bakersfield', 'Alcorn State': 'Alcorn', 'Saint Francis (PA)': 'Saint Francis', 'Mississippi Valley State': 'Mississippi Val.'}

MATRIX_TO_NCAA = {"Louisiana Lafayette": "Louisiana", "Detroit": "Detroit Mercy", "Fort Wayne": "Purdue Fort Wayne", "St. Francis PA": "Saint Francis", "St. Mary's (CA)": "Saint Mary's (CA)", 'Cal State Fullerton': 'Cal St. Fullerton', "St. Peter's": "Saint Peter's", 'Texas A&M-Corpus Christi': 'A&M-Corpus Christi', 'College of Charleston': 'Col. of Charleston', 'Louisiana-Lafayette': 'Louisiana', 'NC-Asheville': 'UNC Asheville', 'McNeese State': 'McNeese', 'NC-Wilmington': 'UNC Wilmington', 'SIU-Edwardsville': 'SIUE', 'St. Francis (PA.)': 'Saint Francis', 'Long Island': 'LIU', 'Appalachian State': 'App State'}

def clean(name: str) -> str:
    name = TORVIK_TO_NCAA.get(name.strip(), MATRIX_TO_NCAA.get(name.strip(), WARRENNOLAN_TO_NCAA.get(name.strip(), name)))
    n = name.strip().lower()
    n = re.sub(r"\s+\d+\*?$", "", n)          # V1 workbook annotations like "Merrimack 153", "LIU 227*"
    n = n.replace("*", "").replace("&", "and")
    return n

def key(name: str) -> str:
    n = clean(name)
    n = re.sub(r"[^a-z0-9 ]", "", n)
    # 'Mich St' / 'Michigan St.' -> state; 'St John's' -> saint handled via aliases
    toks = [ABBREV.get(t, t) for t in n.split()]
    if toks and toks[-1] == "st" and len(toks) > 1:
        toks[-1] = "state"
    n = "".join(toks)
    return ALIASES.get(n, n)

class TeamIndex:
    """Maps source-specific names to one canonical key, tracking what was unmatched."""
    def __init__(self, canonical_names: list[str]):
        self.canon = {key(n): n for n in canonical_names}
    def resolve(self, name: str) -> str | None:
        k = key(name)
        return k if k in self.canon else None
    def unmatched(self, names) -> list[str]:
        return sorted({n for n in names if self.resolve(n) is None})
