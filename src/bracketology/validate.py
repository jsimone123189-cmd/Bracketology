from __future__ import annotations
"""Missing-data validation. Returns a list of problems; empty list = healthy."""
def check(net: dict, torvik: dict, games: dict, unmatched: dict[str, list[str]]) -> list[str]:
    p = []
    if len(net["rows"]) < 340: p.append(f"NET rows {len(net['rows'])} < 340")
    if len(torvik["rows"]) < 340: p.append(f"Torvik rows {len(torvik['rows'])} < 340")
    if len(games["rows"]) < 1000: p.append(f"game rows {len(games['rows'])} suspiciously low")
    if sorted(r["net"] for r in net["rows"])[:3] != [1, 2, 3]: p.append("NET ranks do not start 1,2,3")
    nul = sum(1 for r in torvik["rows"] if r["wab"] is None)
    if nul: p.append(f"{nul} Torvik rows missing WAB")
    for src, names in unmatched.items():
        if names: p.append(f"{src}: {len(names)} unmatched team names, e.g. {names[:5]}")
    return p
