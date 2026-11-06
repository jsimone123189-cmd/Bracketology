from __future__ import annotations
"""Tournament formats. Every other module asks here for field size and seed-line sizes.
2027 comes from the NCAA's printable bracket and schedule pages: 76 teams, 32 automatic, 44 at-large; opening round 11v11 x2, 12v12 x4, 15v15 x2, 16v16 x4.
Its note says the 12 lowest at-large teams and 12 lowest automatic qualifiers play in. Past committees moved the at-large games between lines 10-12,
so the at-large lines here are the printed layout, not a guarantee. Some 68-team seasons had 31 automatic bids (2021, 2025, 2026). The model counts real champions, so these format counts only drive a live warning."""
from dataclasses import dataclass

@dataclass(frozen=True)
class Format:
    lines: tuple[int, ...]            # teams on seed lines 1-16
    automatic: int
    at_large: int
    opening_at_large: dict[int, int]  # seed line -> opening-round games
    opening_automatic: dict[int, int]

    def __post_init__(self):
        if sum(self.lines) != self.automatic + self.at_large: raise ValueError("line sizes must add up to the bids")
        games = {**self.opening_at_large, **self.opening_automatic}
        for line, n in enumerate(self.lines, 1):
            if n != 4 + games.get(line, 0): raise ValueError(f"line {line} has {n} teams and {games.get(line, 0)} opening-round games")

    @property
    def size(self) -> int: return sum(self.lines)
    @property
    def slots(self) -> list[int]: return [line for line, n in enumerate(self.lines, 1) for _ in range(n)]

FORMAT_68 = Format(tuple([4] * 10 + [6] + [4] * 4 + [6]), 32, 36, {11: 2}, {16: 2})
FORMAT_76 = Format(tuple([4] * 10 + [6, 8, 4, 4, 6, 8]), 32, 44, {11: 2, 12: 4}, {15: 2, 16: 4})

def format_for(season: int) -> Format:
    return FORMAT_76 if season >= 2027 else FORMAT_68

def line_sizes(season: int) -> list[int]:
    return list(format_for(season).lines)

def field_size(season: int) -> int:
    return format_for(season).size

def slot_lines(season: int) -> list[int]:
    return format_for(season).slots

def max_score(season: int) -> int:
    return field_size(season) * 6
