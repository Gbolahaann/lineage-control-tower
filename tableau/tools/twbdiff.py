"""Diff a Tableau-saved workbook (GB's adjusted copy) against our build: worksheets (dependencies dropped), dashboards,
calc formulas. Tableau's re-save noise is normalised away (style and filter order, long floats, Æ markers, fold).
Usage: python3 tableau/tools/twbdiff.py <ours.twb> <theirs.twb> [sheet prefix] [dashboard name ...]"""
import sys, re, difflib, xml.etree.ElementTree as ET
mine, theirs, prefix = sys.argv[1], sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else ''

def canon(el, drop=('datasource-dependencies', 'simple-id')):
    out = []
    def walk(e, d):
        if e.tag in drop: return
        def norm(v):
            return re.sub(r'-?\d+\.\d{6,}', lambda m: f'{float(m.group(0)):.6g}', v).replace('Æ', '')
        at = ' '.join(f'{k}={norm(v)!r}' for k, v in sorted(e.attrib.items()) if k not in ('x', 'y', 'w', 'h', 'id') and not (k == 'fold'))
        at = re.sub(r"'(-?\d+)\.0'", r"'\1'", at)
        txt = norm((e.text or '')).strip()
        out.append('  ' * d + f'<{e.tag} {at}>' + (f' {txt}' if txt else ''))
        kids = list(e)
        if e.tag in ('style', 'style-rule', 'encodings', 'zone-style', 'slices', 'datasources', 'view'):
            kids = sorted(kids, key=lambda c: (c.tag, sorted(c.attrib.items()), ET.tostring(c)))
        for c in kids: walk(c, d + 1)
    walk(el, 0)
    return out

A, B = ET.parse(mine).getroot(), ET.parse(theirs).getroot()
def calcs(r):
    return {c.get('caption'): c.find('calculation').get('formula') for c in r.find('datasources').iter('column')
            if c.get('caption') and c.find('calculation') is not None}
ca, cb = calcs(A), calcs(B)
for k in sorted(set(ca) | set(cb)):
    if ca.get(k) != cb.get(k):
        print(f'=== CALC {k}\n  mine:   {ca.get(k)!r:.400}\n  theirs: {cb.get(k)!r:.400}')
wa = {w.get('name'): w for w in A.iter('worksheet')}
wb = {w.get('name'): w for w in B.iter('worksheet')}
for n in sorted(set(wa) | set(wb)):
    if not n.startswith(prefix): continue
    if n not in wa or n not in wb:
        print(f'=== SHEET {n} only in', 'mine' if n in wa else 'theirs'); continue
    d = list(difflib.unified_diff(canon(wa[n]), canon(wb[n]), lineterm='', n=1))
    if d: print(f'=== SHEET {n}'); print('\n'.join(d[2:]))
da = {x.get('name'): x for x in A.iter('dashboard')}
db = {x.get('name'): x for x in B.iter('dashboard')}
for n in sys.argv[4:]:
    d = list(difflib.unified_diff(canon(da[n]), canon(db[n]), lineterm='', n=1))
    if d: print(f'=== DASHBOARD {n}'); print('\n'.join(d[2:]))
