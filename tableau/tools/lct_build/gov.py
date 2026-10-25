"""Tab 8, Governance (GOV): calc pack section 11, build plan 3.9.

GB's choices (24 Oct): the unregistered consumers table, the AI sprawl list and coverage by domain as canvases like
Blast radius; gaps as short lists with "and N more"; hygiene and maturity in the prototype's bar style; the sprawl
callout shortened so it shows in full.

Everything here is a snapshot of the node catalogue plus query history, so the build works the tables out per period
and platform (the prototype's rules, checked against its figures) and Tableau switches them with the parameters.

- KPIs: ownership and documentation coverage (live, dim_nodes), test coverage (the Data quality sheet), declared
  consumers (the build's figures, so they agree with the table).
- Unregistered consumers: one canvas row per principal on its own query-history rows; the reads on two lines.
- AI-built dashboard sprawl: one two-line row per AI-assisted dashboard on its Exposure Daily rows.
- Coverage by domain, hygiene by team, exposure maturity and gaps to close: "scenes" on the 90-row date table, every
  rectangle 4 rows and every text one row, written per platform.
- Gaps: every item in each section; the list scrolls (GB, v44).

GB's v44 review: the unregistered table's columns spread across the card, row lines on coverage by domain (a layer of
its own, so the chips keep their date rows), and the gaps list scrolls with every item.
"""

from __future__ import annotations

import collections
import csv
import datetime as dt

from . import shapes as SH
from .core import (PANEL_WRITES, ACCENT, B_DIM, CALCS, CARD, CRIT, CRIT_INK, CRIT_TINT, GOOD, GOOD_INK, GOOD_TINT, I_DIM,
                   INK1, INK2, INK3, LAT, LINE, LINE_SOFT, LON, NAVY, NL, R_MEA, S_DIM, S_MEA, SEMI, SP_MEA, WARN, WARN_INK,
                   WARN_TINT, Cross, Nest, Pane, R, Sheet, Z, blank, card, card_header, color_map, label_pane, run, sheet, text)
from .lineage import _fit, _grid, _q, _wrap
from .shell import CONTENT_H, CONTENT_PAD
from .usage import W7, W8, _calc, _case, _rounded

P = 'GOV'
ROOT = SH.ROOT
M = ROOT / 'data' / 'marts'
NODES = {r['node_id']: r for r in csv.DictReader(open(M / 'dim_nodes.csv', encoding='utf-8'))}
ORDER = list(NODES)
PERIODS, PLATFORMS = (7, 30, 90), ('All', 'snowflake', 'databricks', 'redshift')
ASOF = dt.date(2026, 10, 19)
COMBO = 'STR([p_period]) + "|" + [p_platform]'
KIND = {'service': 'Service account', 'human': 'Personal login', 'agent': 'Agent', 'app': 'App'}
BAND = lambda v: None if v is None else 'Good' if v >= 0.9 else 'Fair' if v >= 0.7 else 'Poor'
BAND_TINT = {'Good': GOOD_TINT, 'Fair': WARN_TINT, 'Poor': CRIT_TINT}
BAND_INK = {'Good': GOOD_INK, 'Fair': WARN_INK, 'Poor': CRIT_INK}
BAND_BAR = {'Good': GOOD, 'Fair': WARN, 'Poor': CRIT}

# ---------------------------------------------------------------- geometry (content 1312 x CONTENT_H)
KPI_H, MID_H = 96, 356
SIDE = 428                                       # sprawl, domain, hygiene and gaps cards
UNREG_CARD = 1312 - SIDE - 7 - 7                 # 870
BOTTOM_H = CONTENT_H - KPI_H - 14 - MID_H - 14   # 364
UW = UNREG_CARD - 2 * 16 - 2 - SH.SLACK          # 832: unregistered table canvas
SW = SIDE - 2 * 16 - 2 - SH.SLACK                # 390: the side canvases
GW = SW - 18                                     # 372: the gaps list, room for its scroll bar (GB, v44)
UNREG_ROW, SPRAWL_ROW, DOMAIN_ROW, HEAD_H = 40, 45, 30, 22


def _num(v):
    return None if v in ('', None) else float(v)


def _in_plat(n, plat):
    return plat == 'All' or f'|{plat}|' in n['platform_filter_values']


def _short(d):
    return f'{d.day} {d:%b}'


# ================================================================ the build's figures

ACCESS = list(csv.DictReader(open(M / 'mart_observed_access.csv', encoding='utf-8')))
EXP_DAYS = collections.defaultdict(dict)
for _r in csv.DictReader(open(M / 'mart_exposure_daily.csv', encoding='utf-8')):
    EXP_DAYS[_r['exposure_id']][(ASOF - dt.date.fromisoformat(_r['date'])).days] = _r
BLAST = list(csv.DictReader(open(M / 'mart_blast_radius.csv', encoding='utf-8')))


def _unregistered():
    """Per combination: readers in the window that no declared exposure accounts for (the prototype's und list), and
    the declared share."""
    first = {}
    for r in ACCESS:
        first[r['principal']] = min(first.get(r['principal'], r['date']), r['date'])
    out, declared = {}, {}
    for per in PERIODS:
        for plat in PLATFORMS:
            win = [r for r in ACCESS if (ASOF - dt.date.fromisoformat(r['date'])).days < per and float(r['query_count'] or 0) > 0
                   and _in_plat(NODES[r['node_id']], plat)]
            prin = {r['principal'] for r in win}
            mapped = {r['principal'] for r in win if r['is_registered'] == 'True'}
            rows = []
            for p in sorted(prin - mapped):
                rs = [r for r in win if r['principal'] == p]
                rows.append(dict(p=p, kind=KIND.get(rs[0]['principal_type'], rs[0]['principal_type']),
                                 reads=sorted({NODES[r['node_id']]['node_name'] for r in rs}), q=sum(float(r['query_count']) for r in rs),
                                 gb=sum(float(r['bytes_scanned']) for r in rs) / 1e9, cost=sum(float(r['est_cost_usd'] or 0) for r in rs),
                                 first=dt.date.fromisoformat(first[p]), likely=(rs[0]['inferred_exposure_name'] or '-').replace('Unregistered: ', ''),
                                 exp=rs[0]['inferred_exposure_id']))
            out[(per, plat)] = sorted(rows, key=lambda x: -x['q'])
            declared[(per, plat)] = (len(mapped), len(prin))
    return out, declared


UNREG, DECLARED = _unregistered()


def _sprawl():
    dash = [k for k in ORDER if NODES[k]['resource_type'] == 'exposure' and NODES[k]['build_method'] == 'ai_assisted'
            and NODES[k]['exposure_type'] == 'dashboard']
    vals = {}
    for per in PERIODS:
        for k in dash:
            d = EXP_DAYS.get(k, {})
            ev = sum(_num(d[b]['events']) or 0 for b in range(per) if b in d)
            pv = sum(_num(d[b]['events']) or 0 for b in range(per, 2 * per) if b in d) if 2 * per <= 90 else None
            vals[(per, k)] = (ev, (ev - pv) / pv if pv else None)
    sem = collections.Counter()
    for r in BLAST:
        if r['exposure_id'] in dash and r['hops'] in ('1', '1.0') and NODES[r['node_id']]['resource_type'] == 'semantic':
            sem[(r['exposure_id'], r['node_id'])] += 1
    return dash, vals, sem


SPRAWL, SPRAWL_VALS, SPRAWL_SEM = _sprawl()


def _catalogue(plat):
    mods = [k for k in ORDER if NODES[k]['resource_type'] == 'model' and _in_plat(NODES[k], plat)]
    exps = [k for k in ORDER if NODES[k]['resource_type'] == 'exposure' and _in_plat(NODES[k], plat)]
    desc = lambda k: NODES[k]['has_description'] == 'True'
    tested = lambda k: (_num(NODES[k]['test_count']) or 0) > 0
    owned = lambda k: NODES[k]['owner_name'] not in ('', 'No owner')
    domains = []
    for d in sorted({NODES[k]['domain'] for k in mods + exps}):
        m = [k for k in mods if NODES[k]['domain'] == d]
        e = [k for k in exps if NODES[k]['domain'] == d]
        share = lambda xs, f: sum(1 for k in xs if f(k)) / len(xs) if xs else None
        domains.append((d, len(m), share(m, desc), share(m, tested), share(e, owned)))
    teams = []
    for t in sorted({NODES[k]['owner_team'] for k in ORDER if NODES[k]['owner_team'] and NODES[k]['resource_type'] in ('model', 'source')}):
        ns = [k for k in ORDER if NODES[k]['owner_team'] == t and NODES[k]['resource_type'] in ('model', 'source') and _in_plat(NODES[k], plat)]
        if not ns:
            continue
        ms = [k for k in ns if NODES[k]['resource_type'] == 'model']
        d_ = sum(1 for k in ns if desc(k)) / len(ns)
        tc = sum(1 for k in ms if tested(k)) / len(ms) if ms else 1
        teams.append((t, (d_ + tc) / 2, len(ns), d_, tc))
    teams.sort(key=lambda x: x[1])
    mat = collections.Counter(NODES[k]['maturity'] for k in exps)
    gaps = dict(owner=[NODES[k]['display_name'] for k in exps if not owned(k)], tests=[NODES[k]['node_name'] for k in mods if not tested(k)],
                desc=[NODES[k]['node_name'] for k in mods if not desc(k)])
    return dict(domains=domains, teams=teams, mat=mat, gaps=gaps, n_mods=len(mods), n_exps=len(exps))


CAT = {plat: _catalogue(plat) for plat in PLATFORMS}


# ================================================================ scenes on the date table

def _scene_calcs(prefix, scenes, key_expr, pane, styles):
    """Rectangles (4 date rows each) and texts (one row each) per key. scenes: {key: (rects, texts)}, rects
    [(x0, y0, x1, y1, colour key)], texts [(style, text, centre x, centre y)]. Writes {prefix} Rect Point / Rect Key /
    Rect Id and one Text + Point pair per style."""
    pw, ph = pane
    lat = lambda y: f'{(ph / 2 - y) / 100:.4f}'
    lon = lambda x: f'{(x - pw / 2) / 100:.4f}'
    pts, keys, txt = {}, {}, collections.defaultdict(dict)
    for key, (rects, texts) in scenes.items():
        n_rects = len(rects)
        assert n_rects * 4 <= 90 and len(texts) <= 90, f'{prefix} {key}: {n_rects} rects, {len(texts)} texts'
        for i, (x0, y0, x1, y1, ck) in enumerate(rects):
            for c, (x, y) in enumerate(((x0, y0), (x1, y0), (x1, y1), (x0, y1))):
                pts[f'{key}|{i * 4 + c}'] = f'MAKEPOINT({lat(y)}, {lon(x)})'
            keys[f'{key}|{i}'] = ck
        for t, (style, s, cx, cy) in enumerate(texts):
            txt[style][f'{key}|{t}'] = (s, f'MAKEPOINT({lat(cy)}, {lon(cx)})')
    row = f'{key_expr} + "|" + STR([day_index])'
    f = {f'{prefix} Rect Point': _calc(f'{prefix} Rect Point', 'Rectangles of the scene, 4 date rows each (written by the build).', _case(row, pts, quote=False)),
         f'{prefix} Rect Id': _calc(f'{prefix} Rect Id', 'Which rectangle a date row draws.', 'INT([day_index] / 4)'),
         f'{prefix} Rect Key': _calc(f'{prefix} Rect Key', 'Rectangle colour.', _case(f'{key_expr} + "|" + STR(INT([day_index] / 4))', keys))}
    for style in styles:
        d = txt.get(style, {})
        f[f'{prefix} {style} Text'] = _calc(f'{prefix} {style} Text', f'{style} texts of the scene.', _case(row, {k: v[0] for k, v in d.items()}))
        f[f'{prefix} {style} Point'] = _calc(f'{prefix} {style} Point', f'Where each {style.lower()} text sits (centred at half its measured width).',
                                             _case(row, {k: v[1] for k, v in d.items()}, quote=False))
    t = {n: (SP_MEA if n.endswith('Point') else I_DIM if n.endswith('Id') else S_DIM) for n in f}
    return f, t


def _left(x, s, w=W8):
    return x + w(s) / 2


def _right(x, s, w=W8):
    return x - w(s) / 2


def domain_scenes():
    pane = (SW, 6 * DOMAIN_ROW + 2)
    cols = {'models': 150, 'docs': 205, 'tests': 275, 'owned': 345}     # chip left edges; models right edge
    scenes, lines = {}, {}
    for plat in PLATFORMS:
        rects, texts = [], []
        doms = CAT[plat]['domains'][:6]
        # row lines on a layer of their own (GB, v44): 18 chips x 4 rows already use 72 of the date table's 90 rows
        lines[plat] = ([(0, (i + 1) * DOMAIN_ROW, SW, (i + 1) * DOMAIN_ROW + 1, 'Line') for i in range(len(doms) - 1)], [])
        for i, (d, m, docs, tests, own) in enumerate(doms):
            y = i * DOMAIN_ROW + DOMAIN_ROW / 2
            texts += [('Name', d, _left(8, d), y), ('Name', str(m), _right(cols['models'], str(m)), y)]
            for col, v in (('docs', docs), ('tests', tests), ('owned', own)):
                x0 = cols[col]
                if v is None:
                    texts.append(('Dash', '-', x0 + 22, y))
                    continue
                s = f'{v * 100:.0f}%'
                rects.append((x0, y - 8, x0 + 44, y + 8, BAND(v)))
                texts.append((BAND(v), s, x0 + 22, y))
        scenes[plat] = (rects, texts)
    heads = [('DOMAIN', 8, 'l'), ('MODELS', cols['models'], 'r'), ('DOCS', cols['docs'] + 22, 'c'), ('TESTS', cols['tests'] + 22, 'c'),
             ('OWNED', cols['owned'] + 22, 'c')]
    return scenes, lines, pane, heads


def hygiene_scenes():
    n = max(len(CAT[p]['teams']) for p in PLATFORMS)
    row = 31
    pane = (SW, n * row)
    scenes = {}
    for plat in PLATFORMS:
        rects, texts = [], []
        for i, (t, h, _n, _d, _tc) in enumerate(CAT[plat]['teams']):
            y0 = i * row + row - 9
            rects += [(0, y0, SW, y0 + 4, 'Track'), (0, y0, max(2, SW * h), y0 + 4, BAND(h))]
            texts += [('Name', t, _left(0, t), i * row + 9), ('Value', f'{h * 100:.0f}%', _right(SW, f'{h * 100:.0f}%', lambda s: W8(s, True)), i * row + 9)]
        scenes[plat] = (rects, texts)
    return scenes, pane


def maturity_scenes():
    pane = (SW, 22)
    scenes = {}
    for plat in PLATFORMS:
        mat = CAT[plat]['mat']
        total = sum(mat.values()) or 1
        rects, texts, x = [], [], 0
        for k, ck in (('high', 'High'), ('medium', 'Medium'), ('low', 'Low')):
            w = SW * mat.get(k, 0) / total
            if w:
                rects.append((x + 1, 1, x + w - 1, 21, ck))
                s = f'{k.title()} {mat.get(k, 0)}'
                texts.append((ck, s, x + w / 2, 11))
            x += w
        scenes[plat] = (rects, texts)
    return scenes, pane


def gap_scenes():
    """Every gap in each section (GB, v44); the pane is as tall as the longest platform's list and scrolls."""
    sec_h, item = 20, 15
    scenes, height = {}, 0
    for plat in PLATFORMS:
        rects, texts, y = [], [], 0
        for key, title, dot in (('owner', 'NO OWNER', 'Crit'), ('tests', 'NO TESTS', 'Warn'), ('desc', 'NO DESCRIPTION', 'Warn')):
            items = CAT[plat]['gaps'][key]
            texts.append(('Head', title, _left(0, title, lambda s: W7(s, True)), y + 9))
            rects.append((0, y + 17, GW, y + 18, 'Line'))
            y += sec_h
            if not items:
                texts.append(('More', 'None', _left(0, 'None'), y + item / 2))
                y += item
            for name in items:
                nm = _fit(name, GW - 20, 8)
                texts += [(dot, '●', 5, y + item / 2), ('Item', nm, _left(16, nm), y + item / 2)]
                y += item
            y += 4
        scenes[plat] = (rects, texts)
        height = max(height, y)
    return scenes, (GW, height)


DOMAIN_SCENES, DOMAIN_LINES, DOMAIN_PANE, DOMAIN_HEADS = domain_scenes()
HYGIENE_SCENES, HYGIENE_PANE = hygiene_scenes()
MATURITY_SCENES, MATURITY_PANE = maturity_scenes()
GAP_SCENES, GAP_PANE = gap_scenes()


# ================================================================ unregistered table and sprawl list

def _ucols():
    """Column positions: each column as wide as its widest cell or title, the spare width shared out between them so
    the last column ends at the card's right edge (GB, v44). Left columns get their left edge, right ones their right."""
    rows = [x for v in UNREG.values() for x in v]
    head = lambda h: W7(h, True)
    cols = [('p', 'l', max(head('PRINCIPAL'), max(W8(r['p'], True) for r in rows))),
            ('kind', 'l', max(head('KIND'), max(W8(r['kind']) for r in rows))),
            ('reads', 'l', max(head('READS'), max(W8(n + ',') for r in rows for n in r['reads']),
                               max((W8(r['reads'][1] + f' +{len(r["reads"]) - 2}') for r in rows if len(r['reads']) > 2), default=0))),
            ('q', 'r', max(head('QUERIES'), max(W8(f'{r["q"]:,.0f}') for r in rows))),
            ('gb', 'r', max(head('SCANNED'), max(W8(f'{r["gb"]:,.0f} GB') for r in rows))),
            ('cost', 'r', max(head('COST'), max(W8(f'${r["cost"]:,.0f}') for r in rows))),
            ('first', 'l', max(head('FIRST SEEN'), max(W8(_short(r['first'])) for r in rows))),
            ('likely', 'l', max(head('LIKELY WHAT'), max(W8(r['likely']) for r in rows)))]
    edge = 8
    gap = (UW - 2 * edge - sum(w for _, _, w in cols)) / (len(cols) - 1)
    assert gap >= 14, f'GOV unregistered table: {gap:.0f} px between columns'
    x, at = edge, {}
    for k, a, w in cols:
        at[k] = x if a == 'l' else x + w
        x += w + gap
    return at


UCOL = _ucols()
PRINCIPALS = sorted({r['p'] for v in UNREG.values() for r in v})


def unreg_calcs():
    pane, f = (UW, UNREG_ROW), {}
    rank = {f'{p}|{pl}|{r["p"]}': i + 1 for (p, pl), rs in UNREG.items() for i, r in enumerate(rs)}
    key = f'{COMBO} + "|" + [principal]'
    f['GOV Unregistered Rank'] = _calc('GOV Unregistered Rank', 'Row of an unregistered reader in the period and platform, most queries first (written by the build).',
                                       _case(key, rank, quote=False))
    f['Is GOV Unregistered Row'] = _calc('Is GOV Unregistered Row', 'Rows of the table. Put on Filters (True).', 'NOT ISNULL([GOV Unregistered Rank])')
    cells = collections.defaultdict(dict)
    for (p, pl), rs in UNREG.items():
        for r in rs:
            k = f'{p}|{pl}|{r["p"]}'
            reads = r['reads'][:2]
            l1 = reads[0] + (',' if len(reads) > 1 else '')
            l2 = reads[1] + (f' +{len(r["reads"]) - 2}' if len(r['reads']) > 2 else '') if len(reads) > 1 else None
            two = l2 is not None
            vals = {'Principal': (r['p'], 'l', 'p'), 'Kind': (r['kind'], 'l', 'kind'), 'Reads 1': (l1, 'l', 'reads'), 'Reads 2': (l2, 'l', 'reads'),
                    'Queries': (f'{r["q"]:,.0f}', 'r', 'q'), 'Scanned': (f'{r["gb"]:,.0f} GB', 'r', 'gb'), 'Cost': (f'${r["cost"]:,.0f}', 'r', 'cost'),
                    'First': (_short(r['first']), 'l', 'first'), 'Likely': (r['likely'], 'l', 'likely')}
            for n, (s, a, col) in vals.items():
                if s is None:
                    continue
                y = UNREG_ROW / 2 + (-6 if n == 'Reads 1' and two else 6 if n == 'Reads 2' else 0)
                cx = UCOL[col] + W8(s) / 2 if a == 'l' else UCOL[col] - W8(s) / 2
                cells[n][k] = (s, f'MAKEPOINT({(pane[1] / 2 - y) / 100:.4f}, {(cx - pane[0] / 2) / 100:.4f})')
    for n, d in cells.items():
        f[f'GOV Unreg {n} Text'] = _calc(f'GOV Unreg {n} Text', f'{n} cell (written by the build per period and platform).', _case(key, {k: v[0] for k, v in d.items()}))
        f[f'GOV Unreg {n} Point'] = _calc(f'GOV Unreg {n} Point', f'Where the {n.lower()} cell sits.', _case(key, {k: v[1] for k, v in d.items()}, quote=False))
    # clicks: the inferred data product, with its panel values (the reads are not that product's node)
    exp = {r['p']: r['exp'] for v in UNREG.values() for r in v if r['exp']}
    tags = lambda e: '|' + ('moved|' if NODES[e]['migrated_from_platform'] else '') + ('ai|' if NODES[e]['build_method'] == 'ai_assisted' else '') \
        + ('unregistered|' if NODES[e]['is_declared'] != 'True' else '')
    for n, why, fn, quote in (('Exposure', 'The data product a click opens.', lambda e: e, True),
                              ('Status', 'Its status code (p_panel_status).', lambda e: NODES[e]['current_status_code'], False),
                              ('Type', 'Its type (p_panel_type).', lambda e: NODES[e]['resource_type'], True),
                              ('Platform', 'Its platform (p_panel_platform).', lambda e: NODES[e]['platform_now'], True),
                              ('Tags', 'Its tags (p_panel_tags).', tags, True)):
        f[f'GOV Unreg Click {n}'] = _calc(f'GOV Unreg Click {n}', why, _case('[principal]', {p: fn(e) for p, e in exp.items()}, quote=quote))
    heads = [('PRINCIPAL', UCOL['p'], 'l'), ('KIND', UCOL['kind'], 'l'), ('READS', UCOL['reads'], 'l'), ('QUERIES', UCOL['q'], 'r'),
             ('SCANNED', UCOL['gb'], 'r'), ('COST', UCOL['cost'], 'r'), ('FIRST SEEN', UCOL['first'], 'l'), ('LIKELY WHAT', UCOL['likely'], 'l')]
    f.update(_headings('GOV Unreg', heads, UW))
    t = {n: (SP_MEA if n.endswith('Point') else S_DIM) for n in f}
    t.update({'GOV Unregistered Rank': I_DIM, 'Is GOV Unregistered Row': B_DIM, 'GOV Unreg Click Status': I_DIM})
    return f, t


def _headings(prefix, heads, width):
    hx = {i: (x + W7(h, True) / 2) if a == 'l' else (x - W7(h, True) / 2) if a == 'r' else x for i, (h, x, a) in enumerate(heads)}
    return {f'{prefix} Heading': _calc(f'{prefix} Heading', 'Column titles, one date row each.', _case('[day_index]', {i: h for i, (h, _, _) in enumerate(heads)})),
            f'{prefix} Heading Point': _calc(f'{prefix} Heading Point', 'Middle of a column title (measured by the build).',
                                             f'MAKEPOINT(0, ({_case("[day_index]", {i: f"{v:.1f}" for i, v in hx.items()}, "0", False)} - {width / 2:g}) / 100)')}


def sprawl_calcs():
    pane, f = (SW, SPRAWL_ROW), {}
    NODE = '[node_id (dim_nodes.csv)]'
    member = {f'{pl}|{k}': 'TRUE' for pl in PLATFORMS for k in SPRAWL if _in_plat(NODES[k], pl)}
    f['Is GOV Sprawl Row'] = _calc('Is GOV Sprawl Row', 'AI-assisted dashboards under the platform filter. Put on Filters (True).',
                                   _case(f'[p_platform] + "|" + {NODE}', member, 'FALSE', False))
    f['GOV Sprawl Order'] = _calc('GOV Sprawl Order', 'In catalogue order (the prototype\'s).', _case(NODE, {k: i for i, k in enumerate(SPRAWL)}, quote=False))
    name = {k: _fit(NODES[k]['display_name'], 220, 8, True) for k in SPRAWL}
    meta = {k: _fit(f'{NODES[k]["owner_name"]} · created {_short(dt.date.fromisoformat(NODES[k]["created_date"]))} · maturity {NODES[k]["maturity"]}', SW - 8, 7)
            for k in SPRAWL}
    pk = f'STR([p_period]) + "|" + {NODE}'
    views = {f'{p}|{k}': f'{SPRAWL_VALS[(p, k)][0]:,.0f} views' for p in PERIODS for k in SPRAWL}
    up = {f'{p}|{k}': f'  ▲ {abs(c) * 100:.0f}%' for p in PERIODS for k in SPRAWL for c in [SPRAWL_VALS[(p, k)][1]] if c is not None and c >= 0}
    dn = {f'{p}|{k}': f'  ▼ {abs(c) * 100:.0f}%' for p in PERIODS for k in SPRAWL for c in [SPRAWL_VALS[(p, k)][1]] if c is not None and c < 0}
    f['GOV Sprawl Name Text'] = _calc('GOV Sprawl Name Text', 'Dashboard name, bold.', _case(NODE, name))
    f['GOV Sprawl Meta Text'] = _calc('GOV Sprawl Meta Text', 'Owner, created date and maturity, grey.', _case(NODE, meta))
    f['GOV Sprawl Views Text'] = _calc('GOV Sprawl Views Text', 'Views in the period.', _case(pk, views))
    f['GOV Sprawl Up Text'] = _calc('GOV Sprawl Up Text', 'Rise against the period before, green.', _case(pk, up))
    f['GOV Sprawl Down Text'] = _calc('GOV Sprawl Down Text', 'Fall, red.', _case(pk, dn))
    at = lambda cx, y: f'MAKEPOINT({(pane[1] / 2 - y) / 100:.4f}, {(cx - pane[0] / 2) / 100:.4f})'
    f['GOV Sprawl Name Point'] = _calc('GOV Sprawl Name Point', 'Name, first line, left.', _case(NODE, {k: at(8 + W8(v, True) / 2, 14) for k, v in name.items()}, quote=False))
    f['GOV Sprawl Meta Point'] = _calc('GOV Sprawl Meta Point', 'Meta, second line, left.', _case(NODE, {k: at(8 + W7(v) / 2, 31) for k, v in meta.items()}, quote=False))
    right = {k: at(SW - 4 - (W8(views[k]) + W8(up.get(k, '') or dn.get(k, ''))) / 2, 14) for k in views}
    f['GOV Sprawl Views Point'] = _calc('GOV Sprawl Views Point', 'Views and change, right, first line.', _case(pk, right, quote=False))
    f['GOV Sprawl Divider Point'] = _calc('GOV Sprawl Divider Point', 'Line under each row.', _rounded('[Exposure Path Index]', 0, SW, SPRAWL_ROW - 1, SPRAWL_ROW, 0, pane))
    f['GOV Sprawl Row Point'] = _calc('GOV Sprawl Row Point', 'The row (takes the click).', _rounded('[Exposure Path Index]', 0, SW, 0, SPRAWL_ROW - 1, 0, pane))
    # card subtitle: how many AI dashboards, and how many share one semantic object
    sub = {}
    for pl in PLATFORMS:
        ds = [k for k in SPRAWL if _in_plat(NODES[k], pl)]
        c = collections.Counter(s for (e, s) in SPRAWL_SEM if e in ds)
        top = c.most_common(1)
        sub[pl] = f'{len(ds)} AI-assisted dashboards' + (f', {top[0][1]} of them on {NODES[top[0][0]]["node_name"]}' if top else '')
    f['GOV Sprawl Subtitle'] = _calc('GOV Sprawl Subtitle', 'Card subtitle (written by the build per platform).', _case('[p_platform]', sub))
    t = {n: (SP_MEA if n.endswith('Point') else S_DIM) for n in f}
    t.update({'Is GOV Sprawl Row': B_DIM, 'GOV Sprawl Order': I_DIM})
    return f, t


def kpi_calcs():
    f = {
        'GOV Owned Sub Text': '// GOV Owned Sub Text\n// "4 of 27 exposures have no owner".\nSTR(INT([Exposures Without Owner])) + " of " + STR(INT(SUM(IF [resource_type] = "exposure" THEN 1 END))) + " exposures have no owner"',
        'GOV Doc Sub Text': '// GOV Doc Sub Text\n// "15 models have no description".\nSTR(INT([Models Without Description])) + " models have no description"',
        'GOV Test Sub Text': '// GOV Test Sub Text\n// "14 models have no tests".\nSTR(INT([Models Without Tests])) + " models have no tests"',
    }
    dec = {f'{p}|{pl}': v for (p, pl), v in DECLARED.items()}
    f['GOV Declared Text'] = _calc('GOV Declared Text', 'Declared consumers: readers in query history mapped to a declared exposure (written by the build).',
                                   _case(COMBO, {k: f'{m / n * 100:.0f}%' if n else '-' for k, (m, n) in dec.items()}))
    f['GOV Declared Red Text'] = _calc('GOV Declared Red Text', '"3 readers in query history", red when any.',
                                       _case(COMBO, {k: f'{n - m} reader' + ('' if n - m == 1 else 's') + ' in query history' for k, (m, n) in dec.items() if n - m}))
    f['GOV Declared Plain Text'] = _calc('GOV Declared Plain Text', '"No readers in query history" otherwise.',
                                         _case(COMBO, {k: 'No readers in query history' for k, (m, n) in dec.items() if not n - m}))
    t = {n: S_MEA for n in f}
    return f, t


PACK_TYPES = {'Is Exposure Owned': B_DIM, 'Ownership Coverage': R_MEA, 'Exposures Without Owner': R_MEA, 'Documentation Coverage': R_MEA,
              'Models Without Description': R_MEA, 'Model Test Coverage': R_MEA, 'Models Without Tests': R_MEA}

_f, _t = {}, dict(PACK_TYPES)
for fn in (kpi_calcs, unreg_calcs, sprawl_calcs):
    a, b = fn()
    _f.update(a)
    _t.update(b)
for prefix, scenes, key, pane, styles in (('GOV Domain', DOMAIN_SCENES, '[p_platform]', DOMAIN_PANE, ('Name', 'Good', 'Fair', 'Poor', 'Dash')),
                                          ('GOV Domain Line', DOMAIN_LINES, '[p_platform]', DOMAIN_PANE, ()),
                                          ('GOV Hygiene', HYGIENE_SCENES, '[p_platform]', HYGIENE_PANE, ('Name', 'Value')),
                                          ('GOV Maturity', MATURITY_SCENES, '[p_platform]', MATURITY_PANE, ('High', 'Medium', 'Low')),
                                          ('GOV Gaps', GAP_SCENES, '[p_platform]', GAP_PANE, ('Head', 'Item', 'More', 'Crit', 'Warn'))):
    a, b = _scene_calcs(prefix, scenes, key, pane, styles)
    _f.update(a)
    _t.update(b)
_f.update(_headings('GOV Domain', DOMAIN_HEADS, SW))
_t.update({'GOV Domain Heading': S_DIM, 'GOV Domain Heading Point': SP_MEA})
_f['Is GOV Heading Row'] = '// Is GOV Heading Row\n// One date row per column title. Put on Filters (True).\n[day_index] < 8'
_t['Is GOV Heading Row'] = B_DIM
CALCS.add(formulas=_f, types=_t)


# ================================================================ sheets

def _a(n):
    return R(n, 'attr')


def _words(title, point, runs, pane, lod, inert=True, tooltip=None, cell_valign=None):
    return label_pane(title=title, inert=inert, text=[r['_ref'] for r in runs if '_ref' in r], label=runs, align='center',
                      valign='center', lod=[R(point, 'clct'), *lod], pane_size=pane, tooltip=tooltip, cell_valign=cell_valign)


def _scene_sheet(name, prefix, pane, styles, palette, under=()):
    """A scene on the date table: the rectangles (one colour key) and one text layer per style. under: more rectangle
    sets drawn first, [(prefix, colour)], when one set would need more than the date table's 90 rows."""
    sid, path, di = R(f'{prefix} Rect Id'), R('day_index', kind='ok'), R('day_index')
    color_map(R(f'{prefix} Rect Key'), {f'"{k}"': v for k, v in palette.items()})
    layers = [Pane('Polygon', title=f'Shapes {i + 2}', inert=True, mark_color=colour, path=path, label_show=False,
                   lod=[R(f'{p} Rect Point', 'clct'), R(f'{p} Rect Id')], pane_size=pane) for i, (p, colour) in enumerate(under)]
    layers.append(Pane('Polygon', title='Shapes', inert=True, color=R(f'{prefix} Rect Key'), path=path, label_show=False,
                       lod=[R(f'{prefix} Rect Point', 'clct'), sid], pane_size=pane))
    for style, (size, colour, bold) in styles.items():
        layers.append(_words(style, f'{prefix} {style} Point', [run(_a(f'{prefix} {style} Text'), size, colour, SEMI if bold else 'Arial')], pane, [di]))
    return _grid(Sheet(name, rows=[LAT], cols=[LON], layers=True, no_basemap=True, zoom=None, tooltip=False,
                       panes=[Pane('Automatic', pane_size=pane), *layers]), pane)


def _header_canvas(name, prefix, width):
    hp = (width, HEAD_H)
    return _grid(Sheet(name, rows=[LAT], cols=[LON], filters=[R('Is GOV Heading Row')], layers=True, no_basemap=True, zoom=None, tooltip=False,
                       panes=[Pane('Automatic', pane_size=hp),
                              label_pane(title='Titles', inert=True, text=[_a(f'{prefix} Heading')], label=[run(_a(f'{prefix} Heading'), 7, INK3, SEMI)],
                                         align='center', lod=[R(f'{prefix} Heading Point', 'clct'), R('day_index')], pane_size=hp)]), hp)


def kpi_sheets() -> list[Sheet]:
    node = R('Is Platform Match Node')
    refs = lambda rs: [r['_ref'] for r in rs if '_ref' in r]
    tip = lambda t, d: [run(t, 7, INK3, SEMI), run(NL, 7, INK3), run(d, 9, INK1)]
    own = [run('OWNERSHIP COVERAGE', 8, INK3, SEMI), run(NL, 8, INK3), run(R('Ownership Coverage'), 18, NAVY, SEMI), run(NL, 8, INK3), run(R('GOV Owned Sub Text'), 8, INK3)]
    doc = [run('DOCUMENTATION COVERAGE', 8, INK3, SEMI), run(NL, 8, INK3), run(R('Documentation Coverage'), 18, NAVY, SEMI), run(NL, 8, INK3), run(R('GOV Doc Sub Text'), 8, INK3)]
    tst = [run('TEST COVERAGE', 8, INK3, SEMI), run(NL, 8, INK3), run(R('Model Test Coverage'), 18, NAVY, SEMI), run(NL, 8, INK3), run(R('GOV Test Sub Text'), 8, INK3)]
    dec = [run('DECLARED CONSUMERS', 8, INK3, SEMI), run(NL, 8, INK3), run(_a('GOV Declared Text'), 18, NAVY, SEMI), run(NL, 8, INK3),
           run(_a('GOV Declared Red Text'), 8, CRIT_INK, SEMI), run(_a('GOV Declared Plain Text'), 8, INK3), run(' not registered as exposures', 8, INK3)]
    pct = {R('Ownership Coverage'): 'p0%', R('Documentation Coverage'): 'p0%', R('Model Test Coverage'): 'p0%'}
    return [
        Sheet('GOV Ownership KPI', filters=[node], formats=pct, panes=label_pane(text=refs(own), valign='top', label=own,
              tooltip=tip('OWNERSHIP COVERAGE', 'Data products with a named owner, unregistered ones included.'))),
        Sheet('GOV Documentation KPI', filters=[node], formats=pct, panes=label_pane(text=refs(doc), valign='top', label=doc,
              tooltip=tip('DOCUMENTATION COVERAGE', 'Models with a description in dbt.'))),
        Sheet('GOV Test Coverage KPI', filters=[node], formats=pct, panes=label_pane(text=refs(tst), valign='top', label=tst,
              tooltip=tip('TEST COVERAGE', 'Models with at least one dbt test.'))),
        Sheet('GOV Declared KPI', filters=[R('Is First Date Row')], panes=label_pane(text=refs(dec), valign='top', label=dec,
              tooltip=tip('DECLARED CONSUMERS', 'Readers in warehouse query history that a declared exposure accounts for, in the period.'))),
    ]


def unreg_sheets() -> list[Sheet]:
    key, order, pane = R('principal'), R('GOV Unregistered Rank', kind='ok'), (UW, UNREG_ROW)
    clicks = [R(f'GOV Unreg Click {n}') for n in ('Exposure', 'Status', 'Type', 'Platform', 'Tags')] + [R('Clear Node Value'), R('Clear Node Key Value')]
    tip = [run(_a('GOV Unreg Principal Text'), 9, INK1, SEMI), run(NL, 7, INK3), run('LIKELY   ', 7, INK3, SEMI), run(_a('GOV Unreg Likely Text'), 9, NAVY, SEMI),
           run(NL, 7, INK3), run('CLICK TO OPEN ITS LINEAGE', 7, INK3, SEMI)]
    cell = lambda n, size=8, colour=INK1: _words(n, f'GOV Unreg {n} Point', [run(_a(f'GOV Unreg {n} Text'), size, colour)], pane, [key])
    layers = [_words('Principal', 'GOV Unreg Principal Point', [run(_a('GOV Unreg Principal Text'), 8, INK1, SEMI)], pane, [key, *clicks], inert=False, tooltip=tip),
              cell('Kind', 8, INK2), cell('Reads 1'), cell('Reads 2'), cell('Queries'), cell('Scanned'), cell('Cost'), cell('First', 8, INK2), cell('Likely', 8, INK2)]
    table = _grid(Sheet('GOV Unregistered Consumers Table', rows=[Cross([Nest([order, key]), LAT])], cols=[LON], filters=[R('Is GOV Unregistered Row')],
                        # row lines between the principals (a reader's query history need not start on four straight days)
                        hide=[order, key], layers=True, no_basemap=True, zoom=None, divider='rows',
                        panes=[Pane('Automatic', lod=[key], pane_size=pane), *layers]), pane)
    return [_header_canvas('GOV Unregistered Header', 'GOV Unreg', UW), table]


def sprawl_sheets() -> list[Sheet]:
    key, order, pane = R('node_id (dim_nodes.csv)'), R('GOV Sprawl Order', kind='ok'), (SW, SPRAWL_ROW)
    path = R('Exposure Path Index', kind='ok')
    clicks = [R('Clear Node Value'), R('Clear Node Key Value'), *[R(f) for f, _ in PANEL_WRITES]]
    tip = [run(_a('GOV Sprawl Name Text'), 9, INK1, SEMI), run(NL, 7, INK3), run('CLICK TO OPEN ITS LINEAGE', 7, INK3, SEMI)]
    layers = [Pane('Polygon', title='Row', inert=False, mark_color=CARD, path=path, label_show=False, lod=[R('GOV Sprawl Row Point', 'clct'), key, *clicks],
                   pane_size=pane, tooltip=tip),
              Pane('Polygon', title='Divider', inert=True, mark_color=LINE_SOFT, path=path, label_show=False, lod=[R('GOV Sprawl Divider Point', 'clct'), key], pane_size=pane),
              _words('Name', 'GOV Sprawl Name Point', [run(_a('GOV Sprawl Name Text'), 8, INK1, SEMI)], pane, [key]),
              _words('Meta', 'GOV Sprawl Meta Point', [run(_a('GOV Sprawl Meta Text'), 7, INK3)], pane, [key]),
              _words('Views', 'GOV Sprawl Views Point', [run(_a('GOV Sprawl Views Text'), 8, INK2), run(_a('GOV Sprawl Up Text'), 8, GOOD_INK),
                                                         run(_a('GOV Sprawl Down Text'), 8, CRIT_INK)], pane, [key], cell_valign='bottom')]  # GB, v44
    table = _grid(Sheet('GOV AI Sprawl List', rows=[Cross([Nest([order, key]), LAT])], cols=[LON], filters=[R('Is GOV Sprawl Row')], hide=[order, key],
                        layers=True, no_basemap=True, zoom=None, panes=[Pane('Automatic', lod=[key], pane_size=pane), *layers]), pane)
    sub = Sheet('GOV Sprawl Subtitle', filters=[R('Is First Date Row')], tooltip=False,
                panes=label_pane(text=[_a('GOV Sprawl Subtitle')], valign='top', label=[run('AI-built dashboard sprawl', 10, INK1, SEMI), run(NL, 8, INK3),
                                                                                         run(_a('GOV Sprawl Subtitle'), 8, INK3)]))
    return [sub, table]


def sheets() -> list[Sheet]:
    sem = {'Name': (8, INK1, False), 'Good': (7, GOOD_INK, True), 'Fair': (7, WARN_INK, True), 'Poor': (7, CRIT_INK, True), 'Dash': (8, INK3, False)}
    return (kpi_sheets() + unreg_sheets() + sprawl_sheets() + [
        _header_canvas('GOV Domain Header', 'GOV Domain', SW),
        _scene_sheet('GOV Coverage by Domain Table', 'GOV Domain', DOMAIN_PANE, sem, dict(BAND_TINT), under=[('GOV Domain Line', LINE_SOFT)]),
        _scene_sheet('GOV Hygiene by Team Bar', 'GOV Hygiene', HYGIENE_PANE, {'Name': (8, INK1, False), 'Value': (8, INK1, True)},
                     {'Track': '#eef0ee', **BAND_BAR}),
        _scene_sheet('GOV Maturity Bar', 'GOV Maturity', MATURITY_PANE, {'High': (7, NAVY, True), 'Medium': (7, NAVY, True), 'Low': (7, INK2, True)},
                     {'High': '#d5e4f3', 'Medium': '#e9f1f9', 'Low': '#f1f2f4'}),
        _scene_sheet('GOV Gaps List', 'GOV Gaps', GAP_PANE, {'Head': (7, INK3, True), 'Item': (8, INK1, False), 'More': (8, INK3, False),
                                                            'Crit': (8, CRIT, False), 'Warn': (8, WARN, False)}, {'Line': LINE}),
    ])


# ================================================================ dashboard content (build plan 3.9)

def content() -> Z:
    widths = [318, 317, 318, 317]
    names = [('Ownership', 'GOV Ownership KPI'), ('Documentation', 'GOV Documentation KPI'), ('Test Coverage', 'GOV Test Coverage KPI'),
             ('Declared', 'GOV Declared KPI')]
    kpis = []
    for i, ((n, ws), w) in enumerate(zip(names, widths)):
        margins = {}
        if i > 0:
            margins['left'] = 7
        if i < 3:
            margins['right'] = 7
        kpis.append(card(f'GOV KPI {n} Card', [sheet(ws)], fixed=w, pad=(12, 14, 10, 14), margins=margins))
    info = text([run('Register each one as a dbt exposure with an owner and its own service account, then it shows up in Lineage, '
                     'Blast radius and Usage like everything else.', 8, NAVY)], fixed=40,
                **{'background-color': '#eef4fb', 'border-color': '#cfe0f1', 'border-style': 'solid', 'border-width': '1', 'corner-radius': '8',
                   'padding-left': '12', 'padding-top': '6', 'margin-top': '8'})
    unreg = card('GOV Unregistered Card', fixed=UNREG_CARD, margins={'right': 7}, kids=[
        Z('horz', friendly='GOV Unregistered Header', fixed=58, kids=[
            card_header('Unregistered consumers found in query history', 'These read warehouse data in this period but no exposure accounts for them. '
                        'Nobody is told when their data breaks, and their cost has no owner.', None),
            # the prototype's tag: a small chip at the top right, not the full header height
            Z('vert', friendly='GOV Source Tag Holder', fixed=150, kids=[
                text([run('From warehouse query history', 7, INK2)], fixed=20,
                     **{'background-color': '#f5f5f3', 'border-color': LINE, 'border-style': 'solid', 'border-width': '1',
                        'corner-radius': '4', 'padding-left': '6', 'padding-top': '2'}),
                blank()])]),
        sheet('GOV Unregistered Header', HEAD_H), blank(1, LINE), sheet('GOV Unregistered Consumers Table'), info])
    warn = text([run('They read the same semantic object as ', 8, WARN_INK), run('Executive Revenue Dashboard', 8, WARN_INK, SEMI),
                 run('. Merge them into one governed view before the numbers drift.', 8, WARN_INK)], fixed=48,
                **{'background-color': WARN_TINT, 'border-color': '#f3ddb4', 'border-style': 'solid', 'border-width': '1', 'corner-radius': '8',
                   'padding-left': '10', 'padding-right': '10', 'padding-top': '6', 'margin-top': '6'})
    sprawl = card('GOV Sprawl Card', margins={'left': 7}, kids=[sheet('GOV Sprawl Subtitle', 44), sheet('GOV AI Sprawl List'), warn])
    domain = card('GOV Domain Card', fixed=SIDE, margins={'right': 7}, kids=[
        card_header('Coverage by domain', 'Green from 90%, amber from 70%'), sheet('GOV Domain Header', HEAD_H), blank(1, LINE),
        sheet('GOV Coverage by Domain Table')])
    hygiene = card('GOV Hygiene Card', fixed=SIDE, margins={'left': 7, 'right': 7}, kids=[
        card_header('Hygiene score by team', 'Average of documentation and test coverage for the sources and models each team owns', 58),
        sheet('GOV Hygiene by Team Bar'), text([run('EXPOSURE MATURITY', 7, INK3, SEMI)], fixed=24, **{'padding-top': '6'}),
        sheet('GOV Maturity Bar', 26)])
    # the gaps list scrolls (GB, v44): its width leaves room for the scroll bar, its height is free
    gaps = card('GOV Gaps Card', margins={'left': 7}, kids=[card_header('Gaps to close', 'The quickest wins for the next sprint'), sheet('GOV Gaps List')])
    return Z('vert', friendly='GOV Content', style=CONTENT_PAD, kids=[
        Z('horz', friendly='GOV KPI Row', fixed=KPI_H, kids=kpis),
        Z('horz', friendly='GOV Middle Row', fixed=MID_H, style={'margin-top': '14'}, kids=[unreg, sprawl]),
        # the last row is flexible, so it always reaches the bottom padding (skill: sizing)
        Z('horz', friendly='GOV Bottom Row', style={'margin-top': '14'}, kids=[domain, hygiene, gaps])])


def check_fit(zones) -> None:
    by = {(z.name or z.friendly): z.rect for z in zones}
    n_unreg = max(len(v) for v in UNREG.values())
    n_sprawl = max(sum(1 for k in SPRAWL if _in_plat(NODES[k], pl)) for pl in PLATFORMS)
    for name, (w, h) in (('GOV Unregistered Consumers Table', (UW, UNREG_ROW * n_unreg)), ('GOV AI Sprawl List', (SW, SPRAWL_ROW * n_sprawl)),
                         ('GOV Coverage by Domain Table', DOMAIN_PANE), ('GOV Hygiene by Team Bar', HYGIENE_PANE),
                         ('GOV Maturity Bar', MATURITY_PANE), ('GOV Gaps List', (GAP_PANE[0] + 18, 0))):
        _, _, zw, zh = by[name]
        assert w <= zw and h <= zh, f'{name}: needs {w} x {h}, zone is {zw:.0f} x {zh:.0f}'
    _, y, _, h = by['GOV Bottom Row']
    end = 1000 - int(CONTENT_PAD['padding-bottom'])
    assert abs(y + h - end) < 0.5, f'GOV rows end at {y + h:.0f}, content ends at {end}'


_EXP = [('p_selected_exposure', 'Exposure'), ('p_panel_status', 'Status'), ('p_panel_type', 'Type'), ('p_panel_platform', 'Platform'), ('p_panel_tags', 'Tags')]
ACTIONS = [  # (sheet, source Ref factory, parameter, caption)
    *[('GOV Unregistered Consumers Table', (lambda n=n: R(f'GOV Unreg Click {n}')), param, f'GOV Unreg Set {param}') for param, n in _EXP],
    ('GOV Unregistered Consumers Table', lambda: R('Clear Node Value'), 'p_selected_node', 'GOV Unreg Clear Node'),
    ('GOV Unregistered Consumers Table', lambda: R('Clear Node Key Value'), 'p_selected_node_key', 'GOV Unreg Clear Node Key'),
    ('GOV AI Sprawl List', lambda: R('node_id (dim_nodes.csv)'), 'p_selected_exposure', 'GOV Sprawl Select Exposure'),
    ('GOV AI Sprawl List', lambda: R('Clear Node Value'), 'p_selected_node', 'GOV Sprawl Clear Node'),
    ('GOV AI Sprawl List', lambda: R('Clear Node Key Value'), 'p_selected_node_key', 'GOV Sprawl Clear Node Key'),
    *[('GOV AI Sprawl List', (lambda f=f: R(f)), param, f'GOV Sprawl Set {param}') for f, param in PANEL_WRITES],
]
NAV_ACTIONS = [(ws, 'Lineage explorer', f'Go to Lineage from {ws}') for ws in ('GOV Unregistered Consumers Table', 'GOV AI Sprawl List')]
DEHIGHLIGHT = ['GOV Unregistered Consumers Table', 'GOV AI Sprawl List']
