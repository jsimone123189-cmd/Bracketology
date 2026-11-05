from __future__ import annotations
"""Field size and seed-line sizes by season. 2027 line sizes come from the live preseason Bracket Matrix layout and
are an ASSUMPTION until the NCAA's first 76-team bracket; past seasons did not always match the usual sizes either."""
LINES_68 = [4] * 10 + [6] + [4] * 4 + [6]
LINES_76 = [4] * 9 + [6, 8] + [4] * 3 + [6, 8]

def line_sizes(season: int) -> list[int]:
    return LINES_76 if season >= 2027 else LINES_68

def field_size(season: int) -> int:
    return sum(line_sizes(season))

def slot_lines(season: int) -> list[int]:
    return [line for line, n in enumerate(line_sizes(season), 1) for _ in range(n)]

def max_score(season: int) -> int:
    return field_size(season) * 6
