"""Faithful re-implementation of the original Excel model (V1). Logic is NOT changed;
quirks (blank L-N, empty R column, rank>200 non-monotonicity) are reproduced on purpose.
Usage: python -I v1/reproduce_v1.py v1/Bracketology_V1_original.xlsx"""
import sys, openpyxl

def s(rank):  # Excel: 100*(1-(x-1)/(200-1))^2  -- NOT clamped at 200 (V1 quirk)
    return 100 * (1 - (rank - 1) / 199) ** 2

def v1_scores(row):  # row: dict of B..K (blank -> 0, as Excel treats blanks)
    g = lambda k: row.get(k) or 0
    O = (g('B')*.15 + g('C')*.13 + g('D')*.12 + 0            # 0 == blank R-cell the formula points at
         - g('E')*.5 - g('F')*1.5 + g('G')*.06
         + .24*s(g('H')) + .19*s(g('I')) + .17*s(g('J')) + .10*s(g('K')))
    P = O + .03*s(g('L')) + .025*s(g('M')) + .025*s(g('N'))   # L-N blank -> rank 0
    return O, P

if __name__ == '__main__':
    p = sys.argv[1]
    f = openpyxl.load_workbook(p)['Sheet1']; v = openpyxl.load_workbook(p, data_only=True)['Sheet1']
    worst = 0
    for r in range(2, 80):
        row = {c: f[f'{c}{r}'].value for c in 'BCDEFGHIJK'}
        O, P = v1_scores(row)
        worst = max(worst, abs(O - v[f'O{r}'].value), abs(P - v[f'P{r}'].value))
    print(f'rows 2-79 reproduced; max abs diff vs Excel cached values = {worst:.2e}')
