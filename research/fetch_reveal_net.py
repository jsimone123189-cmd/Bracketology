"""NET as of each top-16 reveal date, from Internet Archive captures of the NCAA NET page. Saved to data/history/{y}_net_reveal.json."""
import json
from bracketology import history
REVEAL = {2019: "2019-02-09", 2021: "2021-02-13", 2022: "2022-02-19", 2023: "2023-02-18", 2024: "2024-02-17", 2025: "2025-02-15", 2026: "2026-02-21"}
for y, day in REVEAL.items():
    got = None
    for s in sorted(history.captures(history.NET_URL, day), reverse=True):
        if s[:8] > day.replace("-", ""): continue          # capture must be on or before reveal day
        try: d = history.parse_net(history.snapshot(history.NET_URL, s))
        except Exception as e: print(y, s, "parse failed", repr(e)[:80]); continue
        if len(d["rows"]) > 300: got = (s, d); break
    if got:
        s, d = got; d["capture"] = s; json.dump(d, open(f"data/history/{y}_net_reveal.json", "w")); print(y, "reveal", day, "capture", s, "through", d.get("through"), len(d["rows"]))
    else: print(y, "reveal", day, "NO usable capture")
