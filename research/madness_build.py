"""Download the inputs for the March Madness tools into data/madness/ (git-ignored).
Wikipedia bracket wikitext (one raw request per season, 5 s apart) and Torvik game logs
(one CSV per season, 10 s apart per its robots.txt Crawl-Delay). Both are cached by http.fetch.
Run: PYTHONPATH=src python3 research/madness_build.py
"""
import json
import os
from bracketology.madness import wiki
from bracketology.sources import torvik

os.makedirs("data/madness", exist_ok=True)
for y in wiki.SEASONS:
    json.dump(wiki.season(y), open(f"data/madness/bracket_{y}.json", "w"))
    json.dump(torvik.collect_games(y, ttl=86400 * 365)["rows"], open(f"data/madness/games_{y}.json", "w"))
    print(y, flush=True)
